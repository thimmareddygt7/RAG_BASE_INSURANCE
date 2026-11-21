"""Inspect indexed chunks in Qdrant to verify tables, OCR and header/footer stripping."""

from app.config import load_settings
from app.pipeline import collection_name
from app.store.qdrant_store import QdrantStore

def main():
    settings = load_settings(stage="stage6_ocr_tables")
    col = collection_name(settings, False)
    print("Collection:", col)

    store = QdrantStore(
        settings.qdrant_host,
        settings.qdrant_port,
        col,
        384,
        "dense",
        "bm25",
        "Qdrant/bm25"
    )

    records, _ = store._client.scroll(col, limit=100, with_payload=True)
    print(f"Total chunks in Qdrant: {len(records)}\n")

    tables = [r for r in records if r.payload.get("kind") == "table"]
    print(f"=== 1. Table Chunks Found: {len(tables)} ===")
    for t in tables[:4]:
        p = t.payload
        print(f"Doc: {p['doc_id']} | Page: {p['page']} | Section: {p['section']}")
        print(p["text"])
        print("-" * 50)

    print("\n=== 2. Scanned Document Chunks (SPECIAL_RIDER_SCANNED) ===")
    scanned = [r for r in records if r.payload.get("doc_id") == "SPECIAL_RIDER_SCANNED"]
    for s in scanned:
        p = s.payload
        print(f"Page: {p['page']} | Kind: {p['kind']} | Section: {p['section']}")
        print(p["text"])
        print("-" * 50)

    print("\n=== 3. Header / Footer Stripping Check ===")
    v1_chunks = [r for r in records if r.payload.get("doc_id") == "APEX_HEALTH_V1"]
    has_header = any("Apex General Insurance - Apex Health Shield Policy" in r.payload["text"] for r in v1_chunks)
    has_footer = any("Policy Terms & Conditions | Page" in r.payload["text"] for r in v1_chunks)
    print(f"Running header present in chunks? {has_header} (Should be False)")
    print(f"Running footer present in chunks? {has_footer} (Should be False)")

if __name__ == "__main__":
    main()

