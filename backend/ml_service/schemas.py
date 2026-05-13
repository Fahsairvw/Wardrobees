from pydantic import BaseModel
from typing import Optional, List, Any, Union

class PredictRequest(BaseModel):
    """Request schema for prediction endpoint"""
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    return_segmentation: bool = False
    return_features: bool = True

class PredictionResult(BaseModel):
    """Response schema for prediction"""
    success: bool
    predictions: List[dict] = []
    features: Optional[List[float]] = None
    segmentation_masks: Optional[Any] = None
    inference_time_ms: Optional[float] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model_loaded: bool
    model_variant: str
    device: str