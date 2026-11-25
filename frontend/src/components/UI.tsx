import React from 'react';
import { AlertCircle, CheckCircle2, Info, Loader2 } from 'lucide-react';

export function Card({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`surface-card bg-white/90 border border-slate-200 rounded-xl shadow-xs backdrop-blur-sm ${className}`}
    >
      {children}
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const styles: Record<string, string> = {
    completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    healthy: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    low: 'bg-slate-100 text-slate-700 border-slate-200',
    medium: 'bg-amber-50 text-amber-700 border-amber-200',
    caution: 'bg-amber-50 text-amber-700 border-amber-200',
    partial: 'bg-amber-50 text-amber-700 border-amber-200',
    needs_classification: 'bg-blue-50 text-blue-700 border-blue-200',
    pending: 'bg-slate-100 text-slate-600 border-slate-200',
    extracting: 'bg-blue-50 text-blue-700 border-blue-200',
    analyzing: 'bg-blue-50 text-blue-700 border-blue-200',
    high: 'bg-rose-50 text-rose-700 border-rose-200',
    warning: 'bg-rose-50 text-rose-700 border-rose-200',
    failed: 'bg-rose-50 text-rose-700 border-rose-200',
    unavailable: 'bg-slate-100 text-slate-500 border-slate-200',
  };
  const cls = styles[normalized] || 'bg-slate-100 text-slate-700 border-slate-200';
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border capitalize ${cls}`}
    >
      {status.replace(/_/g, ' ')}
    </span>
  );
}

export function LoadingState({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-slate-500">
      <Loader2 className="w-7 h-7 animate-spin text-blue-600 mb-3" />
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-14 px-6 border border-dashed border-slate-300 rounded-xl bg-white">
      {icon && <div className="text-slate-400 mb-3">{icon}</div>}
      <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      <p className="text-sm text-slate-500 max-w-md mt-1">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function AlertBanner({
  variant = 'info',
  title,
  message,
}: {
  variant?: 'info' | 'success' | 'error' | 'warning';
  title?: string;
  message: string;
}) {
  const styles = {
    info: 'bg-blue-50 border-blue-200 text-blue-900',
    success: 'bg-emerald-50 border-emerald-200 text-emerald-900',
    error: 'bg-rose-50 border-rose-200 text-rose-900',
    warning: 'bg-amber-50 border-amber-200 text-amber-900',
  };
  const Icon =
    variant === 'success' ? CheckCircle2 : variant === 'error' ? AlertCircle : Info;
  return (
    <div className={`flex items-start gap-3 p-4 rounded-xl border text-sm ${styles[variant]}`}>
      <Icon className="w-4 h-4 mt-0.5 shrink-0" />
      <div>
        {title && <p className="font-semibold mb-0.5">{title}</p>}
        <p>{message}</p>
      </div>
    </div>
  );
}

export function formatCurrency(value: number, currency = 'USD'): string {
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return `${currency} ${value.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
  }
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatCategory(category: string): string {
  return category.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
