import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.staff_onboarding import StaffCSVUpload, StaffCSVRow, UploadStatus
from app.routes.dependencies import get_current_user

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])
admin_router = APIRouter(tags=["Onboarding"])

REQUIRED_COLUMNS = {"name", "email", "role", "department"}
OPTIONAL_COLUMNS = {"phone", "employee_id"}


class StaffRowUpdate(BaseModel):
    email: EmailStr | None = None
    name: str | None = None
    role: str | None = None
    department: str | None = None


def _ensure_staff_admin(current_user, institution_id: int | None = None):
    if current_user.role not in ["super_admin", "institution_admin", "admin"]:
        raise HTTPException(
            status_code=403, detail="Not authorized to manage staff CSV"
        )
    if (
        institution_id is not None
        and current_user.role != "super_admin"
        and current_user.institution_id != institution_id
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized for this institution"
        )


def _parse_staff_csv(decoded: str) -> tuple[list[dict], list[str]]:
    reader = csv.DictReader(io.StringIO(decoded))
    fieldnames = set(reader.fieldnames or [])
    missing = sorted(REQUIRED_COLUMNS - fieldnames)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns: {', '.join(missing)}",
        )

    rows = []
    seen_emails = set()
    for index, row in enumerate(reader, start=2):
        email = (row.get("email") or "").strip().lower()
        name = (row.get("name") or "").strip()
        role = (row.get("role") or "").strip()
        department = (row.get("department") or "").strip()
        if not email or not name or not role or not department:
            raise HTTPException(
                status_code=400,
                detail=f"CSV row {index} has blank required fields",
            )
        if email in seen_emails:
            raise HTTPException(
                status_code=400,
                detail=f"CSV contains duplicate email: {email}",
            )
        seen_emails.add(email)
        normalized = dict(row)
        normalized["email"] = email
        normalized["name"] = name
        normalized["role"] = role
        normalized["department"] = department
        rows.append(normalized)
    return rows, list(reader.fieldnames or [])


def _store_staff_csv(
    *,
    db: Session,
    current_user,
    institution_id: int,
    file_name: str,
    raw_content: str,
    rows: list[dict],
    fieldnames: list[str],
):
    upload = StaffCSVUpload(
        institution_id=institution_id,
        uploaded_by=current_user.id,
        file_name=file_name,
        raw_content=raw_content,
        parsed_rows=rows,
        row_count=len(rows),
        upload_status=UploadStatus.PROCESSED,
    )
    db.add(upload)
    db.flush()

    extra_columns = set(fieldnames) - REQUIRED_COLUMNS - OPTIONAL_COLUMNS
    for row in rows:
        extra_fields = {
            key: value
            for key, value in row.items()
            if key in OPTIONAL_COLUMNS or key in extra_columns
        }
        csv_row = StaffCSVRow(
            upload_id=upload.id,
            institution_id=institution_id,
            email=row["email"],
            name=row["name"],
            role=row["role"],
            department=row["department"],
            extra_fields=extra_fields,
        )
        db.add(csv_row)

    db.commit()
    db.refresh(upload)
    return upload


async def _read_csv_file(file: UploadFile) -> str:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    content = await file.read()
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded")


@router.post("/upload-csv")
async def upload_staff_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_staff_admin(current_user)
    decoded = await _read_csv_file(file)
    rows, fieldnames = _parse_staff_csv(decoded)
    upload = _store_staff_csv(
        db=db,
        current_user=current_user,
        institution_id=current_user.institution_id,
        file_name=file.filename,
        raw_content=decoded,
        rows=rows,
        fieldnames=fieldnames,
    )
    return {"upload_id": upload.id, "rows_processed": len(rows)}


@admin_router.post("/admin/institutions/{institution_id}/staff/upload")
async def upload_institution_staff_csv(
    institution_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_staff_admin(current_user, institution_id)
    decoded = await _read_csv_file(file)
    rows, fieldnames = _parse_staff_csv(decoded)
    upload = _store_staff_csv(
        db=db,
        current_user=current_user,
        institution_id=institution_id,
        file_name=file.filename,
        raw_content=decoded,
        rows=rows,
        fieldnames=fieldnames,
    )
    return {"upload_id": upload.id, "rows_processed": len(rows)}


@admin_router.get("/admin/institutions/{institution_id}/staff")
def list_institution_staff(
    institution_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_staff_admin(current_user, institution_id)
    return (
        db.query(StaffCSVRow)
        .filter(StaffCSVRow.institution_id == institution_id)
        .order_by(StaffCSVRow.created_at.desc(), StaffCSVRow.email.asc())
        .all()
    )


@admin_router.get("/admin/institutions/{institution_id}/staff/{row_id}")
def get_institution_staff_row(
    institution_id: int,
    row_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_staff_admin(current_user, institution_id)
    row = (
        db.query(StaffCSVRow)
        .filter(StaffCSVRow.id == row_id, StaffCSVRow.institution_id == institution_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Staff row not found")
    return row


@admin_router.put("/admin/institutions/{institution_id}/staff/{row_id}")
def update_institution_staff_row(
    institution_id: int,
    row_id: str,
    payload: StaffRowUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_staff_admin(current_user, institution_id)
    row = (
        db.query(StaffCSVRow)
        .filter(StaffCSVRow.id == row_id, StaffCSVRow.institution_id == institution_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Staff row not found")
    if payload.email is not None:
        row.email = payload.email.strip().lower()
    if payload.name is not None:
        row.name = payload.name
    if payload.role is not None:
        row.role = payload.role
    if payload.department is not None:
        row.department = payload.department
    db.commit()
    db.refresh(row)
    return row


@admin_router.delete("/admin/institutions/{institution_id}/staff/{row_id}")
def delete_institution_staff_row(
    institution_id: int,
    row_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_staff_admin(current_user, institution_id)
    row = (
        db.query(StaffCSVRow)
        .filter(StaffCSVRow.id == row_id, StaffCSVRow.institution_id == institution_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Staff row not found")
    db.delete(row)
    db.commit()
    return {"status": "deleted", "row_id": row_id}


@router.get("/uploads")
def list_uploads(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in ["super_admin", "institution_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    query = db.query(StaffCSVUpload)
    if current_user.role != "super_admin":
        query = query.filter(
            StaffCSVUpload.institution_id == current_user.institution_id
        )

    return query.all()


@router.get("/uploads/{upload_id}/rows")
def get_upload_rows(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    upload = db.query(StaffCSVUpload).filter(StaffCSVUpload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    if (
        current_user.role != "super_admin"
        and current_user.institution_id != upload.institution_id
    ):
        raise HTTPException(status_code=403, detail="Not authorized")

    return db.query(StaffCSVRow).filter(StaffCSVRow.upload_id == upload_id).all()
