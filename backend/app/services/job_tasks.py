import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from app.db.report_store import get_report_store
from app.services.knowledge_base import KnowledgeBaseBuilder
from app.services.pipeline import PipelineService


ProgressCallback = Callable[[float, str], None]
_pipeline_service: Optional[PipelineService] = None


def get_pipeline_service() -> PipelineService:
    global _pipeline_service
    if _pipeline_service is None:
        _pipeline_service = PipelineService()
    return _pipeline_service


async def process_report_job(metadata: Dict[str, Any], progress: ProgressCallback) -> Dict[str, Any]:
    store = get_report_store()
    file_id = metadata["file_id"]
    user_id = metadata.get("user_id")
    progress(10, "Loading report metadata")
    report = store.get_report(file_id, user_id=user_id)
    if not report:
        raise ValueError(f"File with ID {file_id} not found")

    store.update_report(file_id, user_id=user_id, status="processing", error_message=None)
    progress(25, "Running OCR, NLP, RAG, and simplification")
    result = await get_pipeline_service().process_report(report["file_path"])

    processed_at = datetime.now(timezone.utc).isoformat()
    progress(85, "Saving processed output")
    updated_report = store.update_report(
        file_id,
        user_id=user_id,
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
    progress(100, "Report processing complete")
    return enriched_result


async def rebuild_knowledge_base_job(metadata: Dict[str, Any], progress: ProgressCallback) -> Dict[str, Any]:
    progress(10, "Fetching authoritative medical sources")
    chunks = await asyncio.to_thread(KnowledgeBaseBuilder().build_chunks_from_sources)
    progress(70, "Rebuilding vector index")
    from app.core.rag_engine import RAGEngine

    rag = await asyncio.to_thread(RAGEngine)
    await asyncio.to_thread(rag.rebuild_index)
    progress(100, "Knowledge base rebuild complete")
    return {
        "chunks_built": len(chunks),
        "embedding_backend": rag.embedding_backend,
        "index_mode": "vector" if rag.index is not None else "lexical",
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
