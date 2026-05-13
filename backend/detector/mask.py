import numpy as np
import cv2


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
    H, W = img_bgr.shape[:2]

    # Step 1 — blank black mask
    b_mask = np.zeros((H, W), dtype=np.uint8)

    # Step 2 — draw filled contour → white pixels inside clothing item
    contour_int = contour.astype(np.int32)
    cv2.drawContours(
        image=b_mask,
        contours=[contour_int],
        contourIdx=-1,
        color=255,
        thickness=cv2.FILLED,
    )

    # Step 3 — stack BGR + mask → BGRA (transparent bg)
    # np.dstack adds the mask as the alpha channel
    isolated = np.dstack([img_bgr, b_mask])   # shape: H x W x 4 (BGRA)

    return isolated   # BGRA
