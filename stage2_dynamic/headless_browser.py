"""
Stage 2 Dynamic Scanner - Headless browser analysis with ML model support
"""
from pathlib import Path
import requests
from urllib.parse import urlparse
import json

# Paths
STAGE2_DIR = Path(__file__).parent
MODEL_PATH = STAGE2_DIR / "xgb_dynamic.pkl"
SCALER_PATH = STAGE2_DIR / "dynamic_scaler.pkl"
CONFIG_PATH = STAGE2_DIR / "dynamic_config.json"

# Global model cache
_DYNAMIC_MODEL = None
_DYNAMIC_SCALER = None
_DYNAMIC_CONFIG = None

# Expanded trusted domains and patterns
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

# Bank domain patterns (for fuzzy matching)
BANK_KEYWORDS = ['bank', 'banking', 'netbanking']

# Suspicious TLDs (keep these flagged)
SUSPICIOUS_TLDS = ['.shop', '.xyz', '.top', '.online', '.icu', '.live', '.buzz', '.click', '.gq', '.ml', '.tk', '.ga', '.cf']

def is_trusted_domain(domain: str) -> bool:
    """Check if domain is trusted"""
    domain = domain.lower()
    
    # Remove www. prefix
    if domain.startswith('www.'):
        domain = domain[4:]
    
    # Exact match
    if domain in TRUSTED_DOMAINS:
        return True
    
    # Subdomain match (e.g., retail.onlinesbi.sbi)
    for trusted in TRUSTED_DOMAINS:
        if domain.endswith('.' + trusted) or domain == trusted:
            return True
    
    return False

def is_likely_bank_domain(domain: str) -> bool:
    """Check if domain looks like a bank (has bank keywords + .in/.co.in TLD)"""
    domain = domain.lower()
    
    # Must have bank-related keyword
    has_bank_keyword = any(kw in domain for kw in BANK_KEYWORDS)
    
    # Must have legitimate TLD
    has_legit_tld = domain.endswith(('.in', '.co.in', '.org.in', '.com'))
    
    # Must NOT have suspicious TLD
    has_suspicious_tld = any(domain.endswith(tld) for tld in SUSPICIOUS_TLDS)
    
    return has_bank_keyword and has_legit_tld and not has_suspicious_tld

def load_stage2_model():
    """Load Stage 2 ML model (cached)"""
    global _DYNAMIC_MODEL, _DYNAMIC_SCALER, _DYNAMIC_CONFIG
    
    if _DYNAMIC_MODEL is not None:
        return _DYNAMIC_MODEL, _DYNAMIC_SCALER, _DYNAMIC_CONFIG
    
    try:
        import joblib
        
        if MODEL_PATH.exists():
            _DYNAMIC_MODEL = joblib.load(MODEL_PATH)
            print(f"[STAGE2 ML] Loaded model from {MODEL_PATH}")
        
        if SCALER_PATH.exists():
            _DYNAMIC_SCALER = joblib.load(SCALER_PATH)
            print(f"[STAGE2 ML] Loaded scaler from {SCALER_PATH}")
        
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                _DYNAMIC_CONFIG = json.load(f)
            print(f"[STAGE2 ML] Loaded config from {CONFIG_PATH}")
        
        return _DYNAMIC_MODEL, _DYNAMIC_SCALER, _DYNAMIC_CONFIG
    
    except Exception as e:
        print(f"[STAGE2 ML] Failed to load model: {e}")
        return None, None, None

def extract_behavioral_features(url: str, content: str, behavioral_flags: dict):
    """Extract features for Stage 2 ML model"""
    features = {
        # Domain features
        "has_suspicious_tld": int(behavioral_flags.get("suspicious_domain", False)),
        "redirects_to_different_domain": int(behavioral_flags.get("redirects_to_different_domain", False)),
        
        # Form/input features
        "has_password_field": int(behavioral_flags.get("has_password_field", False)),
        "has_otp_field": int(behavioral_flags.get("has_otp_field", False)),
        "mimics_banking_ui": int(behavioral_flags.get("mimics_banking_ui", False)),
        "requests_sensitive_info": int(behavioral_flags.get("requests_sensitive_info", False)),
        
        # Content features
        "form_count": content.lower().count("<form") if content else 0,
        "input_count": content.lower().count("<input") if content else 0,
        "script_count": content.lower().count("<script") if content else 0,
        "iframe_count": content.lower().count("<iframe") if content else 0,
        
        # Keyword features
        "has_kyc_keyword": int("kyc" in content.lower() if content else False),
        "has_verify_keyword": int("verify" in content.lower() if content else False),
        "has_urgent_keyword": int("urgent" in content.lower() if content else False),
        "has_reward_keyword": int(any(k in content.lower() for k in ["reward", "cashback", "bonus"]) if content else False),
        
        # Network features
        "connection_failed": int(behavioral_flags.get("connection_failed", False)),
    }
    
    return features

