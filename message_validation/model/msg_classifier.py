# message_validation/model/msg_classifier.py

"""
Lightweight classifier – NO .pkl files needed.
You can replace this later with real ML.
"""

from message_validation.msg_utils import extract_urls, urgency_score, has_money_words


SCAM_KEYWORDS = [
    "kyc", "verify", "verification", "update", "block",
    "expire", "offer", "bonus", "reward", "limit",
    "refund", "cashback"
]


def predict_msg(text: str) -> dict:
    text_low = text.lower()

    # keyword score
    kw_hits = sum(1 for k in SCAM_KEYWORDS if k in text_low)

    # urgency score
    urg = urgency_score(text)

    # url presence
    urls = extract_urls(text)
    has_url = len(urls) > 0

    # scam probability (simple rule)
    score = 0
    if kw_hits > 0:
        score += 0.4
    if urg > 0:
        score += 0.3
    if has_url:
        score += 0.3
    if has_money_words(text):
        score += 0.2

    score = min(score, 1.0)

    return {
        "score": round(score, 3),
        "has_url": has_url,
        "urls": urls,
        "urgency": urg,
        "keyword_hits": kw_hits,
        "label": "phish" if score >= 0.55 else "safe"
    }
