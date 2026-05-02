from generate_report_tables import (
    _build_comparison_table,
    _build_ner_table,
    _build_ocr_table,
    _build_simplification_table,
    _build_usability_table,
)


def test_report_table_builders_shape():
    ocr = {"summary": {"character_accuracy": 0.9, "word_accuracy": 0.8, "character_error_rate": 0.1, "word_error_rate": 0.2}}
    ner = {"summary": {"overall": {"precision": 0.9, "recall": 0.8, "f1": 0.85}}}
    simplification = {"summary": {"bleu": 0.3, "bleu_1": 0.5, "bleu_2": 0.4, "rouge_1_f1": 0.6, "rouge_2_f1": 0.5, "rouge_l_f1": 0.62}}
    feedback = {"comprehension_score": 4.5, "usefulness_score": 4.4, "highlighting_score": 4.2, "recommendation_score": 4.7, "responses": 10}

    assert len(_build_ocr_table(ocr)) == 4
    assert _build_ner_table(ner)[0]["entity_type"] == "overall"
    assert len(_build_simplification_table(simplification)) == 6
    assert len(_build_usability_table(feedback)) == 6
    assert len(_build_comparison_table(ocr, ner, simplification, feedback)) == 2
