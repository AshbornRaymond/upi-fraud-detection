"""
Simple reputation store for VPA handles.
Later you can replace this with Firestore, MySQL, or Redis.
"""

# Simulated memory store
VPA_REPUTATION = {
    # Example
    # "john@oksbi": {"reports": 0, "trust": 0.98},
    # "abc98832@okxyz": {"reports": 14, "trust": 0.22},
}

def get_reputation(vpa: str):
    vpa = vpa.lower()
    return VPA_REPUTATION.get(vpa, {"reports": 0, "trust": 0.50})

def update_reputation(vpa: str, is_scam: bool):
    vpa = vpa.lower()
    if vpa not in VPA_REPUTATION:
        VPA_REPUTATION[vpa] = {"reports": 0, "trust": 0.5}

    if is_scam:
        VPA_REPUTATION[vpa]["reports"] += 1
        VPA_REPUTATION[vpa]["trust"] *= 0.75
    else:
        VPA_REPUTATION[vpa]["trust"] = min(1.0, VPA_REPUTATION[vpa]["trust"] + 0.05)
