"""Loads versioned prompts from the PROMPTS_DIR mount.

File naming: {name}_v{N}.md  — the highest N is loaded.
Each file starts with '# version: N' (informational only; N is read from filename).
"""
import glob
import os
import re
from config import PROMPTS_DIR


def load(name: str) -> str:
    """Return the content of the latest version of prompt `name`."""
    pattern = os.path.join(PROMPTS_DIR, f"{name}_v*.md")
    matches = glob.glob(pattern)
    if not matches:
        raise FileNotFoundError(
            f"No prompt found for '{name}' in {PROMPTS_DIR}. "
            f"Expected files matching {pattern}"
        )
    latest = max(
        matches,
        key=lambda f: int(re.search(r"_v(\d+)\.md$", f).group(1)),
    )
    with open(latest) as f:
        return f.read()


def render(name: str, **kwargs: str) -> str:
    """Load prompt and format with keyword substitutions."""
    return load(name).format(**kwargs)
