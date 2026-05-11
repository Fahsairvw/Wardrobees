from fastapi import APIRouter, File, UploadFile, HTTPException
from db import get_user, get_or_create_wardrobe, save_cloth_item
from detector import detect_and_remove_bg

router = APIRouter(tags=['Detect & Upload'])


@router.post('/detect/{user_id}')
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

    saved = [save_cloth_item(item, wardrobe['wardrobe_id']) for item in detected if item.get('confidence', 0) > 0.6]

    return {
        'message': f'{len(saved)} item(s) added to wardrobe',
        'wardrobe_id': wardrobe['wardrobe_id'],
        'items': saved,
    }
