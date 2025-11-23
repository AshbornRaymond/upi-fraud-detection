# qr_api.py
from pathlib import Path
from .qr_parser import parse_qr

def process_qr(img_path: str) -> dict:
    """
    Main backend function.
    Returns:
    {
        "type": "url" / "upi" / "unknown",
        "route": "link_validation" / "vpa_validation" / "none",
        "parsed": {...}
    }
    """
    img_path = str(Path(img_path))
    return parse_qr(img_path)
