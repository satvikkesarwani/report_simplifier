from pathlib import Path

from app.db.report_store import ReportStore


def test_report_store_create_update_and_list(tmp_path: Path):
    store = ReportStore(database_url=f"sqlite:///{tmp_path / 'reports.db'}")

    created = store.create_report(
        report_id="report-1",
        original_filename="cbc.pdf",
        stored_filename="report-1.pdf",
        file_path=str(tmp_path / "report-1.pdf"),
        mime_type="application/pdf",
        size=1234,
    )

    assert created["status"] == "uploaded"

    updated = store.update_report(
        "report-1",
        status="completed",
        document_type="lab_report",
        evaluation={"readability": {"flesch_reading_ease": 67.4}},
        simplified_output={"summary": "Processed"},
        processing_result={"status": "completed"},
        abnormal_count=2,
    )

    assert updated is not None
    assert updated["document_type"] == "lab_report"
    assert updated["evaluation"]["readability"]["flesch_reading_ease"] == 67.4

    reports = store.list_reports(limit=10)
    assert len(reports) == 1
    assert reports[0]["id"] == "report-1"
    assert "processing_result" not in reports[0]

    feedback = store.add_feedback(
        "report-1",
        comprehension_score=5,
        usefulness_score=4,
        highlighting_score=5,
        recommendation_score=4,
        comments="Helpful summary",
    )
    assert feedback is not None
    assert feedback["report_id"] == "report-1"
    assert len(store.list_feedback_for_report("report-1")) == 1

    job = store.create_job(
        job_id="job-1",
        kind="report_processing",
        metadata={"file_id": "report-1"},
    )
    assert job["status"] == "queued"

    updated_job = store.update_job(
        "job-1",
        status="completed",
        progress=100.0,
        message="Done",
        result={"report_id": "report-1"},
    )
    assert updated_job is not None
    assert updated_job["result"]["report_id"] == "report-1"
    assert store.get_pending_jobs() == []
