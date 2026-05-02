import re
from typing import Dict


WORD_PATTERN = re.compile(r"[A-Za-z']+")
SENTENCE_PATTERN = re.compile(r"[.!?]+")


def _count_syllables(word: str) -> int:
    cleaned = re.sub(r"[^a-z]", "", word.lower())
    if not cleaned:
        return 0

    vowels = "aeiouy"
    syllables = 0
    prev_was_vowel = False

    for char in cleaned:
        is_vowel = char in vowels
        if is_vowel and not prev_was_vowel:
            syllables += 1
        prev_was_vowel = is_vowel

    if cleaned.endswith("e") and syllables > 1:
        syllables -= 1

    return max(1, syllables)


def analyze_readability(text: str) -> Dict[str, float]:
    words = WORD_PATTERN.findall(text or "")
    sentences = SENTENCE_PATTERN.findall(text or "")

    word_count = max(len(words), 1)
    sentence_count = max(len(sentences), 1)
    syllable_count = sum(_count_syllables(word) for word in words) or 1

    avg_sentence_length = word_count / sentence_count
    avg_syllables_per_word = syllable_count / word_count

    flesch_reading_ease = 206.835 - (1.015 * avg_sentence_length) - (
        84.6 * avg_syllables_per_word
    )
    flesch_kincaid_grade = (0.39 * avg_sentence_length) + (
        11.8 * avg_syllables_per_word
    ) - 15.59

    return {
        "flesch_reading_ease": round(flesch_reading_ease, 2),
        "flesch_kincaid_grade": round(flesch_kincaid_grade, 2),
        "average_sentence_length": round(avg_sentence_length, 2),
        "average_syllables_per_word": round(avg_syllables_per_word, 2),
        "word_count": float(len(words)),
        "sentence_count": float(len(sentences)),
    }
