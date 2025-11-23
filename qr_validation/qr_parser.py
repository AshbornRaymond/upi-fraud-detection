# qr_validation/qr_parser.py
"""
QR parser that decodes and identifies QR code types
NO domain whitelisting - all URLs go through ML validation
"""

import sys
import json
import logging
import re

logger = logging.getLogger(__name__)

def decode_qr(file_data: bytes) -> str:
    """Decode QR code from image bytes"""
    try:
        from PIL import Image
        from pyzbar.pyzbar import decode as pyzbar_decode
        import io
        
        image = Image.open(io.BytesIO(file_data))
        decoded_objects = pyzbar_decode(image)
        
        if not decoded_objects:
            logger.warning("No QR code detected in image")
            return None
        
        qr_data = decoded_objects[0].data.decode('utf-8', errors='ignore')
        return qr_data
        
    except Exception as e:
        logger.error(f"QR decoding error: {e}", exc_info=True)
        return None

def identify_qr_content_type(data: str) -> str:
    """
    Identify QR code type based ONLY on format, not domain names
    All URLs go to ML validation - no whitelisting
    """
    data_lower = data.lower()
    
    # 1. Google Pay/BHIM encrypted QR (EMVCo standard - starts with "00020101" or "00020201")
    if data.startswith(('00020101', '00020201')):
        logger.info("[QR TYPE] EMVCo encrypted payment QR (Google Pay/BHIM/PhonePe)")
        return "protected_payment"
    
    # 2. Non-URL payment app codes (encrypted data, not clickable links)
    # Only if they DON'T start with http - otherwise it's a phishing URL
    if not data.startswith('http'):
        payment_keywords = ['bhim', 'phonepe', 'paytmmp', 'paytmqr', 'bharatpe', 'gpay']
        if any(kw in data_lower for kw in payment_keywords):
            logger.info("[QR TYPE] Encrypted payment app QR (not URL)")
            return "protected_payment"
    
    # 3. Standard UPI payment string (upi://pay?...)
    if data.startswith(("upi://", "upi://pay")):
        logger.info("[QR TYPE] Standard UPI payment QR")
        return "upi"
    
    # 4. HTTP/HTTPS URLs - ALL go to ML validation (no exceptions!)
    if data.startswith(("http://", "https://")):
        logger.info("[QR TYPE] URL detected - sending to ML validation")
        return "url"
    
    # 5. Plain VPA (email-like format: user@provider)
    if '@' in data and not data.startswith(('http', 'upi', 'mailto')):
        if re.match(r'^[a-zA-Z0-9.\-_]{2,}@[a-zA-Z0-9.\-_]{2,}$', data):
            logger.info("[QR TYPE] Plain VPA address")
            return "vpa"
    
    # 6. System intents (tel, mailto, sms, etc.)
    if data.startswith('geo:') or 'google.navigation:' in data:
        return "geo"
    if data.startswith('tel:'):
        return "tel"
    if data.startswith('mailto:'):
        return "mailto"
    if data.startswith('sms:'):
        return "sms"
    if data.startswith('WIFI:'):
        return "wifi"
    if data.startswith('BEGIN:VCARD'):
        return "vcard"
    if data.startswith('intent://'):
        return "intent"
    
    # 7. Plain text/alphanumeric (serial numbers, tracking codes, etc.)
    if len(data) < 200 and data.replace(' ', '').replace('-', '').replace('_', '').replace('\n', '').isalnum():
        logger.info("[QR TYPE] Plain text/code")
        return "text"
    
    # 8. Unknown format
    logger.warning(f"[QR TYPE] Unknown format: {data[:50]}")
    return "unknown"

def parse_qr_image(file_data: bytes) -> dict:
    """
    Parse QR code image and return structured data
    """
    try:
        decoded_data = decode_qr(file_data)
        
        if not decoded_data:
            return {"error": "No QR code found in image"}
        
        logger.info(f"[QR DECODED] {decoded_data[:100]}")
        
        qr_type = identify_qr_content_type(decoded_data)
        
        result = {
            "type": qr_type,
            "data": decoded_data
        }
        
        # Extract VPA for UPI QR codes
        if qr_type == "upi":
            vpa_match = re.search(r'pa=([^&]+)', decoded_data)
            if vpa_match:
                result["vpa"] = vpa_match.group(1)
        
        return result
        
    except Exception as e:
        logger.error(f"QR parsing error: {e}", exc_info=True)
        return {"error": f"Failed to parse QR: {str(e)}"}

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m qr_validation.qr_parser <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    with open(image_path, 'rb') as f:
        result = parse_qr_image(f.read())
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
