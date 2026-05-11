import psycopg2
import psycopg2.extras
import os
import time
from pathlib import Path
from dotenv import load_dotenv


# Load .env from parent folder
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

DB_CONFIG = {
    'host':     os.getenv('DB_HOST'),
    'port':     int(os.getenv('DB_PORT', 5432)),
    'dbname':   os.getenv('DB_NAME'),
    'user':     os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
}

BASE_DIR    = Path(__file__).parent
STORAGE_DIR = BASE_DIR / 'storage' / 'images'
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


# Connection
def get_conn():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    return conn


# Init DB
def init_db(retry_count=5, retry_delay=2):
    """Create all tables following ERD. Safe to run multiple times."""
    for attempt in range(retry_count):
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:

                    cur.execute('CREATE EXTENSION IF NOT EXISTS vector;')

                    # User
                    cur.execute('''
                        CREATE TABLE IF NOT EXISTS "user" (
                            user_id    SERIAL       PRIMARY KEY,
                            name       VARCHAR(100) NOT NULL,
                            email      VARCHAR(255) NOT NULL UNIQUE,
                            user_role  VARCHAR(50)  NOT NULL DEFAULT 'user',
                            created_at TIMESTAMP    DEFAULT NOW()
                        );
                    ''')

                    # Wardrobe
                    cur.execute('''
                        CREATE TABLE IF NOT EXISTS wardrobe (
                            wardrobe_id SERIAL    PRIMARY KEY,
                            user_id     INTEGER   NOT NULL
                                REFERENCES "user"(user_id) ON DELETE CASCADE,
                            created_at  TIMESTAMP DEFAULT NOW()
                        );
                    ''')

                    # ClothItem
                    cur.execute('''
                        CREATE TABLE IF NOT EXISTS cloth_item (
                            item_id     SERIAL       PRIMARY KEY,
                            name        VARCHAR(255),
                            category    VARCHAR(100) NOT NULL,
                            color       VARCHAR(50),
                            texture     VARCHAR(100),
                            wear_count  INTEGER      DEFAULT 0,
                            date_add    TIMESTAMP    DEFAULT NOW(),
                            embedding   vector(2048),
                            wardrobe_id INTEGER      NOT NULL
                                REFERENCES wardrobe(wardrobe_id) ON DELETE CASCADE
                        );
                    ''')

                    # Image
                    cur.execute('''
                        CREATE TABLE IF NOT EXISTS image (
                            image_id       SERIAL      PRIMARY KEY,
                            mask_url       TEXT        NOT NULL,
                            width          FLOAT,
                            height         FLOAT,
                            upload_status  VARCHAR(50) DEFAULT 'done',
                            segment_status VARCHAR(50) DEFAULT 'done',
                            user_id        VARCHAR(255),
                            item_id        INTEGER
                                REFERENCES cloth_item(item_id) ON DELETE SET NULL
                        );
                    ''')

                    # CareGuide
                    cur.execute('''
                        CREATE TABLE IF NOT EXISTS care_guide (
                            care_id        SERIAL       PRIMARY KEY,
                            washing_inst   TEXT,
                            drying_inst    TEXT,
                            iron_inst      TEXT,
                            dry_clean_only BOOLEAN      DEFAULT FALSE,
                            texture        VARCHAR(100),
                            item_id        INTEGER      NOT NULL
                                REFERENCES cloth_item(item_id) ON DELETE CASCADE
                        );
                    ''')

                    # Feedback
                    cur.execute('''
                        CREATE TABLE IF NOT EXISTS feedback (
                            feedback_id SERIAL    PRIMARY KEY,
                            comment     TEXT      NOT NULL,
                            approve     BOOLEAN   DEFAULT FALSE,
                            create_at   TIMESTAMP DEFAULT NOW(),
                            user_id     INTEGER
                                REFERENCES "user"(user_id) ON DELETE SET NULL
                        );
                    ''')

                    # Indexes
                    cur.execute('CREATE INDEX IF NOT EXISTS idx_wardrobe_user ON wardrobe(user_id);')
                    cur.execute('CREATE INDEX IF NOT EXISTS idx_clothitem_wardrobe ON cloth_item(wardrobe_id);')
                    cur.execute('CREATE INDEX IF NOT EXISTS idx_image_item ON image(item_id);')
                    cur.execute('CREATE INDEX IF NOT EXISTS idx_careguide_item ON care_guide(item_id);')
                    cur.execute('CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id);')

                conn.commit()
            print('Database initialized successfully')
            return

        except psycopg2.OperationalError as e:
            if attempt < retry_count - 1:
                wait = retry_delay * (2 ** attempt)
                print(f'⚠ Database not ready, retrying in {wait}s... ({attempt+1}/{retry_count})')
                print(f'  Error: {str(e)[:80]}')
                time.sleep(wait)
            else:
                print(f'Failed after {retry_count} attempts')
                raise


# User
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
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM "user" WHERE user_id = %s', (user_id,))
            row = cur.fetchone()
    return dict(row) if row else None

def get_user_by_email(email: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM "user" WHERE email = %s', (email,))
            row = cur.fetchone()
    return dict(row) if row else None


# Wardrobe
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


# ClothItem
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
    import uuid
    from pathlib import Path

    # Save PNG file
    item_uuid  = str(uuid.uuid4())
    filename   = f'{item_uuid}.png'
    image_path = STORAGE_DIR / filename
    image_url  = f'/storage/images/{filename}'

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
            item_id   = cloth_row['item_id']

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
        'imageUrl':   image_url,
        'image_id':   image_row['image_id'],
        'confidence': float(item['confidence']),
        'partial':    bool(item.get('partial', False)),
        'warning':    item.get('warning'),
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


# CareGuide
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


# Feedback
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


# Similarity search
def find_similar(
    query_embedding: list[float],
    wardrobe_id: int,
    top_k: int = 5,
    filter_category: str = None,
) -> list[dict]:
    """
    Find most visually similar items in a wardrobe using pgvector cosine similarity.

    Args:
        query_embedding: 2048-dim float list from ResNet50
        wardrobe_id:     only search within this wardrobe
        top_k:           number of results
        filter_category: optional — filter by category name
    """
    embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if filter_category:
                cur.execute('''
                    SELECT
                        ci.item_id, ci.name, ci.category,
                        i.mask_url AS image_url,
                        1 - (ci.embedding <=> %s::vector) AS similarity
                    FROM cloth_item ci
                    LEFT JOIN image i ON i.item_id = ci.item_id
                    WHERE ci.wardrobe_id = %s AND ci.category = %s
                    ORDER BY ci.embedding <=> %s::vector
                    LIMIT %s
                ''', (embedding_str, wardrobe_id,
                      filter_category, embedding_str, top_k))
            else:
                cur.execute('''
                    SELECT
                        ci.item_id, ci.name, ci.category,
                        i.mask_url AS image_url,
                        1 - (ci.embedding <=> %s::vector) AS similarity
                    FROM cloth_item ci
                    LEFT JOIN image i ON i.item_id = ci.item_id
                    WHERE ci.wardrobe_id = %s
                    ORDER BY ci.embedding <=> %s::vector
                    LIMIT %s
                ''', (embedding_str, wardrobe_id, embedding_str, top_k))

            rows = cur.fetchall()

    return [{
        'item_id':    r['item_id'],
        'category':   r['category'],
        'imageUrl':   r['image_url'],
        'similarity': round(float(r['similarity']), 4),
    } for r in rows]


# Stats
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
        'total':       total,
        'by_category': by_category,
    }
