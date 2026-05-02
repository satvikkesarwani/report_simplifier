# 20-Phase Implementation Roadmap
## RAG-Based Medical Report Simplification System

---

## Architecture Overview (Cost-Free Tech Stack + NVIDIA LLM)

| Layer | Technology | Cost |
|-------|-----------|------|
| **Frontend** | React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui | Free |
| **Backend API** | Python FastAPI + Uvicorn | Free |
| **OCR Engine** | Tesseract OCR 5.0+ + pytesseract | Free |
| **NLP Engine** | spaCy + SciSpacy (en_core_sci_lg) | Free |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) | Free |
| **Vector DB** | FAISS (CPU/GPU) | Free |
| **LLM** | NVIDIA NIM API (LLaMA/Mistral) | User's API Key |
| **Database** | PostgreSQL (local) or SQLite | Free |
| **File Storage** | Local filesystem | Free |
| **Image Processing** | OpenCV + Pillow | Free |
| **Deployment** | Docker + Docker Compose | Free |

---

## Phase 1: Project Planning & Requirements Analysis
**Duration:** 3-4 days
**Deliverables:** Requirements doc, user stories, system specification

### Tasks:
- Finalize functional requirements from the BTP report
- Define user personas: patients (primary), doctors (feedback loop), admins
- Map all medical report types to support: CBC, LFT, RFT, Lipid Profile, Radiology, Discharge Summary
- Define acceptance criteria for each module
- Create data flow diagrams (DFD Level 0, 1, 2)
- Document API contract specifications (OpenAPI/Swagger plan)
- Define security requirements (HIPAA/GDPR compliance checklist for future)
- Set up project management board (GitHub Projects)

### Key Decisions:
- Use **FastAPI** (not Flask/Express) because all ML libraries are Python-native
- Use **SQLite** for MVP, **PostgreSQL** for production
- Use **NVIDIA NIM API** (llama-3.1-8b-instruct or mistral-7b-instruct) via user's API key
- Use **FAISS-CPU** for portability, **FAISS-GPU** optional for scale

---

## Phase 2: Development Environment Setup
**Duration:** 2-3 days
**Deliverables:** Consistent dev environment, CI/CD skeleton

