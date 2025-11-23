# vpa_validation/vpa_validator.py
import re
import math
from collections import Counter
from urllib.parse import urlparse

# simple provider allowlist (extend as needed)
PROVIDER_ALLOWLIST = {"oksbi","okhdfcbank","okaxis","okicici","okpay","ptaxis","paytm","gpay","phonepe"}

def _username_entropy(s: str) -> float:
    # Shannon-like entropy over characters
    if not s:
        return 0.0
    counts = Counter(s)
    ln = sum(counts.values())
    ent = 0.0
    for c in counts.values():
        p = c/ln
        ent -= p * math.log2(p)
    return ent

def normalize_vpa(pa: str) -> str:
    return pa.strip().lower()

def parse_vpa(pa: str):
    pa = normalize_vpa(pa)
    # common VPA pattern: localpart@provider (provider may contain dots)
    m = re.match(r'^([^@]+)@([a-z0-9\.\-]+)$', pa)
    if not m:
        return None
    username, provider = m.group(1), m.group(2)
    return {"username": username, "provider": provider}

def validate_vpa(pa: str):
    """
    Return dict:
    {
      "pa": "<original>",
      "valid": True/False,
      "reasons": [...],
      "provider": "<provider if parsed else None>",
      "provider_in_allowlist": True/False/None,
      "username_entropy": float
    }
    """
    out = {"pa": pa, "valid": False, "reasons": [], "provider": None, "provider_in_allowlist": None, "username_entropy": None}
    parsed = parse_vpa(pa)
    if not parsed:
        out["reasons"].append("format_invalid")
        return out

    username = parsed["username"]
    provider = parsed["provider"]
    out["provider"] = provider
    out["provider_in_allowlist"] = provider in PROVIDER_ALLOWLIST

    # basic checks
    if len(username) < 3:
        out["reasons"].append("username_too_short")
    if len(username) > 64:
        out["reasons"].append("username_too_long")
    if not re.match(r'^[a-z0-9\.\-_]+$', username):
        out["reasons"].append("username_has_weird_chars")

    # entropy
    ent = _username_entropy(username)
    out["username_entropy"] = ent
    if ent < 1.2:
        out["reasons"].append("low_username_entropy")

    # provider heuristics
    if not re.match(r'^[a-z0-9\.\-]+$', provider):
        out["reasons"].append("provider_malformed")

    # final decision: valid if no hard reasons (you can tweak)
    hard_reasons = {"format_invalid","username_too_short","provider_malformed"}
    if any(r in hard_reasons for r in out["reasons"]):
        out["valid"] = False
    else:
        out["valid"] = True

    return out

