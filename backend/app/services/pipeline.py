from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.models import (
    AnalysisResult,
    Anomaly,
    Document,
    DocumentChunk,
    ExtractedMetric,
    Transaction,
)
from app.services.ai_service import generate_executive_summary
from app.services.anomaly_service import detect_anomalies
from app.services.calculator import (
    compute_confirmed_insights_and_risks,
    compute_financial_ratios,
)
from app.services.classifier import classify_document
from app.services.extractor import extract_document
from app.services.rag_service import build_summary_chunk_text, index_document_chunks


def run_document_pipeline(
    db: Session,
    doc: Document,
    file_path: Path,
    default_currency: str = "USD",
    forced_category: str | None = None,
    forced_scope: str | None = None,
) -> Document:
    """
    Execute the modular processing pipeline:
    Extraction -> Classification -> Persistence -> Financial Calculations ->
    AI Interpretation -> Anomaly Detection -> RAG Indexing.
    """
    try:
        doc.processing_status = "extracting"
        db.commit()

        # Clear prior derived artifacts if re-running after manual classification
        db.query(ExtractedMetric).filter(ExtractedMetric.document_id == doc.id).delete()
        db.query(Transaction).filter(Transaction.document_id == doc.id).delete()
        db.query(Anomaly).filter(Anomaly.document_id == doc.id).delete()
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
        db.query(AnalysisResult).filter(AnalysisResult.document_id == doc.id).delete()
        db.commit()

        extracted = extract_document(file_path, doc.file_type, default_currency=default_currency)

        doc.raw_text = extracted.raw_text
        doc.page_count = extracted.page_count
        doc.extraction_method = extracted.extraction_method
        doc.ocr_used = extracted.ocr_used
        doc.warnings = extracted.warnings
        doc.extracted_tables = extracted.tables
        doc.currency = extracted.currency or default_currency
        if extracted.reporting_period and not doc.reporting_period:
            doc.reporting_period = extracted.reporting_period

        metric_keys = {m.metric_key for m in extracted.metrics}
        if forced_category:
            cat = forced_category
            scope = forced_scope or (
                "personal"
                if forced_category in {"bank_statement", "transaction_history", "expense_report"}
                else "corporate"
            )
            conf = 1.0
            needs_user = False
        else:
            cat, scope, conf, needs_user = classify_document(
                text=extracted.raw_text,
                filename=doc.original_filename,
                has_transactions=bool(extracted.transactions),
                metric_keys=metric_keys,
            )

        doc.document_category = cat
        doc.document_scope = scope
        doc.classification_confidence = conf
        doc.needs_user_classification = needs_user

        # Persist metrics
        metric_objs = []
        for m in extracted.metrics:
            obj = ExtractedMetric(
                document_id=doc.id,
                metric_key=m.metric_key,
                metric_label=m.metric_label,
                value=m.value,
                currency=m.currency,
                period=m.period,
                category=m.category,
                source_location=m.source_location,
                source_snippet=m.source_snippet,
                confidence=m.confidence,
            )
            db.add(obj)
            metric_objs.append(obj)

        # Persist transactions
        tx_objs = []
        for t in extracted.transactions:
            obj = Transaction(
                document_id=doc.id,
                transaction_date=t.transaction_date,
                description=t.description,
                debit=t.debit,
                credit=t.credit,
                amount=t.amount,
                running_balance=t.running_balance,
                category=t.category,
                source_location=t.source_location,
            )
            db.add(obj)
            tx_objs.append(obj)

        db.flush()

        # Run financial calculations & insights
        doc.processing_status = "analyzing"
        ratio_out = compute_financial_ratios(metric_objs, currency=doc.currency)
        calc_out = compute_confirmed_insights_and_risks(
            metrics=metric_objs,
            transactions=tx_objs,
            ratios=ratio_out["ratios"],
            currency=doc.currency,
        )

        exec_summary, ai_used, ai_insights = generate_executive_summary(
            doc=doc,
            metrics=metric_objs,
            ratios=ratio_out["ratios"],
            insights=calc_out["insights"],
            risks=calc_out["risk_indicators"],
            transaction_summary=calc_out["transaction_summary"],
        )

        combined_insights = calc_out["insights"] + ai_insights
        limitations = list(ratio_out["limitations"])
        if doc.warnings:
            limitations.extend(doc.warnings)
        if not metric_objs and not tx_objs:
            limitations.append(
                "No standardized financial line items or transaction tables could be automatically parsed from this file."
            )

        doc.structured_summary = {
            "metrics_count": len(metric_objs),
            "transactions_count": len(tx_objs),
            "transaction_summary": calc_out["transaction_summary"],
        }

        analysis = AnalysisResult(
            document_id=doc.id,
            executive_summary=exec_summary,
            ratios=ratio_out["ratios"],
            insights=combined_insights,
            risk_indicators=calc_out["risk_indicators"],
            limitations=limitations,
            chart_data=calc_out["chart_data"],
            ai_generated=ai_used,
        )
        db.add(analysis)

        # Anomaly Detection
        detected_anomalies = detect_anomalies(doc=doc, transactions=tx_objs, metrics=metric_objs)
        for a in detected_anomalies:
            db.add(
                Anomaly(
                    document_id=doc.id,
                    transaction_id=a["transaction_id"],
                    anomaly_type=a["anomaly_type"],
                    title=a["title"],
                    metric_or_transaction=a["metric_or_transaction"],
                    detected_amount=a["detected_amount"],
                    expected_comparison=a["expected_comparison"],
                    reason=a["reason"],
                    observation=a["observation"],
                    severity=a["severity"],
                    detection_method=a["detection_method"],
                    source_location=a["source_location"],
                )
            )

        # RAG Chunks (include summary chunk + document chunks)
        summary_chunk_text = build_summary_chunk_text(doc, metric_objs, tx_objs)
        chunk_objs = [
            DocumentChunk(
                document_id=doc.id,
                chunk_index=0,
                source_label="Extracted Summary & Key Figures",
                content=summary_chunk_text,
            )
        ]
        for ch in extracted.chunks:
            chunk_objs.append(
                DocumentChunk(
                    document_id=doc.id,
                    chunk_index=ch.chunk_index + 1,
                    source_label=ch.source_label,
                    content=ch.content,
                )
            )
        index_document_chunks(chunk_objs)
        for ch_obj in chunk_objs:
            db.add(ch_obj)

        doc.processing_status = "needs_classification" if needs_user else "completed"
        doc.analysis_status = "completed" if (metric_objs or tx_objs) else "partial"
        doc.processed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(doc)
        return doc

    except Exception as exc:
        db.rollback()
        doc.processing_status = "failed"
        doc.analysis_status = "failed"
        doc.error_message = str(exc)
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc
