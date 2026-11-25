import json
from typing import Any, Dict, List, Optional, Tuple
import httpx

from app.core.config import get_settings
from app.models.models import Document, ExtractedMetric


def is_llm_configured() -> bool:
    settings = get_settings()
    return bool(settings.LLM_API_KEY and settings.LLM_API_KEY.strip())


def _call_llm(messages: List[Dict[str, str]], temperature: float = 0.2) -> Optional[str]:
    settings = get_settings()
    if not is_llm_configured():
        return None

    provider = settings.LLM_PROVIDER.lower().strip()
    api_key = settings.LLM_API_KEY.strip()
    model = settings.LLM_MODEL.strip()

    try:
        if provider == "gemini":
            # Gemini generateContent REST API
            system_parts = [m["content"] for m in messages if m["role"] == "system"]
            contents = [
                {
                    "role": "user" if m["role"] == "user" else "model",
                    "parts": [{"text": m["content"]}],
                }
                for m in messages
                if m["role"] != "system"
            ]
            payload: Dict[str, Any] = {
                "contents": contents,
                "generationConfig": {"temperature": temperature},
            }
            if system_parts:
                payload["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            resp = httpx.post(url, json=payload, timeout=40.0)
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            return None

        # Default: OpenAI / OpenAI-compatible
        base_url = (settings.LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
            },
            timeout=40.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        return None
    except Exception:
        return None


def generate_executive_summary(
    doc: Document,
    metrics: List[ExtractedMetric],
    ratios: List[Dict[str, Any]],
    insights: List[Dict[str, Any]],
    risks: List[Dict[str, Any]],
    transaction_summary: Dict[str, Any],
) -> Tuple[str, bool, List[Dict[str, Any]]]:
    """
    Generate an executive summary and optional AI interpretive insights.
    Uses the configured LLM when LLM_API_KEY is present; otherwise constructs
    a clear, factual deterministic summary strictly from extracted data.
    """
    facts_context = {
        "filename": doc.original_filename,
        "category": doc.document_category,
        "scope": doc.document_scope,
        "period": doc.reporting_period or "Unspecified",
        "currency": doc.currency,
        "metrics": [
            {
                "label": m.metric_label,
                "value": m.value,
                "source": m.source_location,
            }
            for m in metrics
        ],
        "ratios": [
            {"name": r["name"], "value": r["formatted"], "status": r["status"]}
            for r in ratios
        ],
        "transaction_summary": transaction_summary,
        "confirmed_risks": [r["title"] for r in risks],
    }

    if is_llm_configured():
        prompt = (
            "You are FinSight AI, a cautious financial document analyst. "
            "Write a clear, accessible Executive Summary (3-5 concise paragraphs) for someone without a finance background "
            "explaining: (1) what this document represents, (2) the financial period covered, "
            "(3) the most important extracted financial figures, (4) major observations, and (5) key concerns or missing data.\n"
            "STRICT RULES:\n"
            "- Only cite numbers present in the verified JSON below. Never invent or extrapolate missing figures.\n"
            "- Never allege fraud or financial distress from a single metric.\n"
            "- State that this analysis is informational and not financial, investment, tax, or legal advice.\n\n"
            f"Verified Document Data:\n{json.dumps(facts_context, indent=2)}"
        )
        llm_text = _call_llm([
            {"role": "system", "content": "You produce accurate, jargon-free financial summaries grounded strictly in verified figures."},
            {"role": "user", "content": prompt},
        ])
        if llm_text:
            ai_insight = {
                "title": "AI Executive Interpretation",
                "observation": "Narrative interpretation generated from extracted figures and calculated ratios.",
                "evidence": f"Grounded in {len(metrics)} extracted metrics and {len(ratios)} calculated ratios.",
                "source": "AI Interpretation",
                "observation_type": "ai_interpretation",
            }
            return llm_text.strip(), True, [ai_insight]

    # Deterministic fallback summary strictly from verified extracted facts
    cat_label = doc.document_category.replace("_", " ").title()
    period_str = doc.reporting_period or "an unspecified reporting period"
    parts = [
        f"This {cat_label} ({doc.original_filename}) covers {period_str} with figures reported in {doc.currency}."
    ]

    if metrics:
        top_metrics = ", ".join(
            f"{m.metric_label}: {m.currency} {m.value:,.2f}" for m in metrics[:5]
        )
        parts.append(f"Key extracted financial figures include {top_metrics}.")
    elif transaction_summary:
        parts.append(
            f"The file contains {transaction_summary.get('transaction_count', 0)} parsed transactions with "
            f"total inflows of {doc.currency} {transaction_summary.get('total_inflows', 0):,.2f} and "
            f"total outflows of {doc.currency} {transaction_summary.get('total_outflows', 0):,.2f} "
            f"(net cash flow: {doc.currency} {transaction_summary.get('net_cash_flow', 0):,.2f})."
        )
    else:
        parts.append(
            "No standard financial line items or transaction tables could be automatically extracted from this document."
        )

    if ratios:
        ratio_str = "; ".join(f"{r['name']} is {r['formatted']}" for r in ratios[:4])
        parts.append(f"Programmatic ratio analysis shows: {ratio_str}.")

    if risks:
        risk_str = "; ".join(r["title"] for r in risks[:3])
        parts.append(f"Confirmed areas warranting closer review include: {risk_str}.")
    else:
        parts.append("No major threshold-based risk indicators were triggered by the available figures.")

    parts.append(
        "Note: Configure LLM_API_KEY in backend/.env to enable full natural-language AI prose. "
        "All figures above are deterministically extracted and informational only (not financial, tax, or legal advice)."
    )
    return "\n\n".join(parts), False, []


def answer_document_question(
    doc: Document,
    question: str,
    retrieved_chunks: List[Dict[str, Any]],
    metrics: List[ExtractedMetric],
    history: List[Dict[str, str]],
) -> Tuple[str, List[Dict[str, Any]], bool]:
    """
    Answer a user question using RAG context + verified extracted metrics.
    Returns: (answer_text, citations, used_llm)
    """
    citations = [
        {
            "source_label": ch["source_label"],
            "snippet": ch["snippet"],
            "score": ch["score"],
        }
        for ch in retrieved_chunks
    ]

    metrics_text = "\n".join(
        f"- {m.metric_label}: {m.currency} {m.value:,.2f} (Source: {m.source_location})"
        for m in metrics
    ) or "None extracted."

    context_blocks = "\n\n".join(
        f"[{ch['source_label']}]\n{ch['content']}" for ch in retrieved_chunks
    ) or "No matching document excerpts found."

    if is_llm_configured():
        system_prompt = (
            "You are FinSight AI Financial Assistant. Answer questions strictly using the provided document context and verified metrics.\n"
            "Rules:\n"
            "1. Provide the direct answer, supporting financial figures, source page/table/sheet citation, and a brief explanation.\n"
            "2. If the requested information is NOT present in the context or metrics, explicitly state that it is unavailable in the uploaded document.\n"
            "3. NEVER invent, guess, or fabricate financial numbers.\n"
            "4. Keep explanations clear, accessible, and concise.\n"
            "5. Use plain text only. Do not use Markdown, backticks, or code blocks."
        )
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for msg in history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        user_prompt = (
            f"Document: {doc.original_filename} ({doc.document_category}, Currency: {doc.currency}, Period: {doc.reporting_period or 'Unspecified'})\n\n"
            f"Verified Extracted Metrics:\n{metrics_text}\n\n"
            f"Retrieved Document Context:\n{context_blocks}\n\n"
            f"User Question: {question}"
        )
        messages.append({"role": "user", "content": user_prompt})
        answer = _call_llm(messages, temperature=0.1)
        if answer:
            return answer.strip(), citations, True

    # Keep the no-LLM response focused on verified figures and the citation chips below.
    q_lower = question.lower()
    matched_metrics = [
        m for m in metrics
        if any(word in m.metric_label.lower() or word in m.metric_key.replace("_", " ") for word in q_lower.split() if len(word) >= 3)
    ]

    if matched_metrics:
        lines = ["Verified figures from the uploaded document:"]
        metric_citations = []
        for metric in matched_metrics[:5]:
            lines.append(f"{metric.metric_label}: {metric.currency} {metric.value:,.2f}.")
            if metric.source_location:
                lines.append(f"Source: {metric.source_location}.")
                metric_citations.append(
                    {
                        "source_label": metric.source_location,
                        "snippet": f"{metric.metric_label}: {metric.currency} {metric.value:,.2f}",
                        "score": 1.0,
                    }
                )
        return "\n".join(lines), metric_citations or citations, False

    if retrieved_chunks:
        return (
            "I couldn't match a verified figure to that question. Check the cited document passages below.",
            citations,
            False,
        )

    return (
        "I couldn't find a verified figure or relevant passage for that question in the uploaded document.",
        citations,
        False,
    )


def generate_comparison_explanation(
    docs_summary: List[Dict[str, Any]],
    comparison_rows: List[Dict[str, Any]],
) -> Tuple[str, bool]:
    if not comparison_rows:
        return (
            "No overlapping compatible metrics were found across the selected documents to compare.",
            False,
        )

    if is_llm_configured():
        prompt = (
            "Explain the key changes between these financial documents based strictly on the comparison table below. "
            "Highlight notable increases or decreases and their financial implications without assuming unsupported external causes.\n\n"
            f"Documents: {json.dumps(docs_summary)}\n"
            f"Comparison Table: {json.dumps(comparison_rows, indent=2)}"
        )
        ans = _call_llm([
            {"role": "system", "content": "You explain period-over-period financial changes strictly from verified comparison numbers."},
            {"role": "user", "content": prompt},
        ])
        if ans:
            return ans.strip(), True

    bullets = []
    for row in comparison_rows:
        pct = row.get("percent_change")
        pct_str = f"{pct:+.2f}%" if pct is not None else "N/A"
        bullets.append(
            f"- {row['metric_label']}: changed by {row['currency']} {row['absolute_change']:+,.2f} ({pct_str}) "
            f"from {row['currency']} {row['previous_value']:,.2f} to {row['currency']} {row['current_value']:,.2f}."
        )
    text = (
        "Key observed period-over-period changes based on extracted figures:\n\n"
        + "\n".join(bullets)
        + "\n\nNote: These comparisons reflect extracted statement figures only without assuming external causes."
    )
    return text, False
