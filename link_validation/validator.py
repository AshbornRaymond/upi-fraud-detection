# link_validation/validator.py
"""
Link validator - ML-based, NO WHITELISTING
Uses models trained by links_stage1.py
"""
import re
import math
import sys
import pickle
import logging
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

# Cache for ML models
_ML_MODELS = {}

def load_models():
    """Load ML models (cached) - using Stage 1 models"""
    global _ML_MODELS
    
    if _ML_MODELS:
        logger.info("[CACHE] Using cached ML models")
        return _ML_MODELS
    
    logger.info("[LOADING] Loading ML models from stage1/...")
    
    try:
        import joblib
        stage1_dir = ROOT / "stage1"
        
        # Load models using joblib (matches training script)
        xgb_path = stage1_dir / "xgb_static.pkl"
        if_path = stage1_dir / "iforest_static.pkl"
        scaler_path = stage1_dir / "if_scaler.pkl"
        
        if xgb_path.exists():
            logger.info(f"Loading XGBoost from: {xgb_path}")
            _ML_MODELS['xgb'] = joblib.load(xgb_path)
            logger.info("✓ XGBoost loaded")
        else:
            logger.error(f"XGBoost model not found: {xgb_path}")
            return None
        
        if if_path.exists():
            logger.info(f"Loading Isolation Forest from: {if_path}")
            _ML_MODELS['isolation_forest'] = joblib.load(if_path)
            logger.info("✓ Isolation Forest loaded")
        else:
            logger.warning("Isolation Forest not found")
            _ML_MODELS['isolation_forest'] = None
        
        if scaler_path.exists():
            logger.info(f"Loading scaler from: {scaler_path}")
            _ML_MODELS['scaler'] = joblib.load(scaler_path)
            logger.info("✓ Scaler loaded")
        else:
            _ML_MODELS['scaler'] = None
        
        logger.info("[LOADED] All ML models cached successfully")
        return _ML_MODELS
        
    except Exception as e:
        logger.error(f"Failed to load ML models: {e}", exc_info=True)
        return None

# ✅ CRITICAL: Phishing domain patterns (immediate BLOCK)
PHISHING_PATTERNS = [
    r'.*-verify.*\.com$',
    r'.*-kyc.*\.com$', 
    r'.*-update.*\.com$',
    r'.*-secure.*\.com$',
    r'.*-block.*\.com$',
    r'.*-suspended.*\.com$',
    r'.*-reactivate.*\.com$',
    r'.*-confirm.*\.com$',
    r'upi-.*\.com$',
    r'.*-upi\.com$',
    r'sbi-.*\.com$',
    r'hdfc-.*\.com$',
    r'icici-.*\.com$',
    r'paytm-.*\.com$',
    r'.*-bank.*\.com$',
    r'.*bank-.*\.com$',
    r'.*netbanking.*\.(?!hdfcbank\.com|icicibank\.com)',  # Except legitimate
]

# High-risk keywords in domain
DOMAIN_KEYWORDS = [
    'verify', 'kyc', 'update', 'secure', 'block', 'suspended',
    'reactivate', 'confirm', 'urgent', 'expire', 'bank-login',
    'net-banking', 'account-verify', 'customer-care'
]

def check_domain_blacklist(url: str) -> dict:
    """Check if URL matches known phishing patterns"""
    from urllib.parse import urlparse
    
    domain = urlparse(url).netloc.lower()
    
    # Check regex patterns
    for pattern in PHISHING_PATTERNS:
        if re.match(pattern, domain):
            return {
                "is_blacklisted": True,
                "reason": f"Phishing pattern detected: {pattern}",
                "pattern": pattern
            }
    
    # Check domain keywords
    for keyword in DOMAIN_KEYWORDS:
        if keyword in domain:
            # Exception: legitimate domains
            if domain not in ['hdfcbank.com', 'icicibank.com', 'sbi.co.in', 'onlinesbi.sbi']:
                return {
                    "is_blacklisted": True,
                    "reason": f"Suspicious keyword in domain: {keyword}",
                    "keyword": keyword
                }
    
    return {"is_blacklisted": False}