### Tasks:
- Install Python 3.10+ with conda/venv
- Install Node.js 20+ with npm/pnpm
- Configure Git repository with branch protection (main, dev, feature/*)
- Set up pre-commit hooks: Black, isort, ESLint, Prettier
- Create `docker-compose.yml` for local services (PostgreSQL, optional MinIO for S3)
- Configure environment variable templates (`.env.example`)
- Set up logging infrastructure (structured JSON logs)
- Install system dependencies: Tesseract OCR, libgl1 (OpenCV), poppler-utils (PDF)

### Verification:
```bash
tesseract --version  # Should show 5.0+
python -c "import cv2, spacy, faiss, torch; print('OK')"
node -v  # Should show 20+
```

---

## Phase 3: Repository Structure & Architecture Design
**Duration:** 2-3 days
**Deliverables:** Clean monorepo, module interfaces, design patterns

### Directory Structure:
```
medical-report-simplifier/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Pydantic settings
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── upload.py    # File upload endpoints
│   │   │   │   ├── process.py   # OCR + NLP + RAG + LLM
│   │   │   │   ├── history.py   # Report history CRUD
│   │   │   │   └── health.py    # Health check
│   │   │   └── deps.py          # Dependency injection
│   │   ├── core/
│   │   │   ├── ocr_engine.py    # Tesseract + preprocessing
│   │   │   ├── nlp_engine.py    # spaCy/SciSpacy NER
│   │   │   ├── rag_engine.py    # FAISS + retriever
│   │   │   ├── llm_engine.py    # NVIDIA NIM API client
│   │   │   ├── prompt_builder.py# Prompt templates
│   │   │   └── abnormality.py   # Value comparison logic
│   │   ├── models/
│   │   │   ├── report.py        # SQLAlchemy models
│   │   │   └── schemas.py       # Pydantic schemas
│   │   ├── services/
│   │   │   ├── pipeline.py      # Orchestration service
│   │   │   └── knowledge_base.py# KB construction
│   │   ├── db/
│   │   │   ├── session.py       # DB connection
│   │   │   └── init_db.py       # Migrations
│   │   └── utils/
│   │       ├── file_handler.py  # Save/retrieve uploads
│   │       ├── image_preproc.py # OpenCV preprocessing
│   │       └── readability.py   # Flesch score calc
│   ├── knowledge_base/          # Medical data
│   │   ├── raw/                 # Scraped MedlinePlus/Testing.com
│   │   ├── chunks.json          # Chunked documents
│   │   └── faiss_index/         # Serialized FAISS index
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadZone.tsx
│   │   │   ├── ReportViewer.tsx
│   │   │   ├── ExplanationPanel.tsx
│   │   │   ├── TrendChart.tsx
│   │   │   ├── GlossaryTooltip.tsx
│   │   │   └── LoadingStates.tsx
│   │   ├── pages/
│   │   │   ├── HomePage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   └── ReportDetailPage.tsx
│   │   ├── hooks/
│   │   │   ├── useUpload.ts
│   │   │   ├── useReport.ts
│   │   │   └── useHistory.ts
│   │   ├── services/
│   │   │   └── api.ts           # Axios instance
│   │   ├── types/
│   │   │   └── index.ts         # TypeScript interfaces
│   │   ├── context/
│   │   │   └── AppContext.tsx   # React Context
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
├── Makefile                     # Common commands
├── README.md
└── ROADMAP.md                   # This file
```

### Design Patterns:
- **Backend**: Repository pattern for DB, Strategy pattern for LLM providers, Pipeline pattern for report processing
- **Frontend**: Compound components for UI, Custom hooks for data fetching, Context for global state

---

## Phase 4: Database & Vector Store Schema Design
**Duration:** 3-4 days
**Deliverables:** SQLAlchemy models, Pydantic schemas, FAISS index design

### Tasks:
- Design PostgreSQL schema:
  - `users` table (id, email, created_at)
  - `reports` table (id, user_id, filename, original_text, simplified_text, status, created_at)
  - `extracted_entities` table (id, report_id, entity_type, entity_text, value, unit, normal_range, status, position)
  - `knowledge_chunks` table (id, source, title, content, embedding_vector, metadata)
- Create SQLAlchemy ORM models with relationships
- Set up Alembic for database migrations
- Design FAISS index parameters:
  - Embedding dimension: 384 (all-MiniLM-L6-v2)
  - Index type: IVF4096,Flat (balanced speed/accuracy)
  - nprobe: 64
  - Chunk size: 512 tokens, overlap: 64 tokens
- Create Pydantic request/response schemas for all API endpoints
- Implement database seeding script for test data

### Verification:
- Run migrations successfully
- Insert test report and retrieve with joins
- Verify FAISS index can be created and saved to disk

---

## Phase 5: Backend API Foundation (FastAPI)
**Duration:** 4-5 days
**Deliverables:** Working API server, middleware, error handling

### Tasks:
- Initialize FastAPI app with CORS, GZip compression
- Implement structured logging (Correlation IDs, request timing)
- Add exception handlers (validation errors, 404, 500)
- Create health check endpoint (`/api/health`)
- Set up dependency injection container
- Implement JWT authentication skeleton (optional for MVP, essential for production)
- Add rate limiting (slowapi with Redis, or in-memory for dev)
- Configure static file serving for uploaded reports
- Set up pytest with async test client (httpx)
- Write integration tests for health endpoint

### API Endpoints Draft:
```
POST /api/upload           - Upload PDF/image
GET  /api/reports          - List user reports
GET  /api/reports/{id}     - Get single report
POST /api/process/{id}     - Trigger OCR→NLP→RAG→LLM
GET  /api/reports/{id}/simplified - Get simplified explanation
DELETE /api/reports/{id}   - Delete report
```

### Verification:
```bash
curl http://localhost:8000/api/health
# Should return {"status": "ok", "version": "0.1.0"}
```

---

## Phase 6: Frontend Foundation (React + Tailwind + shadcn/ui)
**Duration:** 4-5 days
**Deliverables:** Working React app, routing, theme, API client

### Tasks:
- Initialize project with Vite + React 18 + TypeScript
- Configure Tailwind CSS with custom theme (medical color palette: calm blues, health greens, alert reds)
- Install and configure shadcn/ui components (Button, Card, Dialog, Tabs, Table, Progress, Alert, Tooltip, Badge, Separator, ScrollArea)
- Set up React Router with routes: `/`, `/dashboard`, `/report/:id`
- Configure Axios instance with base URL, interceptors for auth tokens and error handling
- Create global AppContext for: user state, theme, notifications
- Implement loading states and skeleton screens
- Set up error boundary with fallback UI
- Configure PWA manifest (optional but recommended for mobile)
- Add responsive design breakpoints (mobile-first)

### Theme Configuration:
- Primary: `#2563EB` (medical blue)
- Success/Normal: `#10B981` (green)
- Warning: `#F59E0B` (amber)
- Danger/Abnormal: `#EF4444` (red)
- Background: `#F8FAFC` (slate-50)
- Card: `#FFFFFF`

### Verification:
- Build completes without errors
- All shadcn components render correctly
- Routing works between pages

---

## Phase 7: OCR Module — Tesseract Integration
**Duration:** 5-6 days
**Deliverables:** Robust OCR pipeline with preprocessing

### Tasks:
- Install and configure Tesseract 5.0+ with `eng` and medical whitelist
- Implement OpenCV preprocessing pipeline:
  1. **Grayscale conversion** (COLOR_BGR2GRAY)
  2. **Noise reduction** (Gaussian blur, kernel size 5x5)
  3. **Contrast enhancement** (CLAHE: clipLimit=2.0, tileGridSize=8x8)
  4. **Deskewing** (Hough transform angle detection + rotation)
  5. **Binarization** (Otsu's method)
  6. **Resizing** to 300 DPI optimal
- Handle both PDF and image inputs:
  - PDF: Check for embedded text (pdfplumber), fallback to page rasterization (pdf2image @ 300 DPI)
  - Images: Direct preprocessing + OCR
- Configure Tesseract LSTM engine with custom whitelist: `alphanumeric + punctuation + medical symbols (/, %, ., -, +, µ)`
- Implement OCR output post-processing: fix common misreadings (0 vs O, 1 vs l), line break normalization
- Add confidence threshold filtering (reject characters with conf < 60)
- Create evaluation script to compute CER/WER against ground truth

### Key Configuration:
```python
custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789().,/%-µ +='
```

### Verification:
- Process 10 sample medical reports
- Target CER < 5% for clean scans, < 10% for degraded scans
- Compare with and without preprocessing to validate improvement

---

## Phase 8: PDF & Image Processing Pipeline
**Duration:** 3-4 days
**Deliverables:** Multi-format input handler, page management

### Tasks:
- Implement file validation: max 10MB, allowed types (PDF, PNG, JPG, JPEG)
- Create secure file upload handler (random UUID filenames, scan for malware)
- Build PDF processor:
  - Extract embedded text using pdfplumber
  - Detect scanned vs digital PDF (check for text layer)
  - Convert scanned pages to images using pdf2image (300 DPI, JPEG quality 95)
- Build image processor:
  - Handle EXIF orientation
  - Convert to RGB if necessary
  - Resize if dimension exceeds 4000px (memory management)
- Implement multi-page report handling:
  - Process each page independently
  - Concatenate text with page markers (`--- Page N ---`)
- Add progress tracking for multi-page documents
- Create file cleanup scheduler (delete files older than 7 days)

### Verification:
- Upload 5 PDFs (digital + scanned) and 5 images
- All processed correctly with extracted text
- Multi-page reports concatenated properly

---

## Phase 9: NLP Module — spaCy & SciSpacy Setup
**Duration:** 4-5 days
**Deliverables:** Medical NER pipeline, entity extraction

### Tasks:
- Install spaCy and download `en_core_web_sm` (fallback)
- Install SciSpacy and download `en_core_sci_lg` (primary biomedical model, 560MB)
- Load SciSpacy with optimized pipeline (disable parser, lemmatizer; keep NER + tokenizer)
- Add custom EntityRuler patterns for Indian lab conventions:
  - Abbreviations: Hb, TLC, DLC, RBC, WBC, PCV, MCV, MCH, SGPT, SGOT
  - Common test patterns: "Complete Blood Count", "Liver Function Test", "Renal Function Test"
- Implement custom regex-based value-unit extractor:
  - Pattern: `(\d+\.?\d*)\s*(g/dL|mg/dL|U/L|/µL|mmol/L|%|fL|pg|million/µL|thousand/µL)`
  - Handle ranges: `13-17 g/dL`, `4,000-11,000 /µL`
  - Handle Indian number formats: `13.5` vs `13,5`
- Build entity association logic: match values to nearest preceding test name
- Create entity structuring: output JSON with `{test_name, value, unit, normal_range, status}`
- Implement section detection (header, test table, notes, reference ranges)

### Verification:
- Test on 20 sample report texts
- Verify all common lab tests are recognized
- Check value-unit extraction accuracy > 90%

---

## Phase 10: Medical Entity Recognition & Structuring System
**Duration:** 4-5 days
**Deliverables:** Structured report parser, abnormality detection

### Tasks:
- Build `ReportParser` class that orchestrates:
  1. Text segmentation by lines
  2. Section classification (header, patient info, test table, notes)
  3. Entity extraction (test names, values, units, reference ranges)
  4. Entity association and deduplication
- Implement reference range parser:
  - Patterns: `13.0 - 17.0 g/dL`, `(13.0-17.0)`, `Normal: 13-17`
  - Handle gender/age specific ranges (store metadata)
- Build abnormality detection engine:
  - Compare numeric values against parsed reference ranges
  - Handle directional indicators: `>`, `<`, `HIGH`, `LOW`, `*`, `↑`, `↓`
  - Classify: NORMAL, BORDERLINE_LOW, LOW, BORDERLINE_HIGH, HIGH, CRITICAL
  - Create risk scoring (1-5 scale)
- Implement confidence scoring for each extraction
- Handle edge cases:
  - Text results (Positive/Negative, Detected/Not Detected)
  - Descriptive results (Mild, Moderate, Severe)
  - Missing reference ranges (query knowledge base)

### Output Schema:
```json
{
  "patient_info": {"name": "", "age": "", "gender": "", "date": ""},
  "tests": [
    {
      "test_name": "Hemoglobin",
      "value": "9.5",
      "unit": "g/dL",
      "normal_range": {"min": "13.0", "max": "17.0"},
      "status": "LOW",
      "risk_level": 3,
      "confidence": 0.94
    }
  ],
  "abnormal_count": 3,
  "sections": ["CBC", "LFT", "RFT"]
}
```

### Verification:
- Parse 50 diverse reports and validate structure
- Abnormality detection matches manual review in > 95% cases

---

## Phase 11: Medical Knowledge Base Construction
**Duration:** 5-7 days
**Deliverables:** Structured KB with 5000+ chunks, reference ranges, synonyms

### Tasks:
- **Source 1: MedlinePlus Scraping**
  - Scrape 3,000+ articles on laboratory tests and conditions
  - Target URLs: `https://medlineplus.gov/lab-tests/`, condition pages
  - Extract: title, summary, what the test measures, normal ranges, what results mean
  - Respect robots.txt, add delays, use cached sessions
- **Source 2: Testing.com Parsing**
  - Parse 1,500+ test guides from `https://www.testing.com`
  - Extract structured data: test name, purpose, normal range, high meaning, low meaning
  - Store in JSON format: `{test_name, range: [min, max], unit, high_meaning, low_meaning, description}`
- **Source 3: Consumer Health Vocabulary**
  - Build 10,000+ term mapping: medical term → patient-friendly synonym
  - Examples: `myocardial infarction` → `heart attack`, `hyperlipidemia` → `high cholesterol`
  - Include common abbreviations: `CBC` → `Complete Blood Count`, `WBC` → `White Blood Cell`
- Clean and normalize all content:
  - Remove HTML tags, excessive whitespace
  - Standardize units
  - Deduplicate similar entries
- Create chunking strategy:
  - Chunk size: 512 tokens
  - Overlap: 64 tokens
  - Metadata: source, URL, last_updated, category

### Verification:
- Verify 5,000+ chunks in knowledge base
- Sample random chunks for quality check
- Ensure coverage of top 100 common lab tests

---

## Phase 12: Embedding Model & FAISS Vector Index
**Duration:** 4-5 days
**Deliverables:** Searchable vector database, fast retrieval

### Tasks:
- Install `sentence-transformers` and load `all-MiniLM-L6-v2` (22M params, 384-dim)
- Implement batch embedding generation for all KB chunks
- Build FAISS index:
  - Create training vectors (IVF requires ~30k+ for good clustering)
  - Use `IndexIVFFlat` with nlist=4096 for 50k+ vectors
  - Add IDs mapping (FAISS index position → chunk metadata)
- Implement index persistence:
  - Save index to `knowledge_base/faiss_index/medical_kb.index`
  - Save id-mapping to JSON
- Build retriever class:
  - `embed_query(query: str) -> np.ndarray`
  - `search(query_embedding, k=3, threshold=0.75) -> List[Chunk]`
  - `batch_search(queries, k=3) -> List[List[Chunk]]`
- Add index rebuild capability (when KB updates)
- Implement caching layer for frequent queries (LRU cache in memory)

### Performance Targets:
- Embedding generation: < 50ms per query
- FAISS search: < 10ms for k=3 with nprobe=64
- Index memory footprint: < 500MB for 50k chunks

### Verification:
- Test retrieval with 50 test names
- Verify top-1 relevance > 90%
- Measure query latency

---

## Phase 13: RAG Retrieval Pipeline Implementation
**Duration:** 4-5 days
**Deliverables:** Context-aware medical knowledge retrieval

### Tasks:
- Build `RAGEngine` class:
  - Input: Extracted test entities from NLP module
  - Process: For each test, generate query variations:
    - Test name only: `"Hemoglobin test"`
    - Test + context: `"What does hemoglobin test measure normal range"`
    - Test + abnormality: `"Hemoglobin low means anemia"`
  - Retrieve: Query FAISS for each variation, deduplicate, rank by score
  - Filter: Remove results below cosine similarity 0.75
  - Augment: Format retrieved passages into context string
- Implement test-specific knowledge retrieval:
  - Retrieve normal range info
  - Retrieve clinical interpretation (high/low meanings)
  - Retrieve related conditions
- Build context assembly:
  - Limit total context to 2,000 tokens (fit within LLM context window)
  - Prioritize: test description > normal range > abnormality meaning > related conditions
  - Add source attribution strings
- Implement retrieval logging (for evaluation and debugging)
- Add fallback: if no relevant chunks found, use generic medical knowledge prompt

### Verification:
- Test with 20 sample test entities
- Verify retrieved context contains correct normal ranges
- Check source attribution is present

---

## Phase 14: NVIDIA LLM API Integration
**Duration:** 4-5 days
**Deliverables:** Working LLM client, error handling, retry logic

### Tasks:
- Set up NVIDIA NIM API access:
  - Base URL: `https://integrate.api.nvidia.com/v1`
  - Model: `meta/llama-3.1-8b-instruct` or `mistralai/mistral-7b-instruct-v0.3`
  - Authentication: user's NVIDIA API key in `NVIDIA_API_KEY` env var
- Implement `NvidiaLLMClient` class:
  - `generate(prompt: str, temperature=0.3, max_tokens=2048) -> str`
  - Handle streaming responses (optional, for UX improvement)
  - Implement exponential backoff retry (3 retries)
  - Timeout handling (30s default)
  - Token usage tracking
- Create fallback chain:
  - Primary: NVIDIA NIM (Llama-3.1-8B)
  - Secondary: NVIDIA NIM (Mistral-7B)
  - Tertiary: Local model (if deployed) or error message
- Implement prompt token counting (tiktoken or approximator)
- Add response validation: check for empty/hallucinated outputs
- Create mock LLM client for testing (returns pre-defined responses)

### Key Configuration:
```python
LLM_CONFIG = {
    "model": "meta/llama-3.1-8b-instruct",
    "temperature": 0.3,
    "top_p": 0.7,
    "max_tokens": 2048,
    "system_prompt": "You are a medical explainer..."
}
```

### Verification:
- Test API connectivity
- Generate 10 sample explanations
- Verify response time < 5 seconds
- Test retry logic with simulated failures

---

## Phase 15: Prompt Engineering & Simplification Pipeline
**Duration:** 5-6 days
**Deliverables:** High-quality patient-friendly explanations

### Tasks:
- Design master prompt template with these sections:
  1. **System instruction**: Role (medical explainer), audience (8th-grade reading level), tone (calm, supportive, non-alarmist)
  2. **Safety constraints**: No definitive diagnosis, always suggest consulting doctor, avoid medical advice
  3. **Retrieved knowledge**: FAISS context passages
  4. **Patient values**: Structured test results with statuses
  5. **Formatting instructions**: Use sections, bold abnormal values, bullet points, keep sentences < 20 words
- Create prompt variants:
  - **Per-test prompt**: Detailed explanation for individual tests
  - **Summary prompt**: Overall report summary
  - **Glossary prompt**: Definition of medical terms
  - **Follow-up prompt**: Suggested questions for doctor
- Implement `PromptBuilder` class:
  - Takes structured report + retrieved context
  - Assembles prompt with proper token budget management
  - Truncates context if needed (preserve most relevant)
- Build post-processing pipeline:
  - Readability filter: ensure sentences < 20 words, paragraphs < 4 sentences
  - HTML formatting: wrap abnormal values in `<span class="abnormal">`
  - Add glossary links for medical terms
  - Structure into sections: Summary, Test Details, What This Means, Next Steps
- Implement output caching (same report → cached explanation)

### Example Prompt Structure:
```
[SYSTEM] You are a medical report explainer. Explain in simple language an 8th-grader can understand. Never diagnose. Always suggest seeing a doctor.

[KNOWLEDGE]
Hemoglobin: Protein in red blood cells carrying oxygen. Normal: 13-17 g/dL (men), 12-15.5 g/dL (women). Low: May indicate anemia, blood loss, or nutritional deficiency.

[PATIENT VALUES]
- Hemoglobin: 9.5 g/dL (LOW - below normal range)

[INSTRUCTIONS]
1. Explain what hemoglobin measures
2. State patient's value and normal range
3. Explain what low value may indicate (not diagnose)
4. Suggest questions for doctor
5. Use simple words, short sentences
```

### Verification:
- Generate explanations for 20 test reports
- Check Flesch Reading Ease score target: 60-70
- Verify no hallucinated diagnoses
- Validate all abnormal values are correctly mentioned

---

## Phase 16: Abnormal Value Detection & Visual Highlighting
**Duration:** 4-5 days
**Deliverables:** Color-coded UI, risk indicators, trend visualization

### Tasks:
- Implement abnormal value classification:
  - NORMAL: green
  - BORDERLINE: yellow/amber
  - ABNORMAL (LOW/HIGH): red
  - CRITICAL: dark red with alert icon
- Build HTML tag injection for backend output:
  - `<span class="value-normal">12.5</span>`
  - `<span class="value-high">13,000</span>`
  - `<span class="value-critical">8.0</span>`
- Create React components for visual display:
  - `ValueBadge`: colored badge with value + status
  - `RiskIndicator`: 1-5 scale with color gradient
  - `AbnormalityList`: sorted list of all abnormal values
- Implement trend visualization (if historical data exists):
  - Use Recharts or Chart.js
  - Line charts for values over time
  - Reference range bands (shaded normal zone)
  - Annotations for abnormal readings
- Build `GlossaryTooltip` component:
  - Hover over medical terms to see plain-language definition
  - Popover with pronunciation and related info
- Create printable report view (CSS print media queries)

### Verification:
- Test with reports containing normal, borderline, and critical values
- Verify color coding matches classification
- Check trend charts render correctly

---

## Phase 17: Interactive React Dashboard & UI Components
**Duration:** 6-7 days
**Deliverables:** Complete patient-facing interface

### Tasks:
- **HomePage**:
  - Hero section with value proposition
  - Drag-and-drop upload zone with file type icons
  - Progress indicator during processing (stepper: Upload → OCR → Analysis → Simplification)
  - Recent reports preview
- **ReportViewer** (main feature page):
  - Split view: Original report (left) / Simplified explanation (right)
  - Tabbed sections: Summary, Test Details, Glossary, Ask Doctor
  - Highlighted abnormal values in both views
  - Download/Print/Share buttons
- **DashboardPage**:
  - Grid of all past reports with thumbnails
  - Filter by date, report type, abnormality status
  - Trend charts for repeated tests
  - Search functionality
- **ExplanationPanel**:
  - Structured sections with icons
  - Expandable/collapsible test details
  - "What This Means For You" personalized section
  - Doctor questions checklist
- **LoadingStates**:
  - Animated skeletons
  - Step-by-step progress with explanations
  - Cancel processing button
- **ErrorStates**:
  - OCR failure: "We couldn't read this scan clearly, try a clearer image"
  - Unsupported report: "This report type isn't supported yet"
  - LLM timeout: "Analysis is taking longer, please wait or try again"

### UX Considerations:
- Accessibility: ARIA labels, keyboard navigation, focus management
- Responsive: Works on mobile, tablet, desktop
- Performance: Lazy load components, virtualize long lists
- Feedback: Toast notifications for actions

### Verification:
- Test all pages on Chrome, Firefox, Safari
- Test responsiveness on mobile viewport
- Run Lighthouse audit (target: 90+ on all metrics)

---

## Phase 18: End-to-End Integration & API Orchestration
**Duration:** 5-6 days
**Deliverables:** Complete working pipeline, async processing

### Tasks:
- Build `PipelineService` that orchestrates:
  ```
  Upload File → Validate → Save → Start Background Task
  Background Task:
    1. PDF/Image → OCR (with preprocessing)
    2. Raw Text → NLP (entity extraction + structuring)
    3. Entities → RAG (knowledge retrieval)
    4. Context + Values → LLM (simplification)
    5. Post-processing (readability, HTML highlighting)
    6. Save to database → Notify frontend (SSE/WebSocket/polling)
  ```
- Implement async processing:
  - Use Celery + Redis OR FastAPI BackgroundTasks + polling
  - For MVP: BackgroundTasks with status polling
  - Store processing status: PENDING, OCR_RUNNING, NLP_RUNNING, RAG_RUNNING, LLM_RUNNING, COMPLETED, FAILED
- Add progress updates endpoint (`GET /api/reports/{id}/status`)
- Implement WebSocket or Server-Sent Events for real-time updates
- Build retry logic for failed stages (OCR retry with different config, LLM retry with fallback model)
- Add circuit breaker for external APIs (NVIDIA LLM)
- Implement request timeouts and graceful degradation:
  - If LLM fails: return structured data + raw knowledge context
  - If OCR fails: request clearer image
- Create end-to-end integration tests:
  - Upload → Complete processing → Verify output structure

### Verification:
- Process 10 full reports end-to-end
- Verify status updates at each stage
- Check all outputs are saved correctly
- Test error recovery scenarios

---

## Phase 19: Evaluation Framework & Testing
**Duration:** 5-6 days
**Deliverables:** Automated metrics, test suite, performance benchmarks

### Tasks:
- **OCR Evaluation**:
  - Compute CER and WER against ground truth transcriptions
  - Test set: 50 medical report images with manual transcriptions
  - Script: `python -m evaluation.ocr_eval --input-dir tests/data/ocr/`
- **NER Evaluation**:
  - Compute precision, recall, F1 for each entity type
  - Test set: 100 reports with annotated entities
  - Handle partial matches (overlap scoring)
- **Text Simplification Evaluation**:
  - BLEU-1 through BLEU-4 (using sacrebleu)
  - ROUGE-1, ROUGE-2, ROUGE-L (using rouge-score)
  - Flesch Reading Ease (custom implementation)
  - Flesch-Kincaid Grade Level
  - Test set: 50 reports with expert-written simplified explanations
- **System Evaluation**:
  - End-to-end latency: target < 30 seconds for 5-page report
  - Throughput: reports per minute
  - Memory usage during processing
- **User Satisfaction Framework**:
  - Create survey form (comprehension score, usefulness, recommendation)
  - Implement rating collection in frontend
  - Store feedback in database
- **Test Suite**:
  - Unit tests: > 80% coverage for core modules
  - Integration tests: all API endpoints
  - E2E tests: Playwright or Cypress (upload → result flow)

### Verification:
- Run full evaluation suite
- Verify BLEU-1 > 0.70, Flesch > 60 for simplified output
- All tests pass in CI

---

## Phase 20: Deployment, Documentation & Future Scope
**Duration:** 5-7 days
**Deliverables:** Production deployment, complete docs, handover

### Tasks:
- **Dockerization**:
  - Backend Dockerfile (Python slim, Tesseract installed, multi-stage build)
  - Frontend Dockerfile (Nginx serving built files)
  - `docker-compose.yml` with: backend, frontend, PostgreSQL, Redis (for caching)
- **Documentation**:
  - `README.md`: Project overview, architecture, quick start
  - `API.md`: Complete API documentation (auto-generated from FastAPI)
  - `DEPLOYMENT.md`: Step-by-step deployment guide
  - `CONTRIBUTING.md`: Development workflow
  - `EVALUATION.md`: How to run benchmarks
- **Security Hardening**:
  - Input validation and sanitization
  - File upload restrictions (type, size, content scan)
  - SQL injection prevention (SQLAlchemy parameterized queries)
  - XSS prevention (escape HTML in user-facing outputs)
  - Rate limiting on all endpoints
  - CORS configuration (restrict to known origins)
- **Monitoring & Logging**:
  - Structured logs with correlation IDs
  - Error tracking (Sentry integration placeholder)
  - Health check endpoint for load balancers
  - Prometheus metrics endpoint (optional)
- **Future Scope Implementation** (if time permits):
  - Text-to-speech integration (Web Speech API or ElevenLabs)
  - Multilingual support structure (i18n setup)
  - Patient profile schema (for personalized reference ranges)
- **Handover**:
  - Final presentation slides
  - Demo video script
  - Known issues and limitations document

### Deployment Targets:
- **Development**: `docker-compose up` on local machine
- **Staging**: Deploy to Render/Railway/Fly.io free tier
- **Production**: VPS with Docker (AWS EC2, DigitalOcean, Hetzner)

---

## Timeline Summary

| Phase | Duration | Cumulative |
|-------|----------|------------|
| 1. Planning | 4 days | Week 1 |
| 2. Environment | 3 days | Week 1 |
| 3. Architecture | 3 days | Week 2 |
| 4. Database | 4 days | Week 2 |
| 5. Backend API | 5 days | Week 3 |
| 6. Frontend | 5 days | Week 3-4 |
| 7. OCR | 6 days | Week 4-5 |
| 8. PDF/Image | 4 days | Week 5 |
| 9. NLP Setup | 5 days | Week 6 |
| 10. NER System | 5 days | Week 6-7 |
| 11. Knowledge Base | 7 days | Week 7-8 |
| 12. FAISS Index | 5 days | Week 8 |
| 13. RAG Pipeline | 5 days | Week 9 |
| 14. NVIDIA LLM | 5 days | Week 9-10 |
| 15. Prompt Engineering | 6 days | Week 10-11 |
| 16. Visual Highlighting | 5 days | Week 11 |
| 17. Dashboard UI | 7 days | Week 12 |
| 18. Integration | 6 days | Week 12-13 |
| 19. Evaluation | 6 days | Week 13-14 |
| 20. Deployment | 7 days | Week 14-15 |
| **Buffer** | 10 days | Week 15-16 |
| **TOTAL** | **~117 days** | **~16-17 weeks** |

---

## Critical Path
The following phases must complete sequentially and form the critical path:
**Phase 2 → Phase 3 → Phase 5 → Phase 7 → Phase 9 → Phase 11 → Phase 12 → Phase 13 → Phase 14 → Phase 15 → Phase 18**

Parallelizable phases: Phase 4 (with Phase 3), Phase 6 (with Phase 5), Phase 8 (with Phase 7), Phase 10 (with Phase 9), Phase 16 (with Phase 15), Phase 17 (with Phase 16).

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| NVIDIA API rate limits / downtime | Implement aggressive caching + local fallback model |
| Tesseract OCR accuracy on poor scans | Add manual text input fallback + image quality checker |
| SciSpacy model size (560MB) | Lazy load + model quantization for memory-constrained deploys |
| FAISS index corruption | Regular backups + index rebuild script |
| LLM hallucination | Strong prompt constraints + RAG grounding + doctor disclaimer |
| Large file uploads causing OOM | Streaming processing + file size limits + page-by-page OCR |

---

## Success Criteria (from BTP Report)

1. OCR CER < 5% on clean scans, < 10% on degraded scans
2. NER F1 > 0.88 for test names and values
3. BLEU-1 > 0.70 for simplified text
4. Flesch Reading Ease score 60-70 (8th-grade level)
5. End-to-end processing < 30 seconds per report
6. User comprehension score > 4.0/5.0
7. Zero definitive diagnoses in LLM output (safety)

---

*Roadmap Version: 1.0*
*Based on: RAG-Based Medical Report Simplification System BTP Report (IIIT Pune, 2026)*
