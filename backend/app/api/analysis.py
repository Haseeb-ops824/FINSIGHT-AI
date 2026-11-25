import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    AnalysisResult,
    Anomaly,
    ChatMessage,
    Document,
    DocumentChunk,
    ExtractedMetric,
    GeneratedReport,
    Transaction,
    User,
)
from app.schemas.schemas import (
    AnalysisResultOut,
    AnomalyOut,
    ChatMessageOut,
    ChatRequest,
    CompareRequest,
    GeneratedReportOut,
    ReportGenerateRequest,
)
from app.services.ai_service import (
    answer_document_question,
    generate_comparison_explanation,
)
from app.services.rag_service import retrieve_relevant_chunks
from app.services.report_service import generate_excel_report, generate_pdf_report
from app.services.storage_service import read_object, report_object_key, save_object

router = APIRouter(prefix="/api", tags=["Analysis, RAG, Anomalies, Compare & Reports"])


def _require_doc(db: Session, doc_id: int, user_id: int) -> Document:
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == user_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


# --- Analysis ---
@router.get("/analysis/{doc_id}", response_model=AnalysisResultOut)
def get_analysis(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _require_doc(db, doc_id, current_user.id)
    analysis = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.document_id == doc.id)
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not yet available for this document.")
    return AnalysisResultOut.model_validate(analysis)


