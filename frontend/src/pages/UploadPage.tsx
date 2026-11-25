import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, FileText, X, Loader2, CheckCircle2 } from 'lucide-react';
import { apiRequest, ApiError } from '../api/client';
import type { DocumentItem } from '../types';
import { AlertBanner, Card, formatFileSize } from '../components/UI';

const ACCEPTED_EXTENSIONS = ['.pdf', '.csv', '.xlsx'];
const CONTENT_TYPES: Record<string, string> = {
  '.pdf': 'application/pdf',
  '.csv': 'text/csv',
  '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
};

type UploadSession =
  | { mode: 'proxy' }
  | { mode: 'direct'; document_id: number; upload_url: string };

export function UploadPage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateAndSetFile = (file: File) => {
    setError(null);
    const lower = file.name.toLowerCase();
    const valid = ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext));
    if (!valid) {
      setError('Unsupported file format. Please upload a PDF (.pdf), Excel (.xlsx), or CSV (.csv) file.');
      return;
    }
    if (file.size > 25 * 1024 * 1024) {
      setError('File size exceeds the 25 MB upload limit.');
      return;
    }
    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setError(null);

    try {
      const session = await apiRequest<UploadSession>('/documents/upload-session', {
        method: 'POST',
        body: JSON.stringify({
          filename: selectedFile.name,
          file_size_bytes: selectedFile.size,
        }),
      });
      let doc: DocumentItem;
      if (session.mode === 'proxy') {
        const formData = new FormData();
        formData.append('file', selectedFile);
        doc = await apiRequest<DocumentItem>('/documents/upload', {
          method: 'POST',
          body: formData,
        });
      } else {
        const ext = selectedFile.name.slice(selectedFile.name.lastIndexOf('.')).toLowerCase();
        const response = await fetch(session.upload_url, {
          method: 'PUT',
          headers: {
            'Content-Type': CONTENT_TYPES[ext] || selectedFile.type || 'application/octet-stream',
            'x-upsert': 'true',
          },
          body: selectedFile,
        });
        if (!response.ok) {
          let detail = `Storage upload failed (${response.status}).`;
          try {
            const result: unknown = await response.json();
            if (typeof result === 'object' && result !== null) {
              const body = result as Record<string, unknown>;
              const storageDetail = body.message || body.error;
              if (typeof storageDetail === 'string') detail = storageDetail;
            }
          } catch {
            // Keep the generic error when the storage response is not JSON.
          }
          throw new Error(detail);
        }
        doc = await apiRequest<DocumentItem>(
          `/documents/${session.document_id}/complete-upload`,
          { method: 'POST' }
        );
      }
      navigate(`/documents/${doc.id}/processing`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : err instanceof Error ? err.message : 'Upload failed');
      setUploading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Upload Financial Document</h1>
        <p className="text-sm text-slate-500 mt-1">
          Upload corporate financial statements or personal bank/transaction records for automated
          extraction and analysis.
        </p>
      </div>

      {error && <AlertBanner variant="error" title="Upload error" message={error} />}

      <Card className="p-6 space-y-6">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
            dragging
              ? 'border-blue-500 bg-blue-50/50'
              : 'border-slate-300 hover:border-blue-400 hover:bg-slate-50'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.csv,.xlsx"
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.[0]) validateAndSetFile(e.target.files[0]);
            }}
          />
          <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-4">
            <UploadCloud className="w-6 h-6" />
          </div>
          <p className="text-sm font-semibold text-slate-900">
            Drag and drop your document here, or click to browse
          </p>
          <p className="text-xs text-slate-500 mt-1.5">
            Supports PDF (.pdf), Excel (.xlsx), and CSV (.csv) up to 25 MB
          </p>
        </div>

        {selectedFile && (
          <div className="flex items-center justify-between p-4 rounded-xl bg-slate-50 border border-slate-200">
            <div className="flex items-center gap-3 min-w-0">
              <FileText className="w-5 h-5 text-blue-600 shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">{selectedFile.name}</p>
                <p className="text-xs text-slate-500">{formatFileSize(selectedFile.size)}</p>
              </div>
            </div>
            <button
              onClick={() => setSelectedFile(null)}
              disabled={uploading}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/70"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-600 bg-slate-50 p-4 rounded-xl border border-slate-200">
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-slate-800">Corporate Statements</p>
              <p>Income Statements, Balance Sheets, Cash Flow Statements, Annual Reports</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-slate-800">Personal Finances</p>
              <p>Bank Statements, Transaction Histories, Expense Reports</p>
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium transition-colors"
          >
            {uploading && <Loader2 className="w-4 h-4 animate-spin" />}
            {uploading ? 'Uploading & Processing...' : 'Upload & Process Document'}
          </button>
        </div>
      </Card>
    </div>
  );
}
