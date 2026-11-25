import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  FileSpreadsheet,
  AlertTriangle,
  Activity,
  Upload,
  BarChart3,
  GitCompare,
  MessageSquare,
  ArrowRight,
} from 'lucide-react';
import { apiRequest, ApiError } from '../api/client';
import type { DashboardSummary } from '../types';
import {
  AlertBanner,
  Card,
  EmptyState,
  LoadingState,
  StatusBadge,
  formatCategory,
  formatCurrency,
} from '../components/UI';

export function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<DashboardSummary>('/dashboard')
      .then(setData)
      .catch((err) => setError(err instanceof ApiError ? err.detail : 'Failed to load dashboard'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState message="Loading your financial workspace..." />;
  if (error) return <AlertBanner variant="error" title="Dashboard error" message={error} />;
  if (!data) return null;

  const overviewEntries = Object.entries(data.financial_overview || {});

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Workspace Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">
            Monitor uploaded statements, verified financial metrics, and detected anomalies.
          </p>
        </div>
        <Link
          to="/upload"
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors"
        >
          <Upload className="w-4 h-4" />
          Upload New Document
        </Link>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Documents Analyzed
            </span>
            <FileText className="w-4 h-4 text-blue-600" />
          </div>
          <p className="mt-3 text-2xl font-bold text-slate-900">{data.total_documents}</p>
          <p className="mt-1 text-xs text-slate-500">Uploaded PDF, Excel, & CSV files</p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Reports Generated
            </span>
            <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
          </div>
          <p className="mt-3 text-2xl font-bold text-slate-900">{data.total_reports}</p>
          <p className="mt-1 text-xs text-slate-500">Exported PDF & Excel briefings</p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Anomalies Detected
            </span>
            <AlertTriangle className="w-4 h-4 text-amber-600" />
          </div>
          <p className="mt-3 text-2xl font-bold text-slate-900">{data.total_anomalies}</p>
          <p className="mt-1 text-xs text-slate-500">Unusual patterns requiring review</p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Recent Activity
            </span>
            <Activity className="w-4 h-4 text-slate-600" />
          </div>
          <p className="mt-3 text-2xl font-bold text-slate-900">{data.recent_activity_count}</p>
          <p className="mt-1 text-xs text-slate-500">Recent processing events</p>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <Link
          to="/upload"
          className="quick-action flex items-center justify-between p-4 bg-white/90 border border-slate-200 rounded-xl hover:border-blue-300 hover:bg-blue-50/60"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <Upload className="w-4 h-4" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-900">Upload Document</p>
              <p className="text-xs text-slate-500">PDF, XLSX, or CSV</p>
            </div>
          </div>
          <ArrowRight className="w-4 h-4 text-slate-400" />
        </Link>

        <Link
          to="/analysis"
          className="quick-action flex items-center justify-between p-4 bg-white/90 border border-slate-200 rounded-xl hover:border-blue-300 hover:bg-blue-50/60"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <BarChart3 className="w-4 h-4" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-900">Analyze Statement</p>
              <p className="text-xs text-slate-500">Ratios & risk insights</p>
            </div>
          </div>
          <ArrowRight className="w-4 h-4 text-slate-400" />
        </Link>

        <Link
          to="/compare"
          className="quick-action flex items-center justify-between p-4 bg-white/90 border border-slate-200 rounded-xl hover:border-blue-300 hover:bg-blue-50/60"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <GitCompare className="w-4 h-4" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-900">Compare Documents</p>
              <p className="text-xs text-slate-500">Period-over-period diff</p>
            </div>
          </div>
          <ArrowRight className="w-4 h-4 text-slate-400" />
        </Link>

        <Link
          to="/assistant"
          className="quick-action flex items-center justify-between p-4 bg-white/90 border border-slate-200 rounded-xl hover:border-blue-300 hover:bg-blue-50/60"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <MessageSquare className="w-4 h-4" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-900">Ask AI Assistant</p>
              <p className="text-xs text-slate-500">Document-grounded Q&A</p>
            </div>
          </div>
          <ArrowRight className="w-4 h-4 text-slate-400" />
        </Link>
      </div>

      {/* Extracted Financial Overview (only real metrics) */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Extracted Financial Overview</h2>
            <p className="text-xs text-slate-500">
              Verified figures from your uploaded documents. Missing metrics are never fabricated.
            </p>
          </div>
        </div>
        {overviewEntries.length === 0 ? (
          <EmptyState
            icon={<BarChart3 className="w-8 h-8" />}
            title="No financial metrics extracted yet"
            description="Upload an income statement, balance sheet, cash flow statement, or bank statement to populate verified metrics here."
            action={
              <Link
                to="/upload"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium"
              >
                <Upload className="w-4 h-4" />
                Upload Your First Document
              </Link>
            }
          />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {overviewEntries.map(([key, item]) => (
              <div
                key={key}
                className="p-4 rounded-xl border border-slate-200 bg-slate-50/70"
              >
                <p className="text-xs font-medium text-slate-500">{item.label}</p>
                <p className="mt-1.5 text-xl font-bold text-slate-900">
                  {formatCurrency(item.value, item.currency)}
                </p>
                <p className="mt-1 text-[11px] text-slate-500 truncate" title={item.document_name}>
                  {item.period ? `${item.period} • ` : ''}
                  {item.document_name}
                </p>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Recent Documents Table */}
      <Card className="overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900">Recent Documents</h2>
          <Link to="/documents" className="text-xs font-medium text-blue-600 hover:text-blue-700">
            View all documents
          </Link>
        </div>

        {data.recent_documents.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={<FileText className="w-8 h-8" />}
              title="No documents uploaded"
              description="Drag and drop a PDF, Excel, or CSV financial document to begin automated analysis."
              action={
                <Link
                  to="/upload"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium"
                >
                  Upload Document
                </Link>
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-50 text-xs font-medium text-slate-500 uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Document Name</th>
                  <th className="px-6 py-3">Document Type</th>
                  <th className="px-6 py-3">Upload Date</th>
                  <th className="px-6 py-3">Processing</th>
                  <th className="px-6 py-3">Analysis</th>
                  <th className="px-6 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {data.recent_documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/70">
                    <td className="px-6 py-3.5 font-medium text-slate-900">
                      {doc.original_filename}
                    </td>
                    <td className="px-6 py-3.5 text-slate-600">
                      {formatCategory(doc.document_category)}
                    </td>
                    <td className="px-6 py-3.5 text-slate-500">
                      {new Date(doc.uploaded_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-3.5">
                      <StatusBadge status={doc.processing_status} />
                    </td>
                    <td className="px-6 py-3.5">
                      <StatusBadge status={doc.analysis_status} />
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      <Link
                        to={
                          doc.processing_status === 'completed'
                            ? `/analysis/${doc.id}`
                            : `/documents/${doc.id}/processing`
                        }
                        className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700"
                      >
                        View Analysis
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
