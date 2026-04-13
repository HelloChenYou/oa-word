import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import KnowledgeChunk, KnowledgeDocument
from app.schemas import CreateKnowledgeResp, KnowledgeDetailResp, KnowledgeOut, UpdateKnowledgeReq
from app.services.boundary_guard import ensure_template_file_within_limit, ensure_template_text_within_limit
from app.services.rag import count_document_chunks, replace_document_chunks
from app.services.template_parser import read_template_content

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])
KNOWLEDGE_STORAGE_DIR = Path("storage/knowledge")
ALLOWED_TYPES = {"txt", "md", "docx"}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=CreateKnowledgeResp)
async def upload_knowledge(
    name: str = Form(...),
    doc_type: str = Form("general"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "").suffix.lower().lstrip(".")
    if suffix not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"unsupported file type: {suffix}")

    document_id = f"kb_{uuid.uuid4().hex[:16]}"
    KNOWLEDGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    save_path = KNOWLEDGE_STORAGE_DIR / f"{document_id}.{suffix}"
    content = await file.read()
    ensure_template_file_within_limit(len(content))
    save_path.write_bytes(content)

    raw_text = read_template_content(save_path, suffix)
    ensure_template_text_within_limit(raw_text)
    row = KnowledgeDocument(
        id=document_id,
        name=name,
        doc_type=doc_type,
        file_type=suffix,
        file_path=str(save_path),
        raw_text=raw_text,
        enabled=True,
    )
    db.add(row)
    chunk_count = replace_document_chunks(db, document_id=document_id, raw_text=raw_text)
    db.commit()
    return CreateKnowledgeResp(
        document_id=row.id,
        name=row.name,
        doc_type=row.doc_type,
        file_type=row.file_type,
        chunk_count=chunk_count,
    )


@router.get("", response_model=list[KnowledgeOut])
def list_knowledge(
    keyword: str | None = None,
    enabled: bool | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(KnowledgeDocument)
    if keyword:
        like_keyword = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                KnowledgeDocument.name.like(like_keyword),
                KnowledgeDocument.doc_type.like(like_keyword),
                KnowledgeDocument.raw_text.like(like_keyword),
            )
        )
    if enabled is not None:
        stmt = stmt.where(KnowledgeDocument.enabled == enabled)
    rows = db.execute(stmt.order_by(KnowledgeDocument.created_at.desc())).scalars().all()
    return [
        KnowledgeOut(
            document_id=row.id,
            name=row.name,
            doc_type=row.doc_type,
            file_type=row.file_type,
            enabled=row.enabled,
            chunk_count=count_document_chunks(db, row.id),
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]


@router.get("/{document_id}", response_model=KnowledgeDetailResp)
def get_knowledge(document_id: str, db: Session = Depends(get_db)):
    row = db.get(KnowledgeDocument, document_id)
    if not row:
        raise HTTPException(status_code=404, detail="knowledge document not found")
    return KnowledgeDetailResp(
        document_id=row.id,
        name=row.name,
        doc_type=row.doc_type,
        file_type=row.file_type,
        enabled=row.enabled,
        chunk_count=count_document_chunks(db, row.id),
        raw_text=row.raw_text,
        created_at=row.created_at.isoformat(),
    )


@router.patch("/{document_id}", response_model=KnowledgeDetailResp)
def update_knowledge(document_id: str, payload: UpdateKnowledgeReq, db: Session = Depends(get_db)):
    row = db.get(KnowledgeDocument, document_id)
    if not row:
        raise HTTPException(status_code=404, detail="knowledge document not found")

    if payload.name is not None:
        row.name = payload.name.strip()
    if payload.doc_type is not None:
        row.doc_type = payload.doc_type.strip()
    if payload.enabled is not None:
        row.enabled = payload.enabled
    if payload.raw_text is not None:
        ensure_template_text_within_limit(payload.raw_text)
        row.raw_text = payload.raw_text
        replace_document_chunks(db, document_id=document_id, raw_text=payload.raw_text)

    db.commit()
    db.refresh(row)
    return KnowledgeDetailResp(
        document_id=row.id,
        name=row.name,
        doc_type=row.doc_type,
        file_type=row.file_type,
        enabled=row.enabled,
        chunk_count=count_document_chunks(db, row.id),
        raw_text=row.raw_text,
        created_at=row.created_at.isoformat(),
    )


@router.delete("/{document_id}")
def delete_knowledge(document_id: str, db: Session = Depends(get_db)):
    row = db.get(KnowledgeDocument, document_id)
    if not row:
        raise HTTPException(status_code=404, detail="knowledge document not found")

    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))
    db.delete(row)
    db.commit()
    try:
        Path(row.file_path).unlink(missing_ok=True)
    except OSError:
        pass
    return {"ok": True}
