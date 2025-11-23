# vpa_validator.py
"""
VPA (Virtual Payment Address) validation for QR codes
Comprehensive list of UPI providers in India
"""

import re
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Add parent directory to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# simple vpa pattern: localpart@provider   (allow . - _ and digits in local part)
VPA_RE = re.compile(r'^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z0-9._\-]{2,128}$')

DEFAULT_PROVIDERS = [
    "oksbi","okhdfcbank","okaxis","okicici","okpaytm","oksbi","upi","ybl","axis","sbi","hdfcbank","icici","phonepe","gpay","google","paytm"
]

PROVIDERS_FILE = Path(__file__).parent / "providers.json"

def load_providers():
    if PROVIDERS_FILE.exists():
        try:
            with open(PROVIDERS_FILE,'r',encoding='utf8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [p.lower() for p in data]
        except Exception:
            pass
    return [p.lower() for p in DEFAULT_PROVIDERS]

_PROVIDERS = set(load_providers())

# Known UPI providers
KNOWN_PROVIDERS = {
    # Major Banks
    'oksbi': 'State Bank of India',
    'sbi': 'State Bank of India',
    'okhdfcbank': 'HDFC Bank',
    'hdfcbank': 'HDFC Bank',
    'okaxis': 'Axis Bank',
    'axisbank': 'Axis Bank',
    'okicici': 'ICICI Bank',
    'icici': 'ICICI Bank',
    'federal': 'Federal Bank',
    'pnb': 'Punjab National Bank',
    'boi': 'Bank of India',
    'citi': 'Citibank',
    'sc': 'Standard Chartered',
    'rbl': 'RBL Bank',
    'kotak': 'Kotak Mahindra Bank',
    'indusind': 'IndusInd Bank',
    'yesbank': 'Yes Bank',
    'idbi': 'IDBI Bank',
    'unionbank': 'Union Bank',
    'canara': 'Canara Bank',
    'bob': 'Bank of Baroda',
    
    # Payment Apps - Major
    'paytm': 'Paytm',
    'paytmqr': 'Paytm QR',
    'pthdfc': 'Paytm (HDFC)',
    'ptaxis': 'Paytm (Axis)',
    'ptsbi': 'Paytm (SBI)',
    'ybl': 'PhonePe',
    'phonepe': 'PhonePe',
    'apl': 'Amazon Pay',
    'amazonpay': 'Amazon Pay',
    'ibl': 'BHIM (Axis)',
    'bim': 'BHIM',
    'gpay': 'Google Pay',
    'googlepay': 'Google Pay',
    'okgpay': 'Google Pay',
    
    # Fintech & Neo Banks
    'fbl': 'Freecharge',
    'freecharge': 'Freecharge',
    'mobikwik': 'MobiKwik',
    'ola': 'Ola Money',
    'jio': 'Jio Money',
    'airtel': 'Airtel Payments Bank',
    'airtelbank': 'Airtel Payments Bank',
    'postbank': 'India Post Payments Bank',
    'payzapp': 'PayZapp (HDFC)',
    'pockets': 'Pockets (ICICI)',
    'imobile': 'iMobile (ICICI)',
    
    # Payment Gateways & Aggregators
    'razorpay': 'Razorpay',
    'instamojo': 'Instamojo',
    'cashfree': 'Cashfree',
    'ccavenue': 'CCAvenue',
    'billdesk': 'BillDesk',
    'bharatpe': 'BharatPe',
    'phonepeqr': 'PhonePe QR',
    'superyes': 'SuperMoney',
    'supermoney': 'SuperMoney',
    
    # Regional & Co-operative Banks
    'saraswat': 'Saraswat Bank',
    'kvb': 'Karur Vysya Bank',
    'dcb': 'DCB Bank',
    'tamilnadmercantile': 'Tamilnad Mercantile Bank',
    'jkb': 'Jammu & Kashmir Bank',
    'iob': 'Indian Overseas Bank',
    'indianbank': 'Indian Bank',
    'corpbank': 'Corporation Bank',
    
    # Small Finance Banks
    'equitas': 'Equitas Small Finance Bank',
    'ujjivan': 'Ujjivan Small Finance Bank',
    'au': 'AU Small Finance Bank',
    'fino': 'Fino Payments Bank',
    'janabank': 'Jana Small Finance Bank',
    
    # Credit Card & Others
    'sbicard': 'SBI Card',
    'axiscard': 'Axis Bank Credit Card',
    'hdfccard': 'HDFC Credit Card',
    'icicicard': 'ICICI Credit Card',
}

def validate_vpa_format(vpa: str) -> dict:
    """
    Validate VPA format and provider
    Returns: {
        "verdict": "OK" | "WARN" | "BLOCK",
        "risk_score": float,
        "reasons": list[str],
        "provider": str
    }
    """
    logger.info(f"Validating VPA: {vpa}")
    
    # Check basic format: username@provider
    if not re.match(r'^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z0-9.\-_]{2,128}$', vpa):
        return {
            "verdict": "BLOCK",
            "risk_score": 0.9,
            "reasons": ["❌ Invalid VPA format"],
            "provider": None
        }
    
    # Extract provider
    provider = vpa.split('@')[-1].lower()
    
    # Check against known providers
    if provider in KNOWN_PROVIDERS:
        return {
            "verdict": "OK",
            "risk_score": 0.1,
            "reasons": [
                "✓ Valid VPA format",
                f"✓ Verified provider: {KNOWN_PROVIDERS[provider]}"
            ],
            "provider": KNOWN_PROVIDERS[provider]
        }
    else:
        # Unknown provider - warn but don't block (might be new/regional)
        return {
            "verdict": "WARN",
            "risk_score": 0.5,
            "reasons": [
                "✓ Valid VPA format",
                f"⚠️ Unrecognized payment provider: {provider}",
                "This might be a new or regional provider",
                "⚠️ Verify merchant authenticity before paying"
            ],
            "provider": provider
        }

def is_vpa_format(data: str) -> bool:
    """Quick check if string matches VPA format"""
    return bool(re.match(r'^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z0-9.\-_]{2,128}$', data))
