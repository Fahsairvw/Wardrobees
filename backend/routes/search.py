from fastapi import APIRouter, File, UploadFile, HTTPException
from db import get_user, get_or_create_wardrobe, find_similar
from detector import detect_and_remove_bg

router = APIRouter(tags=['Search'])


@router.post('/similar/{user_id}')
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
    query = detected[0]

    results = find_similar(
        query_embedding=query['embedding'],
        wardrobe_id=wardrobe['wardrobe_id'],
        top_k=top_k,
        filter_category=query['cat_name'],
    )

    return {
        'query_category': query['cat_name'],
        'similar_items': results,
    }
