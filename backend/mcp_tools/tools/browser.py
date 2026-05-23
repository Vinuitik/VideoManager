import re
import tempfile
import os
from urllib.parse import urlparse

from playwright.async_api import async_playwright

_VIDEO_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\.m3u8",
        r"\.mp4",
        r"\.webm",
        r"/manifest",
        r"/playlist",
        r"videodelivery\.net",
        r"akamaized\.net",
        r"fastly\.net",
        r"cloudfront\.net",
        r"cdn.*video",
        r"media.*cdn",
    ]
]


async def inspect_page_network(url: str, cookies_path: str = "") -> dict:
    """Load page in headless Chromium, intercept network requests, return candidate video URLs."""
    candidates: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        )

        if cookies_path and os.path.exists(cookies_path):
            context.add_cookies(_parse_netscape_cookies(cookies_path))

        page = await context.new_page()

        def on_request(request):
            req_url = request.url
            for pattern in _VIDEO_PATTERNS:
                if pattern.search(req_url):
                    candidates.append(
                        {
                            "url": req_url,
                            "method": request.method,
                            "resource_type": request.resource_type,
                            "headers": dict(request.headers),
                        }
                    )
                    break

        page.on("request", on_request)

        try:
            await page.goto(url, wait_until="networkidle", timeout=30_000)
            await page.wait_for_timeout(3_000)
        except Exception:
            pass
        finally:
            await browser.close()

    return {"candidates": candidates, "count": len(candidates)}


async def authenticate_headless(
    url: str,
    domain: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> dict:
    """Log in to a site. Looks up credentials by domain if username/password are omitted.

    Returns {success, cookies_path, error}.
    """
    if not username or not password:
        from services.credentials_store import get as get_creds
        lookup_domain = domain or urlparse(url).netloc
        creds = get_creds(lookup_domain)
        if not creds:
            return {
                "success": False,
                "cookies_path": "",
                "error": (
                    f"No credentials stored for '{lookup_domain}'. "
                    "Use POST /api/credentials to add them."
                ),
            }
        username = creds["username"]
        password = creds["password"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto(url, timeout=30_000)

            for sel in [
                "input[type=email]",
                "input[name=email]",
                "input[name=username]",
                "input[name=login]",
                "#email",
                "#username",
                "#login",
            ]:
                try:
                    await page.fill(sel, username, timeout=2_000)
                    break
                except Exception:
                    continue

            for sel in [
                "input[type=password]",
                "#password",
                "input[name=password]",
                "input[name=pass]",
            ]:
                try:
                    await page.fill(sel, password, timeout=2_000)
                    break
                except Exception:
                    continue

            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle", timeout=15_000)

            cookies = await context.cookies()
            tmp = tempfile.NamedTemporaryFile(
                delete=False, suffix=".txt", prefix="vm_cookies_"
            )
            _write_netscape_cookies(tmp.name, cookies)

            return {"success": True, "cookies_path": tmp.name, "error": ""}
        except Exception as exc:
            return {"success": False, "cookies_path": "", "error": str(exc)}
        finally:
            await browser.close()


# ── helpers ──────────────────────────────────────────────────────────────────

def _write_netscape_cookies(path: str, cookies: list[dict]) -> None:
    with open(path, "w") as f:
        f.write("# Netscape HTTP Cookie File\n")
        for c in cookies:
            domain = c["domain"]
            if not domain.startswith("."):
                domain = "." + domain
            httponly = "TRUE" if c.get("httpOnly") else "FALSE"
            secure = "TRUE" if c.get("secure") else "FALSE"
            expires = int(c.get("expires", 0))
            f.write(
                f"{domain}\t{httponly}\t{c['path']}\t{secure}\t{expires}"
                f"\t{c['name']}\t{c['value']}\n"
            )


def _parse_netscape_cookies(path: str) -> list[dict]:
    cookies = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            domain, httponly, path_, secure, expires, name, value = parts[:7]
            cookies.append(
                {
                    "name": name,
                    "value": value,
                    "domain": domain,
                    "path": path_,
                    "secure": secure == "TRUE",
                    "httpOnly": httponly == "TRUE",
                    "expires": int(expires) if expires.lstrip("-").isdigit() else -1,
                }
            )
    return cookies
