import io
from pathlib import Path
import sys

import openpyxl
import pytest
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.core.database import Base, engine
from app.main import app


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("finsight_test")
    settings = get_settings()
    settings.UPLOAD_DIR = str(tmp_dir / "uploads")

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as c:
        yield c

    Base.metadata.drop_all(bind=engine)


def _create_corporate_pdf(title: str, rows: list[list[str]]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    tbl = Table([[title, ""]] + rows)
    doc.build([tbl])
    return buf.getvalue()


def _create_xlsx_statement(rows: list[list]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Income Statement"
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_full_end_to_end_pipeline(client: TestClient):
    # 1. Register & Login
    reg_resp = client.post(
        "/api/auth/register",
        json={
            "email": "analyst@example.com",
            "full_name": "Alex Morgan",
            "company_or_role": "Financial Analyst",
            "password": "securepassword123",
            "preferred_currency": "USD",
        },
    )
    assert reg_resp.status_code == 201, reg_resp.text
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify profile endpoint
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "analyst@example.com"

    # 2. Upload Corporate PDF Statement (FY 2024)
    pdf_2024 = _create_corporate_pdf(
        "Consolidated Financial Statements FY 2024 (USD)",
        [
            ["Total Revenue", "$1,000,000"],
            ["Cost of Goods Sold", "$400,000"],
            ["Gross Profit", "$600,000"],
            ["Operating Expenses", "$350,000"],
            ["Operating Income", "$250,000"],
            ["Net Income", "$180,000"],
            ["Current Assets", "$500,000"],
            ["Inventory", "$100,000"],
            ["Total Assets", "$1,200,000"],
            ["Current Liabilities", "$250,000"],
            ["Total Liabilities", "$600,000"],
            ["Shareholders' Equity", "$600,000"],
            ["Operating Cash Flow", "$210,000"],
        ],
    )
    up_pdf = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("acme_fy2024.pdf", pdf_2024, "application/pdf")},
    )
    assert up_pdf.status_code == 201, up_pdf.text
    doc_2024 = up_pdf.json()
    assert doc_2024["processing_status"] == "completed"
    assert doc_2024["currency"] == "USD"
    doc_2024_id = doc_2024["id"]

    # 3. Verify Ratios & Analysis Accuracy
    anal_resp = client.get(f"/api/analysis/{doc_2024_id}", headers=headers)
    assert anal_resp.status_code == 200
    anal = anal_resp.json()
    ratio_map = {r["key"]: r["value"] for r in anal["ratios"]}
    assert ratio_map["gross_profit_margin"] == 60.0
    assert ratio_map["net_profit_margin"] == 18.0
    assert ratio_map["current_ratio"] == 2.0
    assert ratio_map["quick_ratio"] == 1.6
    assert ratio_map["debt_to_equity"] == 1.0
    assert ratio_map["return_on_assets"] == 15.0

    # 4. Upload FY 2025 Excel Statement & Compare Documents
    xlsx_2025 = _create_xlsx_statement([
        ["Line Item", "FY 2025 (USD)"],
        ["Total Revenue", 1200000],
        ["Cost of Goods Sold", 450000],
        ["Gross Profit", 750000],
        ["Operating Expenses", 392000],
        ["Net Income", 225000],
        ["Total Assets", 1400000],
        ["Total Liabilities", 550000],
        ["Shareholders' Equity", 850000],
    ])
    up_xlsx = client.post(
        "/api/documents/upload",
        headers=headers,
        files={
            "file": (
                "acme_fy2025.xlsx",
                xlsx_2025,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert up_xlsx.status_code == 201, up_xlsx.text
    doc_2025_id = up_xlsx.json()["id"]

    cmp_resp = client.post(
        "/api/compare",
        headers=headers,
        json={"document_ids": [doc_2024_id, doc_2025_id]},
    )
    assert cmp_resp.status_code == 200, cmp_resp.text
    cmp_data = cmp_resp.json()
    cmp_rows = {r["metric_key"]: r for r in cmp_data["comparison_rows"]}
    assert cmp_rows["revenue"]["percent_change"] == 20.0
    assert cmp_rows["net_income"]["percent_change"] == 25.0

    # 5. Upload Personal Bank Statement CSV & Verify Anomaly Detection
    csv_lines = [
        "Transaction Date,Description,Debit,Credit,Running Balance",
        "2025-01-02,Payroll Direct Deposit,,4200.00,9200.00",
        "2025-01-03,Whole Foods Market,84.50,,9115.50",
        "2025-01-04,Starbucks Coffee,6.75,,9108.75",
        "2025-01-05,Netflix Subscription,15.99,,9092.76",
        "2025-01-06,City Electric Utility,95.00,,8997.76",
        "2025-01-06,City Electric Utility,95.00,,8902.76",
        "2025-01-07,Shell Gas Station,48.20,,8854.56",
        "2025-01-08,Trader Joe's Grocery,72.10,,8782.46",
        "2025-01-09,Uber Trip,24.50,,8757.96",
        "2025-01-10,Amazon Web Services,32.00,,8725.96",
        "2025-01-11,Local Cafe,11.20,,8714.76",
        "2025-01-12,Unusual Luxury Watch Wire,8500.00,,214.76",
    ]
    up_csv = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("bank_statement_jan2025.csv", "\n".join(csv_lines).encode(), "text/csv")},
    )
    assert up_csv.status_code == 201, up_csv.text
    bank_doc_id = up_csv.json()["id"]

    anom_resp = client.get(f"/api/anomalies?document_id={bank_doc_id}", headers=headers)
    assert anom_resp.status_code == 200
    anomalies = anom_resp.json()
    anom_types = {a["anomaly_type"] for a in anomalies}
    assert "unusually_large_transaction" in anom_types
    assert "duplicate_transaction" in anom_types

    # 6. Test RAG Assistant Q&A
    chat_resp = client.post(
        f"/api/chat/{doc_2024_id}",
        headers=headers,
        json={"question": "What is the total revenue and net income?"},
    )
    assert chat_resp.status_code == 200, chat_resp.text
    chat_msg = chat_resp.json()
    assert len(chat_msg["citations"]) > 0
    assert "1,000,000" in chat_msg["content"]

    # 7. Test PDF and Excel Report Generation & Download
    pdf_rep = client.post(
        "/api/reports/generate",
        headers=headers,
        json={"document_id": doc_2024_id, "report_format": "pdf"},
    )
    assert pdf_rep.status_code == 201, pdf_rep.text
    pdf_id = pdf_rep.json()["id"]
    pdf_dl = client.get(f"/api/reports/{pdf_id}/download", headers=headers)
    assert pdf_dl.status_code == 200
    assert pdf_dl.content.startswith(b"%PDF")

    xlsx_rep = client.post(
        "/api/reports/generate",
        headers=headers,
        json={"document_id": bank_doc_id, "report_format": "xlsx"},
    )
    assert xlsx_rep.status_code == 201, xlsx_rep.text
    xlsx_id = xlsx_rep.json()["id"]
    xlsx_dl = client.get(f"/api/reports/{xlsx_id}/download", headers=headers)
    assert xlsx_dl.status_code == 200
    assert xlsx_dl.content[:2] == b"PK"

    # 8. Dashboard & Security Isolation Check
    dash = client.get("/api/dashboard", headers=headers)
    assert dash.status_code == 200
    assert dash.json()["total_documents"] == 3
    assert dash.json()["total_reports"] == 2

    # Second user cannot access user 1's document
    reg2 = client.post(
        "/api/auth/register",
        json={
            "email": "other@example.com",
            "full_name": "Other User",
            "password": "anotherpassword",
        },
    )
    headers2 = {"Authorization": f"Bearer {reg2.json()['access_token']}"}
    forbidden = client.get(f"/api/documents/{doc_2024_id}", headers=headers2)
    assert forbidden.status_code == 404

    # Delete document cleanly
    del_resp = client.delete(f"/api/documents/{bank_doc_id}", headers=headers)
    assert del_resp.status_code == 204


def test_validation_and_manual_classification(client: TestClient):
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "edgecases@example.com",
            "full_name": "Edge Case Tester",
            "password": "password123",
        },
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Unsupported file extension
    bad_up = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )
    assert bad_up.status_code == 400

    # Ambiguous CSV -> low classification confidence -> manual classify
    ambiguous_csv = b"Item,Amount\nMisc Fee,150\n"
    up_amb = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("misc_sheet.csv", ambiguous_csv, "text/csv")},
    )
    assert up_amb.status_code == 201
    amb_doc = up_amb.json()
    assert amb_doc["needs_user_classification"] is True
    assert amb_doc["processing_status"] == "needs_classification"

    reclass = client.post(
        f"/api/documents/{amb_doc['id']}/classify",
        headers=headers,
        json={"document_category": "expense_report", "document_scope": "personal", "reporting_period": "Q1 2025"},
    )
    assert reclass.status_code == 200
    assert reclass.json()["processing_status"] == "completed"
    assert reclass.json()["document_category"] == "expense_report"

    # Incompatible scope comparison check
    corp_xlsx = _create_xlsx_statement([
        ["Line Item", "FY 2025 (USD)"],
        ["Total Revenue", 500000],
    ])
    up_corp = client.post(
        "/api/documents/upload",
        headers=headers,
        files={
            "file": (
                "corp.xlsx",
                corp_xlsx,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert up_corp.status_code == 201
    bad_cmp = client.post(
        "/api/compare",
        headers=headers,
        json={"document_ids": [amb_doc["id"], up_corp.json()["id"]]},
    )
    assert bad_cmp.status_code == 400

