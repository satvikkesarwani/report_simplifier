import os
import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.config import get_settings
from app.db.report_store import get_report_store
from app.utils.file_handler import validate_file
from app.utils.request_guard import get_authenticated_user

router = APIRouter()
settings = get_settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Upload a medical report (PDF or image)."""
    # Validate file
    valid, error_msg = validate_file(file)
    if not valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Generate unique filename
    ext = file.filename.split(".")[-1].lower() if file.filename else "bin"
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}.{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    finally:
        await file.close()

    user = get_authenticated_user(request)

    get_report_store().create_report(
        report_id=file_id,
        original_filename=file.filename or safe_filename,
        stored_filename=safe_filename,
        file_path=file_path,
        mime_type=file.content_type,
        size=os.path.getsize(file_path),
        user_id=user["id"] if user else None,
    )
    
    return {
        "file_id": file_id,
        "filename": file.filename,
        "saved_as": safe_filename,
        "file_path": file_path,
        "size": os.path.getsize(file_path),
        "status": "uploaded",
    }
