import numpy as np
import cv2
import io
from PIL import Image
from rembg import remove
from .config import CAT_NAMES, CONF_THRESHOLD, MIN_SIZE, BORDER_MARGIN, get_group
from .models import yolo_model
from .embedding import get_embedding
from logging import getLogger

logger = getLogger(__name__)


def detect_and_remove_bg(image_bytes: bytes) -> list[dict]:
    # Step 1 — decode
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img_cv is None:
        logger.error('Could not decode image')
        return []

    H, W = img_cv.shape[:2]
    logger.info(f'  Image: {W}x{H}px')

    # Step 2 — YOLO inference
    results = yolo_model(img_cv, conf=CONF_THRESHOLD)[0]

    if results.masks is None or len(results.boxes) == 0:
        logger.info('  No clothing items detected')
        return []

    logger.info(f'  YOLO found {len(results.boxes)} item(s)')
    items = []

    for contour, box in zip(results.masks.xy, results.boxes):
        cat_id = int(box.cls[0])
        confidence = float(box.conf[0])

        x1, y1, x2, y2 = box.xyxy.cpu().numpy().squeeze().astype(np.int32)
        bbox_w = x2 - x1
        bbox_h = y2 - y1

        if bbox_w < MIN_SIZE or bbox_h < MIN_SIZE:
            logger.info(f'  Skip tiny: {bbox_w}x{bbox_h}px ({CAT_NAMES[cat_id]})')
            continue

        is_partial = (
            x1 <= BORDER_MARGIN or
            y1 <= BORDER_MARGIN or
            x2 >= W - BORDER_MARGIN or
            y2 >= H - BORDER_MARGIN
        )

        # Step 3a — build YOLO seg mask on full image
        seg_mask = np.zeros((H, W), dtype=np.uint8)
        cv2.fillPoly(seg_mask, [contour.astype(np.int32)], 255)

        # Step 3b — apply mask → clothing only, everything else black
        clothing_bgr = cv2.bitwise_and(img_cv, img_cv, mask=seg_mask)

        # Step 3c — crop tight to bbox
        PAD = 5
        cx1 = max(0, x1 - PAD)
        cy1 = max(0, y1 - PAD)
        cx2 = min(W, x2 + PAD)
        cy2 = min(H, y2 + PAD)
        cropped_bgr = clothing_bgr[cy1:cy2, cx1:cx2]
        cropped_mask = seg_mask[cy1:cy2, cx1:cx2]

        # Step 3d — convert to RGBA using YOLO mask as alpha
        #           so background is already transparent before rembg
        cropped_rgb = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2RGB)
        cropped_rgba = np.dstack([cropped_rgb, cropped_mask])  # alpha = seg mask
        pil_crop = Image.fromarray(cropped_rgba, 'RGBA')

        # Step 3e — rembg polishes the edges on the already-masked clothing
        pil_img = remove(pil_crop)

        # Step 3f — extract embedding
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

        logger.info(f'{CAT_NAMES[cat_id]} ({confidence:.0%}) '
                    f'— {bbox_w}x{bbox_h}px')

    return items