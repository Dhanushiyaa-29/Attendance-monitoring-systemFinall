"""
Face Landmark Service — 68-point facial landmarks for face alignment.
Uses dlib's shape_predictor_68_face_landmarks model when available.
"""
import numpy as np
import cv2
import os
import logging

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "models", "shape_predictor_68_face_landmarks"
)
LANDMARK_MODEL = os.path.join(MODEL_DIR, "shape_predictor_68_face_landmarks.dat")

_predictor = None
_detector = None
_dlib_available = False


def _load_model():
    """Load dlib landmark predictor once."""
    global _predictor, _detector, _dlib_available
    if _predictor is not None:
        return

    try:
        import dlib  # noqa: F401 — optional dependency

        if not os.path.exists(LANDMARK_MODEL):
            logger.warning(
                "[Landmark] shape_predictor_68_face_landmarks.dat not found. "
                "Alignment will use simple crop only."
            )
            return

        _detector = dlib.get_frontal_face_detector()
        _predictor = dlib.shape_predictor(LANDMARK_MODEL)
        _dlib_available = True
        logger.info("[Landmark] dlib 68-point landmark model loaded.")
    except ImportError:
        logger.warning("[Landmark] dlib not installed. Using basic alignment fallback.")


# Reference eye positions for 96×96 aligned image
LEFT_EYE_REF = np.array([0.35, 0.35])
RIGHT_EYE_REF = np.array([0.65, 0.35])
ALIGNED_SIZE = (96, 96)

# dlib landmark indices
LEFT_EYE_INDICES = list(range(36, 42))
RIGHT_EYE_INDICES = list(range(42, 48))


def _get_eye_centers_dlib(image_bgr: np.ndarray, box: tuple):
    """Return (left_eye, right_eye) centres using dlib landmarks."""
    import dlib

    x, y, w, h = box
    rect = dlib.rectangle(x, y, x + w, y + h)
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    shape = _predictor(gray, rect)
    pts = np.array([[shape.part(i).x, shape.part(i).y] for i in range(68)])

    left_eye = pts[LEFT_EYE_INDICES].mean(axis=0)
    right_eye = pts[RIGHT_EYE_INDICES].mean(axis=0)
    return left_eye, right_eye, pts


def align_face(image_bgr: np.ndarray, box: tuple) -> np.ndarray:
    """
    Align a face using the 68-point landmark model.
    Falls back to a simple resize if the model is unavailable.

    Returns an aligned RGB face image of size ALIGNED_SIZE.
    """
    _load_model()

    x, y, w, h = box
    # Basic crop first
    h_img, w_img = image_bgr.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(w_img, x + w), min(h_img, y + h)
    face_crop = image_bgr[y1:y2, x1:x2]

    if not _dlib_available or face_crop.size == 0:
        # Simple resize fallback
        if face_crop.size > 0:
            aligned = cv2.resize(face_crop, ALIGNED_SIZE)
            return cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB)
        return None

    try:
        left_eye, right_eye, _ = _get_eye_centers_dlib(image_bgr, box)

        # Compute rotation angle
        dy = right_eye[1] - left_eye[1]
        dx = right_eye[0] - left_eye[0]
        angle = np.degrees(np.arctan2(dy, dx))

        # Compute desired eye distance
        desired_dist = (RIGHT_EYE_REF[0] - LEFT_EYE_REF[0]) * ALIGNED_SIZE[0]
        current_dist = np.linalg.norm(right_eye - left_eye)
        scale = desired_dist / (current_dist + 1e-6)

        # Centre of the eyes
        eye_centre = ((left_eye + right_eye) / 2).astype(int)

        M = cv2.getRotationMatrix2D(tuple(eye_centre), angle, scale)

        # Translate so left eye lands on reference position
        M[0, 2] += ALIGNED_SIZE[0] * LEFT_EYE_REF[0] - eye_centre[0]
        M[1, 2] += ALIGNED_SIZE[1] * LEFT_EYE_REF[1] - eye_centre[1]

        aligned = cv2.warpAffine(image_bgr, M, ALIGNED_SIZE, flags=cv2.INTER_CUBIC)
        return cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB)
    except Exception as e:
        logger.warning(f"[Landmark] Alignment failed, using simple crop: {e}")
        aligned = cv2.resize(face_crop, ALIGNED_SIZE)
        return cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB)
