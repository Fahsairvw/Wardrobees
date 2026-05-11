import psycopg2.extras
from .connection import get_conn


def get_or_create_wardrobe(user_id: int) -> dict:
    """
    Get existing wardrobe for user or create one.
    Each user has one wardrobe in this version.
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Check existing
            cur.execute(
                'SELECT * FROM wardrobe WHERE user_id = %s LIMIT 1',
                (user_id,)
            )
            row = cur.fetchone()
            if row:
                return dict(row)
            # Create new
            cur.execute('''
                INSERT INTO wardrobe (user_id)
                VALUES (%s)
                RETURNING wardrobe_id, user_id, created_at
            ''', (user_id,))
            conn.commit()
            return dict(cur.fetchone())
