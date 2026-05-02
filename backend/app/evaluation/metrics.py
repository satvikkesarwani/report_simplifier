import math
import re
from collections import Counter, defaultdict
from statistics import mean
from typing import Dict, Iterable, List, Sequence, Tuple


TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def tokenize(text: str) -> List[str]:
    return TOKEN_PATTERN.findall((text or "").lower())


def _ngrams(tokens: Sequence[str], n: int) -> List[Tuple[str, ...]]:
    if len(tokens) < n or n <= 0:
        return []
    return [tuple(tokens[index : index + n]) for index in range(len(tokens) - n + 1)]


def compute_bleu_scores(reference: str, candidate: str, max_n: int = 4) -> Dict[str, float]:
    reference_tokens = tokenize(reference)
    candidate_tokens = tokenize(candidate)
    reference_length = len(reference_tokens)
    candidate_length = len(candidate_tokens)

    precisions = []
    scores: Dict[str, float] = {}

    for n in range(1, max_n + 1):
        ref_counts = Counter(_ngrams(reference_tokens, n))
        cand_counts = Counter(_ngrams(candidate_tokens, n))
        overlap = sum(min(count, ref_counts[gram]) for gram, count in cand_counts.items())
        total = max(sum(cand_counts.values()), 1)
        precision = overlap / total
        precisions.append(max(precision, 1e-9))
        scores[f"bleu_{n}"] = round(precision, 4)

    if candidate_length == 0:
        brevity_penalty = 0.0
    elif candidate_length > reference_length:
        brevity_penalty = 1.0
    else:
        brevity_penalty = math.exp(1 - (reference_length / max(candidate_length, 1)))

    bleu = brevity_penalty * math.exp(sum(math.log(value) for value in precisions) / max_n)
    scores["bleu"] = round(bleu, 4)
    scores["brevity_penalty"] = round(brevity_penalty, 4)
    return scores


def compute_rouge_scores(reference: str, candidate: str) -> Dict[str, float]:
    reference_tokens = tokenize(reference)
    candidate_tokens = tokenize(candidate)

    rouge_1 = _rouge_n(reference_tokens, candidate_tokens, 1)
    rouge_2 = _rouge_n(reference_tokens, candidate_tokens, 2)
    rouge_l = _rouge_l(reference_tokens, candidate_tokens)

    return {
        "rouge_1_precision": round(rouge_1["precision"], 4),
        "rouge_1_recall": round(rouge_1["recall"], 4),
        "rouge_1_f1": round(rouge_1["f1"], 4),
        "rouge_2_precision": round(rouge_2["precision"], 4),
        "rouge_2_recall": round(rouge_2["recall"], 4),
        "rouge_2_f1": round(rouge_2["f1"], 4),
        "rouge_l_precision": round(rouge_l["precision"], 4),
        "rouge_l_recall": round(rouge_l["recall"], 4),
        "rouge_l_f1": round(rouge_l["f1"], 4),
    }


def _rouge_n(reference_tokens: Sequence[str], candidate_tokens: Sequence[str], n: int) -> Dict[str, float]:
    ref_counts = Counter(_ngrams(reference_tokens, n))
    cand_counts = Counter(_ngrams(candidate_tokens, n))
    overlap = sum(min(count, ref_counts[gram]) for gram, count in cand_counts.items())
    precision = overlap / max(sum(cand_counts.values()), 1)
    recall = overlap / max(sum(ref_counts.values()), 1)
    f1 = _f1(precision, recall)
    return {"precision": precision, "recall": recall, "f1": f1}


def _rouge_l(reference_tokens: Sequence[str], candidate_tokens: Sequence[str]) -> Dict[str, float]:
    lcs_length = _lcs_length(reference_tokens, candidate_tokens)
    precision = lcs_length / max(len(candidate_tokens), 1)
    recall = lcs_length / max(len(reference_tokens), 1)
    f1 = _f1(precision, recall)
    return {"precision": precision, "recall": recall, "f1": f1}


