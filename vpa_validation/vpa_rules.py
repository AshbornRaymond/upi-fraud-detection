from vpa_validation.vpa_utils import is_valid_format, get_provider, entropy

# Trusted PSP/bank domains
ALLOWED_PROVIDERS = {
    "oksbi", "okhdfcbank", "okaxis", "okicici",
    "oksbi", "okyesbank", "okkotak", "okboi",
    "okupi", "okidfc", "ybl", "upi"
}

# Suspicious verification amounts commonly used in scams
SUSPICIOUS_AMOUNTS = {1, 2, 5, 10}

def apply_vpa_rules(vpa: str, amount: float | None):
    vpa = vpa.lower()
    provider = get_provider(vpa)

    result = {
        "vpa": vpa,
        "hard_fail": [],
        "soft_flags": []
    }

    # HARD RULES ========================
    if not is_valid_format(vpa):
        result["hard_fail"].append("Invalid VPA format")

    if provider not in ALLOWED_PROVIDERS:
        result["hard_fail"].append(f"Provider '{provider}' not in trusted list")

    # SOFT RULES ========================
    if entropy(vpa) > 3.7:
        result["soft_flags"].append("High randomness in VPA (entropy anomaly)")

    if amount in SUSPICIOUS_AMOUNTS:
        result["soft_flags"].append("Amount is common scam range (1/2/5/10)")

    if len(vpa.split("@")[0]) <= 3:
        result["soft_flags"].append("Very short handle – suspicious")

    return result