def scan_url_headless(url: str, headless: bool = True):
    """
    Scan URL using headless browser and extract behavioral features
    """
    try:
        domain = urlparse(url).netloc.lower().replace('www.', '')
        
        # ✅ FIX: Return OK verdict for trusted domains
        if is_trusted_domain(domain):
            print(f"[STAGE2] Domain {domain} is whitelisted as trusted")
            return {
                "url": url,
                "risk_score": 0.0,  # ✅ Changed from 0.5 to 0.0
                "verdict": "OK",     # ✅ Add explicit verdict
                "behavioral_flags": {"trusted_domain": True},
                "features": {},
                "reason": "Trusted domain - bypassed scanning"
            }
        
        behavioral_flags = {
            "redirects_to_different_domain": False,
            "has_password_field": False,
            "has_otp_field": False,
            "mimics_banking_ui": False,
            "requests_sensitive_info": False,
            "suspicious_javascript": False,
            "suspicious_domain": False,
            "connection_failed": False,
            "trusted_domain": False
        }
        
        risk_score = 0.0
        content = ""
        
        # Check if domain looks like a bank but isn't whitelisted
        looks_like_bank = is_likely_bank_domain(domain)
        
        # Domain reputation check - ONLY flag truly suspicious TLDs
        if any(domain.endswith(tld) for tld in SUSPICIOUS_TLDS):
            behavioral_flags["suspicious_domain"] = True
            risk_score += 0.35
        
        # Check domain keywords - but be more lenient
        suspicious_keywords = ['cashback', 'reward', 'bonus', 'free-money', 'instant-win', 'verify']
        domain_lower = domain.lower()
        
        # Only flag if multiple suspicious keywords or with bad TLD
        keyword_count = sum(1 for kw in suspicious_keywords if kw in domain_lower)
        if keyword_count >= 2 or (keyword_count >= 1 and behavioral_flags["suspicious_domain"]):
            risk_score += 0.25
        
        # Check for brand impersonation - more precise matching
        brands = {
            'paytm': 'paytm.com',
            'phonepe': 'phonepe.com',
            'gpay': 'pay.google.com',
            'googlepay': 'pay.google.com',
            'sbi': 'onlinesbi.sbi',
            'hdfc': 'hdfcbank.com',
            'icici': 'icicibank.com',
            'axis': 'axisbank.com',
            'kotak': 'kotak.com'
        }
        
        for brand, official in brands.items():
            if brand in domain_lower and not domain.endswith(official):
                # Check if it's a legitimate subdomain or different bank
                if not is_trusted_domain(domain):
                    behavioral_flags["suspicious_domain"] = True
                    risk_score += 0.40
                    break
        
        # Try to fetch the page
        try:
            response = requests.get(url, timeout=5, allow_redirects=True, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            content = response.text
            content_lower = content.lower()
            
            # Check redirects
            redirect_domain = urlparse(response.url).netloc.lower()
            redirect_check = redirect_domain[4:] if redirect_domain.startswith('www.') else redirect_domain
            
            if redirect_check != domain:
                # If redirects to trusted domain, it's OK
                if is_trusted_domain(redirect_check):
                    return {
                        "success": True,
                        "verdict": "OK",
                        "score": 0.1,
                        "behavioral_flags": {"redirects_to_trusted_domain": True},
                        "url": url,
                        "reason": f"Redirects to trusted domain: {redirect_domain}"
                    }
                else:
                    behavioral_flags["redirects_to_different_domain"] = True
                    risk_score += 0.15
            
            # For legitimate sites, password/OTP fields are NORMAL - don't penalize
            has_login_form = 'type="password"' in content_lower or 'type=password' in content_lower
            has_otp = any(k in content_lower for k in ['otp', 'cvv', 'pin'])
            
            behavioral_flags["has_password_field"] = has_login_form
            behavioral_flags["has_otp_field"] = has_otp
            
            # Only penalize if ALSO has suspicious domain
            if has_login_form and behavioral_flags["suspicious_domain"]:
                risk_score += 0.15
            
            if has_otp and behavioral_flags["suspicious_domain"]:
                risk_score += 0.20
            
            # Banking UI is normal for banks - don't penalize unless suspicious
            banking_keywords = ['netbanking', 'account balance', 'fund transfer', 'transaction']
            has_banking_ui = any(kw in content_lower for kw in banking_keywords)
            behavioral_flags["mimics_banking_ui"] = has_banking_ui
            
            if has_banking_ui and behavioral_flags["suspicious_domain"]:
                risk_score += 0.25
            
            # Sensitive info requests - only flag on suspicious domains
            sensitive_fields = ['aadhaar', 'pan card', 'debit card', 'credit card', 'card number', 'expiry']
            has_sensitive = any(field in content_lower for field in sensitive_fields)
            behavioral_flags["requests_sensitive_info"] = has_sensitive
            
            if has_sensitive and behavioral_flags["suspicious_domain"]:
                risk_score += 0.30
            
        except (requests.Timeout, requests.RequestException) as e:
            behavioral_flags["connection_failed"] = True
            
            # CRITICAL CHANGE: Connection failure handling
            if looks_like_bank and not is_trusted_domain(domain):
                # Looks like a bank but not in whitelist AND can't connect = VERY SUSPICIOUS
                print(f"[STAGE2] Suspicious: Bank-like domain {domain} cannot be reached")
                risk_score += 0.50  # Heavy penalty
            elif behavioral_flags["suspicious_domain"]:
                # Suspicious domain that can't connect = likely scam
                risk_score += 0.40
            else:
                # Unknown domain that can't connect = moderately suspicious
                risk_score += 0.25
        
        # Try ML model scoring
        ml_score = None
        model, scaler, config = load_stage2_model()
        
        if model is not None and scaler is not None:
            try:
                import pandas as pd
                import numpy as np
                
                features = extract_behavioral_features(url, content, behavioral_flags)
                feature_list = config.get("feature_list", list(features.keys()))
                
                for feat in feature_list:
                    if feat not in features:
                        features[feat] = 0
                
                df = pd.DataFrame([features])
                X = df[feature_list].fillna(0).astype(float)
                X_scaled = scaler.transform(X)
                ml_prob = float(model.predict_proba(X_scaled)[0, 1])
                ml_score = ml_prob
                
                print(f"[STAGE2 ML] Model score: {ml_score:.2f}, Rule score: {risk_score:.2f}")
                
                # If ML score is very low (<0.3) and rules are medium, trust ML more
                if ml_score < 0.3 and risk_score < 0.6:
                    risk_score = 0.4 * ml_score + 0.6 * risk_score  # Trust rules more for edge cases
                else:
                    risk_score = 0.6 * ml_score + 0.4 * risk_score  # Balanced
                
            except Exception as e:
                print(f"[STAGE2 ML] Prediction failed: {e}")
        
        # More lenient thresholds for whitelisted patterns, strict for unknowns
        if looks_like_bank and behavioral_flags["connection_failed"]:
            # Bank-like domain that doesn't respond = treat carefully
            if risk_score >= 0.6:
                verdict = "BLOCK"
            elif risk_score >= 0.4:
                verdict = "WARN"
            else:
                verdict = "WARN"  # Default to WARN if unsure
        else:
            # Normal thresholds
            if risk_score >= 0.75:
                verdict = "BLOCK"
            elif risk_score >= 0.45:
                verdict = "WARN"
            else:
                verdict = "OK"
        
        result = {
            "success": True,
            "verdict": verdict,
            "score": round(min(risk_score, 1.0), 2),
            "behavioral_flags": behavioral_flags,
            "url": url
        }
        
        if ml_score is not None:
            result["ml_score"] = round(ml_score, 2)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "url": url,
            "verdict": "WARN",
            "score": 0.5
        }

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Stage 2 headless browser scan")
    parser.add_argument("--url", required=True, help="URL to scan")
    parser.add_argument("--headless", default="true", help="Run in headless mode")
    args = parser.parse_args()
    
    result = scan_url_headless(args.url, headless=args.headless.lower() == "true")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()