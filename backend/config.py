import os

VIDEOS_DIR = os.getenv("VIDEOS_DIR", "/videos")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
AGENT_MODEL = "qwen2.5:3b"
EMBED_MODEL = "nomic-embed-text"

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = "download_cases"

PROMPTS_DIR = os.getenv("PROMPTS_DIR", "/prompts")

CREDENTIALS_DB_PATH = os.getenv("CREDENTIALS_DB_PATH", "/data/credentials.db")
