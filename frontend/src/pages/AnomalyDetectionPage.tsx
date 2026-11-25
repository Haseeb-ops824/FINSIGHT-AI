import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import { apiRequest, ApiError } from '../api/client';
import type { AnomalyItem, DocumentItem } from '../types';
import {
  AlertBanner,
  Card,
  EmptyState,
  LoadingState,
  StatusBadge,
  formatCurrency,
} from '../components/UI';

export function AnomalyDetectionPage() {
  const [searchParams] = useSearchParams();
  const initialDocId = searchParams.get('documentId') || '';

  const [anomalies, setAnomalies] = useState<AnomalyItem[]>([]);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [docFilter, setDocFilter] = useState(initialDocId);
  const [severityFilter, setSeverityFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (docFilter) params.set('document_id', docFilter);
    if (severityFilter) params.set('severity', severityFilter);
    const qs = params.toString() ? `?${params.toString()}` : '';

    Promise.all([
      apiRequest<AnomalyItem[]>(`/anomalies${qs}`),
      apiRequest<DocumentItem[]>('/documents'),
    ])
      .then(([anomList, docList]) => {
        setAnomalies(anomList);
        setDocs(docList);
      })
      .catch((err) => setError(err instanceof ApiError ? err.detail : 'Failed to load anomalies'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [docFilter, severityFilter]);

  const toggleReviewed = async (item: AnomalyItem) => {
    try {
      const updated = await apiRequest<AnomalyItem>(
        `/anomalies/${item.id}/review?reviewed=${!item.reviewed}`,
        { method: 'PATCH' }
      );
      setAnomalies((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to update review state');
    }
  };

  const docMap = Object.fromEntries(docs.map((d) => [d.id, d]));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          Financial Anomaly Detection
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Identifies unusual transaction magnitudes, duplicates, frequency spikes, and multivariate
          outliers using rules, statistical analysis, and Isolation Forest.
        </p>
      </div>

      <AlertBanner
        variant="info"
        message="Important: A flagged anomaly is not automatically fraud. These findings highlight unusual statistical or rule-based patterns that require human review."
      />

      {error && <AlertBanner variant="error" message={error} />}

      <Card className="p-4 flex flex-wrap items-center gap-3">
        <select
          value={docFilter}
          onChange={(e) => setDocFilter(e.target.value)}
          className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm"
        >
          <option value="">All Documents</option>
          {docs.map((d) => (
            <option key={d.id} value={d.id}>
              {d.original_filename}
            </option>
          ))}
        </select>

        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm"
        >
          <option value="">All Severities</option>
          <option value="high">High Priority</option>
          <option value="medium">Medium Priority</option>
          <option value="low">Low Priority</option>
        </select>
      </Card>

      {loading ? (
        <LoadingState message="Scanning anomaly findings..." />
      ) : anomalies.length === 0 ? (
        <EmptyState
          icon={<CheckCircle2 className="w-8 h-8 text-emerald-500" />}
          title="No anomalies found"
          description={
            docs.length === 0
              ? 'Upload a bank statement or transaction history CSV/Excel/PDF to run anomaly detection.'
              : 'No unusual transaction patterns matched the current filters.'
          }
          action={
            docs.length === 0 && (
              <Link
                to="/upload"
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium"
              >
                Upload Statement
              </Link>
            )
          }
        />
      ) : (
        <div className="space-y-4">
          {anomalies.map((a) => {
            const doc = docMap[a.document_id];
            const currency = doc?.currency || 'USD';
            return (
              <Card key={a.id} className="p-5 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={a.severity} />
                      <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
                        {a.detection_method.replace('_', ' ')}
                      </span>
                      {doc && (
                        <span className="text-xs text-slate-500">• {doc.original_filename}</span>
                      )}
                    </div>
                    <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                      {a.title}
                    </h3>
                    <p className="text-sm font-medium text-slate-700">{a.metric_or_transaction}</p>
                  </div>

                  <div className="flex items-center gap-3">
                    {a.detected_amount !== null && a.detected_amount !== undefined && (
                      <div className="text-right">
                        <span className="text-xs text-slate-500 block">Detected Amount</span>
                        <span className="text-lg font-bold text-slate-900">
                          {formatCurrency(a.detected_amount, currency)}
                        </span>
                      </div>
                    )}
                    <button
                      onClick={() => toggleReviewed(a)}
                      className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
                        a.reviewed
                          ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                          : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      {a.reviewed ? 'Reviewed' : 'Mark Reviewed'}
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs bg-slate-50 border border-slate-200 rounded-lg p-3.5">
                  <div>
                    <span className="font-semibold text-slate-700 block mb-0.5">Observation</span>
                    <p className="text-slate-600">{a.observation}</p>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-700 block mb-0.5">
                      Reason & Historical Comparison
                    </span>
                    <p className="text-slate-600">{a.reason}</p>
                    {a.expected_comparison && (
                      <p className="text-slate-500 mt-1 flex items-center gap-1">
                        <Info className="w-3.5 h-3.5 shrink-0" />
                        {a.expected_comparison}
                      </p>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
