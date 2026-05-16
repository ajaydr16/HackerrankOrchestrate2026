import os
import re
import chromadb
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CHROMA_DIR = Path(__file__).resolve().parent / ".chromadb"
COLLECTION_NAME = "support_corpus"

MAX_CHUNK_CHARS = 2000


def _extract_metadata(text: str, filepath: Path) -> dict:
    parts = filepath.relative_to(DATA_DIR).parts
    company = parts[0] if parts else "unknown"
    category = "/".join(parts[1:-1]) if len(parts) > 2 else (parts[1] if len(parts) > 1 else "")
    filename = parts[-1] if parts else ""

    title = ""
    m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', text, re.MULTILINE)
    if m:
        title = m.group(1)

    return {"company": company, "category": category, "filename": filename, "title": title}


def _chunk_markdown(text: str) -> list[str]:
    # strip frontmatter
    text = re.sub(r'^---\n.*?\n---\n', '', text, count=1, flags=re.DOTALL)

    sections = re.split(r'(?=^#{1,3}\s)', text, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]

    if not sections:
        return [text.strip()] if text.strip() else []

    chunks = []
    current = ""
    for section in sections:
        if len(current) + len(section) < MAX_CHUNK_CHARS:
            current = current + "\n\n" + section if current else section
        else:
            if current:
                chunks.append(current.strip())
            if len(section) > MAX_CHUNK_CHARS:
                paragraphs = section.split("\n\n")
                sub = ""
                for p in paragraphs:
                    if len(sub) + len(p) < MAX_CHUNK_CHARS:
                        sub = sub + "\n\n" + p if sub else p
                    else:
                        if sub:
                            chunks.append(sub.strip())
                        sub = p
                if sub:
                    chunks.append(sub.strip())
                current = ""
            else:
                current = section

    if current:
        chunks.append(current.strip())

    return chunks


def build_index(force: bool = False) -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    existing = client.list_collections()
    existing_names = [c.name if hasattr(c, 'name') else c for c in existing]
    if COLLECTION_NAME in existing_names and not force:
        collection = client.get_collection(COLLECTION_NAME)
        if collection.count() > 0:
            print(f"Index already exists ({collection.count()} chunks). Use force=True to rebuild.")
            return collection

    if COLLECTION_NAME in existing_names:
        client.delete_collection(COLLECTION_NAME)

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    all_docs = []
    all_ids = []
    all_metas = []

    md_files = sorted(DATA_DIR.rglob("*.md"))
    print(f"Found {len(md_files)} markdown files in corpus.")

    for filepath in md_files:
        text = filepath.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            continue

        meta = _extract_metadata(text, filepath)
        chunks = _chunk_markdown(text)

        for i, chunk in enumerate(chunks):
            if not chunk or len(chunk) < 20:
                continue
            rel_path = str(filepath.relative_to(DATA_DIR)).replace("/", "_").replace(" ", "_")
            doc_id = f"{rel_path}_{i}"
            all_docs.append(chunk)
            all_ids.append(doc_id)
            all_metas.append(meta)

    batch_size = 5000
    for start in range(0, len(all_docs), batch_size):
        end = min(start + batch_size, len(all_docs))
        collection.add(
            documents=all_docs[start:end],
            ids=all_ids[start:end],
            metadatas=all_metas[start:end],
        )
        print(f"  Indexed batch {start}-{end} ({end - start} chunks)")

    print(f"Total: {collection.count()} chunks indexed.")
    return collection


if __name__ == "__main__":
    build_index(force=True)
