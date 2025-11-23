"""
QR code decoding functionality
"""
import os
import io
import logging
from typing import List, Tuple
from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode

logger = logging.getLogger(__name__)

def _pyzbar_decode(img_path: str) -> List[str]:
    try:
        from PIL import Image
    except Exception:
        return []
    try:
        img = Image.open(img_path).convert("RGB")
    except Exception:
        return []
    decoded = pyzbar_decode(img)
    texts = []
    for d in decoded:
        try:
            texts.append(d.data.decode("utf-8", errors="ignore"))
        except Exception:
            pass
    return texts

def _opencv_decode(img_path: str) -> List[str]:
    # OpenCV's QRCodeDetector - good fallback
    try:
        import cv2
    except Exception:
        return []
    try:
        img = cv2.imread(img_path)
        if img is None:
            return []
    except Exception:
        return []
    detector = cv2.QRCodeDetector()
    # try multi first if available
    try:
        retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img)
        if retval and decoded_info:
            return [s for s in decoded_info if s]
    except Exception:
        pass
    # single decode
    try:
        data, points, _ = detector.detectAndDecode(img)
        if data:
            return [data]
    except Exception:
        pass
    return []

def decode_image(image_path: str) -> list:
    image_path = str(image_path)
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)
    # try pyzbar first
    out = _pyzbar_decode(image_path)
    if out:
        return out
    # fallback to OpenCV detector
    out = _opencv_decode(image_path)
    return out

def decode_qr(file_data: bytes) -> str:
    """
    Decode QR code from image bytes
    Returns: decoded string or None if no QR found
    """
    try:
        # Open image
        image = Image.open(io.BytesIO(file_data))
        
        # Decode using pyzbar
        decoded_objects = pyzbar_decode(image)
        
        if not decoded_objects:
            logger.warning("No QR code detected in image")
            return None
        
        # Get first QR code data
        qr_data = decoded_objects[0].data.decode('utf-8', errors='ignore')
        
        return qr_data
        
    except Exception as e:
        logger.error(f"QR decoding error: {e}", exc_info=True)
        return None

def decode_multiple_qr(file_data: bytes) -> list:
    """
    Decode multiple QR codes from image
    Returns: list of decoded strings
    """
    try:
        image = Image.open(io.BytesIO(file_data))
        decoded_objects = pyzbar_decode(image)
        
        return [obj.data.decode('utf-8', errors='ignore') for obj in decoded_objects]
        
    except Exception as e:
        logger.error(f"Multiple QR decoding error: {e}", exc_info=True)
        return []
