# Benchmark Datasets

This directory contains starter benchmark fixtures for the implemented evaluation suite.

Files:
- `sample_ocr.json`
- `sample_ner.json`
- `sample_simplification.json`

Run them with:

```bash
cd backend
python run_benchmark_suite.py --task ocr --input benchmarks/sample_ocr.json
python run_benchmark_suite.py --task ner --input benchmarks/sample_ner.json
python run_benchmark_suite.py --task simplification --input benchmarks/sample_simplification.json
```

These fixtures are not the full academic gold-standard dataset from the report, but they provide a packaged, reproducible local benchmark harness that can be extended with real annotated data.
