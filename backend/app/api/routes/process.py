import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status

from app.db.report_store import get_report_store
from app.services.pipeline import PipelineService
from app.utils.request_guard import get_authenticated_user

router = APIRouter()


def _run_pipeline_sync(file_path: str):
    service = PipelineService()
    return service.process_report_sync(file_path)


@router.post("/process/{file_id}", status_code=status.HTTP_200_OK)
async def process_report(request: Request, file_id: str):
    """Process an uploaded medical report through OCR -> NLP -> RAG -> LLM pipeline."""
    store = get_report_store()
    user = get_authenticated_user(request)
    report = store.get_report(file_id, user_id=user["id"] if user else None)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID {file_id} not found",
        )

    store.update_report(file_id, user_id=user["id"] if user else None, status="processing", error_message=None)

    try:
        result = await asyncio.to_thread(_run_pipeline_sync, report["file_path"])
        processed_at = datetime.now(timezone.utc).isoformat()
        updated_report = store.update_report(
            file_id,
            user_id=user["id"] if user else None,
            status=result["status"],
            document_type=result.get("document_type"),
            raw_text=result.get("raw_text"),
            structured_data=result.get("structured_data"),
            simplified_output=result.get("simplified_output"),
            processing_result=result,
            evaluation=result.get("evaluation"),
            abnormal_count=result.get("simplified_output", {}).get("abnormal_count", 0),
            readability_score=result.get("evaluation", {})
            .get("readability", {})
            .get("flesch_reading_ease"),
            processed_at=processed_at,
            error_message="; ".join(result.get("errors", [])) or None,
        )
        enriched_result = dict(result)
        enriched_result["report_id"] = file_id
        enriched_result["report_metadata"] = _public_report_metadata(updated_report)
        return enriched_result
    except Exception as exc:
        store.update_report(
            file_id,
            user_id=user["id"] if user else None,
            status="failed",
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {exc}",
        )


@router.get("/reports/{file_id}/simplified", status_code=status.HTTP_200_OK)
async def get_simplified_report(request: Request, file_id: str):
    """Get simplified explanation for a processed report."""
    user = get_authenticated_user(request)
    report = get_report_store().get_report(file_id, user_id=user["id"] if user else None)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {file_id} not found",
        )

    if not report.get("processing_result"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This report has not been processed yet.",
        )

    return {
        "report_id": report["id"],
        "status": report["status"],
        "simplified_output": report.get("simplified_output"),
        "evaluation": report.get("evaluation"),
        "document_type": report.get("document_type"),
    }


def _public_report_metadata(report):
    if not report:
        return None

    return {
        "id": report["id"],
        "original_filename": report["original_filename"],
        "status": report["status"],
        "document_type": report.get("document_type"),
        "abnormal_count": report.get("abnormal_count", 0),
        "created_at": report["created_at"],
        "processed_at": report.get("processed_at"),
        "readability_score": report.get("readability_score"),
    }
