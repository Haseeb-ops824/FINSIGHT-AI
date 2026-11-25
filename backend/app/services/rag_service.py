from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import faiss
import httpx
from sklearn.feature_extraction.text import TfidfVectorizer

from app.core.config import get_settings
from app.models.models import Document, DocumentChunk, ExtractedMetric, Transaction


def _get_openai_embeddings(texts: List[str]) -> Optional[List[List[float]]]:
    settings = get_settings()
    if not settings.LLM_API_KEY or settings.LLM_PROVIDER not in {"openai", "openai_compatible"}:
        return None
    base_url = (settings.LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    try:
        resp = httpx.post(
            f"{base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {settings.LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.EMBEDDING_MODEL or "text-embedding-3-small",
                "input": [t[:6000] for t in texts],
            },
            timeout=25.0,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return [item["embedding"] for item in data["data"]]
    except Exception:
        return None


def build_summary_chunk_text(
    doc: Document,
    metrics: List[ExtractedMetric],
    transactions: List[Transaction],
) -> str:
    lines = [
        f"Document: {doc.original_filename}",
        f"Category: {doc.document_category} ({doc.document_scope})",
        f"Currency: {doc.currency} | Reporting Period: {doc.reporting_period or 'Unspecified'}",
    ]
    if metrics:
        lines.append("Extracted Financial Metrics:")
        for m in metrics:
            lines.append(
                f"- {m.metric_label}: {m.currency} {m.value:,.2f} (Source: {m.source_location})"
            )
    if transactions:
        inflows = sum(t.amount for t in transactions if t.amount > 0)
        outflows = sum(abs(t.amount) for t in transactions if t.amount < 0)
        lines.append(
            f"Transactions Summary: {len(transactions)} transactions | Total Inflows: {doc.currency} {inflows:,.2f} | Total Outflows: {doc.currency} {outflows:,.2f}"
        )
        largest = sorted(transactions, key=lambda t: abs(t.amount), reverse=True)[:10]
        lines.append("Top 10 Largest Transactions:")
        for t in largest:
            lines.append(
                f"- {t.transaction_date or 'N/A'} | {t.description} | {doc.currency} {t.amount:,.2f} | {t.category} ({t.source_location})"
            )
    return "\n".join(lines)


def index_document_chunks(chunks: List[DocumentChunk]) -> None:
    """Compute embeddings when API key is configured and store on chunks."""
    if not chunks:
        return
    texts = [c.content for c in chunks]
    embeddings = _get_openai_embeddings(texts)
    if embeddings and len(embeddings) == len(chunks):
        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding_json = emb


def retrieve_relevant_chunks(
    query: str,
    chunks: List[DocumentChunk],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Retrieve the most relevant document chunks using FAISS similarity search.
    Uses dense API embeddings if stored on chunks, otherwise builds an on-the-fly
    TF-IDF vector space indexed in FAISS IndexFlatIP.
    """
    if not chunks:
        return []

    k = min(top_k, len(chunks))

    # Path 1: Stored API embeddings + query embedding
    if all(c.embedding_json for c in chunks):
        q_embs = _get_openai_embeddings([query])
        if q_embs:
            mat = np.array([c.embedding_json for c in chunks], dtype="float32")
            q_vec = np.array([q_embs[0]], dtype="float32")
            faiss.normalize_L2(mat)
            faiss.normalize_L2(q_vec)
            index = faiss.IndexFlatIP(mat.shape[1])
            index.add(mat)
            scores, indices = index.search(q_vec, k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0:
                    continue
                c = chunks[idx]
                results.append({
                    "source_label": c.source_label,
                    "content": c.content,
                    "snippet": c.content[:280].replace("\n", " "),
                    "score": round(float(score), 4),
                })
            if results:
                return results

    # Path 2: Local TF-IDF + FAISS IndexFlatIP (deterministic, zero external dependency)
    corpus = [c.content for c in chunks]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=4096)
    try:
        doc_mat = vectorizer.fit_transform(corpus).toarray().astype("float32")
        q_mat = vectorizer.transform([query]).toarray().astype("float32")
    except ValueError:
        return [
            {
                "source_label": c.source_label,
                "content": c.content,
                "snippet": c.content[:280].replace("\n", " "),
                "score": 0.0,
            }
            for c in chunks[:k]
        ]

    if doc_mat.shape[1] == 0:
        return []

    faiss.normalize_L2(doc_mat)
    faiss.normalize_L2(q_mat)
    index = faiss.IndexFlatIP(doc_mat.shape[1])
    index.add(doc_mat)
    scores, indices = index.search(q_mat, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        c = chunks[idx]
        results.append({
            "source_label": c.source_label,
            "content": c.content,
            "snippet": c.content[:280].replace("\n", " "),
            "score": round(float(score), 4),
        })
    return results
