import psycopg2.extras
from .connection import get_conn


def save_feedback(user_id: int, comment: str) -> dict:
    """Save user feedback."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('''
                INSERT INTO feedback (comment, user_id)
                VALUES (%s, %s)
                RETURNING *
            ''', (comment, user_id))
            conn.commit()
            return dict(cur.fetchone())


def get_all_feedback(approved_only: bool = False) -> list[dict]:
    """Get all feedback (admin use)."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if approved_only:
                cur.execute('SELECT * FROM feedback WHERE approve = TRUE ORDER BY create_at DESC')
            else:
                cur.execute('SELECT * FROM feedback ORDER BY create_at DESC')
            rows = cur.fetchall()
    return [dict(r) for r in rows]
