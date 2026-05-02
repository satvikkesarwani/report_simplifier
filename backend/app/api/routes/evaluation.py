from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Request, status

from app.db.report_store import get_report_store
from app.evaluation.metrics import (
    compute_bleu_scores,
    compute_ocr_accuracy,
    compute_ner_metrics,
    compute_rouge_scores,
    summarize_feedback_scores,
)
from app.utils.request_guard import get_authenticated_user

router = APIRouter()


@router.post("/evaluation/ocr", status_code=status.HTTP_200_OK)
async def evaluate_ocr(
    reference_text: str = Body(...),
    predicted_text: str = Body(...),
):
    return compute_ocr_accuracy(reference_text, predicted_text)


@router.post("/evaluation/ner", status_code=status.HTTP_200_OK)
async def evaluate_ner(
    expected_entities: List[Dict[str, str]] = Body(...),
    predicted_entities: List[Dict[str, str]] = Body(...),
):
    return compute_ner_metrics(expected_entities, predicted_entities)


@router.post("/evaluation/simplification", status_code=status.HTTP_200_OK)
async def evaluate_simplification(
    reference_text: str = Body(...),
    candidate_text: str = Body(...),
):
    result = {}
    result.update(compute_bleu_scores(reference_text, candidate_text))
    result.update(compute_rouge_scores(reference_text, candidate_text))
    return result


@router.post("/reports/{report_id}/feedback", status_code=status.HTTP_201_CREATED)
async def submit_report_feedback(
    request: Request,
    report_id: str,
    comprehension_score: Optional[int] = Body(default=None),
    usefulness_score: Optional[int] = Body(default=None),
    highlighting_score: Optional[int] = Body(default=None),
    recommendation_score: Optional[int] = Body(default=None),
    comments: Optional[str] = Body(default=None),
):
    store = get_report_store()
    user = get_authenticated_user(request)
    report = store.get_report(report_id, user_id=user["id"] if user else None)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {report_id} not found",
        )

    feedback = store.add_feedback(
        report_id,
        comprehension_score=comprehension_score,
        usefulness_score=usefulness_score,
        highlighting_score=highlighting_score,
        recommendation_score=recommendation_score,
        comments=comments,
    )
    return feedback


@router.get("/reports/{report_id}/feedback", status_code=status.HTTP_200_OK)
async def list_report_feedback(request: Request, report_id: str):
    store = get_report_store()
    user = get_authenticated_user(request)
    report = store.get_report(report_id, user_id=user["id"] if user else None)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {report_id} not found",
        )
    entries = store.list_feedback_for_report(report_id)
    summary = summarize_feedback_scores(entries)
    return {"entries": entries, "summary": summary}


@router.get("/evaluation/feedback-summary", status_code=status.HTTP_200_OK)
async def feedback_summary():
    store = get_report_store()
    payload = store.feedback_summary()
    payload["summary"] = summarize_feedback_scores(payload["entries"])
    return payload
