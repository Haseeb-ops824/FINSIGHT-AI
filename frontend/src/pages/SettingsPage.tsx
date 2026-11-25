import React, { useEffect, useState } from 'react';
import { CheckCircle2, Loader2, Server, ShieldAlert } from 'lucide-react';
import { apiRequest, ApiError } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { SystemStatus } from '../types';
import { AlertBanner, Card, StatusBadge } from '../components/UI';

export function SettingsPage() {
  const { user, refreshUser } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [companyOrRole, setCompanyOrRole] = useState(user?.company_or_role || '');
  const [currency, setCurrency] = useState(user?.preferred_currency || 'PKR');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    if (user) {
      setFullName(user.full_name);
      setCompanyOrRole(user.company_or_role || '');
      setCurrency(user.preferred_currency);
    }
  }, [user]);

  useEffect(() => {
    apiRequest<SystemStatus>('/settings/status').then(setStatus).catch(() => {});
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await apiRequest('/auth/me', {
        method: 'PATCH',
        body: JSON.stringify({
          full_name: fullName,
          company_or_role: companyOrRole,
          preferred_currency: currency,
        }),
      });
      await refreshUser();
      setMessage('Profile preferences updated.');
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Settings</h1>
        <p className="text-sm text-slate-500 mt-1">
          Manage your profile preferences and inspect backend AI/OCR capabilities.
        </p>
      </div>

      {message && <AlertBanner variant="success" message={message} />}
      {error && <AlertBanner variant="error" message={error} />}

      <Card className="p-6">
        <h2 className="text-base font-semibold text-slate-900 mb-4">Profile & Preferences</h2>
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Role / Organization
              </label>
              <input
                type="text"
                value={companyOrRole}
                onChange={(e) => setCompanyOrRole(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
              <input
                type="email"
                disabled
                value={user?.email || ''}
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50 text-slate-500 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Default Display Currency
              </label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 bg-white text-sm"
              >
                <option value="PKR">PKR (₨)</option>
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
                <option value="CAD">CAD ($)</option>
                <option value="INR">INR (₹)</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              Save Preferences
            </button>
          </div>
        </form>
      </Card>

      <Card className="p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Server className="w-4 h-4 text-slate-500" />
          <h2 className="text-base font-semibold text-slate-900">Backend Engine Status</h2>
        </div>
        {status ? (
          <div className="divide-y divide-slate-200 text-sm">
            <div className="py-3 flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-900">LLM Integration ({status.llm_provider})</p>
                <p className="text-xs text-slate-500">
                  Model: {status.llm_model}. Configured via backend <code>.env</code> (LLM_API_KEY).
                </p>
              </div>
              {status.llm_configured ? (
                <span className="inline-flex items-center gap-1 text-emerald-700 text-xs font-medium">
                  <CheckCircle2 className="w-4 h-4" /> Active
                </span>
              ) : (
                <StatusBadge status="not_configured" />
              )}
            </div>

            <div className="py-3 flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-900">Tesseract OCR Engine</p>
                <p className="text-xs text-slate-500">
                  Required for scanned image-only PDF pages.
                </p>
              </div>
              <StatusBadge status={status.ocr_available ? 'completed' : 'unavailable'} />
            </div>

            <div className="py-3 flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-900">FAISS Vector Search</p>
                <p className="text-xs text-slate-500">
                  Powers RAG semantic chunk retrieval for AI Financial Assistant.
                </p>
              </div>
              <StatusBadge status={status.faiss_available ? 'completed' : 'unavailable'} />
            </div>

            <div className="py-3 flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-900">Max Upload Limit</p>
                <p className="text-xs text-slate-500">Configured maximum file size per upload.</p>
              </div>
              <span className="font-medium text-slate-900">{status.max_upload_size_mb} MB</span>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">Unable to fetch backend diagnostics.</p>
        )}

        <div className="flex items-start gap-2.5 p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600">
          <ShieldAlert className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
          <p>
            API keys are stored exclusively in backend environment variables (<code>backend/.env</code>)
            and never exposed to the browser. All financial ratios and anomaly statistics are computed
            deterministically in Python.
          </p>
        </div>
      </Card>
    </div>
  );
}
