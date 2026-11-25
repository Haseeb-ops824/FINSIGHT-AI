from collections import defaultdict
from typing import Any, Dict, List, Optional

from app.models.models import ExtractedMetric, Transaction


def _metric_map(metrics: List[ExtractedMetric]) -> Dict[str, ExtractedMetric]:
    return {m.metric_key: m for m in metrics}


def _fmt_num(val: float, currency: str = "USD") -> str:
    return f"{currency} {val:,.2f}"


def compute_financial_ratios(
    metrics: List[ExtractedMetric],
    currency: str = "USD",
) -> Dict[str, Any]:
    """
    Programmatically compute standard corporate financial ratios from verified extracted metrics.
    Only calculates a ratio when required inputs exist and denominators are valid (non-zero).
    """
    m = _metric_map(metrics)
    ratios: List[Dict[str, Any]] = []
    limitations: List[str] = []

    def val(key: str) -> Optional[float]:
        return m[key].value if key in m else None

    revenue = val("revenue")
    cogs = val("cost_of_goods_sold")
    gross_profit = val("gross_profit")
    if gross_profit is None and revenue is not None and cogs is not None:
        gross_profit = round(revenue - cogs, 2)

    net_income = val("net_income")
    current_assets = val("current_assets")
    current_liabilities = val("current_liabilities")
    inventory = val("inventory")
    cash = val("cash_and_equivalents")
    receivables = val("accounts_receivable")
    total_assets = val("total_assets")
    total_liabilities = val("total_liabilities")
    equity = val("shareholders_equity")

    # 1. Gross Profit Margin
    if gross_profit is not None and revenue is not None and revenue != 0:
        gpm = round((gross_profit / revenue) * 100.0, 2)
        ratios.append({
            "key": "gross_profit_margin",
            "name": "Gross Profit Margin",
            "value": gpm,
            "formatted": f"{gpm:.2f}%",
            "formula": "(Gross Profit / Revenue) × 100",
            "calculation": f"({_fmt_num(gross_profit, currency)} / {_fmt_num(revenue, currency)}) × 100 = {gpm:.2f}%",
            "interpretation": (
                "Measures the percentage of revenue retained after direct production or service costs. "
                + ("Strong gross margin indicates healthy core unit economics." if gpm >= 40 else
                   "Moderate gross margin; monitor direct cost efficiency." if gpm >= 20 else
                   "Low gross margin leaves limited room for operating overhead.")
            ),
            "status": "healthy" if gpm >= 35 else ("caution" if gpm >= 15 else "warning"),
            "inputs": {"gross_profit": gross_profit, "revenue": revenue},
        })
    else:
        limitations.append("Gross Profit Margin could not be calculated (requires Revenue and Gross Profit or COGS).")

    # 2. Net Profit Margin
    if net_income is not None and revenue is not None and revenue != 0:
        npm = round((net_income / revenue) * 100.0, 2)
        ratios.append({
            "key": "net_profit_margin",
            "name": "Net Profit Margin",
            "value": npm,
            "formatted": f"{npm:.2f}%",
            "formula": "(Net Income / Revenue) × 100",
            "calculation": f"({_fmt_num(net_income, currency)} / {_fmt_num(revenue, currency)}) × 100 = {npm:.2f}%",
            "interpretation": (
                "Shows how much net profit is generated for each unit of revenue after all expenses and taxes. "
                + ("Positive bottom-line profitability." if npm > 0 else "Negative margin indicates a net loss for the period.")
            ),
            "status": "healthy" if npm >= 10 else ("caution" if npm > 0 else "warning"),
            "inputs": {"net_income": net_income, "revenue": revenue},
        })
    else:
        limitations.append("Net Profit Margin could not be calculated (requires Net Income and Revenue).")

    # 3. Current Ratio
    if current_assets is not None and current_liabilities is not None and current_liabilities != 0:
        cr = round(current_assets / current_liabilities, 2)
        ratios.append({
            "key": "current_ratio",
            "name": "Current Ratio",
            "value": cr,
            "formatted": f"{cr:.2f}x",
            "formula": "Current Assets / Current Liabilities",
            "calculation": f"{_fmt_num(current_assets, currency)} / {_fmt_num(current_liabilities, currency)} = {cr:.2f}x",
            "interpretation": (
                "Evaluates short-term liquidity and ability to cover obligations due within 12 months. "
                + ("Comfortable short-term liquidity buffer." if cr >= 1.5 else
                   "Adequate coverage, though liquidity cushion is modest." if cr >= 1.0 else
                   "Current liabilities exceed current assets, indicating potential short-term liquidity pressure.")
            ),
            "status": "healthy" if cr >= 1.5 else ("caution" if cr >= 1.0 else "warning"),
            "inputs": {"current_assets": current_assets, "current_liabilities": current_liabilities},
        })
    else:
        limitations.append("Current Ratio could not be calculated (requires Current Assets and Current Liabilities).")

    # 4. Quick Ratio
    if current_liabilities is not None and current_liabilities != 0 and (
        (current_assets is not None and inventory is not None) or (cash is not None and receivables is not None)
    ):
        if current_assets is not None and inventory is not None:
            quick_assets = round(current_assets - inventory, 2)
            formula = "(Current Assets − Inventory) / Current Liabilities"
            calc_lhs = f"({_fmt_num(current_assets, currency)} − {_fmt_num(inventory, currency)})"
        else:
            quick_assets = round((cash or 0.0) + (receivables or 0.0), 2)
            formula = "(Cash & Equivalents + Accounts Receivable) / Current Liabilities"
            calc_lhs = f"({_fmt_num(cash or 0.0, currency)} + {_fmt_num(receivables or 0.0, currency)})"

        qr = round(quick_assets / current_liabilities, 2)
        ratios.append({
            "key": "quick_ratio",
            "name": "Quick Ratio",
            "value": qr,
            "formatted": f"{qr:.2f}x",
            "formula": formula,
            "calculation": f"{calc_lhs} / {_fmt_num(current_liabilities, currency)} = {qr:.2f}x",
            "interpretation": (
                "Measures immediate liquidity using only highly liquid assets, excluding inventory. "
                + ("Sufficient liquid assets to meet short-term liabilities." if qr >= 1.0 else
                   "Below 1.0x suggests reliance on inventory turnover or new cash inflows for near-term obligations.")
            ),
            "status": "healthy" if qr >= 1.0 else ("caution" if qr >= 0.7 else "warning"),
            "inputs": {"quick_assets": quick_assets, "current_liabilities": current_liabilities},
        })
    else:
        limitations.append("Quick Ratio could not be calculated (requires Current Assets & Inventory, or Cash & Receivables, plus Current Liabilities).")

    # 5. Debt-to-Equity Ratio
    if total_liabilities is not None and equity is not None and equity != 0:
        dte = round(total_liabilities / equity, 2)
        ratios.append({
            "key": "debt_to_equity",
            "name": "Debt-to-Equity Ratio",
            "value": dte,
            "formatted": f"{dte:.2f}x",
            "formula": "Total Liabilities / Shareholders' Equity",
            "calculation": f"{_fmt_num(total_liabilities, currency)} / {_fmt_num(equity, currency)} = {dte:.2f}x",
            "interpretation": (
                "Indicates financial leverage by comparing total liabilities against shareholders' equity. "
                + ("Conservative leverage profile." if dte <= 1.0 else
                   "Moderate leverage; common in capital-intensive industries." if dte <= 2.0 else
                   "Elevated leverage relative to equity base.")
            ),
            "status": "healthy" if dte <= 1.0 else ("caution" if dte <= 2.0 else "warning"),
            "inputs": {"total_liabilities": total_liabilities, "shareholders_equity": equity},
        })
    else:
        limitations.append("Debt-to-Equity Ratio could not be calculated (requires Total Liabilities and Shareholders' Equity).")

    # 6. Return on Assets
    if net_income is not None and total_assets is not None and total_assets != 0:
        roa = round((net_income / total_assets) * 100.0, 2)
        ratios.append({
            "key": "return_on_assets",
            "name": "Return on Assets (ROA)",
            "value": roa,
            "formatted": f"{roa:.2f}%",
            "formula": "(Net Income / Total Assets) × 100",
            "calculation": f"({_fmt_num(net_income, currency)} / {_fmt_num(total_assets, currency)}) × 100 = {roa:.2f}%",
            "interpretation": (
                "Measures how efficiently the organization converts its asset base into net profit. "
                + ("Strong asset efficiency." if roa >= 5.0 else
                   "Positive but modest return on total assets." if roa > 0 else
                   "Negative ROA reflects a net loss relative to total assets.")
            ),
            "status": "healthy" if roa >= 5.0 else ("caution" if roa > 0 else "warning"),
            "inputs": {"net_income": net_income, "total_assets": total_assets},
        })
    else:
        limitations.append("Return on Assets could not be calculated (requires Net Income and Total Assets).")

    return {"ratios": ratios, "limitations": limitations}


