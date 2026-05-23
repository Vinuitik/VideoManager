import chromadb
from config import CHROMA_HOST, CHROMA_PORT, CHROMA_COLLECTION

_collection = None


def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        _collection = client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection
