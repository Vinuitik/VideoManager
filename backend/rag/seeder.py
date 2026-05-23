import json
import os

from rag.client import get_collection
from rag.embedder import embed


async def seed_if_empty() -> None:
    collection = get_collection()

    if collection.count() > 0:
        return

    seed_path = os.path.join(os.path.dirname(__file__), "seed_cases.json")
    with open(seed_path) as f:
        cases = json.load(f)

    ids, documents, embeddings, metadatas = [], [], [], []

    for i, case in enumerate(cases):
        doc_text = (
            f"Problem: {case['problem']}\n\n"
            f"Chain of thought: {case['cot']}\n\n"
            f"Solution steps: {' → '.join(case['solution_steps'])}"
        )
        ids.append(f"seed_{i}")
        documents.append(doc_text)
        embeddings.append(await embed(doc_text))
        metadatas.append({
            "domain_pattern": case["domain_pattern"],
            "requires_auth": str(case["requires_auth"]),
            "requires_cookies": str(case["requires_cookies"]),
            "tags": ",".join(case.get("tags", [])),
            "cot": case["cot"],
            "solution_steps": json.dumps(case["solution_steps"]),
        })

    collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
    print(f"[RAG] Seeded {len(cases)} cases into ChromaDB")
