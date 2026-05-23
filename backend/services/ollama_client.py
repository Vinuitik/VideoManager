import json
import httpx
from config import OLLAMA_URL, AGENT_MODEL


async def chat(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """Send a chat request to Ollama. Returns the assistant message dict."""
    payload: dict = {
        "model": AGENT_MODEL,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]


def parse_tool_calls(message: dict) -> list[dict]:
    """Extract and normalise tool_calls from an Ollama message.

    Ollama may return arguments as a JSON string or as a parsed dict.
    Always returns a list of {name, arguments} dicts.
    """
    raw = message.get("tool_calls") or []
    result = []
    for tc in raw:
        fn = tc.get("function", {})
        args = fn.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        result.append({"name": fn.get("name", ""), "arguments": args})
    return result
