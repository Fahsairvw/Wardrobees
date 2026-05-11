from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
import numpy as np
import cv2

from detector import detect_and_remove_bg, yolo_model, CAT_NAMES, CONF_THRESHOLD
from db import (
    init_db,
    create_user, get_user, get_user_by_email,
    get_or_create_wardrobe, get_wardrobe_items,
    save_cloth_item, get_cloth_item,
    increment_wear_count, delete_cloth_item,
    save_care_guide, get_care_guide,
    save_feedback, get_all_feedback,
    find_similar, get_stats,
)

# App setup
app = FastAPI(
    title       = 'Wardrobees API',
    description = 'Digital wardrobe',
    version     = '1.0.0',
)

@app.on_event('startup')
async def startup_event():
    init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

storage_path = Path(__file__).parent / 'storage'
storage_path.mkdir(exist_ok=True)
app.mount('/storage', StaticFiles(directory=str(storage_path)), name='storage')


# Pydantic models
class UserCreate(BaseModel):
    name:      str
    email:     str
    user_role: Optional[str] = 'user'

class CareGuideCreate(BaseModel):
    washing_inst:   Optional[str] = None
    drying_inst:    Optional[str] = None
    iron_inst:      Optional[str] = None
    dry_clean_only: Optional[bool] = False
    texture:        Optional[str] = None

class FeedbackCreate(BaseModel):
    user_id: int
    comment: str


# Health
@app.get('/')
def root():
    return {'status': 'API running'}


# User
@app.post('/users')
def register_user(body: UserCreate):
    """
    Create or update a user.
    Auto-creates a wardrobe for new users.
    """
    user     = create_user(body.name, body.email, body.user_role)
    wardrobe = get_or_create_wardrobe(user['user_id'])
    return {'user': user, 'wardrobe': wardrobe}

@app.get('/users/{user_id}')
def fetch_user(user_id: int):
    user = get_user(user_id)
    if not user:
        raise HTTPException(404, 'User not found')
    return user


# Wardrobe
@app.get('/wardrobe/{user_id}')
def get_wardrobe(user_id: int):
    """
    Get wardrobe + all items grouped by category.
    Main screen data for the app.
    """
    user = get_user(user_id)
    if not user:
        raise HTTPException(404, 'User not found')

    wardrobe = get_or_create_wardrobe(user_id)
    items    = get_wardrobe_items(wardrobe['wardrobe_id'])

    grouped = {}
    for item in items:
        cat = item.get('category', 'other')
        grouped.setdefault(cat, []).append(item)

    return {
        'wardrobe_id': wardrobe['wardrobe_id'],
        'user_id':     user_id,
        'total':       len(items),
        'grouped':     grouped,
        'items':       items,
    }

@app.get('/wardrobe/{user_id}/stats')
def wardrobe_stats(user_id: int):
    """Stats for a user's wardrobe — used on home screen."""
    user = get_user(user_id)
    if not user:
        raise HTTPException(404, 'User not found')
    wardrobe = get_or_create_wardrobe(user_id)
    return get_stats(wardrobe['wardrobe_id'])


