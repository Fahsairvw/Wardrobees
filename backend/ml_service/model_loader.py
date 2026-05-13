import os
from pathlib import Path
from ultralytics import YOLO
import torch

class ModelManager:
    """Singleton manager for YOLO model"""
    
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_model(self, model_path: str = None):
        """Load YOLO model (only once)"""
        if self._model is not None:
            return self._model
        
        # Use trained model
        if model_path is None:
            # Look for trained model
            possible_paths = [
                "models/closet_v8.pt",                           # backend/models/
                "../models/closet_v8.pt",                        # sibling to backend/
                "/app/models/closet_v8.pt",                      # Docker container path
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    model_path = path
                    break
        
        if model_path is None or not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model 'closet_v8.pt' not found. Searched in: {possible_paths}"
            )
        
        # Determine device
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load model
        self._model = YOLO(model_path)
        self.model_path = model_path
        self.device = device
        self.variant = "closet_v8" 
        
        print(f"Model loaded: {self.variant}")
        print(f"Path: {model_path}")
        print(f"Device: {device}")
        
        return self._model
    
    def get_model(self):
        """Get loaded model (loads if not already)"""
        if self._model is None:
            self.load_model()
        return self._model
    
    def get_info(self):
        """Get model information"""
        return {
            "model_loaded": self._model is not None,
            "model_path": getattr(self, "model_path", None),
            "model_variant": getattr(self, "variant", "closet_v8"),
            "device": getattr(self, "device", "unknown")
        }

# Singleton instance
model_manager = ModelManager()