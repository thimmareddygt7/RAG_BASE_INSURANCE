# Architecture

## Query path

```mermaid
flowchart LR
    U[User login] -->|JWT with group| API[FastAPI]
    API --> Q[Embed query + sparse query]
    Q --> S[Qdrant hybrid search<br/>dense + BM25, RRF fusion<br/>FILTER: allowed_groups contains user group]
    S --> R[Cross-encoder reranker]
    R --> L[Groq LLM<br/>answer from context only]
    L --> C[Citation check<br/>cited page contains support?]
    C --> A[Answer + document + page<br/>or: not in the documents]
```

## Ingestion path

```mermaid
flowchart LR
    F[PDF / MD / HTML] --> H{sha256 changed?}
    H -- no --> X[Skip]
    H -- yes --> P[Parse pages]
    P --> O{Text layer?}
    O -- no --> OCR[OCR page]
    O -- yes --> T[Layout-aware table parsing]
    OCR --> T
    T --> CH[Chunk: section-aware, tables whole,<br/>title + heading prepended]
    CH --> E[Dense embedding + sparse BM25 vector]
    E --> U[Upsert to Qdrant<br/>doc_id, page, version, allowed_groups<br/>delete old chunks of changed files]
```

## Key design rules

1. **Permissions are enforced inside the vector query.** The group comes from the signed token, never from the request body. Filtering after retrieval would leak restricted text into the reranker and the prompt.
2. **One collection holds dense and sparse vectors**, so hybrid search and the permission filter run in a single Qdrant query.
3. **Models are fixed across stages** (see `eval/stages.yaml`), so measured differences come from the pipeline change and not from a different model.
4. **Every chunk keeps `doc_id`, `page` and `version`**, which makes page-level evaluation and citation checking possible.
