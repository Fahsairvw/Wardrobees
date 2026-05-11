import psycopg2.extras
import uuid
from pathlib import Path
from .connection import get_conn, STORAGE_DIR, BASE_DIR


def save_cloth_item(item: dict, wardrobe_id: int) -> dict:
    """
    Save one detected clothing item to cloth_item table.
    Also saves the PNG to image table.

    Args:
        item:        dict from detector.detect_and_remove_bg()
        wardrobe_id: which wardrobe to add to

    Returns:
        Saved cloth_item row dict (without embedding)
    """
    # Save PNG file
    item_uuid = str(uuid.uuid4())
    filename = f'{item_uuid}.png'
    image_path = STORAGE_DIR / filename
    image_url = f'/storage/images/{filename}'

    with open(image_path, 'wb') as f:
        f.write(item['img_bytes'])

    # Build embedding string for pgvector
    embedding_str = '[' + ','.join(map(str, item['embedding'])) + ']'

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            # Insert cloth_item
            cur.execute('''
                INSERT INTO cloth_item
                    (name, category, color, texture, embedding, wardrobe_id)
                VALUES (%s, %s, %s, %s, %s::vector, %s)
                RETURNING item_id, name, category, color, texture,
                          wear_count, date_add, wardrobe_id
            ''', (
                item['cat_name'],            # name = category name for now
                item['cat_name'],            # category
                item.get('color'),           # color (None for now, add later)
                item.get('texture'),         # texture (None for now)
                embedding_str,
                wardrobe_id,
            ))
            cloth_row = dict(cur.fetchone())
            item_id = cloth_row['item_id']

            # Insert image record linked to cloth_item
            cur.execute('''
                INSERT INTO image
                    (mask_url, width, height,
                     upload_status, segment_status, item_id)
                VALUES (%s, %s, %s, 'done', 'done', %s)
                RETURNING image_id, mask_url, width, height
            ''', (
                image_url,
                int(item['width']),
                int(item['height']),
                item_id,
            ))
            image_row = dict(cur.fetchone())

        conn.commit()

    print(f'  Saved: {item["cat_name"]} → {filename}')

    return {
        **cloth_row,
        'imageUrl': image_url,
        'image_id': image_row['image_id'],
        'confidence': float(item['confidence']),
        'partial': bool(item.get('partial', False)),
        'warning': item.get('warning'),
    }


def get_wardrobe_items(wardrobe_id: int) -> list[dict]:
    """Get all cloth items in a wardrobe with their images."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('''
                SELECT
                    ci.item_id, ci.name, ci.category, ci.color,
                    ci.texture, ci.wear_count, ci.date_add,
                    ci.wardrobe_id,
                    i.image_id, i.mask_url AS image_url,
                    i.width, i.height
                FROM cloth_item ci
                LEFT JOIN image i ON i.item_id = ci.item_id
                WHERE ci.wardrobe_id = %s
                ORDER BY ci.date_add DESC
            ''', (wardrobe_id,))
            rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_cloth_item(item_id: int) -> dict | None:
    """Get single cloth item with image."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('''
                SELECT
                    ci.*, i.mask_url AS image_url,
                    i.width, i.height, i.image_id
                FROM cloth_item ci
                LEFT JOIN image i ON i.item_id = ci.item_id
                WHERE ci.item_id = %s
            ''', (item_id,))
            row = cur.fetchone()
    return dict(row) if row else None


def increment_wear_count(item_id: int) -> bool:
    """Increment wear count when user logs wearing an item."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                UPDATE cloth_item
                SET wear_count = wear_count + 1
                WHERE item_id = %s
            ''', (item_id,))
        conn.commit()
    return True


def delete_cloth_item(item_id: int) -> bool:
    """Delete item and its image file."""
    item = get_cloth_item(item_id)
    if not item:
        return False

    # Delete PNG file
    if item.get('image_url'):
        img_path = BASE_DIR / item['image_url'].lstrip('/')
        if img_path.exists():
            img_path.unlink()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM cloth_item WHERE item_id = %s', (item_id,))
        conn.commit()
    return True
