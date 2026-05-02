#!/usr/bin/env bash

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3.12}"
VENV_DIR="${VENV_DIR:-.venv-biomedical}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-all-MiniLM-L6-v2}"
SCISPACY_MODEL_URL="${SCISPACY_MODEL_URL:-}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Expected ${PYTHON_BIN} to be installed for the biomedical setup." >&2
  exit 1
fi

"${PYTHON_BIN}" -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip wheel setuptools
python -m pip install -r requirements.txt
python -m pip install -r requirements-ml.txt
python -m spacy download en_core_web_sm

if [[ -n "${SCISPACY_MODEL_URL}" ]]; then
  python -m pip install "${SCISPACY_MODEL_URL}"
else
  echo "Skipping the SciSpaCy model tarball install. Set SCISPACY_MODEL_URL to install en_core_sci_lg." >&2
fi

python - <<PY
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("${EMBEDDING_MODEL}")
print(f"Cached embedding model: {model}")
PY

echo "Biomedical environment created at ${VENV_DIR}"
