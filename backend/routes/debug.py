from fastapi import APIRouter, File, UploadFile, HTTPException
import numpy as np
import cv2
from detector import yolo_model, CONF_THRESHOLD, CAT_NAMES

router = APIRouter(tags=['Debug'])


@router.post('/debug')
async def debug(file: UploadFile = File(...)):
    """
    Raw YOLO output — no saving, just detection check (Admin only).
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(400, 'File must be an image')

    nparr = np.frombuffer(await file.read(), np.uint8)
    img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_cv is None:
        raise HTTPException(400, 'Could not decode image')

    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    H, W = img_rgb.shape[:2]
    results = yolo_model(img_rgb, conf=CONF_THRESHOLD)[0]
    detections = []

    if results.boxes:
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            detections.append({
                'category': CAT_NAMES[int(box.cls[0])],
                'confidence': round(float(box.conf[0]), 3),
                'bbox': [x1, y1, x2, y2],
                'bbox_size': f'{x2-x1}x{y2-y1}px',
            })

    return {
        'image_shape': f'{W}x{H}',
        'conf_threshold': CONF_THRESHOLD,
        'n_detected': len(detections),
        'detections': detections,
    }
