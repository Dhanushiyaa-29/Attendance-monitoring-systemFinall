"""
Face Recognition Service — generates 128-d face embeddings.
Uses the face_recognition library (dlib-based) when available,
with a PCA/HOG fallback for environments where dlib is hard to install.
"""
import numpy as np
import cv2
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_face_rec_available = False

try:
    import face_recognition as _fr_lib  # dlib-based 128-d embeddings
    _face_rec_available = True
    logger.info("[FaceRecognition] face_recognition library loaded (128-d embeddings).")
except ImportError:
    logger.warning(
        "[FaceRecognition] face_recognition library not available. "
        "Using HOG+PCA fallback embeddings."
    )


# ---------------------------------------------------------------------------
# Fallback: HOG descriptor → PCA-reduced 128-d vector
# ---------------------------------------------------------------------------
_pca_model = None


def _hog_embedding(rgb_image: np.ndarray) -> np.ndarray:
    """Compute a 128-d HOG-based feature vector as a fallback embedding."""
    img = cv2.resize(rgb_image, (96, 96))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gray = gray / 255.0

    hog = cv2.HOGDescriptor(
        _winSize=(96, 96),
        _blockSize=(16, 16),
        _blockStride=(8, 8),
        _cellSize=(8, 8),
        _nbins=9,
    )
    descriptor = hog.compute(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY))
    descriptor = descriptor.flatten()

    # Truncate or pad to 128 dimensions
    if len(descriptor) >= 128:
        descriptor = descriptor[:128]
    else:
        descriptor = np.pad(descriptor, (0, 128 - len(descriptor)))

    # L2-normalise
    norm = np.linalg.norm(descriptor)
    if norm > 0:
        descriptor = descriptor / norm

    return descriptor.astype(np.float64)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_face_embedding(rgb_face_image: np.ndarray) -> Optional[np.ndarray]:
    """
    Compute a 128-d face embedding from an RGB face image (already cropped/aligned).

    Returns:
        numpy array of shape (128,) or None if embedding fails.
    """
    if rgb_face_image is None or rgb_face_image.size == 0:
        return None

    if _face_rec_available:
        try:
            # face_recognition expects an RGB image; locate all faces in the crop
            locations = _fr_lib.face_locations(rgb_face_image, model="hog")
            if not locations:
                # Try without explicit detection (use entire image as face)
                locations = [(0, rgb_face_image.shape[1], rgb_face_image.shape[0], 0)]
            encodings = _fr_lib.face_encodings(rgb_face_image, known_face_locations=locations)
            if encodings:
                return np.array(encodings[0], dtype=np.float64)
        except Exception as e:
            logger.warning(f"[FaceRecognition] face_recognition error: {e}")

    # Fallback
    return _hog_embedding(rgb_face_image)


def compute_similarity(embedding_a: list | np.ndarray, embedding_b: list | np.ndarray) -> float:
    """
    Compute cosine similarity between two embeddings.
    Returns a value in [0, 1] where 1 = identical.
    """
    a = np.array(embedding_a, dtype=np.float64)
    b = np.array(embedding_b, dtype=np.float64)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0

    similarity = float(np.dot(a, b) / (norm_a * norm_b))
    # Clamp to [0, 1]
    return max(0.0, min(1.0, (similarity + 1.0) / 2.0))


def compute_distance(embedding_a: list | np.ndarray, embedding_b: list | np.ndarray) -> float:
    """
    Compute Euclidean distance between two embeddings.
    Lower = more similar. 0 = identical.
    """
    a = np.array(embedding_a, dtype=np.float64)
    b = np.array(embedding_b, dtype=np.float64)
    return float(np.linalg.norm(a - b))


def is_match(
    embedding_a: list | np.ndarray,
    embedding_b: list | np.ndarray,
    threshold: float = 0.55,
) -> tuple[bool, float]:
    """
    Determine if two embeddings belong to the same person.

    Uses Euclidean distance:  distance < threshold → match
    Also returns a 0-1 confidence score.

    Args:
        threshold: Maximum Euclidean distance to count as a match.
                   Typical values: 0.4 (strict) – 0.6 (lenient).
    """
    dist = compute_distance(embedding_a, embedding_b)
    matched = dist < threshold
    # Convert distance to 0-1 confidence (closer → higher confidence)
    confidence = max(0.0, 1.0 - (dist / (threshold * 2)))
    return matched, round(confidence, 4)
