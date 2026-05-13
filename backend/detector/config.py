# Category and configuration constants

CAT_NAMES = [
    'short sleeve top',
    'long sleeve top',
    'short sleeve outwear',
    'long sleeve outwear',
    'vest',
    'sling',
    'shorts',
    'trousers',
    'skirt',
    'short sleeve dress',
    'long sleeve dress',
    'vest dress',
    'sling dress',
]

CAT_GROUPS = {
    'tops':    [0, 1, 2, 3, 4, 5],
    'bottoms': [6, 7, 8],
    'dresses': [9, 10, 11, 12],
}

# Detection config
CONF_THRESHOLD = 0.25
MIN_SIZE = 80
BORDER_MARGIN = 15


def get_group(cat_id: int) -> str:
    """Get the group name for a clothing category ID."""
    for group, ids in CAT_GROUPS.items():
        if cat_id in ids:
            return group
    return 'other'
