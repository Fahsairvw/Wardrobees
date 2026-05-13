import base64
import numpy as np
from PIL import Image
import io
import requests
from .model_loader import model_manager

class YOLOInference:
    """Handle YOLO inference operations using trained model from ModelManager"""
    
    def __init__(self):
        self.model = model_manager.get_model()
        self.model_names = self.model.names
    
    def _load_image(self, image_url: str = None, image_base64: str = None):
        """Load image from URL or base64 string"""
        if image_url:
            response = requests.get(image_url, timeout=10)
            img = Image.open(io.BytesIO(response.content))
        elif image_base64:
            if "," in image_base64:
                image_base64 = image_base64.split(",")[1]
            img_data = base64.b64decode(image_base64)
            img = Image.open(io.BytesIO(img_data))
        else:
            raise ValueError("Either image_url or image_base64 must be provided")
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        return img
    
    def _extract_features(self, img):
        """Extract feature vector from image using the model"""
        try:
            # Run inference to get features
            results = self.model(img, verbose=False)
            
            if results and len(results) > 0:
                # Try different ways to get features
                if hasattr(results[0], 'features') and results[0].features is not None:
                    features = results[0].features
                    if isinstance(features, np.ndarray):
                        features = features.flatten().tolist()
                    # Check for NaN values
                    if np.isnan(features).any():
                        print("NaN detected in features, using zeros instead")
                        return [0.0] * 512
                    return features
                
                # Alternative: Use embedding from the model
                return [0.0] * 512  # Return zero vector as fallback
            
            return [0.0] * 512
            
        except Exception as e:
            print(f"Feature extraction error: {e}")
            return [0.0] * 512
    
    def predict(self, image_url: str = None, image_base64: str = None, 
                return_segmentation: bool = True, return_features: bool = True):
        """Run inference on image using closet_v8.pt"""
        try:
            img = self._load_image(image_url, image_base64)
            
            # Run YOLO prediction
            results = self.model(img, verbose=False)
            
            predictions = []
            segmentation_masks = []
            
            for result in results:
                # Get bounding box predictions
                if result.boxes is not None:
                    for box in result.boxes:
                        pred = {
                            "class_id": int(box.cls[0]),
                            "class_name": self.model_names[int(box.cls[0])],
                            "confidence": float(box.conf[0]),
                            "bbox": box.xyxy[0].tolist(),
                        }
                        predictions.append(pred)
                
                # Get segmentation masks if requested (skip if too large)
                if return_segmentation and result.masks is not None:
                    # Only return polygon format (smaller)
                    if hasattr(result, 'masks') and result.masks is not None:
                        # Get xy polygons instead of full masks
                        if hasattr(result.masks, 'xy'):
                            for polygon in result.masks.xy:
                                if polygon is not None and len(polygon) > 0:
                                    segmentation_masks.append(polygon.tolist())
            
            # Extract features
            features = None
            if return_features:
                features = self._extract_features(img)
                # Ensure features is a list of floats
                if features is None:
                    features = [0.0] * 512
            
            return {
                "success": True,
                "predictions": predictions,
                "features": features,
                "segmentation_masks": segmentation_masks if return_segmentation and segmentation_masks else None,
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "predictions": [],
                "features": None,
                "segmentation_masks": None
            }

inference_service = YOLOInference()