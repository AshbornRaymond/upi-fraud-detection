# vpa_validation/vpa_utils.py
import re
import hashlib
import math
from collections import Counter

# Basic VPA regex: <localpart>@<provider>
# localpart: letters, digits, ._- and provider: letters/digits
VPA_RE = re.compile(r'^\s*([a-zA-Z0-9.\-_]{2,64})@([a-zA-Z0-9]{2,64})\s*$')

# A tiny allowlist for common PSP/bank providers — extend this from your allowlist file
DEFAULT_ALLOWLIST = {
    "oksbi", "okhdfcbank", "okicici", "okaxis", "okpaytm", "okphonepe", "okgoogle", "oksbi", "ybl", "paytm"
}

def parse_vpa(vpa: str):
    """Return (localpart, provider) or (None, None) if invalid."""
    if vpa is None: return (None, None)
    m = VPA_RE.match(vpa.strip())
    if not m:
        return (None, None)
    return (m.group(1), m.group(2).lower())

def looks_like_vpa(vpa: str) -> bool:
    lp, prov = parse_vpa(vpa)
    return lp is not None

def vpa_format_score(vpa: str) -> float:
    """
    Returns a score 0..1 for how clean/likely-valid the format is.
    1.0 = clearly valid; 0 = invalid format.
    """
    lp, prov = parse_vpa(vpa)
    if lp is None:
        return 0.0
    # penalize very short local parts, extreme punctuation, high randomness
    score = 1.0
    if len(lp) < 3:
        score -= 0.25
    # punctuation density
    punct = sum(1 for c in lp if c in ".-_")
    if punct / max(1, len(lp)) > 0.25:
        score -= 0.2
    # reward typical alpha-numeric ratio
    alpha = sum(1 for c in lp if c.isalpha())
    if alpha / max(1, len(lp)) < 0.3:
        score -= 0.2
    return max(0.0, min(1.0, score))

def vpa_entropy(localpart: str) -> float:
    """Shannon entropy normalized by log(len(alphabet)). Returns 0..1-ish."""
    if not localpart:
        return 0.0
    cnt = Counter(localpart)
    L = len(localpart)
    ent = 0.0
    for c, v in cnt.items():
        p = v / L
        ent -= p * math.log2(p)
    # normalize by max possible entropy for given charset (approx log2(62) for alnum)
    max_ent = math.log2(62) if L>0 else 1.0
    return ent / max_ent

def provider_allowlist_check(provider: str, allowlist=None) -> bool:
    if allowlist is None:
        allowlist = DEFAULT_ALLOWLIST
    return provider.lower() in allowlist

def hash_vpa(vpa: str) -> str:
    """Non-reversible identifier for storing/reputation checks."""
    return hashlib.sha256(vpa.strip().lower().encode('utf-8')).hexdigest()

# small helper to detect suspicious patterns like random digits heavy handles
def vpa_suspicious_flags(localpart: str) -> dict:
    digits = sum(1 for c in localpart if c.isdigit())
    letters = sum(1 for c in localpart if c.isalpha())
    flags = {
        "many_digits": digits >= max(3, int(0.4 * max(1, len(localpart)))),
        "all_digits": letters == 0 and digits > 0,
        "repeated_chars": any(localpart.count(ch) > max(3, len(localpart)//4) for ch in set(localpart))
    }
    return flags
