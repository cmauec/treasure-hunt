"""
Utils for the core app.
"""

import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import numpy as np  # Importa numpy si quieres la opción de devolver un array
from io import BytesIO
from django.core.files import File


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


def optimize_image(image_field, max_size_kb=500):
    """
    Optimize the image to reduce its file size while maintaining quality.

    Args:
        image_field: The image field from the form
        max_size_kb: Maximum size in kilobytes (default 500KB)

    Returns:
        Django File object with the optimized image
    """
    if not image_field:
        return None

    img = Image.open(image_field)

    # Convert to RGB if image is in RGBA mode
    if img.mode == "RGBA":
        img = img.convert("RGB")

    # Initial quality
    quality = 80
    max_size_bytes = max_size_kb * 1024

    # Create a BytesIO object to store the optimized image
    output = BytesIO()

    # Save the image with the initial quality
    img.save(output, format="JPEG", quality=quality, optimize=True)

    # Create a new Django file object
    output.seek(0)
    return File(output, name=image_field.name)
