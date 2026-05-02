# RAG-Based Medical Report Simplification System

An intelligent, end-to-end pipeline that converts complex medical documents into clear, patient-friendly explanations using OCR, NLP, RAG, and NVIDIA LLM APIs.

## Architecture

```
PDF/Image → [OCR: Tesseract] → Raw Text
                ↓
        [NLP: spaCy/SciSpacy] → Structured Entities
                ↓
        [RAG: FAISS + Embeddings] → Medical Knowledge
                ↓
        [LLM: NVIDIA NIM] → Simplified Explanation
                ↓
        React Dashboard with Highlights
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui |
| Backend | Python FastAPI |
| OCR | Tesseract 5.0 + OpenCV |
| NLP | spaCy 3.7 + SciSpacy (en_core_sci_lg) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector DB | FAISS |
| LLM | NVIDIA NIM API (Llama-3.1-8B / Mistral-7B) |
| Database | SQLite (dev) / PostgreSQL (prod) |

## Prerequisites

- Python 3.10+
- Node.js 20+
- Tesseract OCR 5.0+ (`tesseract --version`)
- poppler-utils (for PDF processing)
- NVIDIA API Key (get from [build.nvidia.com](https://build.nvidia.com))

## Quick Start

### 1. Clone and Setup

```bash
git clone <repo-url>
cd medical-report-simplifier
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Download spaCy/SciSpacy models
python -m spacy download en_core_web_sm
# Optional: install a SciSpacy biomedical model if you want stronger NER than the regex/spaCy fallback
# pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz

# Optional: install the ML/vector stack for sentence-transformer embeddings + FAISS retrieval
pip install -r requirements-ml.txt

# Notes:
# - On Python 3.13 this enables vector RAG, but SciSpaCy is skipped because upstream wheels are not available.
# - For full SciSpaCy biomedical NER, use Python 3.12 or lower.
# - For a reproducible Python 3.12 biomedical setup, run:
#   PYTHON_BIN=python3.12 ./setup_biomedical_env.sh

# Create .env
cp ../.env.example .env
# Edit .env and add your NVIDIA_API_KEY

# Run server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/auth/register` | POST | Create a user account and issue a JWT |
| `/api/auth/login` | POST | Log in and issue a JWT |
| `/api/auth/me` | GET | Fetch the current signed-in user |
| `/api/upload` | POST | Upload PDF/image report |
| `/api/process/{file_id}` | POST | Run full simplification pipeline |
| `/api/process/{file_id}/async` | POST | Queue report processing as a background job |
| `/api/reports/{report_id}/file` | GET | Stream the original uploaded file |
| `/api/reports/{report_id}/pages/{page_number}/preview` | GET | Render a report page preview for visual overlays |
| `/api/jobs/{job_id}` | GET | Poll a background job |
| `/api/knowledge-base/rebuild/async` | POST | Rebuild the KB and vector index in the background |
| `/api/health/models` | GET | Inspect the active NLP and embedding backends |

Full API docs at `http://localhost:8000/api/docs`.

## Environment Variables

See `.env.example` for all available options.

Key variables:
- `NVIDIA_API_KEY` - Required for LLM generation
- `DATABASE_URL` - Database connection string
- `UPLOAD_DIR` - Where uploaded files are stored
- `AUTH_ENABLED` - Require either a JWT or app-wide bearer token on protected routes
- `JWT_SECRET_KEY` - Secret used to sign login tokens
- `SPACY_MODEL_PATH` - Optional absolute path to a local SciSpaCy/spaCy model directory
- `EMBEDDING_MODEL_PATH` - Optional absolute path to a local sentence-transformers model directory

## Project Structure

```
medical-report-simplifier/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # API endpoints
│   │   ├── core/              # OCR, NLP, RAG, LLM engines
│   │   ├── services/          # Pipeline orchestration
│   │   ├── models/            # Database models
│   │   └── utils/             # Helpers
│   ├── knowledge_base/        # Medical knowledge data
│   ├── alembic/               # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/             # Route pages
│   │   └── services/          # API client
│   └── package.json
├── docker-compose.yml
├── Makefile
└── ROADMAP.md                 # 20-phase implementation plan
```

## Implementation Phases

See [ROADMAP.md](ROADMAP.md) for the complete 20-phase implementation plan covering:
1. Project Planning
2. Environment Setup
3. Architecture Design
4. Database & Vector Store
5. Backend API Foundation
6. Frontend Foundation
7. OCR Module
8. PDF/Image Processing
9-10. NLP & Entity Recognition
11. Knowledge Base Construction
12. FAISS Vector Index
13. RAG Retrieval Pipeline
14. NVIDIA LLM Integration
15. Prompt Engineering
16. Visual Highlighting
17. Dashboard UI
18. End-to-End Integration
19. Evaluation Framework
20. Deployment & Documentation

## PostgreSQL And Migrations

```bash
cd backend
alembic upgrade head
```

For local PostgreSQL development, set `DATABASE_URL` in `.env` to:

```bash
postgresql://postgres:postgres@localhost:5432/medical_reports
```

## Benchmark Suite

The project now includes a local benchmark runner aligned to the report metrics:

```bash
cd backend
python run_benchmark_suite.py --task ocr --input benchmarks/gold_ocr.json
python run_benchmark_suite.py --task ner --input benchmarks/gold_ner.json
python run_benchmark_suite.py --task simplification --input benchmarks/gold_simplification.json
```

Each input file can be either:
- A JSON array of records
- A JSON object with a `records` key
- A `.jsonl` file with one record per line

Supported schemas:
- OCR: `{"reference_text": "...", "predicted_text": "..."}`
- NER: `{"expected_entities": [...], "predicted_entities": [...]}`
- Simplification: `{"reference_text": "...", "candidate_text": "..."}`

Generate the report-style tables described in the BTP report:

```bash
cd backend
python generate_report_tables.py
```

## Visual Overlays

The dashboard now supports:
- Original PDF/image preview
- Page-level preview images
- Entity and abnormal-test highlight overlays projected onto the report page

This is driven by OCR/PDF word coordinates captured during processing and exposed through the stored `visual_overlays` payload.

## Background Jobs

Long-running work can now be queued through background APIs:

```bash
curl -X POST http://localhost:8000/api/process/<file_id>/async
curl http://localhost:8000/api/jobs/<job_id>
curl -X POST http://localhost:8000/api/knowledge-base/rebuild/async
```

Jobs are now persisted in the application database, so status survives backend restarts and queued/running jobs can be resumed by the app.

## Biomedical Docker Runtime

The backend Docker image now targets a Python 3.12 biomedical runtime and preloads the ML stack:

```bash
docker build --platform linux/amd64 -t medsimplify-biomedical -f backend/Dockerfile backend
docker run --rm medsimplify-biomedical python check_report_runtime.py
```

The image is designed to preload:
- `scispacy`
- `en_core_sci_lg`
- `sentence-transformers/all-MiniLM-L6-v2`

On Apple Silicon hosts, `linux/amd64` is the verified build target because it consistently pulls prebuilt wheels for the biomedical stack instead of forcing slower source builds.

## License

Academic Project - IIIT Pune
