import os
from typing import Tuple

from app.config import get_settings

settings = get_settings()


def preview_dir_for_file(file_path: str) -> str:
    base, _ = os.path.splitext(file_path)
    return f"{base}_previews"


def preview_path_for_page(file_path: str, page_number: int) -> str:
    return os.path.join(preview_dir_for_file(file_path), f"page-{page_number}.jpg")

def validate_file(file) -> Tuple[bool, str]:
    """Validate uploaded file size and extension."""
    # Check file size
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    
    if size > settings.MAX_UPLOAD_SIZE:
        max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
        return False, f"File too large. Maximum size is {max_mb}MB."
    
    # Check extension
    if not file.filename:
        return False, "Filename is required."
    
    ext = file.filename.split(".")[-1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        return False, f"Invalid file type '{ext}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}."
    
    return True, ""