# Detect & save clothing items
@app.post('/detect/{user_id}')
async def detect(user_id: int, file: UploadFile = File(...)):
    """
    Main upload endpoint.
    Flow:
        1. Get/create user wardrobe
        2. YOLO detects clothing items
        3. Mask bg + extract embedding per item
        4. Save to cloth_item + image tables
        5. Return saved items
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(400, 'File must be an image')

    user = get_user(user_id)
    if not user:
        raise HTTPException(404, 'User not found — register first via POST /users')

    wardrobe = get_or_create_wardrobe(user_id)
    detected = detect_and_remove_bg(await file.read())

    if not detected:
        raise HTTPException(
            404,
            'No clothing items detected. Try a clearer photo with better lighting.'
        )

    saved = [save_cloth_item(item, wardrobe['wardrobe_id']) for item in detected]

    return {
        'message':     f'{len(saved)} item(s) added to wardrobe',
        'wardrobe_id': wardrobe['wardrobe_id'],
        'items':       saved,
    }


# Items
@app.get('/items/{item_id}')
def fetch_item(item_id: int):
    """Get item with image + care guide."""
    item = get_cloth_item(item_id)
    if not item:
        raise HTTPException(404, 'Item not found')
    item.pop('embedding', None)
    care = get_care_guide(item_id)
    return {**item, 'care_guide': care}

@app.delete('/items/{item_id}')
def remove_item(item_id: int):
    """Delete item and its PNG file."""
    if not delete_cloth_item(item_id):
        raise HTTPException(404, 'Item not found')
    return {'message': 'Item deleted', 'item_id': item_id}

@app.post('/items/{item_id}/wear')
def log_wear(item_id: int):
    """
    Increment wear_count.
    Call when user marks an outfit as worn today.
    """
    item = get_cloth_item(item_id)
    if not item:
        raise HTTPException(404, 'Item not found')
    increment_wear_count(item_id)
    return {
        'message':    'Wear logged',
        'item_id':    item_id,
        'wear_count': item['wear_count'] + 1,
    }


# Care guide
@app.post('/items/{item_id}/care')
def add_care_guide(item_id: int, body: CareGuideCreate):
    """Add care instructions for a clothing item."""
    if not get_cloth_item(item_id):
        raise HTTPException(404, 'Item not found')
    return save_care_guide(item_id, body.dict())

@app.get('/items/{item_id}/care')
def fetch_care_guide(item_id: int):
    """Get care guide for a clothing item."""
    care = get_care_guide(item_id)
    if not care:
        raise HTTPException(404, 'No care guide for this item')
    return care


# Similarity search
@app.post('/similar/{user_id}')
async def similar(
    user_id: int,
    file: UploadFile = File(...),
    top_k: int = 5,
):
    """
    Find similar items in user's wardrobe.
    Upload a photo → get top_k visually similar items back.
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(400, 'File must be an image')

    user = get_user(user_id)
    if not user:
        raise HTTPException(404, 'User not found')

    detected = detect_and_remove_bg(await file.read())
    if not detected:
        raise HTTPException(404, 'No clothing item detected')

    wardrobe = get_or_create_wardrobe(user_id)
    query    = detected[0]

    results = find_similar(
        query_embedding = query['embedding'],
        wardrobe_id     = wardrobe['wardrobe_id'],
        top_k           = top_k,
        filter_category = query['cat_name'],
    )

    return {
        'query_category': query['cat_name'],
        'similar_items':  results,
    }


# Feedback
@app.post('/feedback')
def submit_feedback(body: FeedbackCreate):
    """Submit feedback from user."""
    if not get_user(body.user_id):
        raise HTTPException(404, 'User not found')
    return save_feedback(body.user_id, body.comment)

@app.get('/feedback')
def list_feedback(approved_only: bool = False):
    """List all feedback (admin)."""
    return get_all_feedback(approved_only)


# Debug
@app.post('/debug')
async def debug(file: UploadFile = File(...)):
    """Raw YOLO output — no saving, just detection check."""
    if not file.content_type.startswith('image/'):
        raise HTTPException(400, 'File must be an image')

    nparr  = np.frombuffer(await file.read(), np.uint8)
    img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_cv is None:
        raise HTTPException(400, 'Could not decode image')

    img_rgb    = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    H, W       = img_rgb.shape[:2]
    results    = yolo_model(img_rgb, conf=CONF_THRESHOLD)[0]
    detections = []

    if results.boxes:
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            detections.append({
                'category':   CAT_NAMES[int(box.cls[0])],
                'confidence': round(float(box.conf[0]), 3),
                'bbox':       [x1, y1, x2, y2],
                'bbox_size':  f'{x2-x1}x{y2-y1}px',
            })

    return {
        'image_shape':    f'{W}x{H}',
        'conf_threshold': CONF_THRESHOLD,
        'n_detected':     len(detections),
        'detections':     detections,
    }
