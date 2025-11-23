# link_validation/link_orchestrator.py
"""
Optimized link validation with cached ML models
"""

import argparse, json, subprocess, sys, os
from urllib.parse import urlparse
import re
from pathlib import Path

# Lazy imports - only load when needed
def load_heavy_deps():
    """Load heavy dependencies only when actually needed"""
    global joblib, tldextract
    import joblib
    import tldextract
    return joblib, tldextract

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ========== GLOBAL MODEL CACHE ==========
_MODEL_CACHE = {
    "loaded": False,
    "cfg": None,
    "xgb": None,
    "iforest": None,
    "scaler": None
}

def load_stage1_artifacts(stage1_dir):
    """Load ML models once and cache them globally"""
    global _MODEL_CACHE
    
    # Return cached models if already loaded
    if _MODEL_CACHE["loaded"]:
        print("[CACHE] Using cached ML models")
        return _MODEL_CACHE["cfg"], _MODEL_CACHE["xgb"], _MODEL_CACHE["iforest"], _MODEL_CACHE["scaler"]
    
    print("[LOADING] Loading ML models (one-time operation)...")
    
    # Lazy load heavy dependencies
    joblib, _ = load_heavy_deps()
    
    cfg_fp = os.path.join(stage1_dir, "ensemble_config.json")
    xgb_fp = os.path.join(stage1_dir, "xgb_static.pkl")
    if_fp = os.path.join(stage1_dir, "iforest_static.pkl")
    scaler_fp = os.path.join(stage1_dir, "if_scaler.pkl")
    
    if not os.path.exists(cfg_fp) or not os.path.exists(xgb_fp):
        raise FileNotFoundError("Missing stage1 artifacts in: " + stage1_dir)
    
    cfg = json.load(open(cfg_fp))
    xgb = joblib.load(xgb_fp)
    
    if os.path.exists(if_fp):
        iforest = joblib.load(if_fp)
    else:
        iforest = None
    
    scaler = joblib.load(scaler_fp) if os.path.exists(scaler_fp) else None
    
    # Cache the loaded models
    _MODEL_CACHE["cfg"] = cfg
    _MODEL_CACHE["xgb"] = xgb
    _MODEL_CACHE["iforest"] = iforest
    _MODEL_CACHE["scaler"] = scaler
    _MODEL_CACHE["loaded"] = True
    
    print("[LOADED] ML models cached successfully")
    
    return cfg, xgb, iforest, scaler

def simple_features_from_url(url: str):
    """Extract features from URL for ML model"""
    parsed = urlparse(url)
    ext = tldextract.extract(url)
    host = parsed.netloc.lower()
    domain = ext.domain.lower()
    tld = ext.suffix.lower()
    path = parsed.path or ""
    qs = parsed.query or ""

    features = {}
    features["url_length"] = len(url)
    features["is_http"] = 1 if parsed.scheme == "http" else 0
    features["subdomain_depth"] = host.count(".") - (1 if domain else 0)
    features["kw_kyc"] = 1 if re.search(r'\bkyc\b', url, re.I) else 0
    features["kw_verify"] = 1 if re.search(r'\bverify\b', url, re.I) else 0
    features["kw_bonus"] = 1 if re.search(r'\bbonus|cashback|reward\b', url, re.I) else 0
    
    # Brand detection
    brands = ["sbi","icici","hdfc","paytm","gpay","phonepe"]
    features["brand_lev_distance"] = min([0 if b in host else 5 for b in brands])
    
    # Domain age (default to old domain)
    features["domain_age_days"] = 9999
    
    # Query complexity
    features["query_entropy"] = len(qs)
    
    return features

def mk_feature_vector(feats_cfg, simple_feats):
    """Build feature vector aligned with model expectations"""
    fl = feats_cfg["feature_list"]
    vec = []
    for f in fl:
        vec.append(float(simple_feats.get(f, 0.0)))
    return vec

def combine_and_decide(cfg, xgb_prob, if_score):
    """Combine XGBoost and Isolation Forest scores"""
    w = cfg["ensemble"]["w_link"]
    t_block = cfg["ensemble"]["t_block"]
    t_ok = cfg["ensemble"]["t_ok"]
    final = w * xgb_prob + (1 - w) * if_score
    
    if final >= t_block:
        return "BLOCK", final
    if final <= t_ok:
        return "OK", final
    return "WARN", final

