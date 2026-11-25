import { useEffect, useState } from 'react';
import { GitCompare, Loader2 } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { apiRequest, ApiError } from '../api/client';
import type { DocumentItem } from '../types';
import { AlertBanner, Card, EmptyState, LoadingState, formatCategory, formatCurrency } from '../components/UI';

interface ComparisonResult {
  documents: Array<{ id: number; filename: string; category: string; period: string; currency: string }>;
  previous_document: { id: number; filename: string; period: string };
  current_document: { id: number; filename: string; period: string };
  compatibility_warnings: string[];
  comparison_rows: Array<{
    metric_key: string;
    metric_label: string;
    currency: string;
    previous_value: number;
    current_value: number;
    absolute_change: number;
    percent_change: number | null;
  }>;
  explanation: string;
  ai_generated: boolean;
}

export function CompareDocumentsPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<DocumentItem[]>('/documents')
      .then((list) => {
        setDocs(list);
        if (list.length >= 2) {
          setSelectedIds([list[1].id, list[0].id]);
        }
      })
      .catch((err) => setError(err instanceof ApiError ? err.detail : 'Failed to load documents'))
      .finally(() => setLoading(false));
  }, []);

  const toggleDoc = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleCompare = async () => {
    if (selectedIds.length < 2) return;
    setComparing(true);
    setError(null);
    setResult(null);
    try {
      const res = await apiRequest<ComparisonResult>('/compare', {
        method: 'POST',
        body: JSON.stringify({ document_ids: selectedIds }),
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Comparison failed');
    } finally {
      setComparing(false);
    }
  };

  if (loading) return <LoadingState message="Loading documents for comparison..." />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Compare Documents</h1>
        <p className="text-sm text-slate-500 mt-1">
          Select two or more compatible financial statements (same currency and scope) to inspect
          period-over-period changes.
        </p>
      </div>

      {error && <AlertBanner variant="error" message={error} />}

      {docs.length < 2 ? (
        <EmptyState
          icon={<GitCompare className="w-8 h-8" />}
          title="At least two documents required"
          description="Upload two or more compatible financial statements (e.g., 2024 and 2025 income statements or monthly bank statements) to compare them."
        />
      ) : (
        <Card className="p-6 space-y-4">
          <h2 className="text-sm font-semibold text-slate-900">Select Documents to Compare</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {docs.map((d) => {
              const checked = selectedIds.includes(d.id);
              return (
                <label
                  key={d.id}
                  className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-colors ${
                    checked ? 'border-blue-500 bg-blue-50/50' : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleDoc(d.id)}
                    className="mt-1 rounded border-slate-300 text-blue-600"
                  />
                  <div className="min-w-0 text-sm">
                    <p className="font-medium text-slate-900 truncate">{d.original_filename}</p>
                    <p className="text-xs text-slate-500">
                      {formatCategory(d.document_category)} • {d.reporting_period || 'No period'} •{' '}
                      {d.currency}
                    </p>
                  </div>
                </label>
              );
            })}
          </div>
          <div className="flex justify-end">
            <button
              onClick={handleCompare}
              disabled={selectedIds.length < 2 || comparing}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium"
            >
              {comparing && <Loader2 className="w-4 h-4 animate-spin" />}
              Compare Selected ({selectedIds.length})
            </button>
          </div>
        </Card>
      )}

      {result && (
        <div className="space-y-6">
          {result.compatibility_warnings.length > 0 && (
            <AlertBanner
              variant="warning"
              message={result.compatibility_warnings.join(' ')}
            />
          )}

          <Card className="overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200">
              <h2 className="text-base font-semibold text-slate-900">
                Metric Comparison Table ({result.previous_document.period} vs.{' '}
                {result.current_document.period})
              </h2>
            </div>
            {result.comparison_rows.length === 0 ? (
              <div className="p-6 text-sm text-slate-500">
                No overlapping compatible metrics were found across the selected documents.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-slate-50 text-xs font-medium text-slate-500 uppercase border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-3">Financial Metric</th>
                      <th className="px-6 py-3 text-right">
                        Previous ({result.previous_document.period})
                      </th>
                      <th className="px-6 py-3 text-right">
                        Current ({result.current_document.period})
                      </th>
                      <th className="px-6 py-3 text-right">Absolute Change</th>
                      <th className="px-6 py-3 text-right">% Change</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {result.comparison_rows.map((row) => (
                      <tr key={row.metric_key} className="hover:bg-slate-50">
                        <td className="px-6 py-3.5 font-medium text-slate-900">
                          {row.metric_label}
                        </td>
                        <td className="px-6 py-3.5 text-right text-slate-600">
                          {formatCurrency(row.previous_value, row.currency)}
                        </td>
                        <td className="px-6 py-3.5 text-right font-medium text-slate-900">
                          {formatCurrency(row.current_value, row.currency)}
                        </td>
                        <td
                          className={`px-6 py-3.5 text-right font-medium ${
                            row.absolute_change >= 0 ? 'text-emerald-700' : 'text-rose-700'
                          }`}
                        >
                          {row.absolute_change >= 0 ? '+' : ''}
                          {formatCurrency(row.absolute_change, row.currency)}
                        </td>
                        <td
                          className={`px-6 py-3.5 text-right font-semibold ${
                            (row.percent_change ?? 0) >= 0 ? 'text-emerald-700' : 'text-rose-700'
                          }`}
                        >
                          {row.percent_change !== null
                            ? `${row.percent_change >= 0 ? '+' : ''}${row.percent_change.toFixed(2)}%`
                            : 'N/A'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          {result.comparison_rows.length > 0 && (
            <Card className="p-6">
              <h2 className="text-base font-semibold text-slate-900 mb-4">
                Period-over-Period Visual Comparison
              </h2>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={result.comparison_rows}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="metric_label" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Legend />
                    <Bar
                      dataKey="previous_value"
                      name={`Previous (${result.previous_document.period})`}
                      fill="#94a3b8"
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar
                      dataKey="current_value"
                      name={`Current (${result.current_document.period})`}
                      fill="#2563eb"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          <Card className="p-6 space-y-2">
            <h2 className="text-base font-semibold text-slate-900">Comparison Summary</h2>
            <p className="text-sm text-slate-700 whitespace-pre-line leading-relaxed">
              {result.explanation}
            </p>
          </Card>
        </div>
      )}
    </div>
  );
}
