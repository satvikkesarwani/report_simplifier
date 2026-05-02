import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from app.db.report_store import get_report_store
from app.evaluation.benchmark_runner import (
    load_benchmark_records,
    run_ner_benchmark,
    run_ocr_benchmark,
    run_simplification_benchmark,
)
from app.evaluation.metrics import summarize_feedback_scores


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate report-style evaluation tables from benchmark and feedback data.")
    # Default to gold datasets; pass --ocr / --ner / --simplification to override
    parser.add_argument("--ocr", default="benchmarks/gold_ocr.json")
    parser.add_argument("--ner", default="benchmarks/gold_ner.json")
    parser.add_argument("--simplification", default="benchmarks/gold_simplification.json")
    parser.add_argument("--output", default="benchmarks/report_tables.json")
    args = parser.parse_args()

    ocr_result = run_ocr_benchmark(load_benchmark_records(args.ocr))
    ner_result = run_ner_benchmark(load_benchmark_records(args.ner))
    simplification_result = run_simplification_benchmark(load_benchmark_records(args.simplification))
    feedback_entries = get_report_store().feedback_summary()["entries"]
    feedback_summary = summarize_feedback_scores(feedback_entries)

    payload = {
        "table_3_ocr_performance_metrics": _build_ocr_table(ocr_result),
        "table_4_text_simplification_quality_metrics": _build_simplification_table(simplification_result),
        "table_5_ner_performance_on_medical_entities": _build_ner_table(ner_result),
        "table_6_system_usability_and_readability_scores": _build_usability_table(feedback_summary),
        "table_7_comparison_with_existing_systems": _build_comparison_table(
            ocr_result, ner_result, simplification_result, feedback_summary
        ),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


def _build_ocr_table(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    summary = result["summary"]
    return [
        {"metric": "Character Accuracy", "value": summary.get("character_accuracy", 0.0)},
        {"metric": "Word Accuracy", "value": summary.get("word_accuracy", 0.0)},
        {"metric": "Character Error Rate", "value": summary.get("character_error_rate", 0.0)},
        {"metric": "Word Error Rate", "value": summary.get("word_error_rate", 0.0)},
    ]


def _build_simplification_table(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    summary = result["summary"]
    return [
        {"metric": "BLEU", "value": summary.get("bleu", 0.0)},
        {"metric": "BLEU-1", "value": summary.get("bleu_1", 0.0)},
        {"metric": "BLEU-2", "value": summary.get("bleu_2", 0.0)},
        {"metric": "ROUGE-1 F1", "value": summary.get("rouge_1_f1", 0.0)},
        {"metric": "ROUGE-2 F1", "value": summary.get("rouge_2_f1", 0.0)},
        {"metric": "ROUGE-L F1", "value": summary.get("rouge_l_f1", 0.0)},
    ]


def _build_ner_table(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    summary = result["summary"]
    rows = []
    for label, metrics in summary.items():
        if not isinstance(metrics, dict):
            continue
        rows.append(
            {
                "entity_type": label,
                "precision": metrics.get("precision", 0.0),
                "recall": metrics.get("recall", 0.0),
                "f1": metrics.get("f1", 0.0),
            }
        )
    return rows


def _build_usability_table(feedback_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    store = get_report_store()
    processed_reports = [r for r in store.list_reports(limit=200) if r.get("readability_score") is not None]
    avg_readability = (
        round(sum(r["readability_score"] for r in processed_reports) / len(processed_reports), 2)
        if processed_reports else None
    )
    rows = [
        {"metric": "Comprehension Score (1-5)", "value": feedback_summary.get("comprehension_score", "N/A")},
        {"metric": "Usefulness Score (1-5)", "value": feedback_summary.get("usefulness_score", "N/A")},
        {"metric": "Highlighting Score (1-5)", "value": feedback_summary.get("highlighting_score", "N/A")},
        {"metric": "Recommendation Score (1-5)", "value": feedback_summary.get("recommendation_score", "N/A")},
        {"metric": "Feedback Responses Collected", "value": feedback_summary.get("responses", 0)},
        {"metric": "Avg Flesch Readability (DB)", "value": avg_readability if avg_readability is not None else "N/A (no processed reports yet)"},
    ]
    return rows


def _build_comparison_table(
    ocr_result: Dict[str, Any],
    ner_result: Dict[str, Any],
    simplification_result: Dict[str, Any],
    feedback_summary: Dict[str, Any],
) -> List[Dict[str, Any]]:
    return [
        {
            "system": "Current RAG-Based System",
            "ocr_word_accuracy": ocr_result["summary"].get("word_accuracy", 0.0),
            "ner_f1": ner_result["summary"].get("overall", {}).get("f1", 0.0),
            "rouge_l_f1": simplification_result["summary"].get("rouge_l_f1", 0.0),
            "user_recommendation": feedback_summary.get("recommendation_score", 0.0),
        },
        {
            "system": "Rule-Based Baseline Placeholder",
            "ocr_word_accuracy": 0.0,
            "ner_f1": 0.0,
            "rouge_l_f1": 0.0,
            "user_recommendation": 0.0,
        },
    ]


if __name__ == "__main__":
    main()
