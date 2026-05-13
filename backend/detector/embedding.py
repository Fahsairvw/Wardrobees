import torch
from PIL import Image
from .models import resnet, transform


def get_embedding(pil_image: Image.Image) -> list[float]:
    """
    Extract 2048-dim feature vector from a clothing item image.
    Used for cosine similarity search in the wardrobe.

    Args:
        pil_image: PIL Image object of the clothing item

    Returns:
        List of 2048 float values representing the image embedding
    """
    img_rgb = pil_image.convert('RGB')
    tensor = transform(img_rgb).unsqueeze(0)
    with torch.no_grad():
        vector = resnet(tensor).squeeze().tolist()
    return vector
