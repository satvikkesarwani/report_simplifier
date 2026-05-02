import argparse
import json
from pathlib import Path

from app.evaluation.benchmark_runner import (
    load_benchmark_records,
    run_ner_benchmark,
    run_ocr_benchmark,
    run_simplification_benchmark,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local benchmark suites for the medical report simplifier.")
    parser.add_argument("--task", choices=["ocr", "ner", "simplification"], required=True)
    parser.add_argument("--input", required=True, help="Path to a JSON or JSONL benchmark file.")
    parser.add_argument("--output", help="Optional JSON file to write the results to.")
    args = parser.parse_args()

    records = load_benchmark_records(args.input)
    if args.task == "ocr":
        result = run_ocr_benchmark(records)
    elif args.task == "ner":
        result = run_ner_benchmark(records)
    else:
        result = run_simplification_benchmark(records)

    payload = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
