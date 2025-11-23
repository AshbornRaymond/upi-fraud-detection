# scan_playwright.py
# Enhanced Playwright scanner with better timeout handling
# Drop into: D:\major project\stage2_dynamic\scan_playwright.py
# Usage: python scan_playwright.py

import asyncio
import csv
import json
import time
import traceback
from pathlib import Path
from typing import List, Optional

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

############################
# CONFIGURATION
############################

DATA_DIR = Path(r"D:\major project\data")
WARN_CSV = DATA_DIR / "warn_urls.csv"         # input WARN list (id,url)
OUT_DIR = Path(r"D:\major project\stage2_dynamic\dynamic_json")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Concurrency: how many pages to scan in parallel (tune based on CPU/RAM)
CONCURRENCY = 3

# Timeouts (ms)
NAV_TIMEOUT_HEADLESS = 60_000   # 60s
NAV_TIMEOUT_FALLBACK = 90_000   # not used unless you manually change script

# Retries: number of attempts per URL (each attempt uses cascading wait_untils)
MAX_ATTEMPTS = 2

# Whether to save screenshots and HTML alongside debug JSON
SAVE_SCREENSHOT = True
SAVE_HTML = True

# Stealth / UA configuration
COMMON_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15"
]

# Optionally provide a list of HTTP proxy strings like "http://user:pass@host:port"
# Leave empty list to run without proxy rotation.
PROXIES: List[str] = []

# Optional headers to add to contexts
EXTRA_HEADERS = {"Accept-Language": "en-US,en;q=0.9"}

# Keep headful fallback DISABLED in this production script.
ENABLE_HEADFUL_FALLBACK = False

############################
# END CONFIG
############################


def safe_write_json(path: Path, data: dict):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf8")
    except Exception as e:
        print("Failed to write json", path, e)


def sanitize_filename(s: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in s)[:180]


async def extract_dom_features(page):
    """Run in-page JS to extract handy DOM signals (script/form/iframe counts, input types, upi intents)."""
    try:
        dom_info = await page.evaluate(
            """() => {
                const info = {};
                info.script_count = document.scripts ? document.scripts.length : 0;
                info.iframe_count = document.querySelectorAll('iframe').length;
                info.form_count = document.querySelectorAll('form').length;
                info.has_password_input = !!document.querySelector('input[type=password]');
                info.has_otp_input = !!document.querySelector('input[autocomplete=one-time-code], input[name*=otp i], input[id*=otp i], input[placeholder*=otp i]');
                info.has_pin_input = !!document.querySelector('input[name*=pin i], input[id*=pin i]');
                info.upi_intents = [];
                const aEls = Array.from(document.querySelectorAll('a[href], area[href]'));
                for (const a of aEls) {
                    const h = (a.getAttribute('href') || '').toLowerCase();
                    if (h.startsWith('upi:') || h.includes('upi/pay') || h.includes('intent://upi')) {
                        info.upi_intents.push(h);
                    }
                }
                try {
                    const html = document.documentElement.innerHTML.toLowerCase();
                    const re = /upi:\\/\\/[^'\"\\s<>]*/g;
                    let m;
                    while ((m = re.exec(html)) !== null) {
                        if (!info.upi_intents.includes(m[0])) info.upi_intents.push(m[0]);
                    }
                } catch(e){}
                return info;
            }"""
        )
        # Normalize missing keys
        for k in ("script_count", "iframe_count", "form_count", "has_password_input", "has_otp_input", "has_pin_input", "upi_intents"):
            dom_info.setdefault(k, 0 if "count" in k or "upi" in k else False)
        return dom_info
    except Exception:
        return {
            "script_count": 0,
            "iframe_count": 0,
            "form_count": 0,
            "has_password_input": False,
            "has_otp_input": False,
            "has_pin_input": False,
            "upi_intents": []
        }


