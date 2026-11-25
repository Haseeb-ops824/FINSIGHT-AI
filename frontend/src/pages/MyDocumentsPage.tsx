import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  Trash2,
  Upload,
  ArrowRight,
  MessageSquare,
  Search,
} from 'lucide-react';
import { apiRequest, ApiError } from '../api/client';
import type { DocumentItem } from '../types';
import {
  AlertBanner,
  Card,
  EmptyState,
  LoadingState,
  StatusBadge,
  formatCategory,
  formatFileSize,
} from '../components/UI';

export function MyDocumentsPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const fetchDocs = () => {
    setLoading(true);
    apiRequest<DocumentItem[]>('/documents')
      .then(setDocs)
      .catch((err) => setError(err instanceof ApiError ? err.detail : 'Failed to load documents'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleDelete = async (doc: DocumentItem) => {
    if (!window.confirm(`Delete "${doc.original_filename}" and all associated analysis data?`)) {
      return;
    }
    setDeletingId(doc.id);
    try {
      await apiRequest(`/documents/${doc.id}`, { method: 'DELETE' });
      setDocs((prev) => prev.filter((d) => d.id !== doc.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to delete document');
    } finally {
      setDeletingId(null);
    }
  };

  const filtered = docs.filter(
    (d) =>
      d.original_filename.toLowerCase().includes(search.toLowerCase()) ||
      d.document_category.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">My Documents</h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage uploaded corporate and personal financial statements.
          </p>
        </div>
        <Link
          to="/upload"
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors"
        >
          <Upload className="w-4 h-4" />
          Upload Document
        </Link>
      </div>

      {error && <AlertBanner variant="error" message={error} />}

      <Card className="p-4">
        <div className="relative max-w-sm">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter by filename or category..."
            className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </Card>

      {loading ? (
        <LoadingState message="Loading documents..." />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<FileText className="w-8 h-8" />}
          title={docs.length === 0 ? 'No documents yet' : 'No matching documents'}
          description={
            docs.length === 0
              ? 'Upload PDF, Excel (.xlsx), or CSV financial documents to extract metrics and run analysis.'
              : 'Try adjusting your search query.'
          }
          action={
            docs.length === 0 && (
              <Link
                to="/upload"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium"
              >
                <Upload className="w-4 h-4" />
                Upload Document
              </Link>
            )
          }
        />
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-50 text-xs font-medium text-slate-500 uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-5 py-3">Document</th>
                  <th className="px-5 py-3">Category</th>
                  <th className="px-5 py-3">Period</th>
                  <th className="px-5 py-3">Size</th>
                  <th className="px-5 py-3">Processing</th>
                  <th className="px-5 py-3">Analysis</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filtered.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/70">
                    <td className="px-5 py-3.5">
                      <p className="font-medium text-slate-900">{doc.original_filename}</p>
                      <p className="text-xs text-slate-500 uppercase">
                        {doc.file_type} • {doc.document_scope}
                      </p>
                    </td>
                    <td className="px-5 py-3.5 text-slate-700">
                      {formatCategory(doc.document_category)}
                    </td>
                    <td className="px-5 py-3.5 text-slate-500">
                      {doc.reporting_period || '—'}
                    </td>
                    <td className="px-5 py-3.5 text-slate-500">
                      {formatFileSize(doc.file_size_bytes)}
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={doc.processing_status} />
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={doc.analysis_status} />
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <div className="inline-flex items-center gap-2">
                        <Link
                          to={`/assistant/${doc.id}`}
                          title="Ask AI Assistant"
                          className="p-1.5 rounded-lg text-slate-500 hover:text-blue-600 hover:bg-blue-50"
                        >
                          <MessageSquare className="w-4 h-4" />
                        </Link>
                        <Link
                          to={
                            doc.processing_status === 'completed'
                              ? `/analysis/${doc.id}`
                              : `/documents/${doc.id}/processing`
                          }
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium text-blue-600 hover:bg-blue-50"
                        >
                          {doc.processing_status === 'completed' ? 'Analysis' : 'Status'}
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                        <button
                          onClick={() => handleDelete(doc)}
                          disabled={deletingId === doc.id}
                          title="Delete document"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 disabled:opacity-40"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
