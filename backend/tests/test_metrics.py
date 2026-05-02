from app.evaluation.metrics import (
    compute_bleu_scores,
    compute_ner_metrics,
    compute_ocr_accuracy,
    compute_rouge_scores,
    summarize_feedback_scores,
)


def test_text_metrics_produce_expected_ranges():
    reference = "Hemoglobin is low and may suggest anemia."
    candidate = "Hemoglobin is low and may suggest anemia."

    bleu = compute_bleu_scores(reference, candidate)
    rouge = compute_rouge_scores(reference, candidate)

    assert bleu["bleu_1"] == 1.0
    assert rouge["rouge_1_f1"] == 1.0
    assert rouge["rouge_l_f1"] == 1.0


def test_ocr_accuracy_is_perfect_for_identical_text():
    metrics = compute_ocr_accuracy("abc def", "abc def")
    assert metrics["character_error_rate"] == 0.0
    assert metrics["word_error_rate"] == 0.0


def test_ner_metrics_match_expected_entities():
    expected = [{"label": "TEST_NAME", "text": "Hemoglobin"}]
    predicted = [{"label": "TEST_NAME", "text": "Hemoglobin"}]

    metrics = compute_ner_metrics(expected, predicted)
    assert metrics["TEST_NAME"]["f1"] == 1.0
    assert metrics["overall"]["precision"] == 1.0


def test_feedback_summary_averages_scores():
    summary = summarize_feedback_scores(
        [
            {"comprehension_score": 4, "usefulness_score": 5, "highlighting_score": 4, "recommendation_score": 5},
            {"comprehension_score": 5, "usefulness_score": 4, "highlighting_score": 5, "recommendation_score": 4},
        ]
    )
    assert summary["comprehension_score"] == 4.5
    assert summary["responses"] == 2