async def create_stealth_context(browser, user_agent: str, proxy: Optional[str] = None):
    """
    Create a new browser context with stealth JS injected.
    Pass proxy None to not use a proxy; otherwise provide proxy string in "server" argument.
    """
    context_kwargs = dict(user_agent=user_agent, locale="en-US", accept_downloads=False)
    if proxy:
        # Playwright expects proxy as dict: {"server": "http://host:port", "username": "", "password": ""}
        context_kwargs["proxy"] = {"server": proxy}

    context = await browser.new_context(**context_kwargs)
    # Add extra headers
    try:
        await context.set_extra_http_headers(EXTRA_HEADERS)
    except Exception:
        pass

    # Inject stealth script: hide webdriver, fake plugins/languages, chrome runtime, permissions handling
    stealth_js = r"""
        // navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined, configurable: true });
        // languages
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'], configurable: true });
        // plugins
        Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5], configurable: true });
        // chrome runtime
        window.chrome = window.chrome || { runtime: {} };
        // permissions query fallback
        const origQuery = (navigator.permissions && navigator.permissions.query) || null;
        if (origQuery) {
            navigator.permissions.query = (parameters) => {
                if (parameters && parameters.name === 'notifications') {
                    return Promise.resolve({ state: Notification.permission });
                }
                return origQuery(parameters);
            };
        }
    """
    try:
        await context.add_init_script(stealth_js)
    except Exception:
        # If add_init_script fails, continue without it (best-effort)
        pass

    return context


async def scan_one(playwright, browser, row: dict, idx: int, total: int, semaphore: asyncio.Semaphore):
    """
    Process a single warn row: try navigation attempts, capture DOM, save debug artifacts.
    """
    id_val = row.get("id") or str(idx)
    url = row.get("url") or row.get("URL") or row.get("link") or ""
    safe_name = sanitize_filename(f"{id_val}_{url}")
    out_prefix = OUT_DIR / safe_name

    async with semaphore:
        print(f"[{idx}/{total}] id={id_val} url={url}")
        debug = {
            "id": id_val,
            "url": url,
            "final_url": None,
            "attempts": [],
            "dom": {},
            "timings": {},
            "upi": [],
            "error": None
        }

        # choose UA and proxy for this attempt (rotate)
        ua = COMMON_UAS[idx % len(COMMON_UAS)]
        proxy = PROXIES[idx % len(PROXIES)] if PROXIES else None

        # We will try per-attempt strategies: domcontentloaded then networkidle; repeat up to MAX_ATTEMPTS
        for attempt_no in range(1, MAX_ATTEMPTS + 1):
            # Create fresh context per attempt for isolation
            context = await create_stealth_context(browser, user_agent=ua, proxy=proxy)
            page = await context.new_page()
            page.set_default_navigation_timeout(NAV_TIMEOUT_HEADLESS)
            page.set_default_timeout(NAV_TIMEOUT_HEADLESS)

            # Optionally tiny human-like move (helps some heuristics)
            try:
                await page.mouse.move(10, 10)
            except Exception:
                pass

            # list of wait_until strategies to try in this attempt
            wait_sequence = ["domcontentloaded", "networkidle"]
            attempt_info = {"attempt_no": attempt_no, "steps": []}
            nav_success = False
            for wait_cond in wait_sequence:
                step = {"wait_until": wait_cond, "timeout_ms": NAV_TIMEOUT_HEADLESS, "result": None, "error": None}
                start = time.perf_counter()
                try:
                    await page.goto(url, wait_until=wait_cond, timeout=NAV_TIMEOUT_HEADLESS)
                    nav_time = time.perf_counter() - start
                    final = page.url
                    # small delay to let dynamic scripts run
                    try:
                        await asyncio.sleep(0.12)
                    except Exception:
                        pass
                    dom = await extract_dom_features(page)
                    step["result"] = {"final_url": final, "nav_time_s": nav_time}
                    attempt_info["steps"].append(step)
                    # record into debug
                    debug["dom"] = dom
                    debug["final_url"] = final
                    debug["timings"]["nav_time_s"] = nav_time
                    debug["upi"] = dom.get("upi_intents", [])
                    nav_success = True
                    # save artifacts
                    if SAVE_SCREENSHOT:
                        try:
                            png_path = out_prefix.with_suffix(".png")
                            await page.screenshot(path=str(png_path), full_page=False)
                        except Exception:
                            pass
                    if SAVE_HTML:
                        try:
                            html_path = out_prefix.with_suffix(".html")
                            html = await page.content()
                            html_path.write_text(html, encoding="utf8", errors="ignore")
                        except Exception:
                            pass
                    break  # break wait_sequence (successful)
                except PlaywrightTimeoutError as te:
                    nav_time = time.perf_counter() - start
                    step["error"] = f"Timeout after {nav_time:.2f}s: {str(te)}"
                    attempt_info["steps"].append(step)
                    # try next wait_cond
                    continue
                except Exception as e:
                    nav_time = time.perf_counter() - start
                    step["error"] = f"Error after {nav_time:.2f}s: {str(e)}"
                    attempt_info["steps"].append(step)
                    continue

            debug["attempts"].append(attempt_info)
            # close page & context
            try:
                await page.close()
            except Exception:
                pass
            try:
                await context.close()
            except Exception:
                pass

            if nav_success:
                debug["error"] = None
                break  # success, no more attempts
            else:
                debug["error"] = f"Attempt {attempt_no} failed (see attempts)."
                # small backoff before next attempt
                await asyncio.sleep(0.5 * attempt_no)

        # Save debug JSON
        debug_path = out_prefix.with_suffix(".debug.json")
        safe_write_json(debug_path, debug)
        if debug.get("error"):
            print("  -> saved debug json:", str(debug_path))
            print("  ERROR:", debug["error"])
        else:
            print("  -> saved debug json:", str(debug_path))

        return debug


