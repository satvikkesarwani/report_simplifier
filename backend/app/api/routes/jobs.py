from fastapi import APIRouter, HTTPException, Request, status

from app.services.background_jobs import get_job_manager
from app.services.job_tasks import process_report_job, rebuild_knowledge_base_job
from app.utils.request_guard import get_authenticated_user

router = APIRouter()
job_manager = get_job_manager()
job_manager.register_handler("report_processing", process_report_job)
job_manager.register_handler("knowledge_base_rebuild", rebuild_knowledge_base_job)


def _ensure_manager_ready():
    job_manager.resume_pending_jobs()
    return job_manager


@router.post("/process/{file_id}/async", status_code=status.HTTP_202_ACCEPTED)
async def process_report_async(request: Request, file_id: str):
    user = get_authenticated_user(request)
    user_id = user["id"] if user else None
    manager = _ensure_manager_ready()
    job = manager.create_job(
        kind="report_processing",
        metadata={"file_id": file_id, "user_id": user_id},
    )
    manager.start_existing_job(job["job_id"])
    return job


@router.post("/knowledge-base/rebuild/async", status_code=status.HTTP_202_ACCEPTED)
async def rebuild_knowledge_base_async():
    manager = _ensure_manager_ready()
    job = manager.create_job(kind="knowledge_base_rebuild")
    manager.start_existing_job(job["job_id"])
    return job


@router.get("/jobs/{job_id}", status_code=status.HTTP_200_OK)
async def get_job_status(job_id: str):
    job = _ensure_manager_ready().get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )
    return job


@router.get("/jobs", status_code=status.HTTP_200_OK)
async def list_jobs():
    return {"jobs": _ensure_manager_ready().list_jobs()}
