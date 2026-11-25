import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pymupdf as fitz
import openpyxl
import pandas as pd
import pdfplumber

from app.core.config import get_settings


@dataclass
class ExtractedMetricItem:
    metric_key: str
    metric_label: str
    value: float
    currency: str
    period: Optional[str]
    category: str
    source_location: str
    source_snippet: str
    confidence: float = 0.9


@dataclass
class ExtractedTransactionItem:
    transaction_date: Optional[str]
    description: str
    debit: Optional[float]
    credit: Optional[float]
    amount: float
    running_balance: Optional[float]
    category: str
    source_location: str


@dataclass
class ExtractedChunkItem:
    chunk_index: int
    source_label: str
    content: str


@dataclass
class ExtractionOutput:
    raw_text: str
    page_count: int
    extraction_method: str
    ocr_used: bool
    warnings: List[str] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    metrics: List[ExtractedMetricItem] = field(default_factory=list)
    transactions: List[ExtractedTransactionItem] = field(default_factory=list)
    chunks: List[ExtractedChunkItem] = field(default_factory=list)
    currency: str = "USD"
    reporting_period: Optional[str] = None
    entity_name: Optional[str] = None


# Canonical financial metric mapping: key -> (display label, category, keyword aliases)
METRIC_PATTERNS: List[Tuple[str, str, str, List[str]]] = [
    ("revenue", "Total Revenue", "income_statement", [
        "total revenue", "net revenue", "total sales", "net sales", "revenue", "sales revenue", "operating revenue"
    ]),
    ("cost_of_goods_sold", "Cost of Goods Sold", "income_statement", [
        "cost of goods sold", "cost of revenue", "cost of sales", "cogs"
    ]),
    ("gross_profit", "Gross Profit", "income_statement", [
        "gross profit", "gross income", "gross margin"
    ]),
    ("operating_expenses", "Operating Expenses", "income_statement", [
        "total operating expenses", "operating expenses", "total expenses", "opex", "selling, general and administrative", "sg&a"
    ]),
    ("operating_income", "Operating Income", "income_statement", [
        "operating income", "operating profit", "income from operations", "ebit"
    ]),
    ("net_income", "Net Income", "income_statement", [
        "net income", "net profit", "net earnings", "profit for the period", "profit after tax"
    ]),
    ("cash_and_equivalents", "Cash & Equivalents", "balance_sheet", [
        "cash and cash equivalents", "cash & cash equivalents", "cash and equivalents"
    ]),
    ("accounts_receivable", "Accounts Receivable", "balance_sheet", [
        "accounts receivable", "trade receivables"
    ]),
    ("inventory", "Inventory", "balance_sheet", [
        "inventories", "inventory"
    ]),
    ("current_assets", "Total Current Assets", "balance_sheet", [
        "total current assets", "current assets"
    ]),
    ("non_current_assets", "Non-Current Assets", "balance_sheet", [
        "total non-current assets", "non-current assets", "fixed assets", "property, plant and equipment"
    ]),
    ("total_assets", "Total Assets", "balance_sheet", [
        "total assets"
    ]),
    ("current_liabilities", "Total Current Liabilities", "balance_sheet", [
        "total current liabilities", "current liabilities"
    ]),
    ("total_liabilities", "Total Liabilities", "balance_sheet", [
        "total liabilities"
    ]),
    ("shareholders_equity", "Shareholders' Equity", "balance_sheet", [
        "total shareholders' equity", "total stockholders' equity", "shareholders' equity",
        "stockholders' equity", "total equity", "owners' equity"
    ]),
    ("operating_cash_flow", "Operating Cash Flow", "cash_flow", [
        "net cash provided by operating activities", "net cash from operating activities",
        "operating cash flow", "cash flow from operations"
    ]),
    ("investing_cash_flow", "Investing Cash Flow", "cash_flow", [
        "net cash used in investing activities", "net cash from investing activities",
        "investing cash flow", "cash flow from investing"
    ]),
    ("financing_cash_flow", "Financing Cash Flow", "cash_flow", [
        "net cash used in financing activities", "net cash from financing activities",
        "financing cash flow", "cash flow from financing"
    ]),
    ("net_change_in_cash", "Net Change in Cash", "cash_flow", [
        "net change in cash", "net increase in cash", "net decrease in cash"
    ]),
]


