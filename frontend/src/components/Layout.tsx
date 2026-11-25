import React, { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  BarChart3,
  MessageSquare,
  AlertTriangle,
  GitCompare,
  FileSpreadsheet,
  Settings,
  Upload,
  LogOut,
  Menu,
  X,
  PieChart,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/documents', label: 'My Documents', icon: FileText },
  { to: '/analysis', label: 'Document Analysis', icon: BarChart3 },
  { to: '/visualizations', label: 'Visualizations', icon: PieChart },
  { to: '/assistant', label: 'AI Financial Assistant', icon: MessageSquare },
  { to: '/anomalies', label: 'Anomaly Detection', icon: AlertTriangle },
  { to: '/compare', label: 'Compare Documents', icon: GitCompare },
  { to: '/reports', label: 'Reports', icon: FileSpreadsheet },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const sidebarContent = (
    <div className="app-sidebar flex flex-col h-full border-r backdrop-blur-xl">
      <div className="sidebar-brand flex items-center justify-between px-5 h-16 border-b">
        <Link to="/dashboard" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-400 text-slate-950 flex items-center justify-center font-bold text-sm">
            FS
          </div>
          <div>
            <span className="text-base font-bold text-slate-900 tracking-tight">FinSight AI</span>
            <span className="sidebar-muted block text-[10px] font-medium uppercase tracking-wider">
              Financial Intelligence
            </span>
          </div>
        </Link>
        <button
          onClick={() => setMobileOpen(false)}
          className="lg:hidden p-1.5 rounded-lg text-slate-500 hover:bg-slate-100"
          aria-label="Close navigation"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="p-4">
        <Link
          to="/upload"
          onClick={() => setMobileOpen(false)}
          className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-lg bg-blue-400 hover:bg-blue-300 hover:shadow-lg hover:shadow-black/10 hover:-translate-y-0.5 text-slate-950 text-sm font-semibold transition-all duration-200"
        >
          <Upload className="w-4 h-4" />
          Upload Document
        </Link>
      </div>

      <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `sidebar-nav-link flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive ? 'is-active' : 'hover:translate-x-0.5'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="p-4 border-t border-white/10 space-y-3">
        <div className="sidebar-note flex items-start gap-2 p-2.5 rounded-lg border text-[11px] leading-relaxed">
          <ShieldCheck className="w-4 h-4 text-blue-300 shrink-0 mt-0.5" />
          <span>
            Informational analysis only. Not financial, investment, tax, or legal advice.
          </span>
        </div>
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-900 truncate">{user?.full_name}</p>
            <p className="sidebar-muted text-xs truncate">{user?.email}</p>
          </div>
          <button
            onClick={handleLogout}
            title="Sign out"
            className="p-2 rounded-lg text-slate-500 hover:text-rose-600 hover:bg-rose-50 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="dark-app min-h-screen flex bg-slate-50">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:block w-64 shrink-0 fixed inset-y-0 left-0 z-30">
        {sidebarContent}
      </aside>

      {/* Mobile Sidebar */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-slate-900/40"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative w-64 max-w-full z-10">{sidebarContent}</aside>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 lg:pl-64 flex flex-col min-w-0">
        <header className="lg:hidden h-14 bg-white border-b border-slate-200 px-4 flex items-center justify-between sticky top-0 z-20">
          <button
            onClick={() => setMobileOpen(true)}
            className="p-2 -ml-2 rounded-lg text-slate-600 hover:bg-slate-100"
            aria-label="Open navigation"
          >
            <Menu className="w-5 h-5" />
          </button>
          <span className="font-semibold text-slate-900 text-sm">FinSight AI</span>
          <Link
            to="/upload"
            className="p-2 rounded-lg text-blue-600 hover:bg-blue-50"
            aria-label="Upload Document"
          >
            <Upload className="w-5 h-5" />
          </Link>
        </header>

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto page-enter">
          {children}
        </main>
      </div>
    </div>
  );
}
