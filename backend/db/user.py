import psycopg2.extras
from .connection import get_conn


def create_user(name: str, email: str, role: str = 'user') -> dict:
    """Create a new user. Returns user dict."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('''
                INSERT INTO "user" (name, email, user_role)
                VALUES (%s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name
                RETURNING user_id, name, email, user_role, created_at
            ''', (name, email, role))
            conn.commit()
            return dict(cur.fetchone())


def get_user(user_id: int) -> dict | None:
    """Get user by ID."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM "user" WHERE user_id = %s', (user_id,))
            row = cur.fetchone()
    return dict(row) if row else None


def get_user_by_email(email: str) -> dict | None:
    """Get user by email."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM "user" WHERE email = %s', (email,))
            row = cur.fetchone()
    return dict(row) if row else None
