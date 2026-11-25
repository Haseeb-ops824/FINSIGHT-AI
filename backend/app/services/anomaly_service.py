from collections import defaultdict
from typing import Any, Dict, List
import numpy as np
from sklearn.ensemble import IsolationForest

from app.models.models import Document, ExtractedMetric, Transaction


def detect_anomalies(
    doc: Document,
    transactions: List[Transaction],
    metrics: List[ExtractedMetric],
) -> List[Dict[str, Any]]:
    """
    Detect unusual financial patterns using rule-based checks, statistical analysis,
    and Isolation Forest. Anomalies are flagged as unusual patterns requiring review,
    not automatically labeled as fraud.
    """
    anomalies: List[Dict[str, Any]] = []
    flagged_tx_ids: set[int] = set()
    currency = doc.currency or "USD"

    if transactions:
        amounts = np.array([abs(t.amount) for t in transactions], dtype=float)
        median_amt = float(np.median(amounts)) if len(amounts) else 0.0
        mean_amt = float(np.mean(amounts)) if len(amounts) else 0.0
        std_amt = float(np.std(amounts)) if len(amounts) else 0.0

        # 1. Statistical & Rule-Based: Unusually large transactions / unusual deposits or withdrawals
        for tx in transactions:
            mag = abs(tx.amount)
            z_score = (mag - mean_amt) / std_amt if std_amt > 1e-6 else 0.0
            ratio_to_median = mag / median_amt if median_amt > 1e-6 else 0.0

            if len(transactions) >= 5 and (z_score >= 2.3 or (ratio_to_median >= 4.0 and mag >= 500)):
                severity = "high" if (z_score >= 3.0 or ratio_to_median >= 6.0) else "medium"
                kind_label = "Deposit" if tx.amount > 0 else "Withdrawal / Expense"
                anomalies.append({
                    "transaction_id": tx.id,
                    "anomaly_type": "unusually_large_transaction",
                    "title": f"Unusual {kind_label} Detected",
                    "metric_or_transaction": f"{tx.description} ({tx.transaction_date or 'N/A'})",
                    "detected_amount": round(mag, 2),
                    "expected_comparison": f"Historical median: {currency} {median_amt:,.2f} (mean: {currency} {mean_amt:,.2f})",
                    "observation": f"This transaction ({currency} {mag:,.2f}) is significantly larger than the document's typical transaction amounts.",
                    "reason": f"Amount is {ratio_to_median:.1f}x the median and {z_score:.2f} standard deviations above the mean.",
                    "severity": severity,
                    "detection_method": "statistical",
                    "source_location": tx.source_location,
                })
                flagged_tx_ids.add(tx.id)

        # 2. Rule-Based: Duplicate transactions (same date + normalized description + identical amount)
        seen_sig: Dict[tuple, List[Transaction]] = defaultdict(list)
        for tx in transactions:
            sig = (
                (tx.transaction_date or "").strip(),
                " ".join(tx.description.lower().split()),
                round(tx.amount, 2),
            )
            seen_sig[sig].append(tx)

        for sig, group in seen_sig.items():
            if len(group) > 1:
                first = group[0]
                anomalies.append({
                    "transaction_id": group[1].id,
                    "anomaly_type": "duplicate_transaction",
                    "title": "Potential Duplicate Transaction",
                    "metric_or_transaction": f"{first.description} ({first.transaction_date or 'N/A'})",
                    "detected_amount": round(abs(first.amount), 2),
                    "expected_comparison": "Expected 1 occurrence; found " + str(len(group)),
                    "observation": f"{len(group)} identical transactions of {currency} {abs(first.amount):,.2f} for '{first.description}' occurred on {first.transaction_date or 'the same date'}.",
                    "reason": "Identical date, merchant/description, and exact monetary amount appeared multiple times.",
                    "severity": "medium",
                    "detection_method": "rule",
                    "source_location": ", ".join(t.source_location or "" for t in group[:3]),
                })

        # 3. Rule-Based + Statistical: Unexpected transaction frequency per day
        by_date: Dict[str, List[Transaction]] = defaultdict(list)
        for tx in transactions:
            if tx.transaction_date:
                by_date[tx.transaction_date].append(tx)

        if len(by_date) >= 4:
            counts = np.array([len(v) for v in by_date.values()], dtype=float)
            mean_c = float(np.mean(counts))
            std_c = float(np.std(counts))
            for d_str, day_txs in by_date.items():
                if len(day_txs) >= 4 and std_c > 0 and (len(day_txs) - mean_c) / std_c >= 2.0:
                    day_total = sum(abs(t.amount) for t in day_txs)
                    anomalies.append({
                        "transaction_id": None,
                        "anomaly_type": "unexpected_frequency",
                        "title": "Unexpected Daily Transaction Frequency",
                        "metric_or_transaction": f"Date {d_str} ({len(day_txs)} transactions)",
                        "detected_amount": round(day_total, 2),
                        "expected_comparison": f"Average daily frequency: {mean_c:.1f} transactions/day",
                        "observation": f"{len(day_txs)} transactions totaling {currency} {day_total:,.2f} were recorded on {d_str}.",
                        "reason": "Daily transaction count exceeded historical daily average by more than 2 standard deviations.",
                        "severity": "low",
                        "detection_method": "statistical",
                        "source_location": d_str,
                    })

        # 4. Recurring / Category spending spike check
        by_merchant: Dict[str, List[Transaction]] = defaultdict(list)
        for tx in transactions:
            if tx.amount < 0:
                norm_desc = " ".join(tx.description.lower().split()[:3])
                by_merchant[norm_desc].append(tx)

        for merchant, m_txs in by_merchant.items():
            if len(m_txs) >= 3:
                m_amts = [abs(t.amount) for t in m_txs]
                m_med = float(np.median(m_amts))
                for t in m_txs:
                    if m_med > 20 and abs(t.amount) >= m_med * 2.2 and t.id not in flagged_tx_ids:
                        anomalies.append({
                            "transaction_id": t.id,
                            "anomaly_type": "recurring_expense_change",
                            "title": "Significant Change in Recurring Expense",
                            "metric_or_transaction": f"{t.description} ({t.transaction_date or 'N/A'})",
                            "detected_amount": round(abs(t.amount), 2),
                            "expected_comparison": f"Typical recurring amount: {currency} {m_med:,.2f}",
                            "observation": f"Charge of {currency} {abs(t.amount):,.2f} is over 2.2x the usual {currency} {m_med:,.2f} for this merchant.",
                            "reason": "Recurring transaction deviated substantially from its own historical median.",
                            "severity": "medium",
                            "detection_method": "rule",
                            "source_location": t.source_location,
                        })
                        flagged_tx_ids.add(t.id)

        # 5. Machine Learning: Isolation Forest for multivariate transaction outliers
        if len(transactions) >= 10:
            features = np.array([
                [abs(t.amount), np.log1p(abs(t.amount)), 1.0 if t.amount < 0 else 0.0]
                for t in transactions
            ])
            iso = IsolationForest(contamination=0.08, random_state=42)
            preds = iso.fit_predict(features)
            scores = iso.decision_function(features)

            for tx, pred, score in zip(transactions, preds, scores):
                if pred == -1 and tx.id not in flagged_tx_ids:
                    mag = abs(tx.amount)
                    anomalies.append({
                        "transaction_id": tx.id,
                        "anomaly_type": "isolation_forest_outlier",
                        "title": "Multivariate Outlier Pattern (Isolation Forest)",
                        "metric_or_transaction": f"{tx.description} ({tx.transaction_date or 'N/A'})",
                        "detected_amount": round(mag, 2),
                        "expected_comparison": f"Historical median: {currency} {median_amt:,.2f}",
                        "observation": f"Isolation Forest flagged this {currency} {mag:,.2f} entry as statistically atypical compared to overall transaction behavior.",
                        "reason": f"Anomaly score ({score:.3f}) fell in the outlier tail of the multivariate distribution.",
                        "severity": "medium" if mag > median_amt * 2 else "low",
                        "detection_method": "isolation_forest",
                        "source_location": tx.source_location,
                    })
                    flagged_tx_ids.add(tx.id)

    # Also check high-level statement anomalies if corporate metrics present without transactions
    elif metrics:
        m_map = {m.metric_key: m for m in metrics}
        ni = m_map.get("net_income")
        ocf = m_map.get("operating_cash_flow")
        if ni and ocf and ni.value > 0 and ocf.value < 0:
            anomalies.append({
                "transaction_id": None,
                "anomaly_type": "cash_profit_divergence",
                "title": "Cash Flow vs. Profit Divergence",
                "metric_or_transaction": "Operating Cash Flow vs. Net Income",
                "detected_amount": ocf.value,
                "expected_comparison": f"Positive Net Income ({currency} {ni.value:,.2f})",
                "observation": f"Operating cash flow is negative ({currency} {ocf.value:,.2f}) despite positive net income ({currency} {ni.value:,.2f}).",
                "reason": "Divergence between accrual profit and cash generation requires working capital review.",
                "severity": "high",
                "detection_method": "rule",
                "source_location": ocf.source_location,
            })

    return anomalies
