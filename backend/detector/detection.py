import numpy as np
import cv2
import io
from PIL import Image
from .config import CAT_NAMES, CONF_THRESHOLD, MIN_SIZE, BORDER_MARGIN, get_group
from .models import yolo_model
from .mask import isolate_with_mask
from .embedding import get_embedding
import logging

logging.basicConfig(level=logging.DEBUG)


def detect_and_remove_bg(image_bytes: bytes) -> list[dict]:
    """
    Full pipeline: image bytes → detected clothing items with transparent bg.

    Steps:
        1. Decode bytes → numpy BGR
        2. Run YOLOv26-seg → bboxes + segmentation contours
        3. For each detection:
           a. Draw contour mask → BGRA (Ultralytics native technique)
           b. Crop tight to bbox
           c. Convert to PIL RGBA PNG
           d. Extract ResNet50 embedding
        4. Return list of item dicts

    Args:
        image_bytes: Raw image bytes from phone upload

    Returns:
        List of dicts per detected item:
        {
            cat_id, cat_name, group,
            confidence,
            img_bytes  (PNG bytes, transparent background),
            width, height,
            embedding  (2048-dim float list),
            partial    (bool),
            warning    (str or None)
        }
    """
    # Step 1 — decode
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)   # BGR

    if img_cv is None:
        logging.error('Could not decode image')
        return []

    H, W = img_cv.shape[:2]
    logging.info(f'  Image: {W}x{H}px')

    # Step 2 — YOLO inference
    # Pass BGR directly — Ultralytics handles conversion internally
    results = yolo_model(img_cv, conf=CONF_THRESHOLD)[0]

    if results.masks is None or len(results.boxes) == 0:
        logging.info('  No clothing items detected')
        return []

    logging.info(f'  YOLO found {len(results.boxes)} item(s)')
    items = []

    # results.masks.xy → list of contour arrays, one per detection
    # results.boxes   → corresponding bboxes + class + conf
    for contour, box in zip(results.masks.xy, results.boxes):
        cat_id = int(box.cls[0])
        confidence = float(box.conf[0])

        # Bbox coordinates
        x1, y1, x2, y2 = box.xyxy.cpu().numpy().squeeze().astype(np.int32)
        bbox_w = x2 - x1
        bbox_h = y2 - y1

        # Skip tiny detections
        if bbox_w < MIN_SIZE or bbox_h < MIN_SIZE:
            logging.info(f'Skip tiny: {bbox_w}x{bbox_h}px ({CAT_NAMES[cat_id]})')
            continue

        # Partial detection — item touches image border
        is_partial = (
            x1 <= BORDER_MARGIN or
            y1 <= BORDER_MARGIN or
            x2 >= W - BORDER_MARGIN or
            y2 >= H - BORDER_MARGIN
        )

        # Step 3a — isolate using Ultralytics native mask technique
        # Returns BGRA with transparent background
        isolated_bgra = isolate_with_mask(img_cv, contour)

        # Step 3b — crop tight to bbox (with small padding)
        PAD = 5
        cx1 = max(0, x1 - PAD)
        cy1 = max(0, y1 - PAD)
        cx2 = min(W, x2 + PAD)
        cy2 = min(H, y2 + PAD)
        cropped_bgra = isolated_bgra[cy1:cy2, cx1:cx2]

        # Step 3c — convert BGRA → RGBA PIL image
        # cv2 uses BGRA, PIL uses RGBA — swap B and R channels
        cropped_rgba = cv2.cvtColor(cropped_bgra, cv2.COLOR_BGRA2RGBA)
        pil_img = Image.fromarray(cropped_rgba, 'RGBA')

        # Step 3d — extract embedding
        embedding = get_embedding(pil_img)

        # Encode to PNG bytes
        buf = io.BytesIO()
        pil_img.save(buf, format='PNG')
        img_bytes_out = buf.getvalue()

        items.append({
            'cat_id': cat_id,
            'cat_name': CAT_NAMES[cat_id],
            'group': get_group(cat_id),
            'confidence': round(confidence, 3),
            'img_bytes': img_bytes_out,
            'width': pil_img.width,
            'height': pil_img.height,
            'embedding': embedding,
            'partial': is_partial,
            'warning': 'Item may be cut off at edge' if is_partial else None,
        })

        logging.info(f'{CAT_NAMES[cat_id]} ({confidence:.0%}) '
                     f'— {bbox_w}x{bbox_h}px')

    return items
