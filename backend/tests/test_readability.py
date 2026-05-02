from app.utils.readability import analyze_readability


def test_readability_returns_expected_keys():
    metrics = analyze_readability(
        "This is a simple report summary. It uses short sentences and common words."
    )

    assert metrics["flesch_reading_ease"] > 0
    assert metrics["flesch_kincaid_grade"] >= 0
    assert metrics["word_count"] >= 10
    assert metrics["sentence_count"] == 2.0
