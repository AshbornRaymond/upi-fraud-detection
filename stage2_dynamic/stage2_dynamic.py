#!/usr/bin/env python
# stage2_dynamic/get_warn_urls_clean.py
# Robust Stage-2 scoring: validates input, skips malformed rows,
# saves scored_full.csv, and optionally creates a relaxed warn set.

import json
import joblib
import pandas as pd
import numpy as np
import re
import math
import socket
import ssl
import requests
import tldextract
import shutil
import time
import traceback
from urllib.parse import urlparse, parse_qs, unquote
from Levenshtein import distance as levenshtein
from pathlib import Path

# ----------------- EDIT THESE PATHS -----------------
S1   = Path(r"D:\major project\stage1")       # folder with xgb_static.pkl, iforest_static.pkl, if_scaler.pkl, ensemble_config.json
DATA = Path(r"D:\major project\data")         # folder with candidate_urls.csv and where outputs will be written
# ---------------------------------------------------

DATA.mkdir(parents=True, exist_ok=True)

def safe_print(*a, **k):
    print(*a, **k)

# ---------------- load stage-1 artifacts (defensive) ----------------
def load_stage1_artifacts(s1):
    missing = []
    def load_json(p):
        try:
            return json.load(open(p, "r", encoding="utf8"))
        except Exception as e:
            raise RuntimeError(f"Failed to load JSON {p}: {e}")
    def load_joblib(p):
        try:
            return joblib.load(p)
        except Exception as e:
            raise RuntimeError(f"Failed to load model {p}: {e}")

    cfg = None
    xgb = None
    iforest = None
    scaler = None

    cfg_fp = s1 / "ensemble_config.json"
    xgb_fp = s1 / "xgb_static.pkl"
    if_fp = s1 / "iforest_static.pkl"
    if_scaler_fp = s1 / "if_scaler.pkl"

    if not cfg_fp.exists():
        raise FileNotFoundError(f"Missing ensemble config: {cfg_fp}")
    cfg = load_json(cfg_fp)

    # optional loads: if missing, script can still run but will warn and use fallbacks
    try:
        if xgb_fp.exists():
            xgb = load_joblib(xgb_fp)
        else:
            safe_print("Warning: xgb_static.pkl not found; xgb_prob will be zeroed.")
    except Exception as e:
        raise

    try:
        if if_fp.exists():
            iforest = load_joblib(if_fp)
        else:
            safe_print("Warning: iforest_static.pkl not found; if_score will be zeroed.")
    except Exception as e:
        raise

    try:
        if if_scaler_fp.exists():
            scaler = load_joblib(if_scaler_fp)
        else:
            safe_print("Warning: if_scaler.pkl not found; if_score will be zeroed.")
    except Exception as e:
        raise

    return cfg, xgb, iforest, scaler

# LAZY LOAD - don't load on import
cfg = None
xgb = None
iforest = None
scaler = None
FEATURES = []
W_LINK = 0.8
T_BLOCK = 0.85
T_OK = 0.15

def ensure_models_loaded():
    """Load models only when needed"""
    global cfg, xgb, iforest, scaler, FEATURES, W_LINK, T_BLOCK, T_OK
    if cfg is None:
        cfg, xgb, iforest, scaler = load_stage1_artifacts(S1)
        FEATURES = cfg.get("feature_list", [])
        W_LINK   = cfg.get("ensemble", {}).get("w_link", 0.8)
        T_BLOCK  = cfg.get("ensemble", {}).get("t_block", 0.85)
        T_OK     = cfg.get("ensemble", {}).get("t_ok", 0.15)

# ---------------- helpers ----------------
KNOWN_BRANDS = ["sbi","hdfc","icici","axis","kotak","paytm","phonepe","gpay","googlepay","onlinesbi","yono"]
RISKY_TLDS   = {"xyz","shop","online","top","icu","live","buzz","info"}
ALLOWLIST_VPA_PROVIDERS = {"oksbi","okhdfcbank","okaxis","okicici","apl","ybl","ibl","paytm","paytmqr"}

def tld_risk_score(tld): return 0.8 if (tld and tld.lower() in RISKY_TLDS) else 0.2

def text_entropy(s):
    if not s: return 0.0
    from collections import Counter
    p, n = Counter(s), float(len(s))
    return -sum((c/n)*math.log2(c/n) for c in p.values())

