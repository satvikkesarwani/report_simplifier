from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import httpx


BASE_URL = os.environ.get("REAL_TEST_BASE_URL", "http://127.0.0.1:8000")
ROOT = Path("/Users/satvikkesarwani/Downloads/medical-report-simplifier")
OUTPUT_DIR = ROOT / "backend" / "test_runs" / f"real_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

CASES = [
    {
        "label": "AIG hematology image",
        "path": Path(
            "/Users/satvikkesarwani/Downloads/BLR-0425-PA-0036693_ARVIND REDDY REPALA 0036693_28-04-2025_1120-45_AM@E.pdf_page_24.png"
        ),
        "expected_terms": ["hemoglobin", "rbc", "wbc", "lymphocytes", "eosinophils", "haematology"],
    },
    {
        "label": "Kauvery electrolytes/CRP image",
        "path": Path(
            "/Users/satvikkesarwani/Downloads/BLR-0425-PA-0039883_ALL CLAIMS DOCM BHUVANESHWARI VIDAL_0001_27-04-2025_1131-10_AM@E.pdf_page_38.png"
        ),
        "expected_terms": ["sodium", "potassium", "chloride", "glucose", "crp", "c reactive"],
    },
    {
        "label": "ILBS liver/coagulation image",
        "path": Path(
            "/Users/satvikkesarwani/Downloads/BLR-0425-PA-0040301_Q-Report3_250422_1436@F.pdf_page_2.png"
        ),
        "expected_terms": ["bilirubin", "albumin", "globulin", "magnesium", "inr", "prothrombin"],
    },
    {
        "label": "Good Life urine examination image",
        "path": Path(
            "/Users/satvikkesarwani/Downloads/BLR-0425-PA-0040652_LAB MERG_27-04-2025_1239-18_PM@E.pdf_page_7.png"
        ),
        "expected_terms": ["urine", "albumin", "sugar", "ketone", "pus cells", "r.b.c"],
    },
    {
        "label": "KIMS-ICON ABG image",
        "path": Path(
            "/Users/satvikkesarwani/Downloads/BLR-0425-PA-0040749_G RAJU_27-04-2025_1103-55_PM.pdf_page_42.png"
        ),
        "expected_terms": ["ph", "pco2", "po2", "sodium", "potassium", "lactate", "arterial blood gases"],
    },
    {
        "label": "Tabular platelet/CBC continuation page image",
        "path": Path(
            "/Users/satvikkesarwani/Downloads/AHD-0425-PA-0007561_JITENDRA TRIVEDI DS_28-04-2025_1019-21_AM.pdf_page_9.png"
        ),
        "expected_terms": ["platelet", "hemoglobin", "rbc", "pcv", "mcv", "wbc"],
    },
]


def short_text(value: str, limit: int = 700) -> str:
    cleaned = " ".join((value or "").split())
    return cleaned[:limit] + ("..." if len(cleaned) > limit else "")


def label_from_score(score: int) -> str:
    if score >= 4:
        return "Pass"
    if score >= 2:
        return "Partial"
    return "Fail"


def score_ocr(raw_text: str, expected_terms: List[str]) -> str:
    lowered = raw_text.lower()
    hits = sum(1 for term in expected_terms if term.lower() in lowered)
    return label_from_score(hits)


def score_extraction(processed: Dict[str, Any], expected_terms: List[str]) -> str:
    structured = processed.get("structured_data", {})
    test_names = [test.get("test_name", "").lower() for test in structured.get("structured_tests", [])]
    entity_names = [entity.get("text", "").lower() for entity in structured.get("entities", [])]
    joined = " ".join(test_names + entity_names)
    hits = sum(1 for term in expected_terms if term.lower() in joined)
    if structured.get("structured_tests"):
        hits += 1
    if processed.get("simplified_output", {}).get("abnormal_count", 0) > 0:
        hits += 1
    return label_from_score(hits)


def score_rag(processed: Dict[str, Any]) -> str:
    tests = processed.get("simplified_output", {}).get("tests", [])
    if not tests:
        explanation = processed.get("simplified_output", {}).get("report_explanation", "")
        if explanation:
            return "Partial"
        return "Fail"
    hit_count = 0
    for test in tests[:5]:
        if test.get("retrieved_sources"):
            hit_count += 1
        if test.get("explanation") and "could not generate" not in test.get("explanation", "").lower():
            hit_count += 1
    return label_from_score(hit_count)


