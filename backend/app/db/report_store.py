import json
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db.init_db import init_db
from app.db.session import SessionLocal, get_session_factory, session_scope
from app.models.entities import Feedback, Job, Report, User


JSON_FIELDS = {"structured_data", "simplified_output", "processing_result", "evaluation", "metadata_json", "result_json"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReportStore:
    """Database-backed persistence layer for users, reports, and feedback."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url
        init_db(database_url)
        self._session_factory: sessionmaker = (
            get_session_factory(database_url) if database_url else SessionLocal
        )

    def create_user(self, *, email: str, password_hash: str) -> Dict[str, Any]:
        with session_scope(self.database_url) as session:
            user = User(email=email, password_hash=password_hash, created_at=_utc_now())
            session.add(user)
            session.flush()
            return self._user_to_dict(user)

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
            return self._user_to_dict(user) if user else None

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            user = session.get(User, user_id)
            return self._user_to_dict(user) if user else None

    def create_report(
        self,
        *,
        report_id: str,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        mime_type: Optional[str],
        size: int,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        now = _utc_now()
        with session_scope(self.database_url) as session:
            report = Report(
                id=report_id,
                user_id=user_id,
                original_filename=original_filename,
                stored_filename=stored_filename,
                file_path=file_path,
                mime_type=mime_type,
                size=size,
                status="uploaded",
                document_type=None,
                raw_text=None,
                structured_data=None,
                simplified_output=None,
                processing_result=None,
                evaluation=None,
                abnormal_count=0,
                readability_score=None,
                created_at=now,
                updated_at=now,
                processed_at=None,
                error_message=None,
            )
            session.add(report)
            session.flush()
            return self._report_to_dict(report)

    def get_report(self, report_id: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            query = select(Report).where(Report.id == report_id)
            if user_id is not None:
                query = query.where(Report.user_id == user_id)
            report = session.execute(query).scalar_one_or_none()
            return self._report_to_dict(report) if report else None

    def list_reports(self, limit: int = 20, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        with self._session_factory() as session:
            query = select(Report)
            if user_id is not None:
                query = query.where(Report.user_id == user_id)
            query = query.order_by(Report.created_at.desc()).limit(limit)
            reports = session.execute(query).scalars().all()
            return [self._report_to_dict(report, include_large_fields=False) for report in reports]

    def update_report(self, report_id: str, user_id: Optional[int] = None, **fields: Any) -> Optional[Dict[str, Any]]:
        with session_scope(self.database_url) as session:
            query = select(Report).where(Report.id == report_id)
            if user_id is not None:
                query = query.where(Report.user_id == user_id)
            report = session.execute(query).scalar_one_or_none()
            if not report:
                return None

            for key, value in fields.items():
                setattr(report, key, self._serialize_value(key, value))
            report.updated_at = _utc_now()
            session.flush()
            return self._report_to_dict(report)

    def delete_report(self, report_id: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        with session_scope(self.database_url) as session:
            query = select(Report).where(Report.id == report_id)
            if user_id is not None:
                query = query.where(Report.user_id == user_id)
            report = session.execute(query).scalar_one_or_none()
            if not report:
                return None
            payload = self._report_to_dict(report)
            session.delete(report)
            return payload

    def add_feedback(
        self,
        report_id: str,
        *,
        comprehension_score: Optional[int],
        usefulness_score: Optional[int],
        highlighting_score: Optional[int],
        recommendation_score: Optional[int],
        comments: Optional[str],
    ) -> Dict[str, Any]:
        with session_scope(self.database_url) as session:
            feedback = Feedback(
                report_id=report_id,
                comprehension_score=comprehension_score,
                usefulness_score=usefulness_score,
                highlighting_score=highlighting_score,
                recommendation_score=recommendation_score,
                comments=comments,
                created_at=_utc_now(),
            )
            session.add(feedback)
            session.flush()
            return self._feedback_to_dict(feedback)

    def get_feedback_entry(self, feedback_id: int) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            feedback = session.get(Feedback, feedback_id)
            return self._feedback_to_dict(feedback) if feedback else None

    def list_feedback_for_report(self, report_id: str) -> List[Dict[str, Any]]:
        with self._session_factory() as session:
            entries = session.execute(
                select(Feedback).where(Feedback.report_id == report_id).order_by(Feedback.created_at.desc())
            ).scalars().all()
            return [self._feedback_to_dict(entry) for entry in entries]

    def feedback_summary(self) -> Dict[str, Any]:
        with self._session_factory() as session:
            entries = session.execute(select(Feedback)).scalars().all()
            return {"responses": len(entries), "entries": [self._feedback_to_dict(entry) for entry in entries]}

    def create_job(self, *, job_id: str, kind: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        now = _utc_now()
        with session_scope(self.database_url) as session:
            job = Job(
                id=job_id,
                kind=kind,
                status="queued",
                progress=0.0,
                message="Queued",
                metadata_json=self._serialize_value("metadata_json", metadata or {}),
                result_json=None,
                error=None,
                created_at=now,
                updated_at=now,
            )
            session.add(job)
            session.flush()
            return self._job_to_dict(job)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            job = session.get(Job, job_id)
            return self._job_to_dict(job) if job else None

    def list_jobs(self, limit: int = 100, statuses: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        with self._session_factory() as session:
            query = select(Job)
            if statuses:
                query = query.where(Job.status.in_(statuses))
            query = query.order_by(Job.created_at.desc()).limit(limit)
            jobs = session.execute(query).scalars().all()
            return [self._job_to_dict(job) for job in jobs]

    def update_job(self, job_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
        with session_scope(self.database_url) as session:
            job = session.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
            if not job:
                return None

            for key, value in fields.items():
                if key == "metadata":
                    setattr(job, "metadata_json", self._serialize_value("metadata_json", value))
                elif key == "result":
                    setattr(job, "result_json", self._serialize_value("result_json", value))
                else:
                    setattr(job, key, value)
            job.updated_at = _utc_now()
            session.flush()
            return self._job_to_dict(job)

    def get_pending_jobs(self) -> List[Dict[str, Any]]:
        return self.list_jobs(limit=1000, statuses=["queued", "running"])

    def _serialize_value(self, key: str, value: Any) -> Any:
        if key in JSON_FIELDS and value is not None:
            return json.dumps(value)
        return value

    def _deserialize_value(self, key: str, value: Any) -> Any:
        if key in JSON_FIELDS and value:
            return json.loads(value)
        return value

    def _report_to_dict(self, report: Report | None, include_large_fields: bool = True) -> Dict[str, Any]:
        if report is None:
            return {}
        payload = {
            "id": report.id,
            "user_id": report.user_id,
            "original_filename": report.original_filename,
            "stored_filename": report.stored_filename,
            "file_path": report.file_path,
            "mime_type": report.mime_type,
            "size": report.size,
            "status": report.status,
            "document_type": report.document_type,
            "raw_text": report.raw_text,
            "structured_data": self._deserialize_value("structured_data", report.structured_data),
            "simplified_output": self._deserialize_value("simplified_output", report.simplified_output),
            "processing_result": self._deserialize_value("processing_result", report.processing_result),
            "evaluation": self._deserialize_value("evaluation", report.evaluation),
            "abnormal_count": report.abnormal_count,
            "readability_score": report.readability_score,
            "created_at": report.created_at,
            "updated_at": report.updated_at,
            "processed_at": report.processed_at,
            "error_message": report.error_message,
        }
        if not include_large_fields:
            payload.pop("raw_text", None)
            payload.pop("structured_data", None)
            payload.pop("simplified_output", None)
            payload.pop("processing_result", None)
            payload.pop("evaluation", None)
        return payload

    def _feedback_to_dict(self, feedback: Feedback | None) -> Dict[str, Any]:
        if feedback is None:
            return {}
        return {
            "id": feedback.id,
            "report_id": feedback.report_id,
            "comprehension_score": feedback.comprehension_score,
            "usefulness_score": feedback.usefulness_score,
            "highlighting_score": feedback.highlighting_score,
            "recommendation_score": feedback.recommendation_score,
            "comments": feedback.comments,
            "created_at": feedback.created_at,
        }

    def _user_to_dict(self, user: User | None) -> Dict[str, Any]:
        if user is None:
            return {}
        return {
            "id": user.id,
            "email": user.email,
            "password_hash": user.password_hash,
            "created_at": user.created_at,
        }

    def _job_to_dict(self, job: Job | None) -> Dict[str, Any]:
        if job is None:
            return {}
        return {
            "job_id": job.id,
            "kind": job.kind,
            "status": job.status,
            "progress": job.progress,
            "message": job.message,
            "metadata": self._deserialize_value("metadata_json", job.metadata_json) or {},
            "result": self._deserialize_value("result_json", job.result_json),
            "error": job.error,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }


@lru_cache()
def get_report_store() -> ReportStore:
    return ReportStore()
