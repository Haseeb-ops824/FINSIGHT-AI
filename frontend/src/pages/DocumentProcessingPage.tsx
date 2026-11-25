import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { CheckCircle2, Clock, AlertCircle, ArrowRight, ScanLine } from 'lucide-react';
import { apiRequest, ApiError } from '../api/client';
import type { DocumentDetail } from '../types';
import { AlertBanner, Card, LoadingState, StatusBadge, formatCategory } from '../components/UI';

const CATEGORIES = [
  { value: 'income_statement', label: 'Income Statement (Corporate)', scope: 'corporate' },
  { value: 'balance_sheet', label: 'Balance Sheet (Corporate)', scope: 'corporate' },
  { value: 'cash_flow_statement', label: 'Cash Flow Statement (Corporate)', scope: 'corporate' },
  { value: 'annual_report', label: 'Annual Report (Corporate)', scope: 'corporate' },
  { value: 'bank_statement', label: 'Bank Statement (Personal)', scope: 'personal' },
  { value: 'transaction_history', label: 'Transaction History (Personal)', scope: 'personal' },
  { value: 'expense_report', label: 'Expense Report (Personal)', scope: 'personal' },
];

export function DocumentProcessingPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState('income_statement');
  const [submittingCategory, setSubmittingCategory] = useState(false);

  const loadDoc = () => {
    if (!id) return;
    apiRequest<DocumentDetail>(`/documents/${id}`)
      .then((res) => {
        setDoc(res);
        if (res.document_category && res.document_category !== 'unknown') {
          setSelectedCategory(res.document_category);
        }
      })
      .catch((err) => setError(err instanceof ApiError ? err.detail : 'Failed to load status'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadDoc();
  }, [id]);

  const handleClassify = async () => {
    if (!id) return;
    setSubmittingCategory(true);
    setError(null);
    const chosen = CATEGORIES.find((c) => c.value === selectedCategory);
    try {
      await apiRequest(`/documents/${id}/classify`, {
        method: 'POST',
        body: JSON.stringify({
          document_category: selectedCategory,
          document_scope: chosen?.scope || 'corporate',
        }),
      });
      loadDoc();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Classification failed');
    } finally {
      setSubmittingCategory(false);
    }
  };

  if (loading) return <LoadingState message="Checking document processing status..." />;
  if (error) return <AlertBanner variant="error" message={error} />;
  if (!doc) return null;

  const isDone = doc.processing_status === 'completed';
  const needsClassification =
    doc.needs_user_classification || doc.processing_status === 'needs_classification';
  const activeStepIndex =
    isDone || doc.processing_status === 'failed'
      ? -1
      : needsClassification
        ? 2
        : doc.processing_status === 'extracting'
          ? 1
          : doc.processing_status === 'analyzing'
            ? doc.analysis_status === 'analyzing'
              ? 4
              : 3
            : -1;

  const steps = [
    { label: 'File validated & stored securely', done: true },
    {
      label: doc.ocr_used
        ? `Text & tables extracted (OCR applied, ${doc.page_count} page(s))`
        : `Content extracted (${doc.extraction_method || 'pending'})`,
      done: doc.processing_status !== 'pending',
    },
    {
      label: `Document classified: ${formatCategory(doc.document_category)} (${Math.round(
        doc.classification_confidence * 100
      )}% confidence)`,
      done: !needsClassification && doc.document_category !== 'unknown',
    },
    {
      label: `Structured extraction (${doc.metrics.length} metrics, ${doc.transactions_count} transactions)`,
      done: isDone,
    },
    {
      label: 'Financial ratios, anomaly scan & RAG index ready',
      done: isDone && doc.analysis_status !== 'pending',
    },
  ];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Document Processing</h1>
          <p className="text-sm text-slate-500 mt-1">{doc.original_filename}</p>
        </div>
        <StatusBadge status={doc.processing_status} />
      </div>

      {doc.error_message && <AlertBanner variant="error" title="Processing error" message={doc.error_message} />}

      {doc.warnings?.length > 0 && (
        <AlertBanner variant="warning" title="Extraction notices" message={doc.warnings.join(' ')} />
      )}

      <Card className="p-6 space-y-4">
        <h2 className="text-base font-semibold text-slate-900">Processing Pipeline</h2>
        <div className="space-y-2.5">
          {steps.map((s, idx) => (
            <div
              key={idx}
              className={`processing-step flex items-center gap-3 rounded-xl border border-transparent px-3 py-3 text-sm ${
                activeStepIndex === idx ? 'is-active' : ''
              }`}
            >
              <span className="relative z-10">
                {s.done ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-700 shrink-0" />
                ) : activeStepIndex === idx ? (
                  <ScanLine className="w-5 h-5 text-blue-700 shrink-0 animate-pulse" />
                ) : doc.processing_status === 'failed' && idx === steps.findIndex((step) => !step.done) ? (
                  <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
                ) : (
                  <Clock className="w-5 h-5 text-slate-400 shrink-0" />
                )}
              </span>
              <span className={`relative z-10 flex-1 ${s.done ? 'text-slate-900 font-medium' : activeStepIndex === idx ? 'text-slate-900 font-medium' : 'text-slate-500'}`}>
                {s.label}
              </span>
              {activeStepIndex === idx && (
                <span className="relative z-10 text-[10px] font-semibold uppercase tracking-wider text-blue-700">
                  In progress
                </span>
              )}
            </div>
          ))}
        </div>
      </Card>

      {needsClassification && (
        <Card className="p-6 border-blue-200 bg-blue-50/40 space-y-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Confirm Document Category
            </h2>
            <p className="text-sm text-slate-600 mt-1">
              Automatic classification confidence was low ({Math.round(doc.classification_confidence * 100)}%).
              Please select the document type to complete structured extraction.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="flex-1 px-3.5 py-2.5 rounded-lg border border-slate-300 bg-white text-sm"
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
            <button
              onClick={handleClassify}
              disabled={submittingCategory}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium"
            >
              {submittingCategory && <ScanLine className="w-4 h-4 animate-pulse" />}
              Confirm & Run Analysis
            </button>
          </div>
        </Card>
      )}

      {isDone && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link
            to="/documents"
            className="px-4 py-2.5 rounded-lg border border-slate-300 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Back to Documents
          </Link>
          <button
            onClick={() => navigate(`/analysis/${doc.id}`)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium"
          >
            View Analysis Report
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