def compute_confirmed_insights_and_risks(
    metrics: List[ExtractedMetric],
    transactions: List[Transaction],
    ratios: List[Dict[str, Any]],
    currency: str = "USD",
) -> Dict[str, Any]:
    """
    Generate deterministic, evidence-backed observations and risk indicators strictly from extracted figures.
    """
    m = _metric_map(metrics)
    insights: List[Dict[str, Any]] = []
    risks: List[Dict[str, Any]] = []

    def get_m(k: str) -> Optional[ExtractedMetric]:
        return m.get(k)

    rev = get_m("revenue")
    opex = get_m("operating_expenses")
    ni = get_m("net_income")
    ocf = get_m("operating_cash_flow")
    ca = get_m("current_assets")
    cl = get_m("current_liabilities")
    tl = get_m("total_liabilities")
    ta = get_m("total_assets")
    eq = get_m("shareholders_equity")

    if rev and opex and rev.value > 0:
        pct = round((opex.value / rev.value) * 100.0, 1)
        insights.append({
            "title": "Operating Expense Share of Revenue",
            "observation": f"Operating expenses represent {pct}% of total revenue ({_fmt_num(opex.value, currency)} vs. {_fmt_num(rev.value, currency)}).",
            "evidence": f"Revenue: {_fmt_num(rev.value, currency)} ({rev.source_location}); Operating Expenses: {_fmt_num(opex.value, currency)} ({opex.source_location})",
            "source": opex.source_location or "Income Statement",
            "observation_type": "confirmed_fact",
        })
        if pct >= 70:
            risks.append({
                "title": "High Operating Cost Concentration",
                "severity": "medium",
                "description": f"Operating expenses consume {pct}% of total revenue, which may compress operating margins if revenue slows.",
                "evidence": f"OpEx / Revenue = {pct}%",
                "kind": "confirmed",
            })

    if ni and ocf:
        if ni.value > 0 and ocf.value < 0:
            insights.append({
                "title": "Cash Flow Divergence from Net Income",
                "observation": f"Operating cash flow is negative ({_fmt_num(ocf.value, currency)}) despite positive net income ({_fmt_num(ni.value, currency)}).",
                "evidence": f"Net Income: {_fmt_num(ni.value, currency)} ({ni.source_location}); Operating Cash Flow: {_fmt_num(ocf.value, currency)} ({ocf.source_location})",
                "source": ocf.source_location or "Cash Flow Statement",
                "observation_type": "confirmed_fact",
            })
            risks.append({
                "title": "Negative Operating Cash Flow vs. Profit",
                "severity": "high",
                "description": "Positive accounting profit has not translated into positive operating cash flow, warranting review of working capital or receivables.",
                "evidence": f"Net Income {_fmt_num(ni.value, currency)} vs. Operating Cash Flow {_fmt_num(ocf.value, currency)}",
                "kind": "confirmed",
            })
        elif ocf.value > 0:
            insights.append({
                "title": "Positive Operating Cash Generation",
                "observation": f"Core operations generated {_fmt_num(ocf.value, currency)} in positive operating cash flow.",
                "evidence": f"Source: {ocf.source_location}",
                "source": ocf.source_location or "Cash Flow Statement",
                "observation_type": "confirmed_fact",
            })

    if ni and ni.value < 0:
        risks.append({
            "title": "Net Loss Reported",
            "severity": "high",
            "description": f"The statement reports a net loss of {_fmt_num(abs(ni.value), currency)} for the period.",
            "evidence": f"Net Income: {_fmt_num(ni.value, currency)} ({ni.source_location})",
            "kind": "confirmed",
        })

    if ca and cl and cl.value > 0 and ca.value < cl.value:
        risks.append({
            "title": "Short-Term Liquidity Pressure",
            "severity": "high",
            "description": f"Current liabilities ({_fmt_num(cl.value, currency)}) exceed current assets ({_fmt_num(ca.value, currency)}).",
            "evidence": f"Current Ratio = {round(ca.value / cl.value, 2)}x",
            "kind": "confirmed",
        })

    if tl and eq and eq.value > 0 and (tl.value / eq.value) > 2.0:
        dte = round(tl.value / eq.value, 2)
        risks.append({
            "title": "Elevated Financial Leverage",
            "severity": "medium",
            "description": f"Total liabilities are {dte}x shareholders' equity, indicating significant debt or obligation financing.",
            "evidence": f"Total Liabilities {_fmt_num(tl.value, currency)} / Equity {_fmt_num(eq.value, currency)}",
            "kind": "confirmed",
        })

    if ta and tl:
        insights.append({
            "title": "Balance Sheet Solvency Snapshot",
            "observation": f"Total assets stand at {_fmt_num(ta.value, currency)} against total liabilities of {_fmt_num(tl.value, currency)}.",
            "evidence": f"Assets: {ta.source_location}; Liabilities: {tl.source_location}",
            "source": ta.source_location or "Balance Sheet",
            "observation_type": "confirmed_fact",
        })

    # Personal / Transaction summary insights
    tx_summary: Dict[str, Any] = {}
    if transactions:
        inflows = round(sum(t.amount for t in transactions if t.amount > 0), 2)
        outflows = round(sum(abs(t.amount) for t in transactions if t.amount < 0), 2)
        net_flow = round(inflows - outflows, 2)

        by_cat: Dict[str, float] = defaultdict(float)
        by_month: Dict[str, Dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})

        for t in transactions:
            if t.amount < 0:
                by_cat[t.category] += abs(t.amount)
            month_key = "Unspecified"
            if t.transaction_date and len(t.transaction_date) >= 7:
                # Try YYYY-MM or MM/DD/YYYY
                d = t.transaction_date.strip()
                if len(d) >= 7 and d[4] in {"-", "/"}:
                    month_key = d[:7]
                elif "/" in d:
                    parts = d.split("/")
                    if len(parts) == 3:
                        yr = parts[2][:4]
                        mo = parts[0].zfill(2)
                        month_key = f"{yr}-{mo}"
            if t.amount > 0:
                by_month[month_key]["income"] += t.amount
            else:
                by_month[month_key]["expenses"] += abs(t.amount)

        sorted_cats = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)
        top_cat = sorted_cats[0] if sorted_cats else None

        insights.append({
            "title": "Transaction Cash Flow Summary",
            "observation": f"Across {len(transactions)} transactions, total inflows were {_fmt_num(inflows, currency)} and total outflows were {_fmt_num(outflows, currency)} (net {_fmt_num(net_flow, currency)}).",
            "evidence": f"Computed directly from {len(transactions)} parsed transaction records.",
            "source": "Transaction Table",
            "observation_type": "confirmed_fact",
        })

        if top_cat and outflows > 0:
            share = round((top_cat[1] / outflows) * 100.0, 1)
            insights.append({
                "title": "Largest Expense Category",
                "observation": f"{top_cat[0]} is the largest spending category at {_fmt_num(top_cat[1], currency)} ({share}% of total outflows).",
                "evidence": f"Aggregated across categorized debit transactions.",
                "source": "Transaction Categories",
                "observation_type": "confirmed_fact",
            })
            if share >= 50:
                risks.append({
                    "title": "High Expense Concentration",
                    "severity": "low",
                    "description": f"{top_cat[0]} accounts for {share}% of total recorded outflows.",
                    "evidence": f"{_fmt_num(top_cat[1], currency)} out of {_fmt_num(outflows, currency)}",
                    "kind": "confirmed",
                })

        if outflows > inflows and inflows > 0:
            risks.append({
                "title": "Outflows Exceed Inflows",
                "severity": "medium",
                "description": f"Total outflows ({_fmt_num(outflows, currency)}) exceeded total inflows ({_fmt_num(inflows, currency)}) during the period.",
                "evidence": f"Net cash flow: {_fmt_num(net_flow, currency)}",
                "kind": "confirmed",
            })

        tx_summary = {
            "transaction_count": len(transactions),
            "total_inflows": inflows,
            "total_outflows": outflows,
            "net_cash_flow": net_flow,
            "expense_by_category": [
                {"category": k, "amount": round(v, 2)} for k, v in sorted_cats
            ],
            "monthly_trends": [
                {
                    "period": k,
                    "income": round(v["income"], 2),
                    "expenses": round(v["expenses"], 2),
                    "savings": round(v["income"] - v["expenses"], 2),
                }
                for k, v in sorted(by_month.items())
            ],
        }

    # Build chart_data strictly from existing data
    chart_data: Dict[str, Any] = {}
    if rev or opex or ni:
        chart_data["income_vs_expense"] = [
            item
            for item in [
                {"name": "Revenue", "value": rev.value} if rev else None,
                {"name": "Operating Expenses", "value": opex.value} if opex else None,
                {"name": "Net Income", "value": ni.value} if ni else None,
            ]
            if item is not None
        ]
    if ta or tl or eq:
        chart_data["assets_vs_liabilities"] = [
            item
            for item in [
                {"name": "Total Assets", "value": ta.value} if ta else None,
                {"name": "Total Liabilities", "value": tl.value} if tl else None,
                {"name": "Shareholders' Equity", "value": eq.value} if eq else None,
            ]
            if item is not None
        ]
    cash_flow_bars = []
    for k, lbl in [
        ("operating_cash_flow", "Operating"),
        ("investing_cash_flow", "Investing"),
        ("financing_cash_flow", "Financing"),
        ("net_change_in_cash", "Net Change"),
    ]:
        metric_obj = get_m(k)
        if metric_obj:
            cash_flow_bars.append({"name": lbl, "value": metric_obj.value})
    if cash_flow_bars:
        chart_data["cash_flow"] = cash_flow_bars

    if tx_summary:
        chart_data["personal"] = tx_summary

    return {
        "insights": insights,
        "risk_indicators": risks,
        "chart_data": chart_data,
        "transaction_summary": tx_summary,
    }