def score_llm(processed: Dict[str, Any]) -> str:
    simplified = processed.get("simplified_output", {})
    summary = simplified.get("summary", "")
    report_explanation = simplified.get("report_explanation", "")
    follow_up = simplified.get("follow_up_questions", [])
    payload = " ".join(
        [
            summary,
            report_explanation,
            " ".join(test.get("explanation", "") for test in simplified.get("tests", [])[:4]),
        ]
    ).lower()
    score = 0
    if summary or report_explanation:
        score += 1
    if follow_up:
        score += 1
    if "doctor" in payload or "healthcare provider" in payload:
        score += 1
    if "diagnosis" not in payload:
        score += 1
    return label_from_score(score)


def score_ui(client: httpx.Client, file_id: str, processed: Dict[str, Any]) -> str:
    overlay_payload = processed.get("structured_data", {}).get("visual_overlays", {})
    if isinstance(overlay_payload, dict):
        overlays_present = bool(overlay_payload.get("highlights"))
    elif isinstance(overlay_payload, list):
        overlays_present = len(overlay_payload) > 0
    else:
        overlays_present = False
    preview = client.get(f"{BASE_URL}/api/reports/{file_id}/pages/1/preview")
    history_item = client.get(f"{BASE_URL}/api/reports/{file_id}")
    score = 0
    if preview.status_code == 200:
        score += 2
    if history_item.status_code == 200:
        score += 1
    if overlays_present:
        score += 1
    return label_from_score(score)


def verdict_from_labels(labels: List[str]) -> str:
    counts = Counter(labels)
    if counts["Fail"] >= 2:
        return "Fail"
    if counts["Pass"] >= 4 and counts["Fail"] == 0:
        return "Pass"
    return "Partial"


def overlay_count(structured: Dict[str, Any]) -> int:
    overlay_payload = structured.get("visual_overlays")
    if isinstance(overlay_payload, dict):
        return len(overlay_payload.get("highlights", []))
    if isinstance(overlay_payload, list):
        return len(overlay_payload)
    return 0


def upload_and_process(client: httpx.Client, case: Dict[str, Any]) -> Dict[str, Any]:
    with case["path"].open("rb") as handle:
        upload = client.post(
            f"{BASE_URL}/api/upload",
            files={"file": (case["path"].name, handle, "image/png")},
            timeout=120.0,
        )
    upload.raise_for_status()
    upload_payload = upload.json()
    file_id = upload_payload["file_id"]

    processed_response = client.post(f"{BASE_URL}/api/process/{file_id}", timeout=240.0)
    processed_response.raise_for_status()
    processed = processed_response.json()

    simplified = client.get(f"{BASE_URL}/api/reports/{file_id}/simplified", timeout=120.0)
    simplified.raise_for_status()

    stored = client.get(f"{BASE_URL}/api/reports/{file_id}", timeout=120.0)
    stored.raise_for_status()

    raw_text = processed.get("raw_text", "")
    structured = processed.get("structured_data", {})
    simplified_output = processed.get("simplified_output", {})

    ocr_quality = score_ocr(raw_text, case["expected_terms"])
    extraction_quality = score_extraction(processed, case["expected_terms"])
    rag_quality = score_rag(processed)
    llm_quality = score_llm(processed)
    ui_quality = score_ui(client, file_id, processed)
    overall = verdict_from_labels([ocr_quality, extraction_quality, rag_quality, llm_quality, ui_quality])

    return {
        "label": case["label"],
        "path": str(case["path"]),
        "upload_response": upload_payload,
        "processing_status": processed.get("status"),
        "report_id": file_id,
        "document_type": processed.get("document_type"),
        "ocr_excerpt": short_text(raw_text),
        "entities_found": len(structured.get("entities", [])),
        "tests_found": len(structured.get("structured_tests", [])),
        "abnormal_count": simplified_output.get("abnormal_count", 0),
        "summary": simplified_output.get("summary", ""),
        "report_explanation": simplified_output.get("report_explanation", ""),
        "follow_up_questions": simplified_output.get("follow_up_questions", []),
        "glossary_terms": list((simplified_output.get("glossary") or {}).keys()),
        "evaluation": processed.get("evaluation", {}),
        "overlay_highlight_count": overlay_count(structured),
        "ocr_quality": ocr_quality,
        "extraction_quality": extraction_quality,
        "rag_quality": rag_quality,
        "llm_quality": llm_quality,
        "ui_quality": ui_quality,
        "overall_verdict": overall,
        "tests": simplified_output.get("tests", []),
        "stored_report_status": stored.json().get("status"),
    }


