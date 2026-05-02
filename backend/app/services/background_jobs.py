import asyncio
from typing import Any, Awaitable, Callable, Dict, Optional
from uuid import uuid4

from app.db.report_store import get_report_store


ProgressCallback = Callable[[float, str], None]
JobHandler = Callable[[Dict[str, Any], ProgressCallback], Awaitable[Dict[str, Any]]]


class BackgroundJobManager:
    def __init__(self):
        self._handlers: Dict[str, JobHandler] = {}
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._store = get_report_store()
        self._resumed = False

    def register_handler(self, kind: str, handler: JobHandler) -> None:
        self._handlers[kind] = handler

    def create_job(self, *, kind: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        job_id = str(uuid4())
        return self._store.create_job(job_id=job_id, kind=kind, metadata=metadata or {})

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get_job(job_id)

    def list_jobs(self) -> list[Dict[str, Any]]:
        return self._store.list_jobs()

    def resume_pending_jobs(self) -> None:
        if self._resumed:
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return
        for job in self._store.get_pending_jobs():
            self.start_existing_job(job["job_id"])
        self._resumed = True

    def start_existing_job(self, job_id: str) -> None:
        if job_id in self._active_tasks:
            return

        job = self._store.get_job(job_id)
        if not job:
            return

        handler = self._handlers.get(job["kind"])
        if handler is None:
            self._store.update_job(
                job_id,
                status="failed",
                progress=100.0,
                message="No handler registered for this job kind.",
                error=f"Unsupported job kind: {job['kind']}",
            )
            return

        task = asyncio.create_task(self._run_job(job_id, handler))
        self._active_tasks[job_id] = task
        task.add_done_callback(lambda _: self._active_tasks.pop(job_id, None))

    async def _run_job(self, job_id: str, handler: JobHandler) -> None:
        job = self._store.get_job(job_id)
        if not job:
            return

        self._store.update_job(
            job_id,
            status="running",
            progress=max(float(job.get("progress", 0.0)), 5.0),
            message="Started",
            error=None,
        )

        def progress_callback(progress: float, message: str) -> None:
            self._store.update_job(
                job_id,
                progress=max(0.0, min(100.0, progress)),
                message=message,
            )

        try:
            result = await handler(job.get("metadata", {}), progress_callback)
            self._store.update_job(
                job_id,
                status="completed",
                progress=100.0,
                message="Completed",
                result=result,
                error=None,
            )
        except Exception as exc:
            self._store.update_job(
                job_id,
                status="failed",
                progress=100.0,
                message="Failed",
                error=str(exc),
            )


_job_manager: Optional[BackgroundJobManager] = None


def get_job_manager() -> BackgroundJobManager:
    global _job_manager
    if _job_manager is None:
        _job_manager = BackgroundJobManager()
    return _job_manager
