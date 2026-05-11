from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db import (
    get_cloth_item, delete_cloth_item, increment_wear_count,
    save_care_guide, get_care_guide
)

router = APIRouter(prefix='/items', tags=['Items'])


class CareGuideCreate(BaseModel):
    washing_inst: str = None
    drying_inst: str = None
    iron_inst: str = None
    dry_clean_only: bool = False
    texture: str = None


@router.get('/{item_id}')
def fetch_item(item_id: int):
    """Get item with image + care guide."""
    item = get_cloth_item(item_id)
    if not item:
        raise HTTPException(404, 'Item not found')
    item.pop('embedding', None)
    care = get_care_guide(item_id)
    return {**item, 'care_guide': care}


@router.delete('/{item_id}')
def remove_item(item_id: int):
    """Delete item and its PNG file."""
    if not delete_cloth_item(item_id):
        raise HTTPException(404, 'Item not found')
    return {'message': 'Item deleted', 'item_id': item_id}


@router.post('/{item_id}/wear')
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
        'message': 'Wear logged',
        'item_id': item_id,
        'wear_count': item['wear_count'] + 1,
    }


@router.post('/{item_id}/care')
def add_care_guide(item_id: int, body: CareGuideCreate):
    """Add care instructions for a clothing item."""
    if not get_cloth_item(item_id):
        raise HTTPException(404, 'Item not found')
    return save_care_guide(item_id, body.dict())


@router.get('/{item_id}/care')
def fetch_care_guide(item_id: int):
    """Get care guide for a clothing item."""
    care = get_care_guide(item_id)
    if not care:
        raise HTTPException(404, 'No care guide for this item')
    return care
