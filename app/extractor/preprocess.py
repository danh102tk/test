"""
LAYER 1 – Image Preprocess (OpenCV nhẹ)
Deskew + contrast enhancement. Giữ dependency nhẹ, dễ bảo trì.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def _order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def detect_skew_angle(gray: np.ndarray) -> float:
    """Ước lượng góc nghiêng (độ) bằng minAreaRect trên các điểm cạnh."""
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    coords = np.column_stack(np.where(edges > 0))
    if len(coords) < 100:
        return 0.0
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    # Giới hạn góc hợp lý cho form scan
    if abs(angle) > 15:
        return 0.0
    return angle


def deskew(image: np.ndarray, angle: float | None = None) -> np.ndarray:
    if angle is None:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        angle = detect_skew_angle(gray)
    if abs(angle) < 0.3:
        return image
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    m = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image, m, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    """CLAHE trên kênh L (Lab) – tăng tương phản nhẹ, không làm mất chi tiết."""
    if len(image.shape) == 2:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(image)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def preprocess_image(pil_image: Image.Image) -> Image.Image:
    """
    Pipeline nhẹ:
    1. Convert BGR
    2. Deskew
    3. Contrast enhancement
    Trả về PIL Image RGB sẵn sàng cho OCR.
    """
    img = np.array(pil_image.convert("RGB"))
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    img = deskew(img)
    img = enhance_contrast(img)

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return Image.fromarray(img)