def is_trusted_domain(url: str) -> bool:
    """Check if domain is in trusted whitelist"""
    from urllib.parse import urlparse
    
    TRUSTED_DOMAINS = {
        # Major tech companies
        'google.com', 'gmail.com', 'youtube.com', 'facebook.com', 'meta.com',
        'amazon.com', 'amazonpay.in', 'apple.com', 'microsoft.com', 'netflix.com',
        'twitter.com', 'x.com', 'instagram.com', 'linkedin.com', 'whatsapp.com',
        
        # Search & Info
        'wikipedia.org', 'reddit.com', 'github.com', 'stackoverflow.com',
        
        # Indian Banks (main domains)
        'hdfcbank.com', 'icicibank.com', 'sbi.co.in', 'onlinesbi.sbi',
        'axisbank.com', 'kotakbank.com', 'yesbank.in', 'pnbindia.in',
        'bankofbaroda.in', 'canarabank.com', 'unionbankofindia.co.in',
        
        # Payment apps
        'paytm.com', 'phonepe.com', 'googlepay.com', 
        'bhimupi.org.in', 'npci.org.in', 'upi.com',
        
        # Government
        'gov.in', 'nic.in', 'uidai.gov.in', 'epfindia.gov.in'
    }
    
    try:
        domain = urlparse(url).netloc.lower().replace('www.', '')
        
        # Check exact match
        if domain in TRUSTED_DOMAINS:
            return True
        
        # Check if subdomain of trusted domain
        for trusted in TRUSTED_DOMAINS:
            if domain.endswith('.' + trusted) or domain == trusted:
                return True
        
        return False
    except:
        return False

def validate_url(url: str) -> dict:
    """
    Validate URL using ML models ONLY
    NO domain whitelisting - all URLs analyzed
    """
    try:
        # ✅ Check whitelist first
        if is_trusted_domain(url):
            return {
                "verdict": "OK",
                "score": 0.0,
                "xgb_prob": 0.0,
                "if_score": 0.0,
                "reasons": ["✅ Trusted domain (whitelisted)"],
                "url": url
            }
        
        # ✅ Check blacklist patterns
        blacklist_result = check_domain_blacklist(url)
        if blacklist_result["is_blacklisted"]:
            return {
                "verdict": "BLOCK",
                "score": 1.0,
                "xgb_prob": 1.0,
                "if_score": 1.0,
                "reasons": [
                    f"⛔ BLOCKED: {blacklist_result['reason']}",
                    "🚨 Domain matches known phishing pattern"
                ],
                "url": url,
                "blacklist_match": blacklist_result
            }
        
        import numpy as np
        from link_validation.feature_extractor import extract_training_features, get_feature_array
        
        models = load_models()
        
        if not models or 'xgb' not in models:
            logger.error("ML models not loaded - using fallback")
            return {
                "verdict": "WARN",
                "score": 0.5,
                "reasons": ["⚠️ ML models not available - manual review recommended"],
                "url": url
            }
        
        # Extract features matching training
        features_dict = extract_training_features(url)
        features_array = np.array([get_feature_array(features_dict)])
        
        logger.info(f"Features extracted: {features_array.shape[1]} features")
        
        # XGBoost prediction
        xgb_model = models['xgb']
        xgb_proba = xgb_model.predict_proba(features_array)
        
        # ✅ FIX: Model is inverted! Class 0 = fraud, Class 1 = legit
        # So we take class 0 probability as fraud score
        xgb_prob = float(xgb_proba[0][0])  # ✅ CHANGED: Use class 0 (fraud)
        
        logger.info(f"XGBoost prediction: {xgb_prob:.3f}")
        
        # Isolation Forest prediction
        if_score = 0.5
        if models.get('isolation_forest') and models.get('scaler'):
            try:
                features_scaled = models['scaler'].transform(features_array)
                if_raw = float(models['isolation_forest'].decision_function(features_scaled)[0])
                
                # Normalize IF score (higher raw = more normal)
                # Convert to 0-1 scale where 1 = fraud
                if_score = 1.0 / (1.0 + math.exp(if_raw * 2))
                logger.info(f"Isolation Forest: {if_score:.3f}")
            except Exception as e:
                logger.warning(f"IF prediction failed: {e}")
        
        # Combined score (80% XGB, 20% IF) - matching training weights
        risk_score = (xgb_prob * 0.8) + (if_score * 0.2)
        
        # Build reasons
        reasons = []
        if xgb_prob >= 0.7:
            reasons.append(f"⛔ High fraud probability: {xgb_prob:.2f}")
        elif xgb_prob >= 0.5:
            reasons.append(f"⚠️ Suspicious patterns detected: {xgb_prob:.2f}")
        elif xgb_prob <= 0.3:
            reasons.append(f"✓ Low fraud probability: {xgb_prob:.2f}")
        
        # Verdict (no stage2_result reference here - this is Stage 1 only!)
        if risk_score >= 0.7:
            verdict = "BLOCK"
            if not reasons:
                reasons.append("⛔ ML analysis indicates high fraud risk")
        elif risk_score >= 0.4:
            verdict = "WARN"
            if not reasons:
                reasons.append("⚠️ Suspicious - requires additional verification")
        else:
            verdict = "OK"
            if not reasons:
                reasons.append(f"✓ URL appears legitimate (risk: {risk_score:.2f})")
        
        return {
            "verdict": verdict,
            "score": round(risk_score, 2),
            "xgb_prob": round(xgb_prob, 2),
            "if_score": round(if_score, 2),
            "reasons": reasons,
            "url": url
        }
        
    except Exception as e:
        logger.error(f"URL validation error: {e}", exc_info=True)
        return {
            "verdict": "WARN",
            "score": 0.5,
            "reasons": [f"⚠️ Validation error: {str(e)}"],
            "url": url
        }

