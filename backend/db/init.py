import psycopg2
import time
from .connection import get_conn


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
