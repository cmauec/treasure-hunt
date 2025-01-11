"""
Utils for the core app.
"""

import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import numpy as np  # Importa numpy si quieres la opción de devolver un array


def generate_image_embedding(image_file, as_list=True):
    """
    Generate an embedding for an uploaded image using CLIP model.

    Args:
        image_file: An InMemoryUploadedFile or similar file object
        as_list: Boolean indicating whether to return the embedding as a list (True) or a NumPy array (False).

    Returns:
        list or numpy.ndarray: The image embedding.
    """
    # Load CLIP model and processor
    model_name = "openai/clip-vit-base-patch32"
    processor = CLIPProcessor.from_pretrained(model_name)
    model = CLIPModel.from_pretrained(model_name)

    # Convert file to PIL Image
    image = Image.open(image_file)

    # Prepare input for the model
    inputs = processor(text=[""], images=image, return_tensors="pt")

    # Generate embedding
    with torch.no_grad():
        outputs = model(**inputs)
        image_embedding = outputs.image_embeds

    # Normalize the embedding
    image_embedding_norm = image_embedding / torch.linalg.norm(
        image_embedding, dim=-1, keepdim=True
    )
    if as_list:
        return image_embedding_norm[0].tolist()
    else:
        return image_embedding_norm.cpu().numpy()[0]