def static_score_for_url(url: str):
    """
    Fast ML-based link validation with model caching
    """
    try:
        # Quick whitelist check (before loading models)
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        trusted = ['google.com', 'youtube.com', 'facebook.com', 'twitter.com', 
                   'instagram.com', 'amazon.in', 'flipkart.com', 'paytm.com',
                   'phonepe.com', 'gpay.com', 'netflix.com', 'linkedin.com']
        
        if any(t in domain for t in trusted):
            return {
                "verdict": "OK",
                "score": 0.0,
                "reasons": ["Trusted domain (whitelisted)"],
                "url": url
            }
        
        # Load models (cached after first load)
        stage1_dir = os.path.join(ROOT, "stage1")
        cfg, xgb, iforest, scaler = load_stage1_artifacts(stage1_dir)
        
        # Extract features
        feats = simple_features_from_url(url)
        vec = mk_feature_vector(cfg, feats)
        
        # XGBoost prediction
        xgb_prob = float(xgb.predict_proba([vec])[:,1]) if hasattr(xgb, "predict_proba") else float(xgb.predict([vec])[0])
        
        # Isolation Forest prediction
        if iforest is not None and scaler is not None:
            import numpy as np
            scaled = scaler.transform([vec])
            raw_if = iforest.decision_function(scaled)
            
            import pandas as pd
            ranks = pd.Series(raw_if).rank(method="average").to_numpy()
            anom = (ranks - ranks.min()) / (ranks.max() - ranks.min() + 1e-9)
            if_score = float(1.0 - anom[0])
        else:
            if_score = 0.5
        
        # Combine scores
        verdict, final_score = combine_and_decide(cfg, xgb_prob, if_score)
        
        # Generate reasons
        reasons = []
        if xgb_prob > 0.6:
            reasons.append(f"High fraud probability: {xgb_prob:.2f}")
        if if_score > 0.6:
            reasons.append(f"Anomalous pattern: {if_score:.2f}")
        if not reasons:
            reasons.append("ML analysis complete")
        
        return {
            "verdict": verdict,
            "score": round(final_score, 2),
            "xgb_prob": round(xgb_prob, 2),
            "if_score": round(if_score, 2),
            "reasons": reasons,
            "url": url
        }
    
    except FileNotFoundError as e:
        # Fallback to rule-based if models not found
        print(f"[FALLBACK] ML models not found: {e}")
        return fallback_rule_based(url)
    
    except Exception as e:
        print(f"[ERROR] ML validation failed: {e}")
        return {
            "verdict": "ERROR",
            "score": 0.5,
            "error": str(e),
            "url": url
        }

def fallback_rule_based(url: str):
    """Simple rule-based fallback if ML fails"""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    score = 0.0
    reasons = []
    
    # Suspicious keywords
    suspicious_keywords = ['verify', 'secure', 'kyc', 'update', 'confirm', 
                          'account', 'blocked', 'suspended', 'urgent']
    
    for keyword in suspicious_keywords:
        if keyword in domain or keyword in url.lower():
            score += 0.15
            reasons.append(f"Suspicious keyword: {keyword}")
    
    # Numbers in domain
    if any(char.isdigit() for char in domain):
        score += 0.2
        reasons.append("Numbers in domain")
    
    # Suspicious TLDs
    suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.gq', '.online', '.shop', 
                      '.xyz', '.top', '.live', '.site']
    
    for tld in suspicious_tlds:
        if domain.endswith(tld):
            score += 0.3
            reasons.append(f"Suspicious TLD: {tld}")
            break
    
    # Bank phishing
    bank_names = ['sbi', 'hdfc', 'icici', 'axis', 'kotak']
    official_domains = ['onlinesbi.sbi', 'hdfcbank.com', 'icicibank.com', 
                       'axisbank.com', 'kotak.com']
    
    for bank in bank_names:
        if bank in domain:
            if not any(official in domain for official in official_domains):
                score += 0.4
                reasons.append(f"Potential {bank.upper()} phishing")
                break
    
    if score >= 0.7:
        verdict = "BLOCK"
    elif score >= 0.3:
        verdict = "WARN"
    else:
        verdict = "OK"
    
    reasons.append("(Rule-based fallback)")
    
    return {
        "verdict": verdict,
        "score": round(score, 2),
        "reasons": reasons,
        "url": url
    }

def run_link_validation(url: str):
    """Wrapper for backward compatibility"""
    return static_score_for_url(url)

def call_stage2(url):
    """Call stage2 dynamic scanner"""
    print("Invoking stage2_dynamic headless scanner for deep scan...")
    cmd = [sys.executable, "-m", "stage2_dynamic.scan_playwright", "--url", url, "--headless", "true"]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print("Stage2 scan failed:", e)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--deep", action="store_true", help="If WARN, run stage2 dynamic scan")
    args = p.parse_args()

    result = static_score_for_url(args.url)
    print(json.dumps(result, indent=2))
    
    if result["verdict"] == "WARN" and args.deep:
        call_stage2(args.url)

if __name__ == "__main__":
    main()
