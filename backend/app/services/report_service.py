from pathlib import Path
from typing import List, Optional

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.models import AnalysisResult, Anomaly, Document, ExtractedMetric, Transaction


def generate_pdf_report(
    output_path: Path,
    doc: Document,
    metrics: List[ExtractedMetric],
    analysis: Optional[AnalysisResult],
    anomalies: List[Anomaly],
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FinTitle", parent=styles["Heading1"], fontSize=18, textColor=colors.HexColor("#0f172a"), spaceAfter=6
    )
    h2_style = ParagraphStyle(
        "FinH2", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#1e3a8a"), spaceBefore=14, spaceAfter=6
    )
    body_style = ParagraphStyle(
        "FinBody", parent=styles["Normal"], fontSize=9.5, leading=14, textColor=colors.HexColor("#334155"), spaceAfter=6
    )
    small_style = ParagraphStyle(
        "FinSmall", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#64748b")
    )

    story = []

    # 1. Document Information
    story.append(Paragraph("FinSight AI — Financial Analysis Report", title_style))
    story.append(Paragraph(f"Document: <b>{doc.original_filename}</b>", body_style))
    meta_rows = [
        ["Document Category", doc.document_category.replace("_", " ").title(), "Scope", doc.document_scope.title()],
        ["Reporting Period", doc.reporting_period or "Unspecified", "Currency", doc.currency],
        ["Extraction Method", doc.extraction_method or "Standard", "Pages / Sheets", str(doc.page_count)],
    ]
    meta_table = Table(meta_rows, colWidths=[1.4 * inch, 2.1 * inch, 1.3 * inch, 2.2 * inch])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # 2. Executive Summary
    story.append(Paragraph("2. Executive Summary", h2_style))
    summary_text = (analysis.executive_summary if analysis else "No executive summary generated.")
    for para in summary_text.split("\n\n"):
        if para.strip():
            story.append(Paragraph(para.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), body_style))

    # 3. Extracted Financial Metrics
    story.append(Paragraph("3. Extracted Financial Metrics", h2_style))
    if metrics:
        m_rows = [["Metric", "Value", "Period", "Source Location"]]
        for m in metrics:
            m_rows.append([
                m.metric_label,
                f"{m.currency} {m.value:,.2f}",
                m.period or doc.reporting_period or "—",
                (m.source_location or "—")[:45],
            ])
        m_table = Table(m_rows, colWidths=[2.1 * inch, 1.5 * inch, 1.3 * inch, 2.1 * inch])
        m_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(m_table)
    else:
        story.append(Paragraph("No corporate summary line items were extracted from this file.", body_style))

    # 4. Financial Ratio Analysis
    story.append(Paragraph("4. Financial Ratio Analysis", h2_style))
    ratios = analysis.ratios if analysis and analysis.ratios else []
    if ratios:
        r_rows = [["Ratio", "Result", "Formula & Calculation", "Status"]]
        for r in ratios:
            r_rows.append([
                r["name"],
                r["formatted"],
                r["calculation"][:60],
                r["status"].title(),
            ])
        r_table = Table(r_rows, colWidths=[1.6 * inch, 0.9 * inch, 3.5 * inch, 1.0 * inch])
        r_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(r_table)
    else:
        story.append(Paragraph("Insufficient ratio inputs available in this document.", body_style))

    # 5. Important Financial Insights & Risk Indicators
    story.append(Paragraph("5. Key Insights & Risk Indicators", h2_style))
    insights = analysis.insights if analysis and analysis.insights else []
    for ins in insights:
        story.append(Paragraph(f"• <b>{ins.get('title')}:</b> {ins.get('observation')}", body_style))
    risks = analysis.risk_indicators if analysis and analysis.risk_indicators else []
    for rk in risks:
        story.append(Paragraph(
            f"• <b>[Risk - {rk.get('severity', 'medium').upper()}] {rk.get('title')}:</b> {rk.get('description')}",
            body_style,
        ))
    if not insights and not risks:
        story.append(Paragraph("No additional rule-based insights or risk indicators recorded.", body_style))

    # 6. Detected Anomalies
    story.append(Paragraph("6. Detected Anomalies", h2_style))
    if anomalies:
        a_rows = [["Severity", "Title", "Item", "Amount", "Method"]]
        for a in anomalies[:20]:
            amt_str = f"{doc.currency} {a.detected_amount:,.2f}" if a.detected_amount is not None else "—"
            a_rows.append([
                a.severity.upper(),
                a.title[:28],
                a.metric_or_transaction[:35],
                amt_str,
                a.detection_method,
            ])
        a_table = Table(a_rows, colWidths=[0.8 * inch, 1.7 * inch, 2.2 * inch, 1.1 * inch, 1.2 * inch])
        a_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#991b1b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(a_table)
    else:
        story.append(Paragraph("No unusual patterns or statistical anomalies were flagged.", body_style))

    # 7. Chart / Summary Data Snapshot
    story.append(Paragraph("7. Visualization Data Summary", h2_style))
    chart_data = analysis.chart_data if analysis and analysis.chart_data else {}
    if chart_data.get("personal"):
        ps = chart_data["personal"]
        story.append(Paragraph(
            f"Transactions: {ps.get('transaction_count', 0)} | Total Inflows: {doc.currency} {ps.get('total_inflows', 0):,.2f} | "
            f"Total Outflows: {doc.currency} {ps.get('total_outflows', 0):,.2f} | Net Cash Flow: {doc.currency} {ps.get('net_cash_flow', 0):,.2f}",
            body_style,
        ))
    elif chart_data:
        story.append(Paragraph("Interactive chart series generated for available statement categories in the web workspace.", body_style))
    else:
        story.append(Paragraph("No chart series generated due to limited numerical series.", body_style))

    # 8. Source References
    story.append(Paragraph("8. Source References", h2_style))
    refs = sorted({m.source_location for m in metrics if m.source_location})
    if refs:
        story.append(Paragraph("Extracted metrics sourced from: " + "; ".join(refs[:15]), body_style))
    else:
        story.append(Paragraph(f"Source file: {doc.original_filename} ({doc.extraction_method or 'standard'})", body_style))

    # 9. Important Limitations & Disclaimer
    story.append(Paragraph("9. Important Limitations & Disclaimer", h2_style))
    lims = analysis.limitations if analysis and analysis.limitations else []
    for lim in lims:
        story.append(Paragraph(f"• {lim}", small_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Disclaimer: This report is generated for informational and educational purposes only. "
        "It does not constitute professional financial, investment, tax, or legal advice. "
        "Flagged anomalies indicate statistical or rule-based patterns requiring review, not fraud.",
        small_style,
    ))

    pdf.build(story)
    return output_path


