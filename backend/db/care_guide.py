import psycopg2.extras
from .connection import get_conn


def save_care_guide(item_id: int, care: dict) -> dict:
    """Save care instructions for a clothing item."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('''
                INSERT INTO care_guide
                    (washing_inst, drying_inst, iron_inst,
                     dry_clean_only, texture, item_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            ''', (
                care.get('washing_inst'),
                care.get('drying_inst'),
                care.get('iron_inst'),
                care.get('dry_clean_only', False),
                care.get('texture'),
                item_id,
            ))
            conn.commit()
            return dict(cur.fetchone())


def get_care_guide(item_id: int) -> dict | None:
    """Get care guide for an item."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                'SELECT * FROM care_guide WHERE item_id = %s', (item_id,)
            )
            row = cur.fetchone()
    return dict(row) if row else None
