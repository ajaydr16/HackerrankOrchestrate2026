import chromadb
from pathlib import Path

CHROMA_DIR = Path(__file__).resolve().parent / ".chromadb"
COLLECTION_NAME = "support_corpus"

_client = None
_collection = None


def _get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _client.get_collection(COLLECTION_NAME)
    return _collection


def retrieve(query: str, company: str | None = None, top_k: int = 8) -> list[dict]:
    collection = _get_collection()

    where_filter = None
    if company and company.lower() not in ("none", ""):
        company_key = company.lower().strip()
        company_map = {"hackerrank": "hackerrank", "claude": "claude", "visa": "visa"}
        if company_key in company_map:
            where_filter = {"company": company_map[company_key]}

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where_filter,
    )

    docs = []
    if results and results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            dist = results["distances"][0][i] if results["distances"] else 0
            docs.append({
                "text": doc,
                "company": meta.get("company", ""),
                "category": meta.get("category", ""),
                "filename": meta.get("filename", ""),
                "title": meta.get("title", ""),
                "distance": dist,
            })

    return docs


def retrieve_multi(query: str, top_k: int = 5) -> dict[str, list[dict]]:
    """Search all companies separately — useful when company is unknown."""
    results = {}
    for company in ["hackerrank", "claude", "visa"]:
        results[company] = retrieve(query, company=company, top_k=top_k)
    return results
