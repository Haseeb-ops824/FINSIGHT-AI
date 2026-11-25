import { useEffect } from 'react';
import { Link, Navigate } from 'react-router-dom';
import {
  ArrowRight,
  BarChart3,
  FileSearch,
  MessageSquare,
  ShieldAlert,
  FileSpreadsheet,
  GitCompare,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export function LandingPage() {
  const { user } = useAuth();

  useEffect(() => {
    const revealItems = document.querySelectorAll<HTMLElement>('[data-scroll-reveal]');
    revealItems.forEach((item, index) => {
      item.classList.add('scroll-reveal');
      item.style.setProperty('--reveal-delay', `${(index % 6) * 75}ms`);
    });

    if (!('IntersectionObserver' in window)) {
      revealItems.forEach((item) => item.classList.add('is-visible'));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          entry.target.classList.toggle('is-visible', entry.isIntersecting);
        });
      },
      { threshold: 0.15, rootMargin: '0px 0px -6% 0px' }
    );
    revealItems.forEach((item) => observer.observe(item));

    return () => observer.disconnect();
  }, []);

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  const features = [
    {
      icon: FileSearch,
      title: 'Multi-Format Document Extraction',
      description:
        'Upload PDFs, Excel workbooks (.xlsx), and CSV files. Automatically parses text, tables, and scanned documents with source page and cell citations.',
    },
    {
      icon: BarChart3,
      title: 'Verified Financial Ratios',
      description:
        'Programmatic Python computation of Gross Margin, Net Margin, Current Ratio, Quick Ratio, Debt-to-Equity, and ROA with transparent formulas.',
    },
    {
      icon: MessageSquare,
      title: 'RAG Financial Assistant',
      description:
        'Ask plain-English questions about any uploaded statement. Answers are grounded in retrieved document chunks and verified figures.',
    },
    {
      icon: ShieldAlert,
      title: 'Transaction Anomaly Detection',
      description:
        'Combines rule-based checks, statistical z-scores, and Isolation Forest to flag unusually large transactions, duplicates, and spending spikes.',
    },
    {
      icon: GitCompare,
      title: 'Period & Statement Comparison',
      description:
        'Compare compatible statements side-by-side to inspect absolute and percentage changes with evidence-backed explanations.',
    },
    {
      icon: FileSpreadsheet,
      title: 'Exportable PDF & Excel Reports',
      description:
        'Download formatted executive PDF reports and structured Excel workbooks with metrics, ratios, insights, and limitations.',
    },
  ];

  return (
    <div className="dark-app min-h-screen text-slate-900">
      <header className="landing-header sticky top-0 z-20 border-b backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white font-bold text-sm shadow-lg shadow-blue-600/20">
              FS
            </div>
            <span className="text-lg font-bold tracking-tight text-slate-900">FinSight AI</span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/login"
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-blue-700 transition-colors"
            >
              Sign in
            </Link>
            <Link
              to="/register"
              className="light-button inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-xl bg-blue-400 hover:bg-blue-300 hover:shadow-lg hover:shadow-black/20 transition-all duration-200"
            >
              Get Started
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-20 sm:pt-24 sm:pb-28">
          <div className="space-y-12">
            <div className="hero-copy reveal-up mx-auto max-w-4xl text-center">
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/75 border border-blue-100 text-blue-700 text-xs font-semibold shadow-sm shadow-blue-900/5 mb-7">
                <Sparkles className="w-3.5 h-3.5" />
                Evidence-backed financial intelligence
                <span className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
              </div>
              <h1 className="mx-auto max-w-4xl text-5xl leading-[0.98] text-slate-950 sm:text-7xl xl:text-8xl">
                Where your financial story
                <span className="editorial-heading block italic text-indigo-300">
                  comes into focus.
                </span>
              </h1>
              <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-slate-600 sm:text-lg">
                A clearer way to understand financial documents: verified figures, transparent analysis,
                and answers that stay connected to their sources.
              </p>
              <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
                <Link
                  to="/register"
                  className="light-button group inline-flex items-center gap-2 px-5 py-3.5 rounded-xl bg-blue-400 hover:bg-blue-300 hover:shadow-xl hover:shadow-black/25 font-semibold text-sm transition-all duration-200"
                >
                  Explore your workspace
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </Link>
                <Link
                  to="/login"
                  className="inline-flex items-center gap-2 px-5 py-3.5 rounded-xl bg-white/10 border border-white/15 hover:border-white/30 hover:bg-white/15 text-slate-700 font-semibold text-sm transition-all duration-200"
                >
                  Sign in
                </Link>
              </div>
            </div>

            <div className="hero-landscape-shell reveal-up [animation-delay:140ms]">
              <img
                className="hero-landscape"
                src="/images/financial-documents-bg.jpg"
                alt="Financial forms, a phone calculator, and a pen on a desk"
                draggable="false"
              />
              <div className="hero-landscape-shade" aria-hidden="true" />
              <div className="landscape-note landscape-note--source">
                <span className="landscape-note__icon"><FileSearch className="h-4 w-4" /></span>
                <span><small>DOCUMENTS</small><strong>PDF · Excel · CSV</strong></span>
              </div>
              <div className="landscape-note landscape-note--analysis">
                <span className="landscape-note__icon"><BarChart3 className="h-4 w-4" /></span>
                <span><small>ANALYSIS</small><strong>Transparent calculations</strong></span>
              </div>
              <div className="landscape-note landscape-note--answers">
                <span className="landscape-note__icon"><MessageSquare className="h-4 w-4" /></span>
                <span><small>ANSWERS</small><strong>Evidence-linked insights</strong></span>
              </div>
              <span className="landscape-caption">
                Clarity grows<br />from the details.
              </span>
            </div>
          </div>

          <div className="mt-24 sm:mt-32">
            <div
              className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"
              data-scroll-reveal
            >
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">One connected workspace</p>
                <h2 className="mt-2 text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900">From raw documents to real understanding.</h2>
              </div>
              <p className="max-w-md text-sm leading-relaxed text-slate-500">A clear view of your finances, with the evidence behind every result.</p>
            </div>
          <div className="feature-grid grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-12">
            {features.map((feat, index) => {
              const Icon = feat.icon;
              return (
                <div
                  key={feat.title}
                  data-scroll-reveal
                  className={`surface-card feature-card group rounded-2xl border border-white/70 bg-white/90 p-6 shadow-sm shadow-black/10 backdrop-blur-sm ${
                    index < 2 ? 'lg:col-span-6' : 'lg:col-span-3'
                  } ${index === 1 ? 'feature-card--dark' : ''}`}
                >
                  <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-600 transition-all duration-300 group-hover:scale-110 group-hover:bg-blue-600 group-hover:text-white group-hover:shadow-lg group-hover:shadow-blue-600/20">
                    <Icon className="w-5 h-5" />
                  </div>
                  <h3 className="text-base font-semibold tracking-tight text-slate-900">{feat.title}</h3>
                  <p className="mt-2 text-sm text-slate-600 leading-relaxed">{feat.description}</p>
                </div>
              );
            })}
          </div>
          </div>
        </section>

        <section className="dark-editorial relative overflow-hidden">
          <div className="absolute -right-40 -top-56 h-[34rem] w-[34rem] rounded-full bg-indigo-500/10 blur-3xl" />
          <div className="relative mx-auto grid max-w-7xl gap-10 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-[1fr_0.8fr] lg:items-end lg:px-8">
            <div data-scroll-reveal>
              <p className="editorial-mark text-xs font-semibold uppercase tracking-[0.2em]">Clarity, with context</p>
              <h2 className="editorial-heading mt-5 max-w-3xl text-4xl leading-tight sm:text-5xl lg:text-6xl">
                Know what the numbers say — and where they came from.
              </h2>
            </div>
            <div data-scroll-reveal>
              <p className="editorial-muted max-w-lg text-base leading-relaxed">
                Explore financial documents through verified calculations and source-linked answers.
                Review the evidence, compare periods, and keep the analysis in your hands.
              </p>
              <Link
                to="/register"
                className="group mt-7 inline-flex items-center gap-3 border-b border-white/30 pb-2 text-sm font-semibold text-white transition-colors hover:border-indigo-300 hover:text-indigo-200"
              >
                Get started
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/10 bg-slate-950/70 py-8 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <span>FinSight AI — Financial Document Analysis Platform</span>
          <span>
            Informational insights only. Does not constitute financial, investment, tax, or legal
            advice.
          </span>
        </div>
      </footer>
    </div>
  );
}
