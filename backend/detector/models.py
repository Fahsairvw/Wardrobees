import torch
import torchvision.models as models
import torchvision.transforms as transforms
from ultralytics import YOLO

# Load YOLO model for detection
yolo_model = YOLO('../models/yolo26.pt')

# Load ResNet50 for embedding extraction
resnet = models.resnet50(pretrained=True)
resnet.fc = torch.nn.Identity()
resnet.eval()

# Image preprocessing pipeline
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])