# --- RAG AI Assistant ---
@router.get("/chat/{doc_id}/history", response_model=List[ChatMessageOut])
def get_chat_history(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _require_doc(db, doc_id, current_user.id)
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.document_id == doc.id, ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    return [ChatMessageOut.model_validate(m) for m in msgs]


@router.post("/chat/{doc_id}", response_model=ChatMessageOut)
def ask_assistant(
    doc_id: int,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _require_doc(db, doc_id, current_user.id)
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == doc.id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )
    metrics = (
        db.query(ExtractedMetric)
        .filter(ExtractedMetric.document_id == doc.id)
        .all()
    )
    prior_msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.document_id == doc.id, ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )

    user_msg = ChatMessage(
        document_id=doc.id,
        user_id=current_user.id,
        role="user",
        content=payload.question.strip(),
        citations=[],
    )
    db.add(user_msg)
    db.flush()

    retrieved = retrieve_relevant_chunks(payload.question, chunks, top_k=5)
    history = [{"role": m.role, "content": m.content} for m in prior_msgs]
    answer_text, citations, _ = answer_document_question(
        doc=doc,
        question=payload.question.strip(),
        retrieved_chunks=retrieved,
        metrics=metrics,
        history=history,
    )

    assistant_msg = ChatMessage(
        document_id=doc.id,
        user_id=current_user.id,
        role="assistant",
        content=answer_text,
        citations=citations,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    return ChatMessageOut.model_validate(assistant_msg)


@router.delete("/chat/{doc_id}/history", status_code=204)
def clear_chat_history(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _require_doc(db, doc_id, current_user.id)
    db.query(ChatMessage).filter(
        ChatMessage.document_id == doc.id,
        ChatMessage.user_id == current_user.id,
    ).delete()
    db.commit()
    return None


# --- Anomalies ---
@router.get("/anomalies", response_model=List[AnomalyOut])
def list_anomalies(
    document_id: Optional[int] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_doc_ids = [
        d.id
        for d in db.query(Document.id).filter(Document.user_id == current_user.id).all()
    ]
    if not user_doc_ids:
        return []

    query = db.query(Anomaly).filter(Anomaly.document_id.in_(user_doc_ids))
    if document_id is not None:
        if document_id not in user_doc_ids:
            raise HTTPException(status_code=404, detail="Document not found")
        query = query.filter(Anomaly.document_id == document_id)
    if severity:
        query = query.filter(Anomaly.severity == severity.lower())

    items = query.order_by(Anomaly.id.desc()).all()
    return [AnomalyOut.model_validate(a) for a in items]


@router.patch("/anomalies/{anomaly_id}/review", response_model=AnomalyOut)
def mark_anomaly_reviewed(
    anomaly_id: int,
    reviewed: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    anom = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
    if not anom:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    _require_doc(db, anom.document_id, current_user.id)
    anom.reviewed = reviewed
    db.commit()
    db.refresh(anom)
    return AnomalyOut.model_validate(anom)


# --- Document Comparison ---
@router.post("/compare")
def compare_documents(
    payload: CompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs: List[Document] = []
    for doc_id in payload.document_ids:
        docs.append(_require_doc(db, doc_id, current_user.id))

    # Validate compatibility: currency, scope, and document category
    currencies = {d.currency for d in docs}
    scopes = {d.document_scope for d in docs}
    categories = {d.document_category for d in docs}

    compatibility_warnings: List[str] = []
    if len(currencies) > 1:
        raise HTTPException(
            status_code=400,
            detail=f"Incompatible currencies selected ({', '.join(currencies)}). Only documents with matching currencies can be compared.",
        )
    if len(scopes) > 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot compare corporate financial statements directly with personal financial documents.",
        )
    if len(categories) > 1 and "annual_report" not in categories:
        compatibility_warnings.append(
            f"Comparing different document categories ({', '.join(categories)}); only overlapping canonical metrics are shown."
        )

    # Order documents chronologically by reporting_period or uploaded_at
    docs_ordered = sorted(docs, key=lambda d: (d.reporting_period or "", d.uploaded_at))
    prev_doc = docs_ordered[0]
    curr_doc = docs_ordered[-1]
    currency = prev_doc.currency

    # Build metric lookup per doc
    doc_metrics: Dict[int, Dict[str, ExtractedMetric]] = {}
    for d in docs_ordered:
        ms = db.query(ExtractedMetric).filter(ExtractedMetric.document_id == d.id).all()
        doc_metrics[d.id] = {m.metric_key: m for m in ms}

    # Include transaction summary totals if personal documents
    for d in docs_ordered:
        summary = (d.structured_summary or {}).get("transaction_summary") or {}
        if summary and not doc_metrics[d.id]:
            synthetic = {}
            for k, lbl in [
                ("total_inflows", "Total Inflows"),
                ("total_outflows", "Total Outflows"),
                ("net_cash_flow", "Net Cash Flow"),
            ]:
                if k in summary:
                    synthetic[k] = ExtractedMetric(
                        metric_key=k,
                        metric_label=lbl,
                        value=float(summary[k]),
                        currency=d.currency,
                    )
            doc_metrics[d.id] = synthetic

    prev_map = doc_metrics[prev_doc.id]
    curr_map = doc_metrics[curr_doc.id]
    shared_keys = [k for k in prev_map.keys() if k in curr_map]

    comparison_rows: List[Dict[str, Any]] = []
    for key in shared_keys:
        p_val = prev_map[key].value
        c_val = curr_map[key].value
        abs_change = round(c_val - p_val, 2)
        pct_change = round(((c_val - p_val) / abs(p_val)) * 100.0, 2) if p_val != 0 else None

        series = [
            {
                "document_id": d.id,
                "label": d.reporting_period or d.original_filename,
                "value": doc_metrics[d.id][key].value if key in doc_metrics[d.id] else None,
            }
            for d in docs_ordered
        ]
        comparison_rows.append({
            "metric_key": key,
            "metric_label": curr_map[key].metric_label,
            "currency": currency,
            "previous_value": p_val,
            "current_value": c_val,
            "absolute_change": abs_change,
            "percent_change": pct_change,
            "series": series,
        })

    docs_summary = [
        {
            "id": d.id,
            "filename": d.original_filename,
            "category": d.document_category,
            "period": d.reporting_period or "Unspecified",
            "currency": d.currency,
        }
        for d in docs_ordered
    ]
    explanation, ai_used = generate_comparison_explanation(docs_summary, comparison_rows)

    return {
        "documents": docs_summary,
        "previous_document": docs_summary[0],
        "current_document": docs_summary[-1],
        "compatibility_warnings": compatibility_warnings,
        "comparison_rows": comparison_rows,
        "explanation": explanation,
        "ai_generated": ai_used,
    }


# --- Reports ---
@router.get("/reports", response_model=List[GeneratedReportOut])
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reports = (
        db.query(GeneratedReport)
        .filter(GeneratedReport.user_id == current_user.id)
        .order_by(GeneratedReport.created_at.desc())
        .all()
    )
    return [GeneratedReportOut.model_validate(r) for r in reports]


@router.post("/reports/generate", response_model=GeneratedReportOut, status_code=201)
def create_report(
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _require_doc(db, payload.document_id, current_user.id)
    metrics = db.query(ExtractedMetric).filter(ExtractedMetric.document_id == doc.id).all()
    transactions = db.query(Transaction).filter(Transaction.document_id == doc.id).all()
    analysis = db.query(AnalysisResult).filter(AnalysisResult.document_id == doc.id).first()
    anomalies = db.query(Anomaly).filter(Anomaly.document_id == doc.id).all()

    ext = payload.report_format.lower()
    stored_filename = f"report_{doc.id}_{uuid.uuid4().hex[:8]}.{ext}"
    with TemporaryDirectory(prefix="finsight-report-") as directory:
        output_path = Path(directory) / stored_filename
        if ext == "pdf":
            generate_pdf_report(output_path, doc, metrics, analysis, anomalies)
        else:
            generate_excel_report(output_path, doc, metrics, transactions, analysis, anomalies)
        save_object(
            report_object_key(current_user.id, stored_filename),
            output_path.read_bytes(),
            "application/pdf"
            if ext == "pdf"
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    title = payload.report_title or f"{doc.original_filename} — Financial Analysis ({ext.upper()})"
    record = GeneratedReport(
        user_id=current_user.id,
        document_id=doc.id,
        report_title=title[:255],
        report_format=ext,
        stored_filename=stored_filename,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return GeneratedReportOut.model_validate(record)


@router.get("/reports/{report_id}/download")
def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rep = (
        db.query(GeneratedReport)
        .filter(GeneratedReport.id == report_id, GeneratedReport.user_id == current_user.id)
        .first()
    )
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        content = read_object(report_object_key(current_user.id, rep.stored_filename))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Generated report file is missing.")

    media_type = (
        "application/pdf"
        if rep.report_format == "pdf"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="FinSight_Report_{rep.id}.{rep.report_format}"'
            )
        },
    )
