import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  FileText,
  Download,
  MessageSquare,
  AlertTriangle,
  CheckCircle2,
  Info,
  ShieldAlert,
} from 'lucide-react';
import { apiRequest, ApiError } from '../api/client';
import type { AnalysisResult, DocumentDetail, DocumentItem, TransactionItem } from '../types';
import {
  AlertBanner,
  Card,
  EmptyState,
  LoadingState,
  StatusBadge,
  formatCategory,
  formatCurrency,
} from '../components/UI';

export function DocumentAnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [selectedId, setSelectedId] = useState<string>(id || '');
  const [docDetail, setDocDetail] = useState<DocumentDetail | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [loading, setLoading] = useState(true);
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
    setError(null);
    Promise.all([
      apiRequest<DocumentDetail>(`/documents/${selectedId}`),
      apiRequest<AnalysisResult>(`/analysis/${selectedId}`).catch(() => null),
      apiRequest<TransactionItem[]>(`/documents/${selectedId}/transactions`).catch(() => []),
    ])
      .then(([detail, anal, txs]) => {
        setDocDetail(detail);
        setAnalysis(anal);
        setTransactions(txs || []);
      })
      .catch((err) => setError(err instanceof ApiError ? err.detail : 'Failed to load analysis'))
      .finally(() => setLoading(false));
  }, [selectedId]);

  if (loading) return <LoadingState message="Loading financial analysis report..." />;
  if (error) return <AlertBanner variant="error" message={error} />;

  if (docs.length === 0) {
    return (
      <EmptyState
        icon={<FileText className="w-8 h-8" />}
        title="No analyzed documents yet"
        description="Upload a financial document first to inspect extracted metrics, financial ratios, and AI analysis."
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
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Document Analysis</h1>
          <p className="text-sm text-slate-500 mt-1">
            Structured financial metrics, ratio formulas, verified observations, and risk signals.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedId}
            onChange={(e) => {
              setSelectedId(e.target.value);
              navigate(`/analysis/${e.target.value}`);
            }}
            className="px-3.5 py-2 rounded-lg border border-slate-300 bg-white text-sm font-medium text-slate-800"
          >
            {docs.map((d) => (
              <option key={d.id} value={d.id}>
                {d.original_filename} ({formatCategory(d.document_category)})
              </option>
            ))}
          </select>

          {docDetail && (
            <>
              <Link
                to={`/assistant/${docDetail.id}`}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-sm font-medium text-slate-700"
              >
                <MessageSquare className="w-4 h-4 text-blue-600" />
                Ask AI
              </Link>
              <Link
                to="/reports"
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium"
              >
                <Download className="w-4 h-4" />
                Export Report
              </Link>
            </>
          )}
        </div>
      </div>

      {docDetail && (
        <>
          {docDetail.needs_user_classification && (
            <AlertBanner
              variant="warning"
              title="Document classification needs confirmation"
              message="Automatic classification confidence was low. You can confirm the category on the processing screen."
            />
          )}

          {/* Metadata strip */}
          <Card className="p-4 flex flex-wrap items-center justify-between gap-4 text-sm">
            <div className="flex flex-wrap items-center gap-4">
              <div>
                <span className="text-xs text-slate-500 block">Category</span>
                <span className="font-semibold text-slate-900">
                  {formatCategory(docDetail.document_category)}
                </span>
              </div>
              <div className="h-7 w-px bg-slate-200 hidden sm:block" />
              <div>
                <span className="text-xs text-slate-500 block">Period</span>
                <span className="font-semibold text-slate-900">
                  {docDetail.reporting_period || 'Unspecified'}
                </span>
              </div>
              <div className="h-7 w-px bg-slate-200 hidden sm:block" />
              <div>
                <span className="text-xs text-slate-500 block">Currency</span>
                <span className="font-semibold text-slate-900">{docDetail.currency}</span>
              </div>
              <div className="h-7 w-px bg-slate-200 hidden sm:block" />
              <div>
                <span className="text-xs text-slate-500 block">Extraction</span>
                <span className="font-medium text-slate-700">
                  {docDetail.extraction_method} ({docDetail.page_count} page/sheet)
                </span>
              </div>
            </div>
            <StatusBadge status={docDetail.analysis_status} />
          </Card>

          {/* A. Executive Summary */}
          {analysis && (
            <Card className="p-6 space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold text-slate-900">A. Executive Summary</h2>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium">
                  {analysis.ai_generated ? 'AI-Synthesized Summary' : 'Deterministic Summary'}
                </span>
              </div>
              <div className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
                {analysis.executive_summary}
              </div>
            </Card>
          )}

          {/* B. Key Financial Metrics */}
          <Card className="p-6 space-y-4">
            <h2 className="text-base font-semibold text-slate-900">B. Key Financial Metrics</h2>
            {docDetail.metrics.length === 0 ? (
              <p className="text-sm text-slate-500">
                No standard corporate summary metrics were extracted from this document.
              </p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {docDetail.metrics.map((m) => (
                  <div
                    key={m.id}
                    className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-1"
                  >
                    <p className="text-xs font-medium text-slate-500">{m.metric_label}</p>
                    <p className="text-xl font-bold text-slate-900">
                      {formatCurrency(m.value, m.currency)}
                    </p>
                    <p className="text-[11px] text-slate-500">
                      {m.period || docDetail.reporting_period || 'Period unspecified'} •{' '}
                      {m.source_location || 'Extracted'}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* C. Financial Performance (Ratios) */}
          {analysis && (
            <Card className="p-6 space-y-4">
              <h2 className="text-base font-semibold text-slate-900">
                C. Financial Performance & Ratios
              </h2>
              {analysis.ratios.length === 0 ? (
                <p className="text-sm text-slate-500">
                  Insufficient extracted inputs to compute corporate profitability or liquidity ratios.
                </p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {analysis.ratios.map((r) => (
                    <div
                      key={r.key}
                      className="p-4 rounded-xl border border-slate-200 bg-white space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold text-slate-900">{r.name}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-bold text-blue-700">{r.formatted}</span>
                          <StatusBadge status={r.status} />
                        </div>
                      </div>
                      <div className="text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 font-mono text-slate-700 space-y-1">
                        <div>Formula: {r.formula}</div>
                        <div>Calc: {r.calculation}</div>
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed">{r.interpretation}</p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {/* D & E: Insights & Risk Indicators */}
          {analysis && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="p-6 space-y-4">
                <h2 className="text-base font-semibold text-slate-900">D. Financial Insights</h2>
                {analysis.insights.length === 0 ? (
                  <p className="text-sm text-slate-500">No automated insights generated.</p>
                ) : (
                  <div className="space-y-3">
                    {analysis.insights.map((ins, i) => (
                      <div
                        key={i}
                        className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/60 space-y-1"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-semibold text-slate-900 flex items-center gap-1.5">
                            <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0" />
                            {ins.title}
                          </span>
                          <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-600">
                            {ins.observation_type === 'confirmed_fact' ? 'Confirmed Data' : 'AI Interpretation'}
                          </span>
                        </div>
                        <p className="text-xs text-slate-700">{ins.observation}</p>
                        <p className="text-[11px] text-slate-500">Evidence: {ins.evidence}</p>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              <Card className="p-6 space-y-4">
                <h2 className="text-base font-semibold text-slate-900">E. Risk Indicators</h2>
                {analysis.risk_indicators.length === 0 ? (
                  <div className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg p-3.5">
                    <CheckCircle2 className="w-4 h-4 shrink-0" />
                    No rule-based risk indicators triggered from available figures.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {analysis.risk_indicators.map((rk, i) => (
                      <div
                        key={i}
                        className="p-3.5 rounded-lg border border-slate-200 bg-white space-y-1"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-semibold text-slate-900 flex items-center gap-1.5">
                            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                            {rk.title}
                          </span>
                          <StatusBadge status={rk.severity} />
                        </div>
                        <p className="text-xs text-slate-700">{rk.description}</p>
                        <p className="text-[11px] text-slate-500">
                          {rk.kind === 'confirmed' ? 'Confirmed figure:' : 'Interpretation:'} {rk.evidence}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          )}

          {/* Transactions preview if any */}
          {transactions.length > 0 && (
            <Card className="overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
                <h2 className="text-base font-semibold text-slate-900">
                  Extracted Transactions ({transactions.length})
                </h2>
                <Link
                  to={`/anomalies?documentId=${docDetail.id}`}
                  className="text-xs font-medium text-blue-600 hover:text-blue-700"
                >
                  View Flagged Anomalies
                </Link>
              </div>
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-sm text-left">
                  <thead className="bg-slate-50 text-xs font-medium text-slate-500 uppercase border-b border-slate-200 sticky top-0">
                    <tr>
                      <th className="px-5 py-2.5">Date</th>
                      <th className="px-5 py-2.5">Description</th>
                      <th className="px-5 py-2.5">Category</th>
                      <th className="px-5 py-2.5 text-right">Amount</th>
                      <th className="px-5 py-2.5 text-right">Balance</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {transactions.slice(0, 100).map((t) => (
                      <tr key={t.id} className="hover:bg-slate-50">
                        <td className="px-5 py-2.5 text-slate-500 whitespace-nowrap">
                          {t.transaction_date || '—'}
                        </td>
                        <td className="px-5 py-2.5 text-slate-900">{t.description}</td>
                        <td className="px-5 py-2.5 text-slate-600 text-xs">{t.category}</td>
                        <td
                          className={`px-5 py-2.5 text-right font-medium whitespace-nowrap ${
                            t.amount >= 0 ? 'text-emerald-700' : 'text-slate-900'
                          }`}
                        >
                          {formatCurrency(t.amount, docDetail.currency)}
                        </td>
                        <td className="px-5 py-2.5 text-right text-slate-500 whitespace-nowrap">
                          {t.running_balance !== null && t.running_balance !== undefined
                            ? formatCurrency(t.running_balance, docDetail.currency)
                            : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Limitations & Disclaimer */}
          {analysis && analysis.limitations.length > 0 && (
            <Card className="p-5 bg-slate-50 space-y-2">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                <Info className="w-4 h-4 text-slate-500" />
                Data Limitations & Scope Notes
              </div>
              <ul className="list-disc list-inside text-xs text-slate-600 space-y-1">
                {analysis.limitations.map((lim, i) => (
                  <li key={i}>{lim}</li>
                ))}
              </ul>
              <div className="pt-2 flex items-center gap-2 text-[11px] text-slate-500">
                <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
                <span>
                  Informational analysis only. Not professional financial, investment, tax, or legal
                  advice.
                </span>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
