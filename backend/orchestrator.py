# orchestrator.py
"""
Lightweight orchestrator that routes requests to specialized validators.

This file acts as a traffic controller. When a validation request comes in,
it figures out what type of input it is (link, VPA, message, or QR code) and
sends it to the right validator module. It also handles caching to make
repeated validations faster.

Think of it like a restaurant manager who takes orders and sends them to
the right kitchen station (appetizers, main course, desserts, etc.).
"""

# Import necessary libraries
import logging  # For tracking what's happening
import sys  # For system operations
import time  # For measuring response times
import hashlib  # For creating unique cache keys
from pathlib import Path  # For file path operations
from datetime import datetime, timedelta  # For handling cache expiration
from urllib.parse import unquote  # For decoding URL-encoded strings

# Setup paths - make sure Python can find all our modules
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Setup logging - track what the orchestrator is doing
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import specialized validators
# We'll import these as needed to avoid loading everything at startup
from qr_validation.qr_parser import parse_qr_image

# Cache system - stores validation results to avoid re-validating the same input
# This makes the system faster when users check the same URL/VPA multiple times
_VALIDATION_CACHE = {}  # Dictionary to store cached results
_CACHE_EXPIRY_HOURS = 24  # Cache expires after 24 hours

def get_cache_key(input_type: str, value: str = None, file_data: bytes = None) -> str:
    """Generate cache key from input"""
    if file_data:
        file_hash = hashlib.md5(file_data).hexdigest()
        return f"qr:{file_hash}"
    else:
        return hashlib.md5(f"{input_type}:{value}".encode()).hexdigest()

def get_from_cache(cache_key: str):
    """Get cached result if not expired"""
    if cache_key in _VALIDATION_CACHE:
        cached = _VALIDATION_CACHE[cache_key]
        age = datetime.now() - cached["timestamp"]
        if age < timedelta(hours=_CACHE_EXPIRY_HOURS):
            return cached["result"]
        else:
            del _VALIDATION_CACHE[cache_key]
    return None

def save_to_cache(cache_key: str, result: dict):
    """Save result to cache with timestamp"""
    _VALIDATION_CACHE[cache_key] = {
        "result": result,
        "timestamp": datetime.now()
    }

