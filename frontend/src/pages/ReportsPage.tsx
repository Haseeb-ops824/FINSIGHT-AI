import { useEffect, useState } from 'react';
import { Download, FileSpreadsheet, FileText, Loader2 } from 'lucide-react';
import { apiRequest, ApiError, downloadFile } from '../api/client';
import type { DocumentItem, GeneratedReport } from '../types';
import { AlertBanner, Card, EmptyState, LoadingState, formatCategory } from '../components/UI';

export function ReportsPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [reports, setReports] = useState<GeneratedReport[]>([]);
  const [selectedDocId, setSelectedDocId] = useState('');
  const [format, setFormat] = useState<'pdf' | 'xlsx'>('pdf');
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadAll = () => {
    Promise.all([
      apiRequest<DocumentItem[]>('/documents'),
      apiRequest<GeneratedReport[]>('/reports'),
    ])
      .then(([docList, repList]) => {
        setDocs(docList);
        setReports(repList);
        if (docList.length > 0 && !selectedDocId) {
          setSelectedDocId(String(docList[0].id));
        }
      })
      .catch((err) => setError(err instanceof ApiError ? err.detail : 'Failed to load reports'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleGenerate = async () => {
    if (!selectedDocId) return;
    setGenerating(true);
    setError(null);
    setSuccess(null);
    try {
      const created = await apiRequest<GeneratedReport>('/reports/generate', {
        method: 'POST',
        body: JSON.stringify({
          document_id: Number(selectedDocId),
          report_format: format,
        }),
      });
      setReports((prev) => [created, ...prev]);
      setSuccess(`Generated ${created.report_format.toUpperCase()} report successfully.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to generate report');
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return <LoadingState message="Loading report center..." />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Financial Reports</h1>
        <p className="text-sm text-slate-500 mt-1">
          Generate and download formatted PDF executive briefings or structured Excel workbooks.
        </p>
      </div>

      {error && <AlertBanner variant="error" message={error} />}
      {success && <AlertBanner variant="success" message={success} />}

      <Card className="p-6 space-y-4">
        <h2 className="text-base font-semibold text-slate-900">Generate New Report</h2>
        {docs.length === 0 ? (
          <p className="text-sm text-slate-500">
            Upload and process a financial document before generating downloadable reports.
          </p>
        ) : (
          <div className="flex flex-col md:flex-row gap-3">
            <select
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              className="flex-1 px-3.5 py-2.5 rounded-lg border border-slate-300 bg-white text-sm"
            >
              {docs.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.original_filename} ({formatCategory(d.document_category)})
                </option>
              ))}
            </select>

            <select
              value={format}
              onChange={(e) => setFormat(e.target.value as 'pdf' | 'xlsx')}
              className="px-3.5 py-2.5 rounded-lg border border-slate-300 bg-white text-sm"
            >
              <option value="pdf">PDF Executive Report (.pdf)</option>
              <option value="xlsx">Structured Excel Workbook (.xlsx)</option>
            </select>

            <button
              onClick={handleGenerate}
              disabled={generating || !selectedDocId}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium"
            >
              {generating && <Loader2 className="w-4 h-4 animate-spin" />}
              Generate Report
            </button>
          </div>
        )}
      </Card>

      <Card className="overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="text-base font-semibold text-slate-900">Generated Reports History</h2>
        </div>

        {reports.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={<FileSpreadsheet className="w-8 h-8" />}
              title="No reports generated yet"
              description="Choose a document and format above to create your first downloadable PDF or Excel report."
            />
          </div>
        ) : (
          <div className="divide-y divide-slate-200">
            {reports.map((rep) => (
              <div
                key={rep.id}
                className="px-6 py-4 flex items-center justify-between gap-4 hover:bg-slate-50/70"
              >
                <div className="flex items-center gap-3 min-w-0">
                  {rep.report_format === 'pdf' ? (
                    <FileText className="w-5 h-5 text-rose-600 shrink-0" />
                  ) : (
                    <FileSpreadsheet className="w-5 h-5 text-emerald-600 shrink-0" />
                  )}
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate">
                      {rep.report_title}
                    </p>
                    <p className="text-xs text-slate-500 uppercase">
                      {rep.report_format} • {new Date(rep.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() =>
                    downloadFile(
                      `/reports/${rep.id}/download`,
                      `FinSight_Report_${rep.id}.${rep.report_format}`
                    )
                  }
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs font-medium text-slate-700"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
