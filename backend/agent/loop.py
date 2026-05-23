"""ReAct agent loop: Think → Act (tool call) → Observe → repeat.

One AgentLoop instance per download job. Runs as an asyncio coroutine so
multiple jobs run concurrently in the same event loop.
"""
from __future__ import annotations

import asyncio
from urllib.parse import urlparse

import state
from agent.prompts import load as load_prompt, render as render_prompt
from services import ollama_client
from mcp_tools.tools import ytdlp, browser, rag as rag_tools

MAX_ITERATIONS = 10

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "query_rag",
            "description": "Search the knowledge base for known solutions. Call this FIRST.",
            "parameters": {
                "type": "object",
                "properties": {
                    "problem": {
                        "type": "string",
                        "description": "Description of the problem including domain and error text",
                    }
                },
                "required": ["problem"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "try_ytdlp",
            "description": "Attempt a yt-dlp download. Returns {success, filename, error}.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to download"},
                    "extra_opts": {
                        "type": "object",
                        "description": (
                            "Extra yt-dlp options. Examples: "
                            "{\"format\": \"best\"}, "
                            "{\"http_headers\": {\"Referer\": \"https://example.com\"}}, "
                            "{\"videopassword\": \"secret\"}"
                        ),
                    },
                    "cookies_path": {
                        "type": "string",
                        "description": "Path to a Netscape-format cookies.txt file",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_page_network",
            "description": (
                "Load page in headless Chromium, intercept all network requests, "
                "return candidate video stream URLs (m3u8, mp4, CDN)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Page URL to inspect"},
                    "cookies_path": {
                        "type": "string",
                        "description": "Optional cookies for authenticated pages",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "authenticate_headless",
            "description": (
                "Log in to a site using stored credentials (looked up by domain). "
                "Returns {success, cookies_path}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Login page URL"},
                    "domain": {
                        "type": "string",
                        "description": "Domain key to look up in credentials store (e.g. 'youtube.com')",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_case",
            "description": "Record this download case for future reference. Always call at the end.",
            "parameters": {
                "type": "object",
                "properties": {
                    "problem": {"type": "string"},
                    "solution": {"type": "string"},
                    "success": {"type": "boolean"},
                    "cot": {
                        "type": "string",
                        "description": "Step-by-step reasoning that led to success or failure",
                    },
                },
                "required": ["problem", "solution", "success", "cot"],
            },
        },
    },
]

_TOOL_FN_MAP = {
    "query_rag": rag_tools.query_rag,
    "try_ytdlp": ytdlp.try_ytdlp,
    "inspect_page_network": browser.inspect_page_network,
    "authenticate_headless": browser.authenticate_headless,
    "write_case": rag_tools.write_case,
}


class AgentLoop:
    def __init__(self, job: state.Job) -> None:
        self.job = job
        self.history: list[dict] = []
        self._wrote_case = False

    async def run(self) -> None:
        self.job.status = "agent"
        self._log("Agent started", "")

        domain = urlparse(self.job.url).netloc

        system_prompt = load_prompt("system")
        self.history.append({"role": "system", "content": system_prompt})

        user_msg = render_prompt(
            "think",
            url=self.job.url,
            domain=domain,
            error=self.job.error or "yt-dlp could not find a supported extractor",
        )
        self.history.append({"role": "user", "content": user_msg})

        for iteration in range(MAX_ITERATIONS):
            try:
                message = await ollama_client.chat(self.history, tools=TOOL_DEFINITIONS)
            except Exception as exc:
                self._log("LLM error", str(exc))
                break

            content = message.get("content") or ""
            tool_calls = ollama_client.parse_tool_calls(message)

            if content:
                self._log("think", content)

            if not tool_calls:
                # Model finished without a tool call
                break

            # Add assistant message (with tool_calls) to history
            self.history.append(message)

            for tc in tool_calls:
                tool_name = tc["name"]
                args = tc["arguments"]

                self._log("act", f"{tool_name}({args})")
                result = await self._call_tool(tool_name, args)
                self._log("observe", str(result))

                # Feed observation back
                self.history.append(
                    {"role": "tool", "name": tool_name, "content": str(result)}
                )

                # Check success
                if tool_name == "try_ytdlp" and isinstance(result, dict) and result.get("success"):
                    self.job.filename = result.get("filename", "")
                    self.job.status = "done"
                    self.job.progress = 100.0
                    self._log("done", f"Downloaded: {self.job.filename}")
                    if not self._wrote_case:
                        await rag_tools.write_case(
                            problem=f"{domain}: {self.job.error}",
                            solution=f"try_ytdlp with args: {args}",
                            success=True,
                            cot=self._build_cot(),
                        )
                        self._wrote_case = True
                    return

                if tool_name == "write_case":
                    self._wrote_case = True

        # Exhausted iterations
        if self.job.status != "done":
            self.job.status = "error"
            if not self._wrote_case:
                await rag_tools.write_case(
                    problem=f"{domain}: {self.job.error}",
                    solution="Agent exhausted all options without success",
                    success=False,
                    cot=self._build_cot(),
                )

    async def _call_tool(self, name: str, args: dict):
        fn = _TOOL_FN_MAP.get(name)
        if fn is None:
            return {"error": f"Unknown tool: {name}"}
        try:
            return await fn(**args)
        except Exception as exc:
            return {"error": str(exc)}

    def _log(self, role: str, content: str) -> None:
        entry = {"role": role, "content": content}
        self.job.agent_log.append(entry)

    def _build_cot(self) -> str:
        steps = [
            f"[{e['role']}] {e['content']}"
            for e in self.job.agent_log
            if e["role"] in ("think", "act", "observe")
        ]
        return "\n".join(steps)
