import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Legend,
} from 'recharts';
import { PieChart as PieIcon } from 'lucide-react';
import { apiRequest, ApiError } from '../api/client';
import type { AnalysisResult, DocumentItem } from '../types';
import { AlertBanner, Card, EmptyState, LoadingState, formatCategory } from '../components/UI';

const COLORS = ['#2563eb', '#0f766e', '#d97706', '#7c3aed', '#e11d48', '#0284c7', '#475569'];

export function VisualizationsPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<DocumentItem[]>('/documents')
      .then((list) => {
        setDocs(list);
        if (list.length > 0) {
          setSelectedId(String(list[0].id));
        } else {
          setLoading(false);
        }
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.detail : 'Failed to load documents');
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    apiRequest<AnalysisResult>(`/analysis/${selectedId}`)
      .then(setAnalysis)
      .catch(() => setAnalysis(null))
      .finally(() => setLoading(false));
  }, [selectedId]);

  if (loading) return <LoadingState message="Building financial visualizations..." />;
  if (error) return <AlertBanner variant="error" message={error} />;

  if (docs.length === 0) {
    return (
      <EmptyState
        icon={<PieIcon className="w-8 h-8" />}
        title="No financial data to visualize"
        description="Upload corporate statements or personal bank/transaction records to view interactive charts."
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

  const chartData = (analysis?.chart_data || {}) as Record<string, any>;
  const incomeVsExpense = chartData.income_vs_expense as Array<{ name: string; value: number }> | undefined;
  const assetsVsLiab = chartData.assets_vs_liabilities as Array<{ name: string; value: number }> | undefined;
  const cashFlow = chartData.cash_flow as Array<{ name: string; value: number }> | undefined;
  const personal = chartData.personal as
    | {
        total_inflows: number;
        total_outflows: number;
        net_cash_flow: number;
        expense_by_category: Array<{ category: string; amount: number }>;
        monthly_trends: Array<{ period: string; income: number; expenses: number; savings: number }>;
      }
    | undefined;

  const ratioChartData = (analysis?.ratios || [])
    .filter((r) => r.value !== null && r.key.includes('margin'))
    .map((r) => ({ name: r.name, value: r.value }));

  const hasAnyChart =
    (incomeVsExpense && incomeVsExpense.length > 0) ||
    (assetsVsLiab && assetsVsLiab.length > 0) ||
    (cashFlow && cashFlow.length > 0) ||
    (personal && (personal.expense_by_category.length > 0 || personal.monthly_trends.length > 0));

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Financial Visualizations
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Interactive charts rendered strictly from verified extracted document figures.
          </p>
        </div>

        <select
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
          className="px-3.5 py-2 rounded-lg border border-slate-300 bg-white text-sm font-medium text-slate-800"
        >
          {docs.map((d) => (
            <option key={d.id} value={d.id}>
              {d.original_filename} ({formatCategory(d.document_category)})
            </option>
          ))}
        </select>
      </div>

      {!hasAnyChart ? (
        <EmptyState
          icon={<PieIcon className="w-8 h-8" />}
          title="Insufficient chartable data for this document"
          description="Charts are only shown when sufficient numerical series are extracted from the selected document."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {incomeVsExpense && incomeVsExpense.length > 0 && (
            <Card className="p-6">
              <h2 className="text-base font-semibold text-slate-900 mb-4">
                Revenue vs. Expenses & Net Income
              </h2>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={incomeVsExpense}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#2563eb" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          {assetsVsLiab && assetsVsLiab.length > 0 && (
            <Card className="p-6">
              <h2 className="text-base font-semibold text-slate-900 mb-4">
                Assets vs. Liabilities & Equity
              </h2>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={assetsVsLiab}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#0f766e" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          {cashFlow && cashFlow.length > 0 && (
            <Card className="p-6">
              <h2 className="text-base font-semibold text-slate-900 mb-4">Cash Flow Breakdown</h2>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={cashFlow}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#4f46e5" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          {ratioChartData.length > 0 && (
            <Card className="p-6">
              <h2 className="text-base font-semibold text-slate-900 mb-4">
                Profitability Margins (%)
              </h2>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={ratioChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis unit="%" tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#0284c7" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          {personal && (
            <>
              <Card className="p-6">
                <h2 className="text-base font-semibold text-slate-900 mb-4">
                  Income vs. Expenses Summary
                </h2>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={[
                        { name: 'Total Inflows', value: personal.total_inflows },
                        { name: 'Total Outflows', value: personal.total_outflows },
                        { name: 'Net Cash Flow', value: personal.net_cash_flow },
                      ]}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip />
                      <Bar dataKey="value" fill="#2563eb" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              {personal.expense_by_category.length > 0 && (
                <Card className="p-6">
                  <h2 className="text-base font-semibold text-slate-900 mb-4">
                    Expense Distribution by Category
                  </h2>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={personal.expense_by_category}
                          dataKey="amount"
                          nameKey="category"
                          cx="50%"
                          cy="50%"
                          outerRadius={95}
                          label
                        >
                          {personal.expense_by_category.map((_, idx) => (
                            <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              )}

              {personal.monthly_trends.length > 0 && (
                <Card className="p-6 lg:col-span-2">
                  <h2 className="text-base font-semibold text-slate-900 mb-4">
                    Monthly Spending & Savings Trends
                  </h2>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={personal.monthly_trends}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                        <YAxis tick={{ fontSize: 12 }} />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="income" stroke="#0f766e" strokeWidth={2} name="Income" />
                        <Line type="monotone" dataKey="expenses" stroke="#e11d48" strokeWidth={2} name="Expenses" />
                        <Line type="monotone" dataKey="savings" stroke="#2563eb" strokeWidth={2} name="Net Savings" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
