# fallback_engine.py
import socket, ssl, datetime, json
from pathlib import Path

LOCAL_BLACKLIST = Path(__file__).parent / "blacklist_domains.txt"

def load_local_blacklist():
    if LOCAL_BLACKLIST.exists():
        return set([l.strip().lower() for l in LOCAL_BLACKLIST.read_text(encoding="utf8").splitlines() if l.strip()])
    return set()

LOCAL_BL = load_local_blacklist()

def domain_from_url(url: str) -> str:
    try:
        u = url.lower().strip()
        if "://" in u:
            u = u.split("://", 1)[1]
        u = u.split("/", 1)[0]
        if ":" in u:
            u = u.split(":", 1)[0]
        return u
    except Exception:
        return url

def check_blacklist(url: str) -> bool:
    d = domain_from_url(url)
    if d in LOCAL_BL:
        return True
    for bad in LOCAL_BL:
        if bad and bad in d:
            return True
    return False

def check_tls_ok(url: str, timeout=5) -> bool:
    d = domain_from_url(url)
    try:
        ctx = ssl.create_default_context()
        sock = socket.create_connection((d, 443), timeout=timeout)
        ss = ctx.wrap_socket(sock, server_hostname=d)
        cert = ss.getpeercert()
        ss.close()
        not_after = cert.get('notAfter')
        not_before = cert.get('notBefore')
        def parse_date(s):
            for fmt in ("%b %d %H:%M:%S %Y %Z", "%b %d %H:%M:%S %Y", "%Y-%m-%dT%H:%M:%SZ"):
                try:
                    return datetime.datetime.strptime(s, fmt)
                except Exception:
                    continue
            return None
        if not_after:
            nda = parse_date(not_after)
            if nda and nda < datetime.datetime.utcnow():
                return False
        if not_before:
            nbd = parse_date(not_before)
            if nbd and nbd > datetime.datetime.utcnow():
                return False
        return True
    except Exception:
        return False

def get_whois_age_days(url: str) -> int | None:
    try:
        import whois
    except Exception:
        return None
    d = domain_from_url(url)
    try:
        w = whois.whois(d)
        created = w.creation_date
        if isinstance(created, list):
            created = created[0]
        if not created:
            return None
        if isinstance(created, str):
            created = datetime.datetime.fromisoformat(created)
        age = datetime.datetime.utcnow() - created
        return age.days
    except Exception:
        return None

def fallback_risk(static_score: float,
                  hard_rule_hits: int = 0,
                  tls_ok: bool = True,
                  upi_in_url: bool = False,
                  whois_age_days: int | None = None,
                  in_blacklist: bool = False) -> dict:
    reasons = []
    risk = static_score * 100.0
    if hard_rule_hits:
        risk += 20 * min(hard_rule_hits, 3)
        reasons.append(f"hard_rules:{hard_rule_hits}")
    if in_blacklist:
        reasons.append("in_blacklist")
        return {"level": "HIGH", "score": 100, "action": "BLOCK", "reasons": reasons}
    if not tls_ok:
        risk += 25
        reasons.append("tls_bad")
    if upi_in_url:
        risk += 30
        reasons.append("upi_in_url")
    if whois_age_days is not None:
        if whois_age_days < 7:
            risk += 30; reasons.append("whois<7d")
        elif whois_age_days < 30:
            risk += 15; reasons.append("whois<30d")
        elif whois_age_days < 180:
            risk += 5; reasons.append("whois<180d")
    score = max(0, min(100, risk))
    if score >= 70:
        level, action = "HIGH", "BLOCK"
    elif score >= 40:
        level, action = "MEDIUM", "CHALLENGE"
    else:
        level, action = "LOW", "ALLOW_WITH_LOG"
    return {"level": level, "score": score, "action": action, "reasons": reasons}

def evaluate_url_fallback(url: str, static_score: float, hard_rule_hits: int = 0, upi_in_url: bool = False):
    bl = check_blacklist(url)
    tls = check_tls_ok(url)
    whois_age = get_whois_age_days(url)
    return fallback_risk(static_score=static_score, hard_rule_hits=hard_rule_hits, tls_ok=tls, upi_in_url=upi_in_url, whois_age_days=whois_age, in_blacklist=bl)

if __name__ == "__main__":
    print(evaluate_url_fallback("https://sbi.com/verify", static_score=0.6, hard_rule_hits=1, upi_in_url=False))
