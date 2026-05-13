import base64
import numpy as np
from PIL import Image
import io
import requests
from .model_loader import model_manager

class YOLOInference:
    """Handle YOLO inference operations using closet_v8.pt"""
    
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
                
                # Get segmentation masks if requested (simplified)
                if return_segmentation and result.masks is not None:
                    for mask in result.masks.data:
                        # Convert to list and take only a sample or use polygon format
                        mask_np = mask.cpu().numpy()
                        
                        # Return as list of lists (smaller)
                        # Only return mask shape info, not every pixel
                        mask_list = mask_np.astype(int).flatten().tolist()
                        
                        # Just return mask dimensions and let frontend handle
                        mask_info = {
                            "shape": list(mask_np.shape),
                            "data": mask_np.astype(int).tolist()  # Still might be large
                        }
                        segmentation_masks.append(mask_info)
            
            # Extract features
            features = None
            if return_features:
                features = self._extract_features(img)
            
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
            }
    
    def _extract_features(self, img):
        """Extract feature vector from image using the model"""
        results = self.model(img, verbose=False)
        if results and hasattr(results[0], 'features'):
            return results[0].features.tolist()
        return None

inference_service = YOLOInference()