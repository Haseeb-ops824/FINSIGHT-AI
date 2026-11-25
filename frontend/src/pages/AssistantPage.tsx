import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Send, Trash2, MessageSquare, FileText, ScanLine, BookOpen } from 'lucide-react';
import { apiRequest, ApiError } from '../api/client';
import type { ChatMessage, DocumentItem } from '../types';
import { AlertBanner, Card, EmptyState, LoadingState, formatCategory } from '../components/UI';

const SUGGESTED_QUESTIONS = [
  'What is the total revenue?',
  'What was the net profit?',
  'Explain the company’s financial position in simple language.',
  'What are the biggest expenses?',
  'What percentage of revenue is spent on operating expenses?',
  'What are the major financial risks?',
  'Is cash flow positive?',
];

const LEGACY_FALLBACK_PREFIX = 'LLM API key (`LLM_API_KEY`) is not configured';

function isLegacyFallback(message: ChatMessage): boolean {
  return message.role === 'assistant' && message.content.startsWith(LEGACY_FALLBACK_PREFIX);
}

function displayAssistantContent(message: ChatMessage): string {
  if (!isLegacyFallback(message)) {
    return message.content;
  }

  const metricPattern = /^- \*\*(.*?)\*\*: (.*?) \*\(Source: (.*?)\)\*$/gm;
  const figures: string[] = [];
  let match: RegExpExecArray | null;
  while ((match = metricPattern.exec(message.content)) !== null) {
    figures.push(`${match[1]}: ${match[2]}.\nSource: ${match[3]}.`);
  }

  return figures.length
    ? `Verified figures from the uploaded document:\n${figures.slice(0, 5).join('\n')}`
    : 'I could not find a verified figure in this response. Check the cited document passages below.';
}

export function AssistantPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [selectedId, setSelectedId] = useState<string>(id || '');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<DocumentItem[]>('/documents')
      .then((list) => {
        setDocs(list);
        if (!id && list.length > 0) {
          setSelectedId(String(list[0].id));
        } else if (id) {
          setSelectedId(id);
        } else {
          setLoading(false);
        }
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.detail : 'Failed to load documents');
        setLoading(false);
      });
  }, [id]);

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    apiRequest<ChatMessage[]>(`/chat/${selectedId}/history`)
      .then(setMessages)
      .catch((err) => setError(err instanceof ApiError ? err.detail : 'Failed to load chat'))
      .finally(() => setLoading(false));
  }, [selectedId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const sendQuestion = async (text: string) => {
    if (!selectedId || !text.trim() || sending) return;
    const trimmed = text.trim();
    setQuestion('');
    setSending(true);
    setError(null);

    const optimisticUser: ChatMessage = {
      id: Date.now(),
      document_id: Number(selectedId),
      role: 'user',
      content: trimmed,
      citations: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUser]);

    try {
      const reply = await apiRequest<ChatMessage>(`/chat/${selectedId}`, {
        method: 'POST',
        body: JSON.stringify({ question: trimmed }),
      });
      setMessages((prev) => [...prev, reply]);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to send question');
    } finally {
      setSending(false);
    }
  };

  const handleClear = async () => {
    if (!selectedId) return;
    await apiRequest(`/chat/${selectedId}/history`, { method: 'DELETE' });
    setMessages([]);
  };

  if (docs.length === 0 && !loading) {
    return (
      <EmptyState
        icon={<MessageSquare className="w-8 h-8" />}
        title="Upload a document to start chatting"
        description="The AI Financial Assistant uses RAG retrieval over your uploaded financial statements to provide citation-backed answers."
        action={
          <Link
            to="/upload"
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium"
          >
            Upload Document
          </Link>
        }
      />
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] max-h-[820px] space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            AI Financial Assistant
          </h1>
          <p className="text-sm text-slate-500">
            Ask questions grounded in extracted metrics and FAISS-retrieved document passages.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={selectedId}
            onChange={(e) => {
              setSelectedId(e.target.value);
              navigate(`/assistant/${e.target.value}`);
            }}
            className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm font-medium text-slate-800 max-w-xs"
          >
            {docs.map((d) => (
              <option key={d.id} value={d.id}>
                {d.original_filename} ({formatCategory(d.document_category)})
              </option>
            ))}
          </select>
          {messages.length > 0 && (
            <button
              onClick={handleClear}
              title="Clear conversation"
              className="p-2 rounded-lg border border-slate-300 bg-white text-slate-500 hover:text-rose-600 hover:bg-rose-50"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {error && <AlertBanner variant="error" message={error} />}

      <Card className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {loading ? (
            <LoadingState message="Loading conversation..." />
          ) : messages.length === 0 ? (
            <div className="py-8 max-w-2xl mx-auto text-center space-y-5">
              <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
                <FileText className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-slate-900">
                  Ask anything about the selected document
                </h2>
                <p className="text-sm text-slate-500 mt-1">
                  FinSight AI retrieves relevant pages, tables, and extracted figures and includes
                  source citations with every answer.
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-2">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => sendQuestion(q)}
                    className="px-3 py-1.5 rounded-full border border-slate-200 bg-slate-50 hover:bg-blue-50 hover:border-blue-200 text-xs font-medium text-slate-700 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m) => (
              <div
                key={m.id}
                className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-3xl rounded-xl px-4 py-3 text-sm leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-50 border border-slate-200 text-slate-800'
                  }`}
                >
                  <div className="whitespace-pre-line font-sans text-[15px] leading-7">
                    {displayAssistantContent(m)}
                  </div>
                  {m.role === 'assistant' &&
                    !isLegacyFallback(m) &&
                    m.citations &&
                    m.citations.length > 0 && (
                    <div className="mt-3 pt-2.5 border-t border-slate-200/80 space-y-1.5">
                      <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                        <BookOpen className="w-3.5 h-3.5" />
                        Retrieved Sources
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {m.citations.slice(0, 4).map((c, idx) => (
                          <span
                            key={idx}
                            title={c.snippet}
                            className="inline-flex items-center px-2 py-0.5 rounded bg-white border border-slate-200 text-[11px] text-slate-600"
                          >
                            {c.source_label}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {sending && (
            <div className="flex justify-start">
              <div
                role="status"
                aria-live="polite"
                className="ai-pending flex items-center gap-3 rounded-xl border border-blue-200/80 bg-blue-50/70 px-4 py-3 text-sm text-slate-600"
              >
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-white text-blue-700 shadow-sm">
                  <ScanLine className="h-4 w-4" />
                </span>
                Retrieving document context and generating response...
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <form
          onSubmit={(e: React.FormEvent) => {
            e.preventDefault();
            sendQuestion(question);
          }}
          className="p-4 border-t border-slate-200 bg-white flex items-center gap-3"
        >
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about revenue, expenses, cash flow, or risks..."
            className="flex-1 px-4 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={!question.trim() || sending}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium transition-colors"
          >
            <Send className="w-4 h-4" />
            Send
          </button>
        </form>
      </Card>
    </div>
  );
}