def validate_input(input_type: str, value: str, file_data=None):
    """Main orchestrator - routes to appropriate validator"""
    cache_key = get_cache_key(input_type, value, file_data)
    start_time = time.time()
    
    # Check cache
    cached_result = get_from_cache(cache_key)
    if cached_result:
        cache_time = time.time() - start_time
        logger.info(f"✓ Cache hit! Response time: {cache_time*1000:.0f}ms")
        return {
            **cached_result,
            "cached": True,
            "response_time_ms": int(cache_time * 1000)
        }
    
    logger.info("=" * 60)
    logger.info(f"Request - type: {input_type}, value: {value}, file: {file_data is not None}")
    
    # Route to appropriate validator
    try:
        if input_type == "link":
            result = validate_link(value)
        elif input_type == "vpa":
            result = validate_vpa(value)
        elif input_type == "message":
            result = validate_message(value)
        elif input_type == "qr":
            result = validate_qr(file_data)
        else:
            result = {"error": "Invalid type"}
        
        response_time = time.time() - start_time
        result["cached"] = False
        result["response_time_ms"] = int(response_time * 1000)
        
        if "error" not in result:
            save_to_cache(cache_key, result)
        
        logger.info(f"✓ Result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"✗ Error: {e}", exc_info=True)
        return {"error": str(e)}

def validate_link(url: str):
    """Route link validation - ML-based with NO whitelisting"""
    logger.info(f"[LINK VALIDATION] {url}")
    
    try:
        # Import here to avoid circular dependency
        from link_validation.validator import validate_url as ml_validate
        
        # Run ML validation (no whitelisting)
        ml_result = ml_validate(url)
        logger.info(f"[STAGE1] {ml_result}")
        
        stage1_verdict = ml_result.get("verdict", "WARN")
        stage1_score = ml_result.get("score", 0.5)
        stage1_reasons = ml_result.get("reasons", [])
        
        # Stage 2: Only if WARN or BLOCK
        stage2_result = None
        stage2_reasons = []
        
        if stage1_verdict in ["WARN", "BLOCK"]:
            logger.info(f"[DECISION] {stage1_verdict} verdict → triggering Stage 2")
            try:
                from stage2_dynamic.stage2_validator import validate_url_stage2
                logger.info("[STAGE2] Running headless browser scan...")
                stage2_result = validate_url_stage2(url)
                logger.info(f"[STAGE2] {stage2_result}")
                
                # ✅ BUILD STAGE 2 REASONS
                if stage2_result and stage2_result.get("success"):
                    behavioral = stage2_result.get("behavioral", {})
                    
                    # Always mention headless browser
                    if behavioral.get("trusted_domain"):
                        stage2_reasons.append("✅ Verified safe by headless browser scan")
                    elif behavioral.get("connection_failed"):
                        stage2_reasons.append("🔍 Headless browser: Site unreachable")
                    else:
                        stage2_reasons.append("🔍 Analyzed by headless browser")
                    
                    # Add specific findings
                    if behavioral.get("suspicious_domain"):
                        stage2_reasons.append("⚠️ Browser detected: Suspicious domain pattern")
                    if behavioral.get("has_password_field"):
                        stage2_reasons.append("⚠️ Browser detected: Password input field")
                    if behavioral.get("has_otp_field"):
                        stage2_reasons.append("⚠️ Browser detected: OTP input field")
                    if behavioral.get("mimics_banking_ui"):
                        stage2_reasons.append("⚠️ Browser detected: Fake banking interface")
                    if behavioral.get("redirects_to_different_domain"):
                        stage2_reasons.append("⚠️ Browser detected: Suspicious redirect")
                    if behavioral.get("suspicious_javascript"):
                        stage2_reasons.append("⚠️ Browser detected: Malicious JavaScript")
                    
                    # Add reasons to stage2 result
                    stage2_result["reasons"] = stage2_reasons
                    logger.info(f"[STAGE2 REASONS] {stage2_reasons}")
                    
            except Exception as e:
                logger.error(f"[STAGE2] Failed: {e}", exc_info=True)
                stage2_result = None
                stage2_reasons = [f"⚠️ Browser scan failed: {str(e)}"]
        
        # ✅ COMBINE ALL REASONS
        all_reasons = []
        
        # Add stage 1 reasons (limit to 2)
        all_reasons.extend(stage1_reasons[:2])
        
        # Add ALL stage 2 reasons
        if stage2_reasons:
            all_reasons.extend(stage2_reasons)
        
        # Determine final verdict
        if stage2_result and stage2_result.get("success"):
            stage2_verdict = stage2_result.get("verdict", "WARN")
            stage2_score = stage2_result.get("score", 0.5)
            
            # ✅ AGGREGATE SCORING: Use weighted average or maximum
            # Option 1: Use maximum (most conservative)
            final_score = max(stage1_score, stage2_score)
            
            # Option 2: Weighted average (60% Stage1, 40% Stage2)
            # final_score = (stage1_score * 0.6) + (stage2_score * 0.4)
            
            # ✅ FINAL VERDICT: Use the more severe verdict
            if stage1_verdict == "BLOCK" or stage2_verdict == "BLOCK":
                final_verdict = "BLOCK"
            elif stage1_verdict == "WARN" or stage2_verdict == "WARN":
                final_verdict = "WARN"
            else:
                final_verdict = "OK"
        else:
            final_verdict = stage1_verdict
            final_score = stage1_score
        
        logger.info(f"[FINAL VERDICT] {final_verdict}")
        logger.info(f"[ALL REASONS] {all_reasons}")
        
        return {
            "input": {"type": "link", "value": url},
            "stage1": {
                "verdict": stage1_verdict,
                "score": stage1_score,
                "reasons": stage1_reasons
            },
            "stage2": stage2_result,
            "final_verdict": final_verdict,
            "risk_score": final_score,
            "reasons": all_reasons if all_reasons else ["Analysis completed"]
        }
        
    except Exception as e:
        logger.error(f"Link validation failed: {e}", exc_info=True)
        return {
            "input": {"type": "link", "value": url},
            "error": str(e),
            "final_verdict": "WARN",
            "risk_score": 0.5,
            "reasons": [f"Validation error: {str(e)}"]
        }

def validate_vpa(vpa: str):
    """Route VPA validation to existing validator"""
    vpa = unquote(vpa)
    logger.info(f"Processing VPA: {vpa}")
    
    try:
        from qr_validation.vpa_validator import validate_vpa_format
        result = validate_vpa_format(vpa)
        return {
            "input": {"type": "vpa", "value": vpa},
            **result
        }
    except Exception as e:
        logger.warning(f"VPA validator error, using fallback: {e}")
        import re
        
        if not re.match(r'^[a-zA-Z0-9.\-_]{2,}@[a-zA-Z0-9.\-_]{2,}$', vpa):
            return {
                "input": {"type": "vpa", "value": vpa},
                "verdict": "BLOCK",
                "risk_score": 0.9,
                "reasons": ["Invalid VPA format"]
            }
        
        provider = vpa.split('@')[-1].lower()
        known_providers = ['oksbi', 'okhdfcbank', 'okaxis', 'okicici', 'apl', 'ybl', 'ibl', 'paytm', 'paytmqr', 'superyes']
        
        if provider not in known_providers:
            return {
                "input": {"type": "vpa", "value": vpa},
                "verdict": "WARN",
                "risk_score": 0.6,
                "reasons": [f"Unknown payment provider: {provider}"]
            }
        
        return {
            "input": {"type": "vpa", "value": vpa},
            "verdict": "OK",
            "risk_score": 0.1,
            "reasons": ["Valid VPA format", f"Known provider: {provider}"]
        }

def validate_message(message: str):
    """Validate SMS/Message and extract URLs for validation"""
    logger.info(f"Processing message: {message[:50]}...")
    import re
    
    risk_score = 0.0
    reasons = []
    
    suspicious_keywords = [
        'kyc', 'verify', 'suspended', 'blocked', 'expire', 'update',
        'urgent', 'immediately', 'click here', 'limited time',
        'congratulations', 'winner', 'prize', 'lottery', 'cashback',
        'refund', 'reward', 'claim', 'account', 'bank'
    ]
    
    message_lower = message.lower()
    found_keywords = [kw for kw in suspicious_keywords if kw in message_lower]
    
    if found_keywords:
        risk_score += 0.15 * len(found_keywords)
        reasons.append(f"Suspicious keywords: {', '.join(found_keywords[:3])}")
    
    # Extract and validate URLs
    urls = re.findall(r'https?://[^\s]+', message)
    url_results = []
    
    if urls:
        for url in urls:
            url = url.rstrip('.,;:)]}')
            logger.info(f"[MESSAGE] Validating extracted URL: {url}")
            
            link_result = validate_link(url)
            url_verdict = link_result.get("final_verdict", "WARN")
            
            url_results.append({
                "url": url,
                "verdict": url_verdict,
                "stage1": link_result.get("stage1"),
                "stage2": link_result.get("stage2")
            })
            
            if url_verdict == "BLOCK":
                risk_score += 0.5
                reasons.append(f"⛔ Blocked URL detected: {url[:50]}")
            elif url_verdict == "WARN":
                risk_score += 0.3
                reasons.append(f"⚠️ Suspicious URL: {url[:50]}")
    
    phones = re.findall(r'\b\d{10}\b', message)
    if phones:
        risk_score += 0.1
        reasons.append(f"Contains {len(phones)} phone number(s)")
    
    verdict = "BLOCK" if risk_score >= 0.7 else ("WARN" if risk_score >= 0.3 else "OK")
    
    result = {
        "input": {"type": "message", "value": message},
        "verdict": verdict,
        "risk_score": min(risk_score, 1.0),
        "reasons": reasons if reasons else ["No immediate threats detected"]
    }
    
    if url_results:
        result["extracted_urls"] = url_results
    
    return result

def validate_qr(file_data):
    """Route QR validation to existing qr_parser module"""
    logger.info("Processing QR code image")
    
    try:
        qr_result = parse_qr_image(file_data)
        
        if not qr_result or "error" in qr_result:
            return qr_result or {"error": "Failed to parse QR code"}
        
        qr_type = qr_result.get("type", "unknown")
        qr_data = qr_result.get("data", "")
        
        logger.info(f"[QR PARSED] Type: {qr_type}, Data: {qr_data[:50]}")
        
        from qr_validation.qr_utils import get_qr_description
        default_verdict, default_risk, default_reasons = get_qr_description(qr_type, qr_data)
        
        if qr_type == "url":
            logger.info(f"[QR] URL detected, validating: {qr_data}")
            link_result = validate_link(qr_data)
            
            stage1 = link_result.get("stage1", {})
            stage2 = link_result.get("stage2", {})
            risk_score = (stage2.get("score") if stage2 else None) or stage1.get("score", 0)
            
            return {
                "input": {"type": "qr", "value": qr_data},
                "decoded_url": qr_data,
                "qr_type": "URL QR Code",
                "verdict": link_result.get("final_verdict", "UNKNOWN"),
                "risk_score": risk_score,
                "stage1": stage1,
                "stage2": stage2,
                "reasons": link_result.get("reasons", [])
            }
        
        elif qr_type == "upi":
            vpa = qr_result.get("vpa")
            if vpa:
                vpa = unquote(vpa)
                logger.info(f"[QR] UPI VPA (decoded): {vpa}")
                vpa_result = validate_vpa(vpa)
                return {
                    "input": {"type": "qr", "value": "[UPI Payment QR]"},
                    "qr_type": "UPI Payment QR",
                    "vpa": vpa,
                    "verdict": vpa_result.get("verdict", "UNKNOWN"),
                    "risk_score": vpa_result.get("risk_score", 0),
                    "reasons": vpa_result.get("reasons", [])
                }
            else:
                return {
                    "input": {"type": "qr", "value": qr_data[:50]},
                    "qr_type": "Malformed UPI QR",
                    "verdict": "WARN",
                    "risk_score": 0.5,
                    "reasons": ["Could not extract VPA from UPI QR"]
                }
        
        elif qr_type == "vpa":
            vpa_result = validate_vpa(qr_data)
            return {
                "input": {"type": "qr", "value": qr_data},
                "qr_type": "Plain VPA QR",
                "verdict": vpa_result.get("verdict", "UNKNOWN"),
                "risk_score": vpa_result.get("risk_score", 0),
                "reasons": vpa_result.get("reasons", [])
            }
        
        else:
            type_names = {
                "protected_payment": "Protected Payment QR",
                "geo": "Location/Maps QR",
                "social_media": "Social Media Link QR",
                "tel": "Phone Number QR",
                "mailto": "Email Address QR",
                "sms": "SMS QR",
                "wifi": "WiFi Credentials QR",
                "vcard": "Contact Card QR",
                "intent": "App Intent QR",
                "text": "Plain Text QR",
                "unknown": "Unknown Format QR"
            }
            
            return {
                "input": {"type": "qr", "value": qr_data[:100] if len(qr_data) > 100 else qr_data},
                "qr_type": type_names.get(qr_type, "Unknown QR"),
                "decoded": qr_data if qr_type != "protected_payment" else "[Encrypted Data]",
                "verdict": default_verdict,
                "risk_score": default_risk,
                "reasons": default_reasons
            }
            
    except Exception as e:
        logger.error(f"QR validation error: {e}", exc_info=True)
        return {"error": f"Failed to validate QR: {str(e)}"}

def main_cli():
    """Command line interface"""
    import argparse
    import json
    parser = argparse.ArgumentParser(description="UPI Fraud Detection Orchestrator")
    parser.add_argument("--link", help="Validate a URL")
    parser.add_argument("--vpa", help="Validate a VPA/UPI ID")
    parser.add_argument("--msg", help="Validate a message")
    parser.add_argument("--qr", help="Validate a QR code image")
    
    args = parser.parse_args()
    
    if args.link:
        result = validate_input("link", args.link)
    elif args.vpa:
        result = validate_input("vpa", args.vpa)
    elif args.msg:
        result = validate_input("message", args.msg)
    elif args.qr:
        with open(args.qr, 'rb') as f:
            result = validate_input("qr", None, f.read())
    else:
        parser.print_help()
        return
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main_cli()
