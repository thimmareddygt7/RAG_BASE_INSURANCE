# ============================================================
# Health Insurance RAG: API image
# ============================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface

# System libraries used by PyMuPDF, lxml and sentence-transformers.
# tesseract-ocr is used for scanned pages (Stage 6).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libglib2.0-0 \
        libgl1 \
        libgomp1 \
        tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only PyTorch keeps the image far smaller than the default CUDA build.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# Dependencies first so this layer is cached between code changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Only the code the API needs (data/ is mounted at runtime, secrets are never copied).
COPY app ./app
COPY eval ./eval
COPY scripts ./scripts
COPY config.yaml .

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p data/raw data/gold data/synthetic data/vectorstore "$HF_HOME" \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
