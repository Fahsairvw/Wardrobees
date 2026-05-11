from ultralytics import YOLO
from PIL import Image
import numpy as np
import cv2
import io
import torch
import torchvision.models as models
import torchvision.transforms as transforms

# Category definitions
CAT_NAMES = [
    'short sleeve top',
    'long sleeve top',
    'short sleeve outwear',
    'long sleeve outwear',
    'vest',
    'sling',
    'shorts',
    'trousers',
    'skirt',
    'short sleeve dress',
    'long sleeve dress',
    'vest dress',
    'sling dress',
]

CAT_GROUPS = {
    'tops':    [0, 1, 2, 3, 4, 5],
    'bottoms': [6, 7, 8],
    'dresses': [9, 10, 11, 12],
}

#Config
CONF_THRESHOLD = 0.25
MIN_SIZE       = 80
BORDER_MARGIN  = 15

def get_group(cat_id: int) -> str:
    for group, ids in CAT_GROUPS.items():
        if cat_id in ids:
            return group
    return 'other'


# Load models once at startup
yolo_model = YOLO('../models/closet_v8.pt')

resnet = models.resnet50(pretrained=True)
resnet.fc = torch.nn.Identity()
resnet.eval()

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std= [0.229, 0.224, 0.225]
    )
])


# Embedding extraction
def get_embedding(pil_image: Image.Image) -> list[float]:
    """
    Extract 2048-dim feature vector from a clothing item image.
    Used for cosine similarity search.
    """
    img_rgb = pil_image.convert('RGB')
    tensor  = transform(img_rgb).unsqueeze(0)
    with torch.no_grad():
        vector = resnet(tensor).squeeze().tolist()
    return vector


# Native mask isolation (Ultralytics technique)
def isolate_with_mask(img_bgr: np.ndarray, contour: np.ndarray) -> np.ndarray:
    """
    Isolate one clothing item using its YOLO segmentation contour.

    Technique from Ultralytics docs:
        1. Create blank binary mask same size as image
        2. Draw filled contour onto mask (white = keep, black = remove)
        3. Stack image + mask using np.dstack → RGBA
           → pixels outside contour become transparent

    Args:
        img_bgr:  Original image in BGR format (H x W x 3)
        contour:  Polygon contour from results.masks.xy (N x 2 float array)

    Returns:
        RGBA numpy array (H x W x 4) — background fully transparent
    """
    H, W  = img_bgr.shape[:2]

    # Step 1 — blank black mask
    b_mask = np.zeros((H, W), dtype=np.uint8)

    # Step 2 — draw filled contour → white pixels inside clothing item
    contour_int = contour.astype(np.int32)
    cv2.drawContours(
        image      = b_mask,
        contours   = [contour_int],
        contourIdx = -1,
        color      = 255,
        thickness  = cv2.FILLED,
    )

    # Step 3 — stack BGR + mask → BGRA (transparent bg)
    # np.dstack adds the mask as the alpha channel
    isolated = np.dstack([img_bgr, b_mask])   # shape: H x W x 4 (BGRA)

    return isolated   # BGRA


# Main detection function
def detect_and_remove_bg(image_bytes: bytes) -> list[dict]:
    """
    Full pipeline: image bytes → detected clothing items with transparent bg.

    Steps:
        1. Decode bytes → numpy BGR
        2. Run YOLOv8-seg → bboxes + segmentation contours
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
    nparr  = np.frombuffer(image_bytes, np.uint8)
    img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)   # BGR

    if img_cv is None:
        print('Could not decode image')
        return []

    H, W = img_cv.shape[:2]
    print(f'  Image: {W}x{H}px')

    # Step 2 — YOLO inference
    # Pass BGR directly — Ultralytics handles conversion internally
    results = yolo_model(img_cv, conf=CONF_THRESHOLD)[0]

    if results.masks is None or len(results.boxes) == 0:
        print('  No clothing items detected')
        return []

    print(f'  YOLO found {len(results.boxes)} item(s)')
    items = []

    # results.masks.xy → list of contour arrays, one per detection
    # results.boxes   → corresponding bboxes + class + conf
    for contour, box in zip(results.masks.xy, results.boxes):
        cat_id     = int(box.cls[0])
        confidence = float(box.conf[0])

        # Bbox coordinates
        x1, y1, x2, y2 = box.xyxy.cpu().numpy().squeeze().astype(np.int32)
        bbox_w = x2 - x1
        bbox_h = y2 - y1

        # Skip tiny detections
        if bbox_w < MIN_SIZE or bbox_h < MIN_SIZE:
            print(f'  Skip tiny: {bbox_w}x{bbox_h}px ({CAT_NAMES[cat_id]})')
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
        cx1 = max(0, x1 - PAD);  cy1 = max(0, y1 - PAD)
        cx2 = min(W, x2 + PAD);  cy2 = min(H, y2 + PAD)
        cropped_bgra = isolated_bgra[cy1:cy2, cx1:cx2]

        # Step 3c — convert BGRA → RGBA PIL image
        # cv2 uses BGRA, PIL uses RGBA — swap B and R channels
        cropped_rgba = cv2.cvtColor(cropped_bgra, cv2.COLOR_BGRA2RGBA)
        pil_img      = Image.fromarray(cropped_rgba, 'RGBA')

        # Step 3d — extract embedding
        embedding = get_embedding(pil_img)

        # Encode to PNG bytes
        buf = io.BytesIO()
        pil_img.save(buf, format='PNG')
        img_bytes_out = buf.getvalue()

        items.append({
            'cat_id':     cat_id,
            'cat_name':   CAT_NAMES[cat_id],
            'group':      get_group(cat_id),
            'confidence': round(confidence, 3),
            'img_bytes':  img_bytes_out,
            'width':      pil_img.width,
            'height':     pil_img.height,
            'embedding':  embedding,
            'partial':    is_partial,
            'warning':    'Item may be cut off at edge' if is_partial else None,
        })

        flag = 'edge' if is_partial else '✅'
        print(f'  {flag} {CAT_NAMES[cat_id]} ({confidence:.0%}) '
              f'— {bbox_w}x{bbox_h}px')

    return items
