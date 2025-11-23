"""
Utility functions for QR code analysis
"""
import re

def identify_qr_content_type(data: str) -> str:
    """
    Identify QR code type - wrapper that calls qr_parser
    """
    # Import here to avoid circular dependency
    from qr_validation.qr_parser import identify_qr_content_type as _identify
    return _identify(data)

def extract_vpa_from_upi(upi_string: str) -> str:
    """Extract VPA from UPI string"""
    match = re.search(r'pa=([^&]+)', upi_string)
    return match.group(1) if match else None

def is_protected_payment_qr(data: str) -> bool:
    """Check if QR is a protected payment app format (encrypted, not URL)"""
    data_lower = data.lower()
    
    # EMVCo format
    if data.startswith(('00020101', '00020201')):
        return True
    
    # Payment app keywords BUT NOT if it's an HTTP URL
    if data.startswith('http'):
        return False
    
    protected_keywords = ['gpay', 'phonepe', 'paytmmp', 'paytmqr', 'bharatpe', 'bhim']
    return any(kw in data_lower for kw in protected_keywords)

def get_qr_description(qr_type: str, data: str) -> tuple:
    """
    Get human-readable description for QR type
    Returns: (verdict, risk_score, reasons)
    """
    descriptions = {
        "protected_payment": (
            "OK",
            0.05,
            [
                "🔒 Encrypted payment QR code",
                "Can only be processed within official payment app",
                "Protected against tampering - Safe to scan"
            ]
        ),
        "upi": (
            "OK",
            0.2,
            ["Standard UPI payment QR", "VPA will be validated"]
        ),
        "geo": (
            "OK",
            0.1,
            ["📍 Location/Navigation QR", "Safe - Opens in maps app"]
        ),
        "vpa": (
            "OK",
            0.2,
            ["Plain VPA address", "Payment provider will be validated"]
        ),
        "tel": (
            "OK",
            0.1,
            ["📞 Phone number", "Safe - Opens dialer"]
        ),
        "mailto": (
            "OK",
            0.1,
            ["📧 Email address", "Safe - Opens email client"]
        ),
        "sms": (
            "OK",
            0.1,
            ["💬 SMS/Message", "Safe - Opens messaging app"]
        ),
        "wifi": (
            "OK",
            0.1,
            ["📶 WiFi credentials", "Safe - For network connection"]
        ),
        "vcard": (
            "OK",
            0.1,
            ["👤 Contact card", "Safe - Adds contact"]
        ),
        "intent": (
            "OK",
            0.15,
            ["📲 App intent", "Opens specific application"]
        ),
        "text": (
            "OK",
            0.15,
            ["Plain text/code", "No fraud indicators"]
        ),
        "url": (
            "WARN",
            0.5,
            [
                "🔗 URL detected - Running ML analysis...",
                "All URLs are validated through 2-stage detection",
                "No domain is whitelisted by default"
            ]
        ),
        "unknown": (
            "WARN",
            0.4,
            ["⚠️ Unknown QR format", "Scan with caution"]
        )
    }
    
    return descriptions.get(qr_type, ("WARN", 0.5, ["Unknown QR type"]))
