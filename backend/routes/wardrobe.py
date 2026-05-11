from fastapi import APIRouter, HTTPException
from db import get_user, get_or_create_wardrobe, get_wardrobe_items, get_stats

router = APIRouter(prefix='/wardrobe', tags=['Wardrobe'])


@router.get('/{user_id}')
def get_wardrobe(user_id: int):
    """
    Get wardrobe + all items grouped by category.
    Main screen data for the app.
    """
    user = get_user(user_id)
    if not user:
        raise HTTPException(404, 'User not found')

    wardrobe = get_or_create_wardrobe(user_id)
    items = get_wardrobe_items(wardrobe['wardrobe_id'])

    grouped = {}
    for item in items:
        cat = item.get('category', 'other')
        grouped.setdefault(cat, []).append(item)

    return {
        'wardrobe_id': wardrobe['wardrobe_id'],
        'user_id': user_id,
        'total': len(items),
        'grouped': grouped,
        'items': items,
    }


@router.get('/{user_id}/stats')
def wardrobe_stats(user_id: int):
    """Stats for a user's wardrobe — used on home screen."""
    user = get_user(user_id)
    if not user:
        raise HTTPException(404, 'User not found')
    wardrobe = get_or_create_wardrobe(user_id)
    return get_stats(wardrobe['wardrobe_id'])
