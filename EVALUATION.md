# Evaluation Guide

This project now includes a lightweight evaluation framework aligned with the BTP report.

## Available Metrics

- OCR accuracy: character error rate, word error rate, character accuracy, word accuracy
- Text simplification: BLEU-1 through BLEU-4, aggregate BLEU, ROUGE-1, ROUGE-2, ROUGE-L
- Readability: Flesch Reading Ease, Flesch-Kincaid Grade Level
- NER extraction: precision, recall, and F1 by label plus overall micro scores
- User feedback: comprehension, usefulness, highlighting clarity, recommendation

## API Endpoints

- `POST /api/evaluation/ocr`
- `POST /api/evaluation/ner`
- `POST /api/evaluation/simplification`
- `POST /api/reports/{report_id}/feedback`
- `GET /api/reports/{report_id}/feedback`
- `GET /api/evaluation/feedback-summary`

## Example Payloads

### OCR

```json
{
  "reference_text": "Hemoglobin 13.5 g/dL",
  "predicted_text": "Hemoglobin 13.5 g/dL"
}
```

### NER

```json
{
  "expected_entities": [
    { "label": "TEST_NAME", "text": "Hemoglobin" }
  ],
  "predicted_entities": [
    { "label": "TEST_NAME", "text": "Hemoglobin" }
  ]
}
```

### Simplification

```json
{
  "reference_text": "Your hemoglobin is slightly low and may suggest anemia.",
  "candidate_text": "Your hemoglobin is a bit low, which can happen with anemia."
}
```

## Local Verification

Run backend tests:

```bash
python3 -m pytest backend/tests
```

Build the frontend:

```bash
cd frontend
npm run build
```

Run the benchmark suite:

```bash
cd backend
python run_benchmark_suite.py --task ocr --input path/to/ocr.json
python run_benchmark_suite.py --task ner --input path/to/ner.json
python run_benchmark_suite.py --task simplification --input path/to/simplification.json
```

The runner accepts `.json` and `.jsonl` files and emits:
- `count`
- `summary`
- `per_example`

Example OCR dataset:

```json
[
  {
    "reference_text": "Hemoglobin 13.5 g/dL",
    "predicted_text": "Hemoglobin 13.5 g/dL"
  }
]
```

## Knowledge Base

To build the authoritative chunk store when network access is available:

```bash
cd backend
python3 build_knowledge_base.py
```

## Biomedical Environment

For a report-spec Python 3.12 environment with SciSpaCy support:

```bash
cd backend
PYTHON_BIN=python3.12 ./setup_biomedical_env.sh
```

If you already have a direct `en_core_sci_lg` tarball URL, pass it as `SCISPACY_MODEL_URL=...`.

## Model Diagnostics

To inspect which NLP and embedding backends are active at runtime:

```bash
curl http://localhost:8000/api/health/models
```
