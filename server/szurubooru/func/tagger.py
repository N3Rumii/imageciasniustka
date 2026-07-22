"""
WD14 Auto-Tagger for szurubooru.
Uses SmilingWolf/wd-v1-4-moat-tagger-v2 ONNX model (~180MB).
Falls back to wd-v1-4-vit-tagger-v2 if moat not available.
"""

import os
import logging
import numpy as np
from PIL import Image
from io import BytesIO
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Paths
MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "models", "tagger"
)
MODEL_PATH = os.path.join(MODEL_DIR, "model.onnx")
TAGS_PATH = os.path.join(MODEL_DIR, "selected_tags.csv")

# Model URLs (moat-v2 = smallest, ~180MB ONNX)
MODEL_URL = (
    "https://huggingface.co/SmilingWolf/wd-v1-4-moat-tagger-v2/resolve/main/"
    "model.onnx"
)
TAGS_URL = (
    "https://huggingface.co/SmilingWolf/wd-v1-4-moat-tagger-v2/resolve/main/"
    "selected_tags.csv"
)

_session = None  # Lazy-loaded ONNX session
_tag_list = None  # Loaded tag names
_rating_indexes = None  # Indexes of rating tags (safe, questionable, explicit)


def _ensure_model():
    """Download model files if missing."""
    global _session
    if _session is not None:
        return
    os.makedirs(MODEL_DIR, exist_ok=True)
    if not os.path.exists(MODEL_PATH):
        logger.info("Downloading WD14 tagger model (~180MB)...")
        _download(MODEL_URL, MODEL_PATH)
    if not os.path.exists(TAGS_PATH):
        logger.info("Downloading tag list...")
        _download(TAGS_URL, TAGS_PATH)
    _load_model()


def _download(url: str, path: str):
    import urllib.request
    urllib.request.urlretrieve(url, path)


def _load_model():
    """Load ONNX model and tag list into memory."""
    global _session, _tag_list, _rating_indexes
    import onnxruntime as ort
    import csv

    _session = ort.InferenceSession(
        MODEL_PATH, providers=["CPUExecutionProvider"]
    )
    # Read CSV without pandas (lightweight)
    with open(TAGS_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        _tag_list = [row["name"] for row in reader if "name" in row]
    # Identify rating tag indexes (used to filter out rating predictions)
    _rating_indexes = set()
    for i, name in enumerate(_tag_list):
        if name.startswith("rating:"):
            _rating_indexes.add(i)
    logger.info("WD14 tagger loaded: %d tags, %dMB", len(_tag_list),
                os.path.getsize(MODEL_PATH) // (1024 * 1024))


def _preprocess_image(content: bytes, target_size: int = 448) -> np.ndarray:
    """Preprocess image for WD14 model (matches SmilingWolf reference pipeline).

    Reference: https://github.com/SmilingWolf/SW-CV-ModelZoo/blob/main/Utils/dbimutils.py
    - Make square with white padding (preserves aspect ratio)
    - Resize to target_size
    - Convert RGB -> BGR (model trained with OpenCV's BGR convention)
    - Cast to float32 WITHOUT normalizing (model expects 0..255 range)
    """
    img = Image.open(BytesIO(content)).convert("RGB")
    # Pad to square with white, preserving aspect ratio
    w, h = img.size
    if w != h:
        max_dim = max(w, h)
        new_img = Image.new("RGB", (max_dim, max_dim), (255, 255, 255))
        paste_x = (max_dim - w) // 2
        paste_y = (max_dim - h) // 2
        new_img.paste(img, (paste_x, paste_y))
        img = new_img
    # Resize to target
    img = img.resize((target_size, target_size), Image.LANCZOS)
    arr = np.array(img, dtype=np.float32)
    arr = arr[:, :, ::-1]  # RGB -> BGR (model trained on OpenCV BGR)
    arr = np.expand_dims(arr, axis=0)  # Add batch dimension
    return arr


def _predict_tags(image_array: np.ndarray) -> np.ndarray:
    """Run inference, return probability array."""
    input_name = _session.get_inputs()[0].name
    return _session.run(None, {input_name: image_array})[0][0]


def generate_tags(
    content: bytes,
    threshold: float = 0.35,
    general_threshold: float = 0.25,
) -> List[Tuple[str, float]]:
    """
    Generate tags for an image.
    Returns list of (tag_name, confidence) tuples sorted by confidence.
    """
    _ensure_model()
    arr = _preprocess_image(content)
    probs = _predict_tags(arr)

    results = []
    for i, prob in enumerate(probs):
        if i in _rating_indexes:
            continue  # Skip rating tags
        tag_name = _tag_list[i]  # Keep underscores (szurubooru requires ^\S+$)
        if tag_name in ("general", "sensitive"):
            continue  # Skip category headers
        t = threshold
        # Lower threshold for general category tags (indexes 4-~3000)
        if i > 3 and i < 3500:
            t = general_threshold
        if prob > t:
            results.append((tag_name, float(prob)))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def unload():
    """Free model from memory."""
    global _session, _tag_list, _rating_indexes
    _session = None
    _tag_list = None
    _rating_indexes = None
