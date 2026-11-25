import hashlib
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Anomaly, Document, ExtractedMetric, Transaction, User
from app.schemas.schemas import (
    DocumentClassifyRequest,
    DocumentDetailOut,
    DocumentOut,
    DocumentUploadSessionRequest,
    ExtractedMetricOut,
    TransactionOut,
)
from app.services.pipeline import run_document_pipeline
from app.services.storage_service import (
    delete_object,
    create_signed_upload_url,
    document_object_key,
    read_object,
    save_object,
    StorageServiceError,
    temporary_file,
    uses_remote_storage,
)

router = APIRouter(prefix="/api/documents", tags=["Documents"])
ALLOWED_EXTENSIONS = {".pdf", ".csv", ".xlsx"}
CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _get_user_doc(db: Session, doc_id: int, user_id: int) -> Document:
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == user_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


@router.get("", response_model=List[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    return [DocumentOut.model_validate(d) for d in docs]


@router.post("/upload-session")
def create_upload_session(
    payload: DocumentUploadSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = get_settings()
    filename = Path(payload.filename).name
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed formats: PDF (.pdf), Excel (.xlsx), CSV (.csv).",
        )
    if payload.file_size_bytes > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )

    try:
        remote_storage = uses_remote_storage()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not remote_storage:
        return {"mode": "proxy"}

    stored_name = f"{uuid.uuid4().hex}{ext}"
    object_key = document_object_key(current_user.id, stored_name)
    try:
        upload_url = create_signed_upload_url(object_key)
    except StorageServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    doc = Document(
        user_id=current_user.id,
        original_filename=filename,
        stored_filename=stored_name,
        file_type=ext.lstrip("."),
        file_size_bytes=payload.file_size_bytes,
        currency=current_user.preferred_currency or "PKR",
        processing_status="uploading",
        analysis_status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"mode": "direct", "document_id": doc.id, "upload_url": upload_url}


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = get_settings()
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed formats: PDF (.pdf), Excel (.xlsx), CSV (.csv).",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )

    file_hash = hashlib.sha256(content).hexdigest()
    stored_name = f"{uuid.uuid4().hex}{ext}"
    object_key = document_object_key(current_user.id, stored_name)
    try:
        save_object(object_key, content, CONTENT_TYPES[ext])
    except StorageServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    doc = Document(
        user_id=current_user.id,
        original_filename=Path(file.filename).name[:255],
        stored_filename=stored_name,
        file_type=ext.lstrip("."),
        file_size_bytes=len(content),
        file_hash=file_hash,
        currency=current_user.preferred_currency or "PKR",
        processing_status="pending",
        analysis_status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    with temporary_file(content, ext) as file_path:
        doc = run_document_pipeline(
            db=db,
            doc=doc,
            file_path=file_path,
            default_currency=current_user.preferred_currency or "PKR",
        )
    return DocumentOut.model_validate(doc)


@router.post("/{doc_id}/complete-upload", response_model=DocumentOut)
def complete_document_upload(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _get_user_doc(db, doc_id, current_user.id)
    if doc.processing_status != "uploading":
        raise HTTPException(status_code=409, detail="This document is not awaiting an upload.")

    settings = get_settings()
    object_key = document_object_key(current_user.id, doc.stored_filename)
    try:
        content = read_object(object_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail="Uploaded file was not found in storage.") from exc
    except StorageServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )
    if len(content) != doc.file_size_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file size does not match the selected file.")

    doc.file_size_bytes = len(content)
    doc.file_hash = hashlib.sha256(content).hexdigest()
    db.commit()

    ext = Path(doc.stored_filename).suffix.lower()
    with temporary_file(content, ext) as file_path:
        doc = run_document_pipeline(
            db=db,
            doc=doc,
            file_path=file_path,
            default_currency=current_user.preferred_currency or "PKR",
        )
    return DocumentOut.model_validate(doc)


@router.get("/{doc_id}", response_model=DocumentDetailOut)
def get_document_detail(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _get_user_doc(db, doc_id, current_user.id)
    metrics = (
        db.query(ExtractedMetric)
        .filter(ExtractedMetric.document_id == doc.id)
        .all()
    )
    tx_count = db.query(Transaction).filter(Transaction.document_id == doc.id).count()
    anom_count = db.query(Anomaly).filter(Anomaly.document_id == doc.id).count()

    base = DocumentOut.model_validate(doc).model_dump()
    return DocumentDetailOut(
        **base,
        metrics=[ExtractedMetricOut.model_validate(m) for m in metrics],
        transactions_count=tx_count,
        anomalies_count=anom_count,
        structured_summary=doc.structured_summary or {},
        extracted_tables=doc.extracted_tables or [],
    )


@router.post("/{doc_id}/classify", response_model=DocumentOut)
def classify_document_manually(
    doc_id: int,
    payload: DocumentClassifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _get_user_doc(db, doc_id, current_user.id)
    if payload.reporting_period is not None:
        doc.reporting_period = payload.reporting_period
    if payload.currency is not None:
        doc.currency = payload.currency

    object_key = document_object_key(current_user.id, doc.stored_filename)
    try:
        content = read_object(object_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Stored file not found on server.")

    with temporary_file(content, Path(doc.stored_filename).suffix) as file_path:
        doc = run_document_pipeline(
            db=db,
            doc=doc,
            file_path=file_path,
            default_currency=doc.currency,
            forced_category=payload.document_category,
            forced_scope=payload.document_scope,
        )
    return DocumentOut.model_validate(doc)


@router.get("/{doc_id}/transactions", response_model=List[TransactionOut])
def get_document_transactions(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _get_user_doc(db, doc_id, current_user.id)
    txs = (
        db.query(Transaction)
        .filter(Transaction.document_id == doc.id)
        .order_by(Transaction.id.asc())
        .all()
    )
    return [TransactionOut.model_validate(t) for t in txs]


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _get_user_doc(db, doc_id, current_user.id)
    delete_object(document_object_key(current_user.id, doc.stored_filename))
    db.delete(doc)
    db.commit()
    return None
