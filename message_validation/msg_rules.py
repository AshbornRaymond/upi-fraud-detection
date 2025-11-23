"""Rule-based checks for message validation"""
import re

def check_rules(text: str, features: dict = None):
    """
    Apply rule-based fraud detection on message text
    Returns fraud indicators and score
    """
    if features is None:
        from message_validation.msg_utils import extract_features
        features = extract_features(text)
    
    reasons = []
    fraud_score = 0.0
    
    text_lower = text.lower()
    
    # High-risk keywords
    high_risk = ['kyc', 'verify', 'suspended', 'blocked', 'expire', 'urgent', 'immediately']
    for word in high_risk:
        if word in text_lower:
            fraud_score += 0.2
            reasons.append(f"High-risk keyword: {word}")
    
    # URLs in message
    if features.get('has_url', False):
        fraud_score += 0.15
        reasons.append("Contains URL")
    
    # Phone numbers
    if features.get('has_phone', False):
        fraud_score += 0.1
        reasons.append("Contains phone number")
    
    # Urgency indicators
    urgency_words = ['urgent', 'immediately', 'now', 'asap', 'today', 'within']
    urgency_count = sum(1 for w in urgency_words if w in text_lower)
    if urgency_count > 0:
        fraud_score += 0.1 * urgency_count
        reasons.append(f"Urgency indicators: {urgency_count}")
    
    # ALL CAPS (aggressive)
    if text.isupper() and len(text) > 20:
        fraud_score += 0.15
        reasons.append("All caps text")
    
    # Cap fraud score at 1.0
    fraud_score = min(fraud_score, 1.0)
    
    return {
        "is_suspicious": fraud_score >= 0.4,
        "fraud_score": fraud_score,
        "reasons": reasons
    }

if __name__ == "__main__":
    test_msg = "URGENT: Your account has been suspended. Click here to verify KYC immediately"
    result = check_rules(test_msg)
    print(f"Fraud Score: {result['fraud_score']}")
    print(f"Reasons: {result['reasons']}")