def run_one_headless_scan(url: str, timeout: int = 30):
    """
    Scan URL with Playwright - improved error handling
    """
    result = {
        "url": url,
        "success": False,
        "error": None,
        "script_count": 0,
        "iframe_count": 0,
        "form_count": 0,
        "has_otp_input": False,
        "has_pin_input": False,
        "upi_count": 0,
        "timings": 0
    }
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            page = context.new_page()
            
            try:
                # Navigate with shorter timeout
                page.goto(url, timeout=timeout * 1000, wait_until='domcontentloaded')
                
                # Wait a bit for dynamic content
                page.wait_for_timeout(2000)
                
                # Extract features
                features = page.evaluate("""() => {
                    return {
                        script_count: document.scripts.length,
                        iframe_count: document.querySelectorAll('iframe').length,
                        form_count: document.querySelectorAll('form').length,
                        has_otp_input: !!document.querySelector('input[autocomplete="one-time-code"], input[name*="otp" i], input[id*="otp" i]'),
                        has_pin_input: !!document.querySelector('input[type="password"], input[name*="pin" i], input[id*="pin" i]'),
                        upi_links: Array.from(document.querySelectorAll('a[href]'))
                            .map(a => a.href)
                            .filter(h => h.toLowerCase().includes('upi') || h.startsWith('upi:'))
                    };
                }""")
                
                result.update({
                    "success": True,
                    "script_count": features.get("script_count", 0),
                    "iframe_count": features.get("iframe_count", 0),
                    "form_count": features.get("form_count", 0),
                    "has_otp_input": features.get("has_otp_input", False),
                    "has_pin_input": features.get("has_pin_input", False),
                    "upi_count": len(features.get("upi_links", []))
                })
                
            except PlaywrightTimeout:
                result["error"] = f"Page load timeout after {timeout}s"
            except Exception as e:
                result["error"] = f"Page error: {str(e)}"
            finally:
                browser.close()
    
    except Exception as e:
        result["error"] = f"Browser launch failed: {str(e)}"
    
    return result


async def main():
    if not WARN_CSV.exists():
        print("WARN CSV not found:", WARN_CSV)
        return

    # load warn rows
    rows = []
    with WARN_CSV.open("r", encoding="utf8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    total = len(rows)
    if total == 0:
        print("WARN list empty.")
        return
    print(f"Scanning {total} WARN URLs from {WARN_CSV} with concurrency={CONCURRENCY}")

    semaphore = asyncio.Semaphore(CONCURRENCY)
    async with async_playwright() as playwright:
        # Launch a single headless browser; contexts will be created per task
        browser = await playwright.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"])
        # schedule tasks
        tasks = [asyncio.create_task(scan_one(playwright, browser, row, idx + 1, total, semaphore)) for idx, row in enumerate(rows)]
        # Wait for completions (gather preserves exceptions)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Close browser
        try:
            await browser.close()
        except Exception:
            pass

    # Summarize outcomes (count successes)
    success = sum(1 for r in results if isinstance(r, dict) and not r.get("error"))
    print(f"Done. {success}/{total} successful navigations (no error).")

if __name__ == "__main__":
    asyncio.run(main())
