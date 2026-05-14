import os
from pathlib import Path
from ultralytics import YOLO
import torch
from logging import getLogger

logger = getLogger(__name__)

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
                "models/yolo26.pt",                           # backend/models/
                "../models/yolo26.pt",                        # sibling to backend/
                "/app/models/yolo26.pt",                      # Docker container path
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    model_path = path
                    break
        
        if model_path is None or not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model 'yolo26.pt' not found. Searched in: {possible_paths}"
            )
        
        # Determine device
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load model
        self._model = YOLO(model_path)
        self.model_path = model_path
        self.device = device
        self.variant = "yolo26" 
        
        logger.info(f"Model loaded: {self.variant}")
        logger.info(f"Path: {model_path}")
        logger.info(f"Device: {device}")
        
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
            "model_variant": getattr(self, "variant", "yolo26"),
            "device": getattr(self, "device", "unknown")
        }

# Singleton instance
model_manager = ModelManager()