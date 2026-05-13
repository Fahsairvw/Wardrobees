from fastapi import APIRouter, HTTPException, Query
from ml_service.schemas import PredictRequest, PredictionResult, HealthResponse
from ml_service.inference import inference_service
from ml_service.model_loader import model_manager
import time
import time
import numpy as np

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
    image1_url: str = Query(None, description="URL of first image"),
    image1_base64: str = Query(None, description="Base64 of first image"),
    image2_url: str = Query(None, description="URL of second image"),
    image2_base64: str = Query(None, description="Base64 of second image")
):
    """
    Compute similarity between two clothing images
    Returns cosine similarity score (0 to 1)
    """
    from sklearn.metrics.pairwise import cosine_similarity
    
    # Validate input
    if not image1_url and not image1_base64:
        raise HTTPException(status_code=400, detail="image1_url or image1_base64 required")
    if not image2_url and not image2_base64:
        raise HTTPException(status_code=400, detail="image2_url or image2_base64 required")
    
    # Get features for first image
    result1 = inference_service.predict(
        image_url=image1_url,
        image_base64=image1_base64,
        return_segmentation=False,
        return_features=True
    )
    
    # Get features for second image
    result2 = inference_service.predict(
        image_url=image2_url,
        image_base64=image2_base64,
        return_segmentation=False,
        return_features=True
    )
    
    if not result1["success"]:
        raise HTTPException(status_code=500, detail=f"Failed to process image1: {result1.get('error')}")
    if not result2["success"]:
        raise HTTPException(status_code=500, detail=f"Failed to process image2: {result2.get('error')}")
    
    features1 = result1.get("features")
    features2 = result2.get("features")
    
    if features1 is None or features2 is None:
        raise HTTPException(status_code=400, detail="Feature extraction failed for one or both images")
    
    # Convert to numpy arrays
    f1 = np.array(features1).reshape(1, -1)
    f2 = np.array(features2).reshape(1, -1)
    
    # Check for NaN or empty values
    if np.isnan(f1).any() or np.isnan(f2).any():
        raise HTTPException(status_code=500, detail="Feature vectors contain invalid values (NaN)")
    
    if f1.size == 0 or f2.size == 0:
        raise HTTPException(status_code=500, detail="Feature vectors are empty")
    
    # Calculate similarity
    similarity = cosine_similarity(f1, f2)[0][0]
    
    # Ensure similarity is between 0 and 1
    similarity = max(0.0, min(1.0, similarity))
    
    return {
        "similarity_score": float(similarity),
        "is_duplicate": similarity > 0.85,
        "message": "Duplicate detected!" if similarity > 0.85 else "No duplicate found"
    }