def render_report(runtime: Dict[str, Any], cases: List[Dict[str, Any]], history_count: int) -> str:
    lines: List[str] = []
    lines.append("# Real Testing Report")
    lines.append("")
    lines.append("This run contains patient data and generated outputs and should remain local.")
    lines.append("")
    lines.append("## Runtime Snapshot")
    lines.append("")
    lines.append(f"- Backend health: `{runtime['health'].get('status')}`")
    lines.append(f"- App version: `{runtime['health'].get('version')}`")
    lines.append(f"- NLP backend/model: `{runtime['models']['nlp'].get('backend')}` / `{runtime['models']['nlp'].get('active_model')}`")
    lines.append(
        f"- RAG embedding backend: `{runtime['models']['rag'].get('embedding_backend')}`"
    )
    lines.append(f"- Chunks loaded: `{runtime['models']['rag'].get('chunks_loaded')}`")
    lines.append(f"- Index available: `{runtime['models']['rag'].get('index_available')}`")
    lines.append(f"- Stored report count after run: `{history_count}`")
    lines.append("")
    lines.append("## Per-Image Matrix")
    lines.append("")
    lines.append("| Case | Status | Doc Type | OCR | Extraction | RAG | LLM | UI | Verdict |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for case in cases:
        lines.append(
            f"| {case['label']} | {case['processing_status']} | {case['document_type']} | "
            f"{case['ocr_quality']} | {case['extraction_quality']} | {case['rag_quality']} | "
            f"{case['llm_quality']} | {case['ui_quality']} | {case['overall_verdict']} |"
        )
    lines.append("")
    lines.append("## Case Notes")
    lines.append("")
    for case in cases:
        lines.append(f"### {case['label']}")
        lines.append("")
        lines.append(f"- File: `{Path(case['path']).name}`")
        lines.append(f"- Report ID: `{case['report_id']}`")
        lines.append(f"- Document type: `{case['document_type']}`")
        lines.append(f"- Entities found: `{case['entities_found']}`")
        lines.append(f"- Structured tests found: `{case['tests_found']}`")
        lines.append(f"- Abnormal count: `{case['abnormal_count']}`")
        lines.append(f"- Overlay highlights: `{case['overlay_highlight_count']}`")
        lines.append(f"- OCR excerpt: `{case['ocr_excerpt']}`")
        lines.append(f"- Summary: {case['summary'] or case['report_explanation'] or 'None'}")
        lines.append(f"- Follow-up questions: {json.dumps(case['follow_up_questions'])}")
        lines.append(f"- Glossary terms: {json.dumps(case['glossary_terms'])}")
        lines.append("")
    lines.append("## Top Findings")
    lines.append("")
    failing = [case for case in cases if case["overall_verdict"] != "Pass"]
    if failing:
        for case in failing:
            lines.append(
                f"- `{case['label']}`: OCR `{case['ocr_quality']}`, extraction `{case['extraction_quality']}`, "
                f"RAG `{case['rag_quality']}`, LLM `{case['llm_quality']}`, UI `{case['ui_quality']}`."
            )
    else:
        lines.append("- No major failures were found in this batch.")
    lines.append("")
    lines.append("## Readiness Conclusion")
    lines.append("")
    pass_count = sum(1 for case in cases if case["overall_verdict"] == "Pass")
    partial_count = sum(1 for case in cases if case["overall_verdict"] == "Partial")
    if pass_count >= 4 and partial_count <= 2:
        conclusion = "Ready for broader real-user testing, with attention to weaker report formats."
    elif pass_count >= 2:
        conclusion = "Ready only for selected lab-report formats."
    else:
        conclusion = "Not yet ready for broad testing."
    lines.append(f"- {conclusion}")
    return "\n".join(lines) + "\n"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=120.0) as client:
        health = client.get(f"{BASE_URL}/api/health")
        health.raise_for_status()
        models = client.get(f"{BASE_URL}/api/health/models", timeout=180.0)
        models.raise_for_status()

        runtime = {"health": health.json(), "models": models.json()}
        case_results = [upload_and_process(client, case) for case in CASES]
        history = client.get(f"{BASE_URL}/api/reports?limit=50", timeout=120.0)
        history.raise_for_status()

    json_path = OUTPUT_DIR / "real_test_results.json"
    report_path = OUTPUT_DIR / "REAL_TEST_REPORT.md"
    json_path.write_text(json.dumps({"runtime": runtime, "cases": case_results}, indent=2), encoding="utf-8")
    report_path.write_text(
        render_report(runtime, case_results, history.json().get("count", 0)),
        encoding="utf-8",
    )

    print(json.dumps({"output_dir": str(OUTPUT_DIR), "report": str(report_path), "results": str(json_path)}))


if __name__ == "__main__":
    main()
