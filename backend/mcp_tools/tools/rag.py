import json
import uuid
from rag.client import get_collection
from rag.embedder import embed


async def query_rag(problem: str, n_results: int = 3) -> list[dict]:
    """Semantic search over the download cases knowledge base.

    Returns up to n_results cases sorted by similarity (highest first).
    """
    embedding = await embed(problem)
    collection = get_collection()

    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(n_results, collection.count() or 1),
        include=["documents", "metadatas", "distances"],
    )

    cases = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(docs, metas, dists):
        cases.append(
            {
                "document": doc,
                "similarity": round(1.0 - dist, 3),
                "tags": meta.get("tags", ""),
                "cot": meta.get("cot", ""),
                "solution_steps": json.loads(meta.get("solution_steps", "[]")),
                "requires_auth": meta.get("requires_auth") == "True",
                "requires_cookies": meta.get("requires_cookies") == "True",
            }
        )

    return cases


async def write_case(
    problem: str,
    solution: str,
    success: bool,
    cot: str,
    tags: list[str] | None = None,
) -> dict:
    """Record a download case (success or failure) into the knowledge base."""
    doc_text = (
        f"Problem: {problem}\n\n"
        f"Chain of thought: {cot}\n\n"
        f"Solution: {solution}\n\n"
        f"Outcome: {'success' if success else 'failure'}"
    )
    embedding = await embed(doc_text)
    collection = get_collection()

    case_id = f"case_{uuid.uuid4().hex[:8]}"
    collection.add(
        ids=[case_id],
        documents=[doc_text],
        embeddings=[embedding],
        metadatas=[
            {
                "domain_pattern": "",
                "requires_auth": "False",
                "requires_cookies": "False",
                "tags": ",".join(tags or []),
                "cot": cot,
                "solution_steps": json.dumps([solution]),
                "success": str(success),
            }
        ],
    )

    return {"stored": True, "id": case_id}
