from types import SimpleNamespace

from app.services import ai_service


def test_fallback_returns_plain_verified_metric_and_citations(monkeypatch):
    monkeypatch.setattr(ai_service, "is_llm_configured", lambda: False)
    metric = SimpleNamespace(
        metric_label="Total Revenue",
        metric_key="total_revenue",
        currency="USD",
        value=30860.0,
        source_location="Page 1, Table 1, Row 2",
    )
    chunks = [
        {
            "source_label": "Page 4 (Part 2)",
            "content": "A long, irrelevant transaction excerpt.",
            "snippet": "A long, irrelevant transaction excerpt.",
            "score": 0.8,
        }
    ]

    answer, citations, used_llm = ai_service.answer_document_question(
        doc=None,
        question="What is the total revenue?",
        retrieved_chunks=chunks,
        metrics=[metric],
        history=[],
    )

    assert answer == (
        "Verified figures from the uploaded document:\n"
        "Total Revenue: USD 30,860.00.\n"
        "Source: Page 1, Table 1, Row 2."
    )
    assert citations[0]["source_label"] == "Page 1, Table 1, Row 2"
    assert not used_llm
    assert "**" not in answer
    assert "LLM_API_KEY" not in answer
    assert "irrelevant transaction excerpt" not in answer


def test_fallback_does_not_dump_retrieved_excerpt_when_metric_is_missing(monkeypatch):
    monkeypatch.setattr(ai_service, "is_llm_configured", lambda: False)

    answer, citations, used_llm = ai_service.answer_document_question(
        doc=None,
        question="What is the cash balance?",
        retrieved_chunks=[
            {
                "source_label": "Page 3",
                "content": "Long source document content.",
                "snippet": "Long source document content.",
                "score": 0.5,
            }
        ],
        metrics=[],
        history=[],
    )

    assert answer == (
        "I couldn't match a verified figure to that question. "
        "Check the cited document passages below."
    )
    assert citations[0]["source_label"] == "Page 3"
    assert not used_llm
    assert "Long source document content" not in answer
