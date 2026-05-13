# Database module - exports all functions for backward compatibility

from .init import init_db
from .user import create_user, get_user, get_user_by_email
from .wardrobe import get_or_create_wardrobe
from .cloth_item import (
    save_cloth_item, get_wardrobe_items, get_cloth_item,
    increment_wear_count, delete_cloth_item
)
from .care_guide import save_care_guide, get_care_guide
from .feedback import save_feedback, get_all_feedback
from .search import find_similar
from .stats import get_stats

__all__ = [
    'init_db',
    'create_user', 'get_user', 'get_user_by_email',
    'get_or_create_wardrobe',
    'save_cloth_item', 'get_wardrobe_items', 'get_cloth_item',
    'increment_wear_count', 'delete_cloth_item',
    'save_care_guide', 'get_care_guide',
    'save_feedback', 'get_all_feedback',
    'find_similar',
    'get_stats',
]
