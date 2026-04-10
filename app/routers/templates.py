import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Template
from app.schemas import CreateTemplateResp, TemplateDetailResp, TemplateOut
from app.services.template_parser import parse_template_file

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])
TEMPLATE_STORAGE_DIR = Path("storage/templates")
ALLOWED_TYPES = {"txt", "md", "docx"}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=CreateTemplateResp)
async def upload_template(
    name: str = Form(...),
    doc_type: str = Form("general"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "").suffix.lower().lstrip(".")
    if suffix not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"unsupported file type: {suffix}")

    template_id = f"tpl_{uuid.uuid4().hex[:16]}"
    TEMPLATE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    save_path = TEMPLATE_STORAGE_DIR / f"{template_id}.{suffix}"
    content = await file.read()
    save_path.write_bytes(content)

    raw_text, parsed_json = parse_template_file(save_path, suffix)
    row = Template(
        id=template_id,
        name=name,
        doc_type=doc_type,
        file_type=suffix,
        file_path=str(save_path),
        raw_text=raw_text,
        parsed_json=parsed_json,
    )
    db.add(row)
    db.commit()
    return CreateTemplateResp(
        template_id=row.id,
        name=row.name,
        doc_type=row.doc_type,
        file_type=row.file_type,
        parsed=json.loads(row.parsed_json),
    )


@router.get("", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db)):
    rows = db.execute(select(Template).order_by(Template.created_at.desc())).scalars().all()
    return [
        TemplateOut(
            template_id=row.id,
            name=row.name,
            doc_type=row.doc_type,
            file_type=row.file_type,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]


@router.get("/{template_id}", response_model=TemplateDetailResp)
def get_template(template_id: str, db: Session = Depends(get_db)):
    row = db.get(Template, template_id)
    if not row:
        raise HTTPException(status_code=404, detail="template not found")
    return TemplateDetailResp(
        template_id=row.id,
        name=row.name,
        doc_type=row.doc_type,
        file_type=row.file_type,
        raw_text=row.raw_text,
        parsed=json.loads(row.parsed_json),
        created_at=row.created_at.isoformat(),
    )
