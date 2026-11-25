from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Anomaly, Document, ExtractedMetric, GeneratedReport, User
from app.schemas.schemas import DashboardSummaryOut, DocumentOut

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardSummaryOut)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    total_reports = (
        db.query(GeneratedReport)
        .filter(GeneratedReport.user_id == current_user.id)
        .count()
    )
    doc_ids = [d.id for d in docs]
    total_anomalies = (
        db.query(Anomaly).filter(Anomaly.document_id.in_(doc_ids)).count()
        if doc_ids
        else 0
    )

    # Aggregate verified metrics from the user's most recent completed documents without fabricating missing metrics.
    overview_metrics = {}
    target_keys = [
        ("revenue", "Total Revenue"),
        ("operating_expenses", "Total Expenses"),
        ("net_income", "Net Profit"),
        ("total_assets", "Total Assets"),
        ("total_liabilities", "Total Liabilities"),
    ]

    if doc_ids:
        metrics = (
            db.query(ExtractedMetric)
            .filter(ExtractedMetric.document_id.in_(doc_ids))
            .all()
        )
        doc_map = {d.id: d for d in docs}
        # Pick latest document value per canonical key (and note currency/source)
        for key, display_label in target_keys:
            matching = [m for m in metrics if m.metric_key == key]
            if matching:
                # Sort by parent document upload time descending
                matching.sort(key=lambda m: doc_map[m.document_id].uploaded_at, reverse=True)
                latest = matching[0]
                overview_metrics[key] = {
                    "label": display_label,
                    "value": latest.value,
                    "currency": latest.currency,
                    "period": latest.period or doc_map[latest.document_id].reporting_period,
                    "document_id": latest.document_id,
                    "document_name": doc_map[latest.document_id].original_filename,
                }

    recent_activity = []
    for doc in docs[:8]:
        recent_activity.append(
            {
                "id": f"doc-{doc.id}",
                "type": "document",
                "title": f"Uploaded {doc.original_filename}",
                "status": doc.processing_status,
                "category": doc.document_category,
                "timestamp": doc.uploaded_at.isoformat(),
                "document_id": doc.id,
            }
        )

    return DashboardSummaryOut(
        total_documents=len(docs),
        total_reports=total_reports,
        total_anomalies=total_anomalies,
        recent_activity_count=len(recent_activity),
        recent_documents=[DocumentOut.model_validate(d) for d in docs[:6]],
        financial_overview=overview_metrics,
        recent_activity=recent_activity,
    )
