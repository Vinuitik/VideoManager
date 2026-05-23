"""FastMCP server — exposes the agent tools over Streamable HTTP.

Internal callers (AgentLoop) import tool functions directly.
External callers (Claude Code, future mobile) call via HTTP at /mcp.
"""
from fastmcp import FastMCP

from mcp_tools.tools.ytdlp import try_ytdlp as _try_ytdlp
from mcp_tools.tools.browser import inspect_page_network as _inspect, authenticate_headless as _auth
from mcp_tools.tools.cookies import extract_browser_cookies as _cookies
from mcp_tools.tools.rag import query_rag as _query_rag, write_case as _write_case

mcp = FastMCP(
    "videomanager-tools",
    description="Video download agent tools — yt-dlp, browser inspection, auth, RAG",
)


@mcp.tool()
async def try_ytdlp(url: str, extra_opts: dict = None, cookies_path: str = "") -> dict:
    """Attempt a yt-dlp download. Returns {success, filename, error}."""
    return await _try_ytdlp(url, extra_opts, cookies_path)


@mcp.tool()
async def inspect_page_network(url: str, cookies_path: str = "") -> dict:
    """Load page in headless Chromium and intercept video stream requests."""
    return await _inspect(url, cookies_path)


@mcp.tool()
async def authenticate_headless(
    url: str,
    domain: str = "",
    username: str = "",
    password: str = "",
) -> dict:
    """Log in to a site using stored or provided credentials. Returns cookies_path."""
    return await _auth(url, domain or None, username or None, password or None)


@mcp.tool()
async def extract_browser_cookies(domain: str, browser: str = "auto") -> dict:
    """Extract cookies from host Chrome or Firefox. Limited in Docker — prefer authenticate_headless."""
    return await _cookies(domain, browser)


@mcp.tool()
async def query_rag(problem: str, n_results: int = 3) -> list:
    """Search the download knowledge base for known solutions."""
    return await _query_rag(problem, n_results)


@mcp.tool()
async def write_case(
    problem: str,
    solution: str,
    success: bool,
    cot: str,
    tags: list = None,
) -> dict:
    """Record a download case (success or failure) for future RAG retrieval."""
    return await _write_case(problem, solution, success, cot, tags)
