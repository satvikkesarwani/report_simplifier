import os

import pytest

from app.db.init_db import init_db
from app.db.report_store import ReportStore


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL is not configured")
def test_report_store_roundtrip_on_postgres():
    store = ReportStore(database_url=POSTGRES_TEST_URL)
    init_db(POSTGRES_TEST_URL)

    created = store.create_report(
        report_id="pg-report-1",
        original_filename="report.pdf",
        stored_filename="report.pdf",
        file_path="/tmp/report.pdf",
        mime_type="application/pdf",
        size=1024,
    )

    assert created["id"] == "pg-report-1"
    assert store.get_report("pg-report-1")["original_filename"] == "report.pdf"
