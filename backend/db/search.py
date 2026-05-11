import psycopg2.extras
from .connection import get_conn


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
        'item_id': r['item_id'],
        'category': r['category'],
        'imageUrl': r['image_url'],
        'similarity': round(float(r['similarity']), 4),
    } for r in rows]
