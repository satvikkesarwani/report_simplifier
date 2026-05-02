from app.evaluation.benchmark_runner import (
    aggregate_numeric_metrics,
    run_ner_benchmark,
    run_ocr_benchmark,
    run_simplification_benchmark,
)


def test_ocr_benchmark_summary():
    result = run_ocr_benchmark(
        [
            {"reference_text": "Hemoglobin 13.5", "predicted_text": "Hemoglobin 13.5"},
            {"reference_text": "WBC 8.4", "predicted_text": "WBC 8.5"},
        ]
    )

    assert result["task"] == "ocr"
    assert result["count"] == 2
    assert "character_accuracy" in result["summary"]


def test_ner_benchmark_summary():
    result = run_ner_benchmark(
        [
            {
                "expected_entities": [{"label": "TEST_NAME", "text": "Hemoglobin"}],
                "predicted_entities": [{"label": "TEST_NAME", "text": "Hemoglobin"}],
            }
        ]
    )

    assert result["summary"]["overall"]["f1"] == 1.0


def test_simplification_benchmark_summary():
    result = run_simplification_benchmark(
        [
            {
                "reference_text": "Hemoglobin is slightly low and may suggest anemia.",
                "candidate_text": "Hemoglobin is a bit low and may indicate anemia.",
            }
        ]
    )

    assert result["task"] == "simplification"
    assert "rouge_l_f1" in result["summary"]


def test_aggregate_numeric_metrics_nested_dicts():
    summary = aggregate_numeric_metrics(
        [
            {"overall": {"precision": 1.0, "recall": 0.5}},
            {"overall": {"precision": 0.5, "recall": 1.0}},
        ]
    )

    assert summary["overall"]["precision"] == 0.75
    assert summary["overall"]["recall"] == 0.75
