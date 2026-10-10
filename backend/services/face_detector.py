"""
Face Detection Service using OpenCV DNN with SSD MobileNet V1.
Falls back to Haar Cascade if model files are not found.
"""
import cv2
import numpy as np
import os
import logging

logger = logging.getLogger(__name__)

# Paths for SSD MobileNet V1 model files
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models", "ssd_mobilenet_v1")
PROTOTXT = os.path.join(MODEL_DIR, "deploy.prototxt")
CAFFEMODEL = os.path.join(MODEL_DIR, "res10_300x300_ssd_iter_140000.caffemodel")

_net = None
_use_dnn = False


def _load_model():
    """Load SSD MobileNet V1 model once and cache it."""
    global _net, _use_dnn
    if _net is not None:
        return

    if os.path.exists(PROTOTXT) and os.path.exists(CAFFEMODEL):
        try:
            _net = cv2.dnn.readNetFromCaffe(PROTOTXT, CAFFEMODEL)
            _use_dnn = True
            logger.info("[FaceDetector] SSD MobileNet V1 model loaded.")
            return
        except Exception as e:
            logger.warning(f"[FaceDetector] Could not load DNN model: {e}")

    # Fallback: Haar Cascade (always available in OpenCV)
    logger.warning("[FaceDetector] Model files not found. Falling back to Haar Cascade.")
    _net = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    _use_dnn = False


def detect_faces(image_bgr: np.ndarray) -> list[dict]:
    """
    Detect faces in a BGR image.

    Returns a list of dicts with keys:
        - box: (x, y, w, h)
        - confidence: float 0-1
    """
    _load_model()
    results = []

    if _use_dnn:
        h, w = image_bgr.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(image_bgr, (300, 300)),
            scalefactor=1.0,
            size=(300, 300),
            mean=(104.0, 177.0, 123.0),
        )
        _net.setInput(blob)
        detections = _net.forward()

        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])
            if confidence < 0.5:
                continue
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            x1, y1, x2, y2 = box.astype(int)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            results.append({
                "box": (x1, y1, x2 - x1, y2 - y1),
                "confidence": confidence,
            })
    else:
        # Haar Cascade fallback
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        faces = _net.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        for (x, y, w, h) in faces:
            results.append({"box": (x, y, w, h), "confidence": 0.9})

    return results


def decode_image(image_bytes: bytes) -> np.ndarray | None:
    """Decode raw bytes into a BGR numpy array."""
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        logger.error(f"[FaceDetector] Image decode error: {e}")
        return None


def crop_face(image_bgr: np.ndarray, box: tuple, padding: float = 0.2) -> np.ndarray | None:
    """Crop the face region with optional padding."""
    x, y, w, h = box
    pad_x = int(w * padding)
    pad_y = int(h * padding)
    h_img, w_img = image_bgr.shape[:2]
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(w_img, x + w + pad_x)
    y2 = min(h_img, y + h + pad_y)
    crop = image_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    return crop
