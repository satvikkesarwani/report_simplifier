import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.evaluation.metrics import (
    compute_bleu_scores,
    compute_ocr_accuracy,
    compute_ner_metrics,
    compute_rouge_scores,
)


def load_benchmark_records(path: str | Path) -> List[Dict[str, Any]]:
    source = Path(path)
    if source.suffix == ".jsonl":
        records = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        payload = json.loads(source.read_text(encoding="utf-8"))
        records = payload if isinstance(payload, list) else payload.get("records", [])

    if not isinstance(records, list):
        raise ValueError("Benchmark input must be a list of records.")
    return records


def aggregate_numeric_metrics(items: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    items = list(items)
    if not items:
        return {}

    summary: Dict[str, Any] = {}
    keys = {key for item in items for key in item.keys()}
    for key in keys:
        values = [item[key] for item in items if key in item]
        numeric_values = [float(value) for value in values if isinstance(value, (int, float))]
        dict_values = [value for value in values if isinstance(value, dict)]

        if numeric_values and len(numeric_values) == len(values):
            summary[key] = round(sum(numeric_values) / len(numeric_values), 4)
        elif dict_values and len(dict_values) == len(values):
            summary[key] = aggregate_numeric_metrics(dict_values)

    return summary


def run_ocr_benchmark(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    per_example = [
        compute_ocr_accuracy(record.get("reference_text", ""), record.get("predicted_text", ""))
        for record in records
    ]
    return {"task": "ocr", "count": len(per_example), "summary": aggregate_numeric_metrics(per_example), "per_example": per_example}


def run_ner_benchmark(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    per_example = [
        compute_ner_metrics(record.get("expected_entities", []), record.get("predicted_entities", []))
        for record in records
    ]
    return {"task": "ner", "count": len(per_example), "summary": aggregate_numeric_metrics(per_example), "per_example": per_example}


def run_simplification_benchmark(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    per_example = []
    for record in records:
        reference = record.get("reference_text", "")
        candidate = record.get("candidate_text", "")
        metrics = {}
        metrics.update(compute_bleu_scores(reference, candidate))
        metrics.update(compute_rouge_scores(reference, candidate))
        per_example.append(metrics)

    return {
        "task": "simplification",
        "count": len(per_example),
        "summary": aggregate_numeric_metrics(per_example),
        "per_example": per_example,
    }
