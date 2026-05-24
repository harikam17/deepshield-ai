import numpy as np
from PIL import Image, ImageOps
import io


TARGET_SIZE = (224, 224)


def preprocess_image(filepath: str) -> np.ndarray:
    """
    Full preprocessing pipeline:
    1. Load image
    2. Convert to RGB
    3. EXIF-aware rotation
    4. Resize to 224x224
    5. Normalize to [0, 1]
    Returns: np.ndarray of shape (224, 224, 3)
    """
    img = Image.open(filepath)

    # Fix EXIF orientation
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # Ensure RGB (handle RGBA, grayscale, palette)
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Resize using high-quality Lanczos resampling
    img = img.resize(TARGET_SIZE, Image.LANCZOS)

    # Convert to numpy float32 array
    arr = np.array(img, dtype=np.float32)

    # Normalize to [0, 1]
    arr = arr / 255.0

    return arr


def preprocess_from_bytes(image_bytes: bytes) -> np.ndarray:
    """Preprocess image from raw bytes (for streaming use)."""
    img = Image.open(io.BytesIO(image_bytes))

    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    if img.mode != "RGB":
        img = img.convert("RGB")

    img = img.resize(TARGET_SIZE, Image.LANCZOS)
    arr = np.array(img, dtype=np.float32) / 255.0
    return arr


def validate_image(filepath: str) -> tuple[bool, str]:
    """
    Validate that file is a readable image.
    Returns (is_valid, error_message).
    """
    try:
        img = Image.open(filepath)
        img.verify()
        return True, ""
    except Exception as e:
        return False, f"Invalid image file: {str(e)}"