TRANSACTION_CATEGORIES = [
    ("Payroll / Income", ["payroll", "salary", "direct deposit", "dividend", "interest credit", "refund", "stripe payout", "client payment", "wire in"]),
    ("Housing & Rent", ["rent", "mortgage", "lease", "property management", "hoa"]),
    ("Utilities & Telecom", ["electric", "water", "gas", "internet", "comcast", "verizon", "at&t", "utility", "power"]),
    ("Software & Subscriptions", ["aws", "amazon web services", "google cloud", "azure", "saas", "software", "github", "slack", "adobe", "openai", "netflix", "spotify"]),
    ("Travel & Transport", ["uber", "lyft", "airline", "delta", "united", "hotel", "airbnb", "fuel", "shell", "chevron", "parking"]),
    ("Dining & Groceries", ["restaurant", "cafe", "starbucks", "coffee", "grocery", "whole foods", "trader joe", "doordash", "ubereats"]),
    ("Taxes & Fees", ["irs", "tax", "bank fee", "wire fee", "overdraft", "service charge"]),
    ("Transfers", ["transfer", "ach", "zelle", "venmo", "wire transfer"]),
]


def categorize_transaction(description: str, amount: float) -> str:
    desc_lower = description.lower()
    for cat, keywords in TRANSACTION_CATEGORIES:
        if any(kw in desc_lower for kw in keywords):
            return cat
    return "Other Income" if amount > 0 else "Other Expense"


def parse_numeric(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        if pd.isna(raw):
            return None
        return float(raw)

    s = str(raw).strip()
    if not s or s in {"-", "—", "--", "N/A", "n/a", "nil"}:
        return None

    # Accounting negative format: (1,234.56)
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()
    if s.startswith("-"):
        negative = True
        s = s[1:].strip()

    # Remove currency symbols and commas/spaces
    s = re.sub(r"[$€£₹,\s]", "", s)
    # Strip trailing percentage or footnote markers like *
    s = re.sub(r"[*†]$", "", s)

    # Reject pure years like 2024 or 2025 when parsing standalone tokens only if needed elsewhere
    if not re.match(r"^\d+(\.\d+)?$", s):
        return None

    val = float(s)
    return -val if negative else val


def detect_currency_and_period(text: str, default_currency: str = "USD") -> Tuple[str, Optional[str], float]:
    """Detect currency, reporting period, and scale multiplier (e.g. 1000 if 'in thousands')."""
    sample = text[:6000]
    currency = default_currency
    if "EUR" in sample or "€" in sample:
        currency = "EUR"
    elif "GBP" in sample or "£" in sample:
        currency = "GBP"
    elif "INR" in sample or "₹" in sample:
        currency = "INR"
    elif "CAD" in sample:
        currency = "CAD"
    elif "USD" in sample or "$" in sample:
        currency = "USD"

    multiplier = 1.0
    lower = sample.lower()
    if re.search(r"\b(in thousands|\$000s?|000s omitted)\b", lower):
        multiplier = 1000.0
    elif re.search(r"\b(in millions|\$m\b)\b", lower):
        multiplier = 1_000_000.0

    period = None
    period_patterns = [
        r"(FY\s*20\d{2}(?:\s*[-–]\s*20\d{2})?)",
        r"(Q[1-4]\s*20\d{2})",
        r"(Fiscal Year\s+(?:Ended\s+)?[A-Za-z]+\s+\d{1,2},?\s*20\d{2})",
        r"(For the (?:Year|Quarter|Month|Period) Ended\s+[A-Za-z]+\s+\d{1,2},?\s*20\d{2})",
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+20\d{2})",
        r"(20\d{2}-\d{2}-\d{2}\s*(?:to|-|through)\s*20\d{2}-\d{2}-\d{2})",
    ]
    for pat in period_patterns:
        m = re.search(pat, sample, re.IGNORECASE)
        if m:
            period = re.sub(r"\s+", " ", m.group(1)).strip()
            break

    return currency, period, multiplier


