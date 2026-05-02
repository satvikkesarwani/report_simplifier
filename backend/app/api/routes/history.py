import os

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import FileResponse

from app.db.report_store import get_report_store
from app.utils.file_handler import preview_path_for_page
from app.utils.request_guard import get_authenticated_user

router = APIRouter()


@router.get("/reports", status_code=status.HTTP_200_OK)
async def list_reports(request: Request, limit: int = Query(default=20, ge=1, le=100)):
    user = get_authenticated_user(request)
    reports = get_report_store().list_reports(limit=limit, user_id=user["id"] if user else None)
    return {"reports": reports, "count": len(reports)}


@router.get("/reports/{report_id}", status_code=status.HTTP_200_OK)
async def get_report(request: Request, report_id: str):
    user = get_authenticated_user(request)
    report = get_report_store().get_report(report_id, user_id=user["id"] if user else None)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {report_id} not found",
        )

    return report


@router.get("/reports/{report_id}/file", status_code=status.HTTP_200_OK)
async def get_report_file(request: Request, report_id: str):
    user = get_authenticated_user(request)
    report = get_report_store().get_report(report_id, user_id=user["id"] if user else None)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {report_id} not found",
        )

    file_path = report.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original file is no longer available on disk.",
        )

    return FileResponse(
        path=file_path,
        filename=report.get("original_filename") or os.path.basename(file_path),
        media_type=report.get("mime_type") or "application/octet-stream",
    )


@router.get("/reports/{report_id}/pages/{page_number}/preview", status_code=status.HTTP_200_OK)
async def get_report_page_preview(request: Request, report_id: str, page_number: int):
    user = get_authenticated_user(request)
    report = get_report_store().get_report(report_id, user_id=user["id"] if user else None)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {report_id} not found",
        )

    file_path = report.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original file is no longer available on disk.",
        )

    ext = os.path.splitext(file_path)[1].lower()
    if ext in {".png", ".jpg", ".jpeg"} and page_number == 1:
        media_type = "image/png" if ext == ".png" else "image/jpeg"
        return FileResponse(path=file_path, filename=os.path.basename(file_path), media_type=media_type)

    preview_path = preview_path_for_page(file_path, page_number)
    if not os.path.exists(preview_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preview image for page {page_number} is not available.",
        )

    return FileResponse(path=preview_path, filename=os.path.basename(preview_path), media_type="image/jpeg")


@router.delete("/reports/{report_id}", status_code=status.HTTP_200_OK)
async def delete_report(request: Request, report_id: str):
    store = get_report_store()
    user = get_authenticated_user(request)
    report = store.delete_report(report_id, user_id=user["id"] if user else None)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {report_id} not found",
        )

    file_path = report.get("file_path")
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

    return {"status": "deleted", "report_id": report_id}
