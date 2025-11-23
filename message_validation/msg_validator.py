# message_validation/msg_validator.py

"""
Message validator – combines rules + classifier
Usage:
    python -m message_validation.msg_validator "your message text"
"""

import re
import sys
import json
from pathlib import Path

from message_validation.model.msg_classifier import predict_msg
from message_validation.msg_rules import rule_based_flags
from message_validation.msg_utils import extract_urls, extract_features

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def validate_message(text: str):
    """
    Main message validation function
    Returns verdict and analysis
    """
    if not text or not text.strip():
        return {
            "verdict": "ERROR",
            "error": "Empty message",
            "is_fraud": False,
        }

    try:
        # Extract features
        features = extract_features(text)

        # Check rules
        rules_result = check_rules(text, features)

        # Determine verdict
        is_fraud = rules_result.get("is_suspicious", False)
        fraud_score = rules_result.get("fraud_score", 0.0)

        if fraud_score >= 0.7:
            verdict = "BLOCK"
        elif fraud_score >= 0.4:
            verdict = "WARN"
        else:
            verdict = "OK"

        return {
            "verdict": verdict,
            "is_fraud": is_fraud,
            "fraud_score": fraud_score,
            "reasons": rules_result.get("reasons", []),
            "features": features,
        }

    except Exception as e:
        return {
            "verdict": "ERROR",
            "error": str(e),
            "is_fraud": False,
        }


def main():
    if len(sys.argv) < 2:
        print('Usage: python -m message_validation.msg_validator "your text"')
        sys.exit(1)

    text = " ".join(sys.argv[1:])
    result = predict_msg(text)

    # add rule-based flags
    rules = rule_based_flags(text)

    result["rule_flags"] = rules

    print(json.dumps(result, indent=2))


# Ensure backward compatibility
analyze_message = validate_message

if __name__ == "__main__":
    if len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:])
        result = validate_message(msg)
        import json

        print(json.dumps(result, indent=2))
    else:
        # Test messages
        test_messages = [
            "Click here to update your KYC: https://secure-bank.com/update",
            "Your order has been delivered",
            "URGENT: Verify your account within 24 hours",
        ]

        for msg in test_messages:
            print(f"\nMessage: {msg}")
            result = validate_message(msg)
            print(f"Verdict: {result['verdict']}")
