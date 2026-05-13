import psycopg2.extras
from .connection import get_conn


def get_stats(wardrobe_id: int = None) -> dict:
    """Wardrobe statistics."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            if wardrobe_id:
                cur.execute(
                    'SELECT COUNT(*) AS total FROM cloth_item WHERE wardrobe_id = %s',
                    (wardrobe_id,)
                )
            else:
                cur.execute('SELECT COUNT(*) AS total FROM cloth_item')
            total = cur.fetchone()['total']

            cur.execute('''
                SELECT category, COUNT(*) AS count
                FROM cloth_item
                WHERE (%s::integer IS NULL OR wardrobe_id = %s)
                GROUP BY category
                ORDER BY count DESC
            ''', (wardrobe_id, wardrobe_id))
            by_category = [dict(r) for r in cur.fetchall()]

    return {
        'total': total,
        'by_category': by_category,
    }