def _lcs_length(first: Sequence[str], second: Sequence[str]) -> int:
    rows = len(first) + 1
    cols = len(second) + 1
    table = [[0] * cols for _ in range(rows)]

    for i in range(1, rows):
        for j in range(1, cols):
            if first[i - 1] == second[j - 1]:
                table[i][j] = table[i - 1][j - 1] + 1
            else:
                table[i][j] = max(table[i - 1][j], table[i][j - 1])

    return table[-1][-1]


def compute_ocr_accuracy(reference_text: str, predicted_text: str) -> Dict[str, float]:
    ref_chars = list(reference_text or "")
    pred_chars = list(predicted_text or "")
    ref_words = (reference_text or "").split()
    pred_words = (predicted_text or "").split()

    cer = _edit_distance(ref_chars, pred_chars) / max(len(ref_chars), 1)
    wer = _edit_distance(ref_words, pred_words) / max(len(ref_words), 1)

    return {
        "character_error_rate": round(cer, 4),
        "word_error_rate": round(wer, 4),
        "character_accuracy": round(1 - cer, 4),
        "word_accuracy": round(1 - wer, 4),
    }


def _edit_distance(reference: Sequence[str], candidate: Sequence[str]) -> int:
    rows = len(reference) + 1
    cols = len(candidate) + 1
    table = [[0] * cols for _ in range(rows)]

    for i in range(rows):
        table[i][0] = i
    for j in range(cols):
        table[0][j] = j

    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if reference[i - 1] == candidate[j - 1] else 1
            table[i][j] = min(
                table[i - 1][j] + 1,
                table[i][j - 1] + 1,
                table[i - 1][j - 1] + cost,
            )

    return table[-1][-1]


def compute_ner_metrics(
    expected_entities: Iterable[Dict[str, str]],
    predicted_entities: Iterable[Dict[str, str]],
) -> Dict[str, Dict[str, float]]:
    labels = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    expected = [
        (entity.get("label", ""), entity.get("text", "").strip().lower())
        for entity in expected_entities
    ]
    predicted = [
        (entity.get("label", ""), entity.get("text", "").strip().lower())
        for entity in predicted_entities
    ]

    expected_counts = Counter(expected)
    predicted_counts = Counter(predicted)

    all_keys = set(expected_counts) | set(predicted_counts)
    for label, text in all_keys:
        matched = min(expected_counts[(label, text)], predicted_counts[(label, text)])
        labels[label]["tp"] += matched
        labels[label]["fp"] += max(predicted_counts[(label, text)] - matched, 0)
        labels[label]["fn"] += max(expected_counts[(label, text)] - matched, 0)

    metrics: Dict[str, Dict[str, float]] = {}
    micro_tp = micro_fp = micro_fn = 0

    for label, counts in labels.items():
        precision = counts["tp"] / max(counts["tp"] + counts["fp"], 1)
        recall = counts["tp"] / max(counts["tp"] + counts["fn"], 1)
        f1 = _f1(precision, recall)
        metrics[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": counts["tp"] + counts["fn"],
        }
        micro_tp += counts["tp"]
        micro_fp += counts["fp"]
        micro_fn += counts["fn"]

    micro_precision = micro_tp / max(micro_tp + micro_fp, 1)
    micro_recall = micro_tp / max(micro_tp + micro_fn, 1)
    metrics["overall"] = {
        "precision": round(micro_precision, 4),
        "recall": round(micro_recall, 4),
        "f1": round(_f1(micro_precision, micro_recall), 4),
        "support": micro_tp + micro_fn,
    }
    return metrics


def summarize_feedback_scores(entries: Iterable[Dict[str, float]]) -> Dict[str, float]:
    collected: Dict[str, List[float]] = defaultdict(list)
    for entry in entries:
        for key in (
            "comprehension_score",
            "usefulness_score",
            "highlighting_score",
            "recommendation_score",
        ):
            value = entry.get(key)
            if value is not None:
                collected[key].append(float(value))

    summary = {
        key: round(mean(values), 2) if values else 0.0 for key, values in collected.items()
    }
    summary["responses"] = sum(len(values) for values in collected.values()) // max(len(collected), 1)
    return summary


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)
