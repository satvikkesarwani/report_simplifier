# Backend Dockerfile — Python 3.12 for scispacy 0.5.5 compatibility
FROM python:3.12-slim

ARG SCISPACY_MODEL_URL=https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.5/en_core_sci_lg-0.5.5.tar.gz
ARG EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENV HF_HOME=/root/.cache/huggingface
ENV TRANSFORMERS_CACHE=/root/.cache/huggingface/hub
ENV PIP_PREFER_BINARY=1
ENV PYTHONUNBUFFERED=1

# ── System dependencies ────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies (cached layer) ────────────────────────────────────────
COPY requirements.txt requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-ml.txt

# ── NLP models ─────────────────────────────────────────────────────────────────
# Fallback English model (always available, small)
RUN python -m spacy download en_core_web_sm

# Biomedical SciSpaCy model — en_core_sci_lg 0.5.5 (requires Python <= 3.12)
# The || true means a network failure won't abort the build; fallback stays active.
RUN pip install --no-cache-dir "${SCISPACY_MODEL_URL}" \
    && python -c "import spacy; spacy.load('en_core_sci_lg'); print('SciSpaCy en_core_sci_lg OK')" \
    || echo "WARNING: SciSpaCy install failed — falling back to en_core_web_sm"

# ── Sentence-transformers embedding model (warm HF hub cache) ──────────────────
# ARG variables are NOT expanded inside Python heredoc blocks, so we use -c.
# The model name is interpolated at Docker build time via shell substitution.
RUN python -c "from sentence_transformers import SentenceTransformer; \
m = SentenceTransformer('${EMBEDDING_MODEL}'); \
print('Embedding model cached:', '${EMBEDDING_MODEL}', 'dim=', m.get_sentence_embedding_dimension())"

# ── Application code ───────────────────────────────────────────────────────────
COPY . .

# Ensure upload directory exists
RUN mkdir -p uploads

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