def _match_metric_label(label: str) -> Optional[Tuple[str, str, str]]:
    clean = re.sub(r"[^a-z0-9&\s'-]", " ", label.lower())
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean or len(clean) > 90:
        return None
    for key, display_label, cat, aliases in METRIC_PATTERNS:
        for alias in aliases:
            if clean == alias or clean.startswith(alias + " ") or (len(alias) >= 8 and alias in clean):
                return key, display_label, cat
    return None


def _extract_metrics_from_rows(
    rows: List[Tuple[str, List[str]]],
    currency: str,
    period: Optional[str],
    multiplier: float,
) -> List[ExtractedMetricItem]:
    found: Dict[str, ExtractedMetricItem] = {}
    for location, cells in rows:
        if not cells:
            continue
        label_cell = str(cells[0]).strip()
        match = _match_metric_label(label_cell)
        if not match:
            continue
        key, display_label, cat = match
        # Pick the first valid numeric value in remaining cells (typically current period column)
        numeric_val = None
        for cell in cells[1:]:
            parsed = parse_numeric(cell)
            if parsed is not None:
                # Avoid accidentally picking a column header year like 2024 or 2025 if another number exists
                if parsed in {2020.0, 2021.0, 2022.0, 2023.0, 2024.0, 2025.0, 2026.0} and len(cells) > 2:
                    continue
                numeric_val = parsed * multiplier
                break
        if numeric_val is None:
            continue
        if key not in found:
            found[key] = ExtractedMetricItem(
                metric_key=key,
                metric_label=display_label,
                value=round(numeric_val, 2),
                currency=currency,
                period=period,
                category=cat,
                source_location=location,
                source_snippet=" | ".join(str(c) for c in cells[:4]),
                confidence=0.95,
            )
    return list(found.values())


def _extract_metrics_from_text_lines(
    pages: List[Tuple[str, str]],
    currency: str,
    period: Optional[str],
    multiplier: float,
    existing_keys: set[str],
) -> List[ExtractedMetricItem]:
    items: List[ExtractedMetricItem] = []
    seen = set(existing_keys)
    line_regex = re.compile(r"^([A-Za-z][A-Za-z0-9\s,&'/-]{2,65}?)\s{2,}([\(\)\-\$€£₹0-9,\.]+)(?:\s+.*)?$")
    colon_regex = re.compile(r"^([A-Za-z][A-Za-z0-9\s,&'/-]{2,65}?)\s*[:]\s*([\(\)\-\$€£₹0-9,\.]+)(?:\s+.*)?$")

    for page_label, text in pages:
        for line_idx, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            m = colon_regex.match(line) or line_regex.match(line)
            if not m:
                # Fallback: label followed by whitespace and currency/number at end
                parts = re.split(r"\s+(?=[\(\-\$€£₹]?\d[\d,]*\.?\d*\)?$)", line)
                if len(parts) < 2:
                    continue
                label_part, num_part = parts[0], parts[1]
            else:
                label_part, num_part = m.group(1), m.group(2)

            match = _match_metric_label(label_part)
            if not match:
                continue
            key, display_label, cat = match
            if key in seen:
                continue
            val = parse_numeric(num_part)
            if val is None:
                continue
            seen.add(key)
            items.append(
                ExtractedMetricItem(
                    metric_key=key,
                    metric_label=display_label,
                    value=round(val * multiplier, 2),
                    currency=currency,
                    period=period,
                    category=cat,
                    source_location=f"{page_label}, Line {line_idx}",
                    source_snippet=line[:180],
                    confidence=0.85,
                )
            )
    return items


