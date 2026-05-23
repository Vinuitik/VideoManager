import asyncio


async def extract_browser_cookies(domain: str, browser: str = "auto") -> dict:
    """Extract cookies for a domain from the host browser (Chrome or Firefox).

    NOTE: Host browser access is limited inside Docker on Windows.
    If this fails, store credentials via POST /api/credentials and use
    authenticate_headless instead.
    """

    def _extract() -> dict:
        try:
            import browser_cookie3
        except ImportError:
            return {"success": False, "cookies": [], "error": "browser_cookie3 not available"}

        errors = []

        if browser in ("chrome", "auto"):
            try:
                jar = browser_cookie3.chrome(domain_name=domain)
                cookies = [
                    {"name": c.name, "value": c.value, "domain": c.domain}
                    for c in jar
                ]
                if cookies:
                    return {"success": True, "cookies": cookies, "browser": "chrome"}
            except Exception as exc:
                errors.append(f"chrome: {exc}")

        if browser in ("firefox", "auto"):
            try:
                jar = browser_cookie3.firefox(domain_name=domain)
                cookies = [
                    {"name": c.name, "value": c.value, "domain": c.domain}
                    for c in jar
                ]
                if cookies:
                    return {"success": True, "cookies": cookies, "browser": "firefox"}
            except Exception as exc:
                errors.append(f"firefox: {exc}")

        return {
            "success": False,
            "cookies": [],
            "error": (
                "No cookies found from host browser. "
                "Inside Docker, host browser cookies are inaccessible. "
                f"Details: {'; '.join(errors)}. "
                "Use POST /api/credentials and authenticate_headless instead."
            ),
        }

    return await asyncio.get_event_loop().run_in_executor(None, _extract)
