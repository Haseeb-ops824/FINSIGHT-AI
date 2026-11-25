from typing import Tuple


CATEGORY_KEYWORDS = {
    "income_statement": {
        "scope": "corporate",
        "strong": [
            "income statement",
            "statement of operations",
            "profit and loss",
            "profit & loss",
            "p&l",
            "cost of goods sold",
            "cost of revenue",
            "gross profit",
            "operating income",
            "operating expenses",
        ],
        "weak": ["revenue", "net income", "ebitda", "gross margin", "sales"],
    },
    "balance_sheet": {
        "scope": "corporate",
        "strong": [
            "balance sheet",
            "statement of financial position",
            "current assets",
            "non-current assets",
            "current liabilities",
            "shareholders' equity",
            "stockholders' equity",
            "total assets",
            "total liabilities",
        ],
        "weak": ["equity", "retained earnings", "accounts receivable", "accounts payable"],
    },
    "cash_flow_statement": {
        "scope": "corporate",
        "strong": [
            "cash flow statement",
            "statement of cash flows",
            "operating cash flow",
            "cash flows from operating activities",
            "investing activities",
            "financing activities",
            "net change in cash",
        ],
        "weak": ["depreciation", "capital expenditures", "dividends paid", "free cash flow"],
    },
    "annual_report": {
        "scope": "corporate",
        "strong": [
            "annual report",
            "form 10-k",
            "consolidated financial statements",
            "management's discussion and analysis",
            "md&a",
            "independent auditor",
        ],
        "weak": ["fiscal year", "board of directors", "shareholders", "consolidated"],
    },
    "bank_statement": {
        "scope": "personal",
        "strong": [
            "bank statement",
            "account summary",
            "opening balance",
            "beginning balance",
            "ending balance",
            "closing balance",
            "running balance",
            "statement period",
            "account number",
        ],
        "weak": ["deposit", "withdrawal", "debit", "credit", "routing", "checking", "savings"],
    },
    "transaction_history": {
        "scope": "personal",
        "strong": [
            "transaction history",
            "transaction log",
            "transaction date",
            "posting date",
            "merchant",
            "card ending",
        ],
        "weak": ["debit", "credit", "amount", "category", "description", "balance"],
    },
    "expense_report": {
        "scope": "personal",
        "strong": [
            "expense report",
            "reimbursement",
            "expense claim",
            "receipt",
            "expense category",
            "business expense",
        ],
        "weak": ["travel", "meals", "lodging", "mileage", "total expenses", "approved"],
    },
}


def classify_document(
    text: str,
    filename: str,
    has_transactions: bool = False,
    metric_keys: set[str] | None = None,
) -> Tuple[str, str, float, bool]:
    """
    Classify a financial document into one of the supported corporate or personal categories.
    Returns: (category, scope, confidence, needs_user_classification)
    """
    metric_keys = metric_keys or set()
    combined = f"{filename.lower()}\n{text[:15000].lower()}"

    scores: dict[str, float] = {}
    for cat, rules in CATEGORY_KEYWORDS.items():
        score = 0.0
        for kw in rules["strong"]:
            if kw in combined:
                score += 2.5
        for kw in rules["weak"]:
            if kw in combined:
                score += 0.8
        scores[cat] = score

    # Structural boosts from extracted data
    if {"revenue", "gross_profit", "operating_expenses", "net_income"} & metric_keys:
        scores["income_statement"] += 2.0
    if {"total_assets", "total_liabilities", "shareholders_equity"} & metric_keys:
        scores["balance_sheet"] += 2.0
    if {"operating_cash_flow", "investing_cash_flow", "financing_cash_flow"} & metric_keys:
        scores["cash_flow_statement"] += 2.0
    if (
        {"revenue", "total_assets", "operating_cash_flow"} <= metric_keys
        and len(metric_keys) >= 6
    ):
        scores["annual_report"] += 3.0
    if has_transactions:
        scores["bank_statement"] += 1.8
        scores["transaction_history"] += 1.8

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_cat, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0

    if best_score < 2.0:
        return "unknown", "corporate", round(min(best_score / 5.0, 0.35), 2), True

    # Confidence calculation based on absolute signal and margin over runner-up
    margin = best_score - second_score
    raw_conf = min(0.98, 0.35 + (best_score / 12.0) * 0.40 + (margin / 6.0) * 0.25)
    confidence = round(max(0.1, raw_conf), 2)

    scope = CATEGORY_KEYWORDS[best_cat]["scope"]
    needs_user = confidence < 0.55
    return best_cat, scope, confidence, needs_user
