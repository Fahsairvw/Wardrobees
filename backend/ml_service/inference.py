import base64
import numpy as np
from PIL import Image
import io
import requests
import torch
from .model_loader import model_manager

class YOLOInference:
    """Handle YOLO inference operations using yolo26.pt"""
    
    def __init__(self):
        self.model = model_manager.get_model()
        self.model_names = self.model.names
        self.device = model_manager.device
    
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
        """
        Extract feature vector from image using the YOLO model's backbone.
        Returns a 512-dimensional embedding vector.
        """
        try:
            # Method 1: Get features from model's internal representations
            # Resize to model's expected input size
            img_resized = img.resize((640, 640))
            
            # Convert to tensor
            from torchvision import transforms
            transform = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225])
            ])
            
            img_tensor = transform(img_resized).unsqueeze(0).to(self.device)
            
            # Extract features from model's backbone
            with torch.no_grad():
                # Access the model's internal layers
                if hasattr(self.model, 'model'):
                    # For YOLO models, get features from backbone
                    features = self.model.model.model[-2].forward(img_tensor)
                    
                    if isinstance(features, torch.Tensor):
                        # Global average pooling
                        features = features.mean(dim=[2, 3]).flatten().cpu().numpy()
                        
                        # Normalize
                        norm = np.linalg.norm(features)
                        if norm > 0:
                            features = (features / norm).tolist()
                        
                        return features
            
            # Method 2: Use YOLO's predict and get features from result
            results = self.model(img, verbose=False)
            
            if results and len(results) > 0:
                # Check if result has embeddings attribute
                if hasattr(results[0], 'embeddings') and results[0].embeddings is not None:
                    embeddings = results[0].embeddings
                    if isinstance(embeddings, torch.Tensor):
                        embeddings = embeddings.cpu().numpy()
                    if embeddings.size > 0:
                        features = embeddings.flatten().tolist()
                        norm = np.linalg.norm(features)
                        if norm > 0:
                            features = (np.array(features) / norm).tolist()
                        return features
            
            # Method 3: Use fallback
            return self._get_fallback_features(img)
            
        except Exception as e:
            print(f"Feature extraction error: {e}")
            return self._get_fallback_features(img)
    
    def _get_fallback_features(self, img):
        """
        Fallback: Extract simple image statistics as features.
        This is a last resort if the model's embedding extraction fails.
        """
        try:
            # Convert to numpy
            img_resized = img.resize((224, 224))
            img_np = np.array(img_resized) / 255.0
            
            # Extract simple features: color histograms, edges, etc.
            features = []
            
            # Color histograms (RGB)
            for c in range(3):
                hist = np.histogram(img_np[:,:,c], bins=16, range=(0,1))[0]
                features.extend(hist)
            
            # Mean and std per channel
            for c in range(3):
                features.append(np.mean(img_np[:,:,c]))
                features.append(np.std(img_np[:,:,c]))
            
            # Normalize features
            features = np.array(features)
            norm = np.linalg.norm(features)
            if norm > 0:
                features = (features / norm).tolist()
            
            print(f"Using fallback features (dimension: {len(features)})")
            return features
            
        except Exception as e:
            print(f"Fallback feature extraction failed: {e}")
            # Return zero vector as last resort
            return [0.0] * 512
    
    def predict(self, image_url: str = None, image_base64: str = None, 
                return_segmentation: bool = True, return_features: bool = True):
        """Run inference on image using closet_v8.pt"""
        try:
            img = self._load_image(image_url, image_base64)
            
            results = self.model(img, verbose=False)
            
            predictions = []
            segmentation_masks = []
            
            for result in results:
                # Get bounding box predictions
                if result.boxes is not None:
                    for box in result.boxes:
                        # Handle box access correctly
                        cls_id = int(box.cls[0]) if hasattr(box.cls, '__len__') else int(box.cls)
                        conf = float(box.conf[0]) if hasattr(box.conf, '__len__') else float(box.conf)
                        
                        pred = {
                            "class_id": cls_id,
                            "class_name": self.model_names[cls_id],
                            "confidence": conf,
                            "bbox": box.xyxy[0].tolist() if hasattr(box.xyxy[0], 'tolist') else list(box.xyxy[0])
                        }
                        predictions.append(pred)
                
                # Get segmentation masks if requested
                if return_segmentation and result.masks is not None:
                    if hasattr(result.masks, 'xy') and result.masks.xy is not None:
                        for polygon in result.masks.xy:
                            if polygon is not None and len(polygon) > 0:
                                segmentation_masks.append(polygon.tolist())
            
            # Extract features
            features = None
            if return_features:
                features = self._extract_features(img)
                if features is None:
                    features = self._get_fallback_features(img)
            
            return {
                "success": True,
                "predictions": predictions,
                "features": features,
                "segmentation_masks": segmentation_masks if return_segmentation and segmentation_masks else None,
            }
            
        except Exception as e:
            print(f"Prediction error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "predictions": [],
                "features": None,
                "segmentation_masks": None
            }

inference_service = YOLOInference()