def _extract_transactions_from_dataframe(
    df: pd.DataFrame,
    source_prefix: str,
) -> List[ExtractedTransactionItem]:
    if df.empty or len(df.columns) < 2:
        return []

    cols_lower = {str(c).strip().lower(): c for c in df.columns}

    def find_col(candidates: List[str]) -> Optional[Any]:
        for cand in candidates:
            for cl, orig in cols_lower.items():
                if cand == cl or cand in cl:
                    return orig
        return None

    date_col = find_col(["transaction date", "posting date", "date", "posted"])
    desc_col = find_col(["description", "merchant", "memo", "narrative", "details", "payee", "particulars"])
    debit_col = find_col(["debit", "withdrawal", "outflow", "charge"])
    credit_col = find_col(["credit", "deposit", "inflow"])
    amount_col = find_col(["amount", "transaction amount", "value", "total"])
    balance_col = find_col(["running balance", "balance", "ending balance"])

    if not desc_col and not amount_col and not (debit_col or credit_col):
        return []
    if not amount_col and not debit_col and not credit_col:
        return []

    txs: List[ExtractedTransactionItem] = []
    for idx, row in df.iterrows():
        desc = str(row[desc_col]).strip() if desc_col and not pd.isna(row[desc_col]) else "Transaction"
        if not desc or desc.lower() in {"nan", "none", "total", "opening balance", "closing balance"}:
            continue

        t_date = None
        if date_col and not pd.isna(row[date_col]):
            t_date = str(row[date_col]).strip()[:32]

        debit_val = parse_numeric(row[debit_col]) if debit_col else None
        credit_val = parse_numeric(row[credit_col]) if credit_col else None
        amount_val = parse_numeric(row[amount_col]) if amount_col else None

        if amount_val is None:
            if debit_val is not None and debit_val != 0:
                amount_val = -abs(debit_val)
            elif credit_val is not None and credit_val != 0:
                amount_val = abs(credit_val)
            else:
                continue
        else:
            if debit_val is not None and debit_val > 0 and amount_val > 0 and (credit_val is None or credit_val == 0):
                amount_val = -abs(amount_val)

        if debit_val is None and amount_val < 0:
            debit_val = abs(amount_val)
        if credit_val is None and amount_val > 0:
            credit_val = abs(amount_val)

        bal_val = parse_numeric(row[balance_col]) if balance_col else None
        row_num = int(idx) + 2 if isinstance(idx, int) else idx
        cat = categorize_transaction(desc, amount_val)

        txs.append(
            ExtractedTransactionItem(
                transaction_date=t_date,
                description=desc[:500],
                debit=round(debit_val, 2) if debit_val is not None else None,
                credit=round(credit_val, 2) if credit_val is not None else None,
                amount=round(amount_val, 2),
                running_balance=round(bal_val, 2) if bal_val is not None else None,
                category=cat,
                source_location=f"{source_prefix}, Row {row_num}",
            )
        )
    return txs


def _build_chunks(labeled_blocks: List[Tuple[str, str]], max_chars: int = 1200) -> List[ExtractedChunkItem]:
    chunks: List[ExtractedChunkItem] = []
    idx = 0
    for label, text in labeled_blocks:
        clean = text.strip()
        if not clean:
            continue
        start = 0
        part = 1
        while start < len(clean):
            slice_text = clean[start:start + max_chars].strip()
            if slice_text:
                part_label = label if len(clean) <= max_chars else f"{label} (Part {part})"
                chunks.append(ExtractedChunkItem(chunk_index=idx, source_label=part_label, content=slice_text))
                idx += 1
                part += 1
            start += max_chars - 150 if len(clean) > max_chars else max_chars
    return chunks


def _run_ocr_on_page(page: fitz.Page) -> Tuple[Optional[str], Optional[str]]:
    settings = get_settings()
    try:
        import pytesseract
        from PIL import Image
        import io

        if settings.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img)
        return text, None
    except Exception as exc:
        return None, str(exc)


def extract_document(file_path: Path, file_type: str, default_currency: str = "USD") -> ExtractionOutput:
    """
    Extract text, tables, metrics, transactions, and RAG chunks from PDF, XLSX, or CSV.
    """
    ft = file_type.lower().lstrip(".")
    if ft == "pdf":
        return _extract_pdf(file_path, default_currency)
    if ft == "xlsx":
        return _extract_xlsx(file_path, default_currency)
    if ft == "csv":
        return _extract_csv(file_path, default_currency)
    raise ValueError(f"Unsupported file type: {file_type}")


