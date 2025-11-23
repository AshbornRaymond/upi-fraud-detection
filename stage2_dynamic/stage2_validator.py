"""
Stage 2 Validator - Entry point for headless browser validation
Calls scan_playwright for browser automation and headless_browser for ML scoring
"""
import sys
import json
from pathlib import Path

# Ensure stage2_dynamic is in path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def validate_url_stage2(url: str, timeout: int = 30) -> dict:
    """
    Stage 2 validation using headless browser + ML model
    
    Returns:
        {
            "success": bool,
            "verdict": "BLOCK" | "WARN" | "OK",
            "score": float (0-1, higher = more fraudulent),
            "features": dict,
            "reason": str
        }
    """
    try:
        from stage2_dynamic.headless_browser import scan_url_headless
        
        print(f"[STAGE2] Starting headless validation for: {url}")
        
        # Run headless browser validation
        result = scan_url_headless(url, headless=True)
        
        if not result or not isinstance(result, dict):
            return {
                "success": False,
                "verdict": "WARN",
                "score": 0.5,
                "reason": "Headless browser validation returned no data"
            }
        
        # Extract score from result
        score = result.get("risk_score", 0.5)
        
        # ✅ FIX: Check if already marked as trusted
        if result.get("behavioral_flags", {}).get("trusted_domain"):
            return {
                "success": True,
                "verdict": "OK",  # ✅ Override to OK
                "score": 0.0,     # ✅ Set score to 0
                "features": result.get("features", {}),
                "behavioral": result.get("behavioral_flags", {}),
                "reason": "Trusted domain - whitelisted"
            }
        
        # If scan failed, return neutral
        if result.get("error"):
            return {
                "success": False,
                "verdict": "WARN",
                "score": 0.5,
                "reason": f"Browser scan error: {result.get('error')}"
            }
        
        # Determine verdict based on score
        if score >= 0.7:
            verdict = "BLOCK"
            reason = "High-risk patterns detected by headless browser"
        elif score >= 0.4:
            verdict = "WARN"
            reason = "Suspicious behavior detected, manual review recommended"
        else:
            verdict = "OK"
            reason = "No significant threats detected"
        
        print(f"[STAGE2] Result: {verdict} (score: {score:.2f})")
        
        return {
            "success": True,
            "verdict": verdict,
            "score": score,
            "features": result.get("features", {}),
            "behavioral": result.get("behavioral_flags", {}),
            "reason": reason
        }
        
    except Exception as e:
        print(f"[STAGE2] Error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "verdict": "WARN",
            "score": 0.5,
            "reason": f"Stage 2 error: {str(e)}"
        }

if __name__ == "__main__":
    # Test Stage 2 directly
    if len(sys.argv) < 2:
        print("Usage: python -m stage2_dynamic.stage2_validator <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    result = validate_url_stage2(url)
    print(json.dumps(result, indent=2))