def generate_excel_report(
    output_path: Path,
    doc: Document,
    metrics: List[ExtractedMetric],
    transactions: List[Transaction],
    analysis: Optional[AnalysisResult],
    anomalies: List[Anomaly],
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()

    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    def style_header(ws, row_idx: int = 1):
        for cell in ws[row_idx]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="left", vertical="center")

    # Sheet 1: Overview & Executive Summary
    ws_over = wb.active
    ws_over.title = "Overview"
    ws_over.append(["Field", "Value"])
    style_header(ws_over)
    ws_over.append(["Document Name", doc.original_filename])
    ws_over.append(["Category", doc.document_category])
    ws_over.append(["Scope", doc.document_scope])
    ws_over.append(["Reporting Period", doc.reporting_period or "Unspecified"])
    ws_over.append(["Currency", doc.currency])
    ws_over.append(["Extraction Method", doc.extraction_method or ""])
    ws_over.append(["Executive Summary", analysis.executive_summary if analysis else ""])
    ws_over.column_dimensions["A"].width = 24
    ws_over.column_dimensions["B"].width = 90

    # Sheet 2: Extracted Metrics
    ws_metrics = wb.create_sheet("Extracted Metrics")
    ws_metrics.append(["Metric Key", "Metric Label", "Value", "Currency", "Period", "Source Location"])
    style_header(ws_metrics)
    for m in metrics:
        ws_metrics.append([m.metric_key, m.metric_label, m.value, m.currency, m.period or "", m.source_location or ""])
    for col in ("A", "B", "C", "D", "E", "F"):
        ws_metrics.column_dimensions[col].width = 24

    # Sheet 3: Financial Ratios
    ws_ratios = wb.create_sheet("Financial Ratios")
    ws_ratios.append(["Ratio Name", "Formatted Value", "Numeric Value", "Status", "Formula", "Calculation", "Interpretation"])
    style_header(ws_ratios)
    if analysis and analysis.ratios:
        for r in analysis.ratios:
            ws_ratios.append([
                r.get("name"),
                r.get("formatted"),
                r.get("value"),
                r.get("status"),
                r.get("formula"),
                r.get("calculation"),
                r.get("interpretation"),
            ])
    for col in ("A", "B", "C", "D", "E", "F", "G"):
        ws_ratios.column_dimensions[col].width = 26

    # Sheet 4: Transactions (if any)
    if transactions:
        ws_tx = wb.create_sheet("Transactions")
        ws_tx.append(["Date", "Description", "Category", "Debit", "Credit", "Signed Amount", "Running Balance", "Source"])
        style_header(ws_tx)
        for t in transactions:
            ws_tx.append([
                t.transaction_date or "",
                t.description,
                t.category,
                t.debit,
                t.credit,
                t.amount,
                t.running_balance,
                t.source_location or "",
            ])
        ws_tx.column_dimensions["B"].width = 40

    # Sheet 5: Anomalies
    ws_anom = wb.create_sheet("Anomalies")
    ws_anom.append(["Severity", "Type", "Title", "Item", "Detected Amount", "Expected Comparison", "Reason", "Method"])
    style_header(ws_anom)
    for a in anomalies:
        ws_anom.append([
            a.severity,
            a.anomaly_type,
            a.title,
            a.metric_or_transaction,
            a.detected_amount,
            a.expected_comparison or "",
            a.reason,
            a.detection_method,
        ])
    ws_anom.column_dimensions["D"].width = 36
    ws_anom.column_dimensions["G"].width = 48

    wb.save(str(output_path))
    return output_path