def _reconstruct_visual_lines(page: fitz.Page) -> str:
    """Reconstruct visual rows from PDF word coordinates so borderless tables stay aligned."""
    words = page.get_text("words") or []
    if not words:
        return page.get_text("text") or ""

    rows: Dict[float, List[Tuple[float, float, str]]] = {}
    for w in words:
        x0, y0, x1, _y1, word = float(w[0]), float(w[1]), float(w[2]), float(w[3]), str(w[4])
        # Snap y0 into 4pt buckets to handle slight baseline variations
        y_bucket = round(y0 / 4.0) * 4.0
        rows.setdefault(y_bucket, []).append((x0, x1, word))

    lines: List[str] = []
    for y_key in sorted(rows.keys()):
        row_words = sorted(rows[y_key], key=lambda item: item[0])
        parts: List[str] = []
        prev_x1: Optional[float] = None
        for x0, x1, word in row_words:
            if prev_x1 is not None:
                gap = x0 - prev_x1
                parts.append("  " if gap > 10.0 else " ")
            parts.append(word)
            prev_x1 = x1
        lines.append("".join(parts))
    return "\n".join(lines)


def _extract_pdf(file_path: Path, default_currency: str) -> ExtractionOutput:
    warnings: List[str] = []
    pages_text: List[Tuple[str, str]] = []
    tables_out: List[Dict[str, Any]] = []
    table_rows_for_metrics: List[Tuple[str, List[str]]] = []
    transactions: List[ExtractedTransactionItem] = []
    ocr_used = False

    doc = fitz.open(str(file_path))
    page_count = len(doc)

    for page_idx in range(page_count):
        page = doc[page_idx]
        page_label = f"Page {page_idx + 1}"
        text = _reconstruct_visual_lines(page)

        if len(text.strip()) < 30:
            ocr_text, ocr_err = _run_ocr_on_page(page)
            if ocr_text and len(ocr_text.strip()) > len(text.strip()):
                text = ocr_text
                ocr_used = True
            elif ocr_err:
                warnings.append(
                    f"{page_label} appears scanned or image-based, and OCR could not run ({ocr_err})."
                )
        pages_text.append((page_label, text))
    doc.close()

    # Extract tables using pdfplumber
    has_tables = False
    try:
        with pdfplumber.open(str(file_path)) as pdf:
            for p_idx, p in enumerate(pdf.pages):
                extracted = p.extract_tables() or []
                for t_idx, tbl in enumerate(extracted):
                    cleaned_rows = [
                        [str(cell).replace("\n", " ").strip() if cell is not None else "" for cell in row]
                        for row in tbl
                        if row and any(cell is not None and str(cell).strip() for cell in row)
                    ]
                    if not cleaned_rows:
                        continue
                    has_tables = True
                    loc = f"Page {p_idx + 1}, Table {t_idx + 1}"
                    headers = cleaned_rows[0]
                    body = cleaned_rows[1:] if len(cleaned_rows) > 1 else []
                    tables_out.append({"location": loc, "headers": headers, "rows": body[:100]})

                    for r_idx, row in enumerate(cleaned_rows, start=1):
                        table_rows_for_metrics.append((f"{loc}, Row {r_idx}", row))

                    if len(cleaned_rows) >= 2 and len(headers) >= 3:
                        try:
                            df_tbl = pd.DataFrame(body, columns=headers)
                            transactions.extend(_extract_transactions_from_dataframe(df_tbl, loc))
                        except Exception:
                            pass
    except Exception as exc:
        warnings.append(f"Table parser notice: {exc}")

    full_text = "\n\n".join(f"--- {lbl} ---\n{txt}" for lbl, txt in pages_text)
    currency, period, multiplier = detect_currency_and_period(full_text, default_currency)

    metrics = _extract_metrics_from_rows(table_rows_for_metrics, currency, period, multiplier)
    metric_keys = {m.metric_key for m in metrics}
    metrics.extend(_extract_metrics_from_text_lines(pages_text, currency, period, multiplier, metric_keys))

    method = "ocr" if ocr_used else ("table_parser" if has_tables else "selectable_text")
    chunks = _build_chunks(pages_text)

    return ExtractionOutput(
        raw_text=full_text,
        page_count=page_count,
        extraction_method=method,
        ocr_used=ocr_used,
        warnings=warnings,
        tables=tables_out,
        metrics=metrics,
        transactions=transactions,
        chunks=chunks,
        currency=currency,
        reporting_period=period,
    )