def validate_message(message: str):
    """Validate SMS/Message with STRICT phishing detection"""
    logger.info(f"Processing message: {message[:50]}...")

    risk_score = 0.0
    reasons = []
    flags = []
    
    # ✅ EXPANDED: High-risk keywords (weighted)
    HIGH_RISK_KEYWORDS = {
        'urgent': 0.25, 'suspended': 0.3, 'blocked': 0.3, 'expire': 0.25,
        'immediately': 0.25, 'verify now': 0.3, 'action required': 0.3,
        'account locked': 0.35, 'security alert': 0.3, 'unusual activity': 0.3,
        'confirm identity': 0.3, 'update kyc': 0.35, 'reactivate': 0.3,
        'link expires': 0.25, 'last chance': 0.25, 'act now': 0.25
    }
    
    MEDIUM_RISK_KEYWORDS = {
        'kyc': 0.15, 'verify': 0.15, 'update': 0.1, 'click here': 0.15,
        'limited time': 0.15, 'prize': 0.2, 'lottery': 0.25, 'winner': 0.2,
        'congratulations': 0.15, 'cashback': 0.1, 'refund': 0.15,
        'reward': 0.15, 'claim': 0.15, 'free': 0.1, 'bonus': 0.1
    }
    
    # ✅ NEW: Bank/Financial impersonation keywords
    IMPERSONATION_KEYWORDS = {
        'sbi', 'hdfc', 'icici', 'axis', 'paytm', 'phonepe', 'googlepay',
        'bhim', 'upi', 'netbanking', 'aadhaar', 'pan card', 'epfo'
    }

    message_lower = message.lower()
    
    # Check high-risk keywords
    for keyword, weight in HIGH_RISK_KEYWORDS.items():
        if keyword in message_lower:
            risk_score += weight
            flags.append(f"🚨 High-risk: '{keyword}'")
    
    # Check medium-risk keywords
    for keyword, weight in MEDIUM_RISK_KEYWORDS.items():
        if keyword in message_lower:
            risk_score += weight
            flags.append(f"⚠️ Suspicious: '{keyword}'")
    
    # ✅ NEW: Check for impersonation
    impersonation_found = [kw for kw in IMPERSONATION_KEYWORDS if kw in message_lower]
    if impersonation_found:
        risk_score += 0.2 * len(impersonation_found)
        flags.append(f"🏦 Impersonation attempt: {', '.join(impersonation_found[:2])}")
    
    # ✅ IMPROVED: Extract URLs (including obfuscated)
    # Standard URLs
    urls = re.findall(r'https?://[^\s]+', message)
    # Obfuscated URLs (hxxp, h**p, etc.)
    obfuscated = re.findall(r'h[x*]{2}ps?://[^\s]+', message)
    # Dotted domains (bit[.]ly, google[.]com)
    dotted = re.findall(r'\w+\[\.\]\w+(?:\[\.\]\w+)*', message)
    
    all_urls = urls + obfuscated + dotted
    url_results = []

    if all_urls:
        for url in all_urls:
            url = url.rstrip('.,;:)]}')
            
            # Clean obfuscated URLs
            url = url.replace('hxxp', 'http').replace('h**p', 'http')
            url = url.replace('[.]', '.')
            
            logger.info(f"[MESSAGE] Validating extracted URL: {url}")

            try:
                link_result = validate_link(url)
                url_verdict = link_result.get("final_verdict", "WARN")

                url_results.append({
                    "url": url,
                    "verdict": url_verdict,
                    "stage1": link_result.get("stage1"),
                    "stage2": link_result.get("stage2")
                })

                # ✅ STRICTER: Higher penalties for suspicious URLs
                if url_verdict == "BLOCK":
                    risk_score += 0.6  # Increased from 0.5
                    flags.append(f"⛔ BLOCKED URL: {url[:40]}")
                elif url_verdict == "WARN":
                    risk_score += 0.4  # Increased from 0.3
                    flags.append(f"⚠️ Suspicious URL: {url[:40]}")
                
                # ✅ NEW: Check for URL shorteners (always suspicious in messages)
                shorteners = ['bit.ly', 'tinyurl', 'goo.gl', 't.co', 'ow.ly', 'is.gd']
                domain = urlparse(url).netloc.lower()
                if any(short in domain for short in shorteners):
                    risk_score += 0.25
                    flags.append(f"🔗 URL shortener detected: {domain}")
                    
            except Exception as e:
                logger.error(f"Error validating URL {url}: {e}")
                risk_score += 0.3
                flags.append(f"❌ Invalid URL: {url[:40]}")

    # ✅ NEW: Check for phone numbers (often used in phishing)
    phones = re.findall(r'\b\d{10}\b', message)
    if phones:
        risk_score += 0.15 * len(phones)
        flags.append(f"📞 Contains phone number(s): {len(phones)}")
    
    # ✅ NEW: Check for ALL CAPS (urgency tactic)
    caps_words = re.findall(r'\b[A-Z]{4,}\b', message)
    if len(caps_words) >= 3:
        risk_score += 0.2
        flags.append(f"📢 Excessive caps (urgency): {len(caps_words)} words")
    
    # ✅ NEW: Check for excessive punctuation (urgency)
    exclamations = message.count('!')
    if exclamations >= 3:
        risk_score += 0.15
        flags.append(f"❗ Excessive urgency marks: {exclamations}!")
    
    # ✅ NEW: Check for time pressure
    time_pressure = ['within 24 hours', 'today only', 'expires today', 'last day', 'final reminder']
    if any(phrase in message_lower for phrase in time_pressure):
        risk_score += 0.25
        flags.append("⏰ Time pressure tactics detected")
    
    # ✅ NEW: Check for credential requests
    credential_keywords = ['password', 'pin', 'otp', 'cvv', 'card number', 'account number']
    if any(kw in message_lower for kw in credential_keywords):
        risk_score += 0.4
        flags.append("🔐 Requests sensitive credentials")

    # Cap risk score at 1.0
    risk_score = min(risk_score, 1.0)
    
    # ✅ STRICTER: Lower thresholds
    if risk_score >= 0.5:  # Changed from 0.7
        verdict = "BLOCK"
        reasons.append("⛔ HIGH RISK: Multiple fraud indicators")
    elif risk_score >= 0.3:  # Changed from 0.4
        verdict = "WARN"
        reasons.append("⚠️ SUSPICIOUS: Manual review recommended")
    else:
        verdict = "OK"
        reasons.append("✅ No significant threats detected")
    
    # Add top flags to reasons
    reasons.extend(flags[:5])  # Show top 5 flags

    result = {
        "input": {"type": "message", "value": message},
        "verdict": verdict,
        "risk_score": round(risk_score, 2),
        "reasons": reasons,
        "extracted_urls": url_results,
        "analysis": {
            "total_flags": len(flags),
            "urls_found": len(all_urls),
            "phones_found": len(phones),
            "impersonation_detected": bool(impersonation_found)
        }
    }
    
    logger.info(f"[MESSAGE VERDICT] {verdict} (score: {risk_score:.2f})")
    return result
