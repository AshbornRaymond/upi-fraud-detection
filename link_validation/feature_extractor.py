"""
Feature extractor matching the trained Stage 1 models
Extracts the EXACT features used during training
"""
import re
import math
from urllib.parse import urlparse, parse_qs
from collections import Counter

def extract_training_features(url: str) -> dict:
    """
    Extract features matching links_stage1.py training
    Returns dict with all 38 features expected by the models
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()
    query = parsed.query.lower()
    full_url = url.lower()
    
    features = {}
    
    # === BASE FEATURES (23 features) ===
    
    # Domain/SSL features (simplified - no external API calls)
    features['domain_age_days'] = 100.0  # Default: assume established domain
    
    # If domain contains suspicious keywords, treat as new/risky
    if any(word in domain for word in ['verify', 'secure', 'kyc', 'update', 'confirm', 'login', 'signin', 'account']):
        features['domain_age_days'] = 10.0  # Likely new/suspicious
    
    # TLD risk
    suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.gq', '.pw', '.cc', '.top', '.xyz', '.club', '.online', '.site']
    features['tld_risk'] = 0.8 if any(tld in domain for tld in suspicious_tlds) else 0.2
    
    # URL structure
    features['url_length'] = float(len(url))
    features['subdomain_depth'] = float(domain.count('.'))
    
    # ✅ FIXED: Brand impersonation detection
    brands = ['google', 'amazon', 'paytm', 'phonepe', 'gpay', 'axis', 'hdfc', 'icici', 'sbi', 'kotak', 'bank']
    
    # Official domains (whitelist)
    official_domains = [
        'google.com', 'google.co.in',
        'amazon.in', 'amazon.com',
        'paytm.com', 
        'phonepe.com',
        'axisbank.com', 'axisbank.co.in',
        'hdfcbank.com',
        'icicibank.com',
        'onlinesbi.sbi', 'onlinesbi.com',
        'kotak.com', 'kotakbank.com'
    ]
    
    # Check if domain contains brand name
    has_brand = any(brand in domain for brand in brands)
    
    # Check if it's an official domain
    is_official = any(official in domain for official in official_domains)
    
    # ✅ KEY FIX: If brand name is present but NOT official = HIGH RISK
    if has_brand and not is_official:
        features['brand_lev_distance'] = 1.0  # Brand impersonation detected
        features['domain_age_days'] = 5.0  # Treat as very new domain
    elif is_official:
        features['brand_lev_distance'] = 0.0  # Official domain
        features['domain_age_days'] = 3650.0  # Old, trusted domain
    else:
        features['brand_lev_distance'] = 999.0  # No brand present
    
    # SSL/Protocol
    features['ssl_valid'] = 1.0 if parsed.scheme == 'https' else 0.0
    features['is_http'] = 1.0 if parsed.scheme == 'http' else 0.0
    
    # Query analysis
    def entropy(s):
        if not s:
            return 0.0
        counts = Counter(s)
        length = len(s)
        return -sum((c/length) * math.log2(c/length) for c in counts.values())
    
    features['query_entropy'] = entropy(query) if query else 0.0
    features['redirect_count'] = 0.0  # Default (would need network check)
    
    # Keyword flags (phishing indicators)
    features['kw_kyc'] = 1.0 if 'kyc' in full_url else 0.0
    features['kw_verify'] = 1.0 if 'verify' in full_url else 0.0
    features['kw_bonus'] = 1.0 if 'bonus' in full_url else 0.0
    
    # UPI intent detection
    features['upi_intent_pay'] = 1.0 if 'upi://pay' in full_url else 0.0
    features['upi_intent_collect'] = 1.0 if 'upi://collect' in full_url else 0.0
    
    # UPI parameters
    params = parse_qs(query)
    features['upi_pa_present'] = 1.0 if 'pa' in params else 0.0
    features['upi_am_present'] = 1.0 if ('am' in params or 'amount' in params) else 0.0
    
    amount = 0.0
    if 'am' in params:
        try:
            amount = float(params['am'][0])
        except:
            pass
    elif 'amount' in params:
        try:
            amount = float(params['amount'][0])
        except:
            pass
    features['upi_amount'] = amount
    
    # VPA analysis (if present)
    pa_value = params.get('pa', [''])[0]
    vpa_pattern = re.compile(r'^([a-zA-Z0-9.\-_]{2,64})@([a-zA-Z0-9.\-_]{2,64})$')
    vpa_match = vpa_pattern.match(pa_value)
    
    features['vpa_format_valid'] = 1.0 if vpa_match else 0.0
    
    if vpa_match:
        provider = vpa_match.group(2).lower()
        known_providers = ['oksbi', 'okhdfcbank', 'okicici', 'okaxis', 'paytm', 'ybl', 'phonepe', 'gpay']
        features['vpa_provider_allow'] = 1.0 if provider in known_providers else 0.0
        features['vpa_entropy'] = entropy(vpa_match.group(1))
    else:
        features['vpa_provider_allow'] = 0.0
        features['vpa_entropy'] = 0.0
    
    # QR-related
    features['qr_present'] = 0.0  # Default for URL validation
    features['qr_param_missing_count'] = 0.0
    features['qr_from_shortener'] = 1.0 if any(short in domain for short in ['bit.ly', 'tinyurl', 'goo.gl', 't.co']) else 0.0
    
    # === ENGINEERED FEATURES (15 features) ===
    
    # Log transforms
    features['log_domain_age_days'] = math.log1p(max(0, features['domain_age_days']))
    features['log_upi_amount'] = math.log1p(max(0, features['upi_amount']))
    features['log_url_length'] = math.log1p(max(0, features['url_length']))
    features['log_query_entropy'] = math.log1p(max(0, features['query_entropy']))
    
    # Domain age flags
    features['is_new_domain_30'] = 1.0 if features['domain_age_days'] <= 30 else 0.0
    features['is_new_domain_60'] = 1.0 if features['domain_age_days'] <= 60 else 0.0
    
    # Risk flags
    features['risky_tld_flag'] = 1.0 if features['tld_risk'] >= 0.6 else 0.0
    features['brand_impersonation'] = 1.0 if (has_brand and not is_official) else 0.0  # ✅ FIXED
    features['long_url_flag'] = 1.0 if features['url_length'] >= 120 else 0.0
    features['deep_subdomain_flag'] = 1.0 if features['subdomain_depth'] >= 3 else 0.0
    features['http_or_bad_ssl'] = 1.0 if (features['is_http'] == 1.0 or features['ssl_valid'] == 0.0) else 0.0
    features['has_kyc_or_verify'] = 1.0 if (features['kw_kyc'] == 1.0 or features['kw_verify'] == 1.0) else 0.0
    features['small_amount_verification'] = 1.0 if (features['upi_am_present'] == 1.0 and features['upi_amount'] <= 10) else 0.0
    features['pay_intent_no_collect'] = 1.0 if (features['upi_intent_pay'] == 1.0 and features['upi_intent_collect'] == 0.0) else 0.0
    features['kyc_on_new_domain'] = 1.0 if (features['is_new_domain_60'] == 1.0 and features['has_kyc_or_verify'] == 1.0) else 0.0
    
    return features

def get_feature_array(features_dict: dict) -> list:
    """Convert feature dict to ordered array matching training order"""
    feature_order = [
        # Base features (23)
        "domain_age_days", "tld_risk", "url_length", "subdomain_depth", "brand_lev_distance",
        "ssl_valid", "is_http", "query_entropy", "redirect_count",
        "kw_kyc", "kw_verify", "kw_bonus",
        "upi_intent_pay", "upi_intent_collect", "upi_pa_present", "upi_am_present", "upi_amount",
        "vpa_format_valid", "vpa_provider_allow", "vpa_entropy",
        "qr_present", "qr_param_missing_count", "qr_from_shortener",
        # Engineered features (15)
        "log_domain_age_days", "log_upi_amount", "log_url_length", "log_query_entropy",
        "is_new_domain_30", "is_new_domain_60", "risky_tld_flag", "brand_impersonation",
        "long_url_flag", "deep_subdomain_flag", "http_or_bad_ssl", "has_kyc_or_verify",
        "small_amount_verification", "pay_intent_no_collect", "kyc_on_new_domain"
    ]
    
    return [features_dict.get(f, 0.0) for f in feature_order]