def subdomain_depth(h):
    if not h: return 0
    return max(0, len(h.split(".")) - 2)

def brand_lev_distance(h):
    h = (h or "").lower()
    try:
        return min(levenshtein(h, b) for b in KNOWN_BRANDS) if h else 12
    except Exception:
        return 12

def find_upi_links(s):
    return re.findall(r"(upi://[^\s\"'<>]+|intent://upi/pay[^\s\"'<>]*|gpay://upi/[^\s\"'<>]*|phonepe://upi/[^\s\"'<>]*)", s or "", re.I)

def parse_upi_params(u):
    # parse simple query params after '?'
    q = u.split("?",1)[1] if "?" in u else ""
    params = {k.lower(): v for k,v in parse_qs(q).items()}
    # flatten
    params = {k: (v[0] if isinstance(v, list) and len(v)>0 else v) for k,v in params.items()}
    try:
        am = float(params.get("am", params.get("amount", 0)) or 0)
    except Exception:
        am = 0.0
    return dict(intent_pay=int(u.lower().startswith("upi://pay") or "upi/pay" in u.lower()),
                intent_collect=int(u.lower().startswith("upi://collect")),
                pa_present=int("pa" in params),
                am_present=int(("am" in params) or ("amount" in params)),
                amount=am)

def vpa_feats(v):
    fmt = int(bool(re.match(r"^[a-zA-Z0-9.\-_]{2,}@[a-zA-Z0-9.\-_]{2,}$", v)))
    provider = v.split("@")[-1].lower() if "@" in v else ""
    allow = int(provider in ALLOWLIST_VPA_PROVIDERS)
    name  = v.split("@")[0] if "@" in v else v
    return fmt, allow, text_entropy(name.lower())

def get_domain_age_days(_domain):
    # placeholder: if you add whois integration, replace here
    return 180.0

def is_ssl_valid(url):
    try:
        p = urlparse(url)
        if p.scheme.lower() != "https":
            return 1  # keep 1 for 'valid' on non-https so earlier logic remains lenient
        host = p.hostname
        port = p.port or 443
        if not host:
            return 0
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=3) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as s:
                _ = s.getpeercert()
        return 1
    except Exception:
        return 0

def expand_shorteners(url, timeout=4):
    # Try HEAD first (faster), fall back to GET
    try:
        r = requests.head(url, allow_redirects=True, timeout=timeout)
        return r.url, len(r.history)
    except Exception:
        try:
            r = requests.get(url, allow_redirects=True, timeout=timeout)
            return r.url, len(r.history)
        except Exception:
            return url, 0

def extract_features(url):
    final, redirs = expand_shorteners(url)
    p = urlparse(final)
    host = p.hostname or ""
    ext = tldextract.extract(final)
    eTLD1 = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
    tld = ext.suffix.split(".")[0] if ext.suffix else ""
    q = (p.query or "") + (("#"+p.fragment) if p.fragment else "")
    feats = {
        "domain_age_days": float(get_domain_age_days(eTLD1)),
        "tld_risk": float(tld_risk_score(tld)),
        "url_length": float(len(final)),
        "subdomain_depth": int(subdomain_depth(host)),
        "brand_lev_distance": float(brand_lev_distance(host)),
        "ssl_valid": int(is_ssl_valid(final)),
        "is_http": int(p.scheme.lower()=="http"),
        "query_entropy": float(text_entropy(unquote(q))),
        "redirect_count": int(redirs),
        "kw_kyc": int("kyc" in final.lower()),
        "kw_verify": int(("verify" in final.lower()) or ("verification" in final.lower())),
        "kw_bonus": int(any(k in final.lower() for k in ["bonus","reward","cashback"])),
        "upi_intent_pay": 0, "upi_intent_collect": 0, "upi_pa_present": 0, "upi_am_present": 0, "upi_amount": 0.0,
        "vpa_format_valid": 0, "vpa_provider_allow": 0, "vpa_entropy": 0.0,
        "qr_present": 0, "qr_param_missing_count": 0, "qr_from_shortener": int(redirs>0),
    }
    try:
        for u in find_upi_links(final):
            F = parse_upi_params(u)
            feats["upi_intent_pay"]     = max(feats["upi_intent_pay"], F["intent_pay"])
            feats["upi_intent_collect"] = max(feats["upi_intent_collect"], F["intent_collect"])
            feats["upi_pa_present"]     = max(feats["upi_pa_present"], F["pa_present"])
            feats["upi_am_present"]     = max(feats["upi_am_present"], F["am_present"])
            feats["upi_amount"]         = max(feats["upi_amount"], F["amount"])
    except Exception:
        pass

    m = re.search(r"(?:^|[?&])pa=([A-Za-z0-9.\-_]+@[A-Za-z0-9.\-_]+)", final)
    if m:
        try:
            fmt, allow, ent = vpa_feats(m.group(1))
            feats.update(vpa_format_valid=int(fmt), vpa_provider_allow=int(allow), vpa_entropy=float(ent))
        except Exception:
            pass
    return feats

