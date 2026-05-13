# Detector module - exports all functions for backward compatibility

from .config import CAT_NAMES, CAT_GROUPS, CONF_THRESHOLD, MIN_SIZE, BORDER_MARGIN, get_group
from .models import yolo_model, resnet, transform
from .embedding import get_embedding
from .mask import isolate_with_mask
from .detection import detect_and_remove_bg

__all__ = [
    'CAT_NAMES',
    'CAT_GROUPS',
    'CONF_THRESHOLD',
    'MIN_SIZE',
    'BORDER_MARGIN',
    'get_group',
    'yolo_model',
    'resnet',
    'transform',
    'get_embedding',
    'isolate_with_mask',
    'detect_and_remove_bg',
]