def _extract_xlsx(file_path: Path, default_currency: str) -> ExtractionOutput:
    wb = openpyxl.load_workbook(str(file_path), data_only=True)
    sheet_names = wb.sheetnames
    warnings: List[str] = []
    labeled_blocks: List[Tuple[str, str]] = []
    tables_out: List[Dict[str, Any]] = []
    table_rows_for_metrics: List[Tuple[str, List[str]]] = []
    transactions: List[ExtractedTransactionItem] = []

    for sname in sheet_names:
        ws = wb[sname]
        rows_data: List[List[str]] = []
        for r_idx, row in enumerate(ws.iter_rows(values_only=False), start=1):
            vals = [str(cell.value).strip() if cell.value is not None else "" for cell in row]
            if any(vals):
                rows_data.append(vals)
                first_col_letter = openpyxl.utils.get_column_letter(2 if len(vals) > 1 else 1)
                loc = f"Sheet '{sname}', Row {r_idx} (Cell {first_col_letter}{r_idx})"
                table_rows_for_metrics.append((loc, vals))

        if rows_data:
            text_block = "\n".join(" | ".join(r) for r in rows_data)
            labeled_blocks.append((f"Sheet '{sname}'", text_block))
            headers = rows_data[0]
            body = rows_data[1:]
            tables_out.append({
                "location": f"Sheet '{sname}'",
                "headers": headers,
                "rows": body[:100],
            })
            if len(rows_data) >= 2:
                try:
                    df_sheet = pd.read_excel(str(file_path), sheet_name=sname)
                    transactions.extend(_extract_transactions_from_dataframe(df_sheet, f"Sheet '{sname}'"))
                except Exception as exc:
                    warnings.append(f"Could not parse transactions on sheet '{sname}': {exc}")

    wb.close()
    full_text = "\n\n".join(f"--- {lbl} ---\n{txt}" for lbl, txt in labeled_blocks)
    currency, period, multiplier = detect_currency_and_period(full_text, default_currency)

    metrics = _extract_metrics_from_rows(table_rows_for_metrics, currency, period, multiplier)
    metric_keys = {m.metric_key for m in metrics}
    metrics.extend(_extract_metrics_from_text_lines(labeled_blocks, currency, period, multiplier, metric_keys))
    chunks = _build_chunks(labeled_blocks)

    return ExtractionOutput(
        raw_text=full_text,
        page_count=max(1, len(sheet_names)),
        extraction_method="openpyxl",
        ocr_used=False,
        warnings=warnings,
        tables=tables_out,
        metrics=metrics,
        transactions=transactions,
        chunks=chunks,
        currency=currency,
        reporting_period=period,
    )


def _extract_csv(file_path: Path, default_currency: str) -> ExtractionOutput:
    warnings: List[str] = []
    df = None
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(str(file_path), encoding=enc)
            break
        except Exception:
            continue

    if df is None:
        raise ValueError("Unable to decode CSV file with UTF-8 or Latin-1 encoding.")

    headers = [str(c) for c in df.columns]
    rows_str = [["" if pd.isna(v) else str(v) for v in row] for row in df.values.tolist()]
    table_rows_for_metrics = [(f"CSV Row {idx + 2}", row) for idx, row in enumerate(rows_str)]

    text_lines = [" | ".join(headers)] + [" | ".join(r) for r in rows_str]
    full_text = "\n".join(text_lines)

    currency, period, multiplier = detect_currency_and_period(full_text, default_currency)
    metrics = _extract_metrics_from_rows(table_rows_for_metrics, currency, period, multiplier)
    transactions = _extract_transactions_from_dataframe(df, "CSV")
    chunks = _build_chunks([("CSV Data", full_text)])

    return ExtractionOutput(
        raw_text=full_text,
        page_count=1,
        extraction_method="pandas_csv",
        ocr_used=False,
        warnings=warnings,
        tables=[{"location": "CSV Table", "headers": headers, "rows": rows_str[:100]}],
        metrics=metrics,
        transactions=transactions,
        chunks=chunks,
        currency=currency,
        reporting_period=period,
    )