def add_engineering(df):
    df = df.copy()
    for c in ["domain_age_days","upi_amount","url_length","query_entropy"]:
        df[f"log_{c}"] = np.log1p(df[c].clip(lower=0))
    df["is_new_domain_30"]   = (df["domain_age_days"]<=30).astype(int)
    df["is_new_domain_60"]   = (df["domain_age_days"]<=60).astype(int)
    df["risky_tld_flag"]     = (df["tld_risk"]>=0.6).astype(int)
    df["brand_impersonation"]= (df["brand_lev_distance"]<=2.0).astype(int)
    df["long_url_flag"]      = (df["url_length"]>=120).astype(int)
    df["deep_subdomain_flag"]= (df["subdomain_depth"]>=3).astype(int)
    df["http_or_bad_ssl"]    = ((df["is_http"]==1)|(df["ssl_valid"]==0)).astype(int)
    df["has_kyc_or_verify"]  = ((df["kw_kyc"]==1)|(df["kw_verify"]==1)).astype(int)
    df["small_amount_verification"] = ((df["upi_am_present"]==1)&(df["upi_amount"]<=10)).astype(int)
    df["pay_intent_no_collect"]     = ((df["upi_intent_pay"]==1)&(df["upi_intent_collect"]==0)).astype(int)
    if "kyc_on_new_domain" in FEATURES:
        df["kyc_on_new_domain"] = (df["is_new_domain_60"] & df["has_kyc_or_verify"]).astype(int)
    return df

def if_anom(X_scaled):
    if iforest is None or scaler is None:
        # fallback: return neutral score 0.5
        if isinstance(X_scaled, (list, np.ndarray)) and np.asarray(X_scaled).ndim==2 and np.asarray(X_scaled).shape[0] == 1:
            return np.array([0.5], dtype=float)
        return np.full((np.asarray(X_scaled).shape[0],), 0.5, dtype=float)
    raw = iforest.decision_function(X_scaled)
    raw = np.asarray(raw).ravel()
    if raw.size == 1:
        return np.array([0.5], dtype=float)
    ranks = pd.Series(raw).rank(method="average").to_numpy()
    rmin, rmax = ranks.min(), ranks.max()
    if rmax == rmin:
        return np.full_like(ranks, 0.5, dtype=float)
    anom = (ranks - rmin) / (rmax - rmin)
    return 1.0 - anom

def safe_int_label(val, default=-1):
    try:
        if pd.isna(val): return int(default)
        return int(val)
    except Exception:
        return int(default)

def safe_write_csv(path: Path, df):
    """Write atomically; on PermissionError write to timestamped fallback file."""
    try:
        tmp = path.with_suffix(".tmp.csv")
        df.to_csv(tmp, index=False)
        try:
            tmp.replace(path)  # atomic on most OSes
            safe_print(f"Saved -> {path}")
            return path
        except Exception:
            # fallback: try os.replace
            import os
            os.replace(str(tmp), str(path))
            safe_print(f"Saved -> {path}")
            return path
    except PermissionError:
        import datetime
        alt = path.parent / f"{path.stem}_out_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            df.to_csv(alt, index=False)
            safe_print(f"Permission denied for {path}. Wrote to fallback: {alt}")
            return alt
        except Exception as e:
            safe_print("Failed to write fallback file:", e)
            raise
    except Exception as e:
        safe_print("Unexpected error writing CSV:", e)
        traceback.print_exc()
        raise

