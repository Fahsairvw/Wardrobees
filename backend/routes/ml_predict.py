from fastapi import APIRouter, HTTPException
from ml_service.schemas import PredictRequest, PredictionResult, HealthResponse
from ml_service.inference import inference_service
from ml_service.model_loader import model_manager
import time

router = APIRouter(prefix="/ml", tags=["ML Prediction"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    info = model_manager.get_info()
    return HealthResponse(
        status="healthy" if info["model_loaded"] else "degraded",
        model_loaded=info["model_loaded"],
        model_variant=info["model_variant"],
        device=info["device"]
    )

@router.post("/predict", response_model=PredictionResult)
async def predict(request: PredictRequest):
    """
    Run clothing detection and segmentation
    
    Input formats:
    - image_url: HTTPS URL to an image
    - image_base64: Base64 encoded image string
    
    Returns:
    - predictions: List of detected clothing items with class, confidence, bbox
    - features: Feature vector for similarity matching
    - segmentation_masks: Polygon masks for each detected item
    """
    if not request.image_url and not request.image_base64:
        raise HTTPException(status_code=400, detail="Either image_url or image_base64 required")
    
    start_time = time.time()
    
    result = inference_service.predict(
        image_url=request.image_url,
        image_base64=request.image_base64,
        return_segmentation=request.return_segmentation,
        return_features=request.return_features
    )
    
    inference_time = (time.time() - start_time) * 1000
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Inference failed"))
    
    # Add inference time to response
    result["inference_time_ms"] = round(inference_time, 2)
    
    return result

@router.post("/similarity")
async def compute_similarity(
    image1_url: str = None,
    image1_base64: str = None,
    image2_url: str = None,
    image2_base64: str = None
):
    """
    Compute similarity between two clothing images
    Returns cosine similarity score (0 to 1)
    """
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    
    # Get features for both images
    result1 = inference_service.predict(image_url=image1_url, image_base64=image1_base64)
    result2 = inference_service.predict(image_url=image2_url, image_base64=image2_base64)
    
    if not result1["success"] or not result2["success"]:
        raise HTTPException(status_code=500, detail="Failed to process one or both images")
    
    features1 = np.array(result1.get("features", [])).reshape(1, -1)
    features2 = np.array(result2.get("features", [])).reshape(1, -1)
    
    if features1.size == 0 or features2.size == 0:
        raise HTTPException(status_code=400, detail="Feature extraction failed")
    
    similarity = cosine_similarity(features1, features2)[0][0]
    
    return {
        "similarity_score": float(similarity),
        "is_duplicate": similarity > 0.85,
        "message": "Duplicate detected!" if similarity > 0.85 else "No duplicate found"
    }