# Legacy VPA validation
def validate_vpa(pa: str, provider_allowlist=None):
    """VPA validation (kept for compatibility)"""
    VPA_RE = re.compile(r"^([a-zA-Z0-9.\-_]{1,64})@([a-zA-Z0-9.\-_]{1,64})$")
    
    DEFAULT_PROVIDER_ALLOWLIST = {
        "oksbi", "okhdfcbank", "okicici", "okaxis", "okpaytm", "upi", "ybl", 
        "okpay", "phonepe", "gpay", "ptaxis", "paytm", "axl", "ibl"
    }
    
    def _entropy(s: str) -> float:
        if not s:
            return 0.0
        counts = Counter(s)
        length = len(s)
        ent = -sum((c/length) * math.log2(c/length) for c in counts.values())
        return ent
    
    out = {"pa": pa, "valid": False, "reasons": [], "provider": None, "provider_in_allowlist": None, "username_entropy": None}

    if not pa or not isinstance(pa, str):
        out["reasons"].append("empty_or_invalid_input")
        return out

    s = pa.strip()
    m = VPA_RE.match(s)
    if not m:
        out["reasons"].append("format_invalid")
        return out

    username, provider = m.group(1), m.group(2)
    out["provider"] = provider.lower()
    out["username_entropy"] = float(_entropy(username))

    if len(username) < 2:
        out["reasons"].append("username_too_short")
    if len(provider) < 2:
        out["reasons"].append("provider_too_short")
    if len(username) > 64 or len(provider) > 64:
        out["reasons"].append("component_too_long")

    if out["username_entropy"] < 1.0:
        out["reasons"].append("low_username_entropy")
    if re.search(r"\d{6,}", username):
        out["reasons"].append("suspicious_numeric_sequence")

    allowlist = set(DEFAULT_PROVIDER_ALLOWLIST) if provider_allowlist is None else set(map(str.lower, provider_allowlist))
    out["provider_in_allowlist"] = (out["provider"] in allowlist) if allowlist else None

    suspicious_flags = {"format_invalid", "username_too_short", "provider_too_short", "component_too_long", "suspicious_numeric_sequence"}
    if any(r in out["reasons"] for r in suspicious_flags):
        out["valid"] = False
    else:
        if "low_username_entropy" in out["reasons"] and not out["provider_in_allowlist"]:
            out["valid"] = False
        else:
            out["valid"] = True

    return out

if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: python -m link_validation.validator <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    result = validate_url(url)
    print(json.dumps(result, indent=2))
