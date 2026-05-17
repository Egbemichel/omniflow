import os
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session
from app.database import SessionLocal, get_db
from app.repositories.form_repository import FormRepository
from app.routes.dependencies import require_admin
from app.schemas.form_schema import FormUploadResponse
from app.services.event_service import EventService
from app.services.ocr_service import OCRService

router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/pdf": "pdf",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/tiff": "tiff",
}


def _max_bytes() -> int:
    max_mb = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
    return max_mb * 1024 * 1024


def _upload_root() -> str:
    return os.getenv("UPLOAD_DIR", "/data/uploads")


def _safe_extension(filename: str, mime_type: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower().lstrip(".")
    if not ext:
        ext = ALLOWED_MIME_TYPES[mime_type]
    return ext


def _save_upload_file(upload_file: UploadFile, target_path: str, max_bytes: int, content_length: int | None) -> None:
    if content_length is not None and content_length > max_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    size = 0
    with open(target_path, "wb") as out_file:
        while True:
            chunk = upload_file.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                out_file.close()
                try:
                    os.remove(target_path)
                except OSError:
                    pass
                raise HTTPException(status_code=413, detail="File too large")
            out_file.write(chunk)


def _run_ocr(form_id: str, file_path: str, institution_id: int, admin_id: int) -> None:
    db = SessionLocal()
    repo = FormRepository(db)
    ocr_service = OCRService()
    event_service = EventService()
    field_count = 0
    try:
        form = repo.get_form_any(form_id)
        if not form:
            return
        fields = ocr_service.extract_fields(file_path)
        field_count = repo.replace_fields(form_id, fields)
        repo.update_status(form, "READY")
    except Exception:
        form = repo.get_form_any(form_id)
        if form:
            repo.update_status(form, "FAILED")
    finally:
        try:
            event_service.publish_ocr_completed(form_id, institution_id, admin_id, field_count)
        finally:
            db.close()


@router.post("/forms/upload", response_model=FormUploadResponse, status_code=201)
async def upload_form(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported file type")

    form_id = str(uuid.uuid4())
    institution_id = int(current_user["institution_id"])
    admin_id = int(current_user["user_id"])

    upload_dir = os.path.join(_upload_root(), str(institution_id))
    os.makedirs(upload_dir, exist_ok=True)

    ext = _safe_extension(file.filename or "", file.content_type)
    file_path = os.path.join(upload_dir, f"{form_id}.{ext}")

    content_length = request.headers.get("content-length")
    content_len_int = int(content_length) if content_length and content_length.isdigit() else None
    _save_upload_file(file, file_path, _max_bytes(), content_len_int)

    repo = FormRepository(db)
    repo.create_form(
        form_id=form_id,
        institution_id=institution_id,
        admin_id=admin_id,
        original_filename=file.filename or "uploaded",
        file_path=file_path,
        mime_type=file.content_type,
        status="PROCESSING",
    )

    background_tasks.add_task(_run_ocr, form_id, file_path, institution_id, admin_id)

    return {"form_id": form_id, "status": "PROCESSING"}