# ============== MAIN EXECUTION - ONLY RUN IF CALLED DIRECTLY ==============
def run_batch_scoring():
    """Run batch scoring on candidate URLs - callable function"""
    ensure_models_loaded()
    
    cand_path = DATA / "candidate_urls_stage2.csv"
    if not cand_path.exists():
        raise FileNotFoundError(f"candidate_urls_stage2.csv not found at {cand_path}")

    safe_print("Reading:", cand_path)
    cand = pd.read_csv(cand_path)

    # basic cleaning: drop rows without valid url
    cand.columns = [c.strip() for c in cand.columns]
    if not {"id","url"}.issubset(set(cand.columns)):
        raise ValueError("candidate_urls.csv must have columns: id,url[,label_is_phish]")

    orig_count = len(cand)
    cand = cand.dropna(subset=['url'])
    cand = cand[cand['url'].astype(str).str.strip().str.lower() != 'nan']
    cand = cand[cand['url'].astype(str).str.strip() != '']
    cand = cand.reset_index(drop=True)
    safe_print(f"Dropped {orig_count - len(cand)} malformed rows; keeping {len(cand)} rows to score.")

    rows = []
    for _, r in cand.iterrows():
        rid = str(r["id"])
        url = str(r["url"]).strip()

        feats = extract_features(url)
        df1 = add_engineering(pd.DataFrame([feats]))

        # Ensure all configured FEATURES are present
        for col in FEATURES:
            if col not in df1.columns:
                df1[col] = 0.0
        df1 = df1.fillna(0.0)

        X = df1[FEATURES].astype(float)

        try:
            if xgb is not None:
                xgb_prob = float(np.asarray(xgb.predict_proba(X)[:, 1]).ravel()[0])
            else:
                xgb_prob = 0.0
        except Exception as e:
            safe_print("XGBoost predict error for id", rid, "url", url, "->", e)
            xgb_prob = 0.0

        try:
            # scale then compute iforest anomaly
            if scaler is not None:
                X_scaled = scaler.transform(X.values)
            else:
                X_scaled = X.values
            if_score = float(np.asarray(if_anom(X_scaled)).ravel()[0])
        except Exception as e:
            safe_print("Iforest/scale error for id", rid, "->", e)
            if_score = 0.5

        final = float(W_LINK * xgb_prob + (1 - W_LINK) * if_score)
        verdict = "BLOCK" if final >= T_BLOCK else ("OK" if final <= T_OK else "WARN")
        lbl = safe_int_label(r.get("label_is_phish", -1), default=-1)

        rows.append({
            "id": rid, "url": url, "verdict": verdict,
            "xgb_prob": xgb_prob, "if_score": if_score, "final": final,
            "label_is_phish": lbl
        })

    scored = pd.DataFrame(rows)

    # --- SAVE full scored results ---
    scored_path = DATA / "scored_full.csv"
    saved = safe_write_csv(scored_path, scored)

    safe_print("Saved full scored table ->", saved)
    safe_print("Verdict counts:", scored['verdict'].value_counts().to_dict())
    safe_print("Final score min/max:", scored['final'].min(), scored['final'].max())

    # --- OPTIONAL: create a relaxed WARN set for Stage-2 testing ---
    t_ok_relaxed = 0.10
    t_block_relaxed = 0.25
    mask_relaxed = (scored["final"] > t_ok_relaxed) & (scored["final"] < t_block_relaxed)
    relaxed_warn = scored.loc[mask_relaxed, ["id","url","label_is_phish"]].copy()
    relaxed_out = DATA / "warn_urls_relaxed.csv"
    if not relaxed_warn.empty:
        safe_write_csv(relaxed_out, relaxed_warn)
        try:
            shutil.copy(relaxed_out, DATA / "warn_urls.csv")
            safe_print(f"Relaxed WARN count: {len(relaxed_warn)} -> {relaxed_out} (copied to warn_urls.csv)")
        except Exception:
            safe_print("Could not copy relaxed warn CSV to warn_urls.csv (permission?).")
    else:
        safe_print("Relaxed WARN set empty; warn_urls.csv unchanged.")

    # save the actual WARNs (if any)
    warn = scored[scored["verdict"] == "WARN"][["id", "url", "label_is_phish"]].copy()
    out_path = DATA / "warn_urls.csv"
    try:
        safe_write_csv(out_path, warn)
        safe_print(f"Scored {len(scored)} links. WARN: {len(warn)} → {out_path}")
    except Exception:
        safe_print("Failed to write warn_urls.csv. Check permissions.")

# Only run if this script is executed directly
if __name__ == "__main__":
    run_batch_scoring()
