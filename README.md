# FinSight AI

**FinSight AI** is a full-stack, AI-powered financial document analysis platform designed to transform corporate financial statements and personal bank/transaction records into structured, understandable, and evidence-backed financial intelligence.

> **Disclaimer:** FinSight AI provides informational analysis only and does not constitute professional financial, investment, tax, or legal advice.

---

## Core Capabilities

- **Multi-Format Document Processing**: Drag-and-drop upload for PDF (`.pdf`), Excel (`.xlsx`), and CSV (`.csv`) files with PyMuPDF, `pdfplumber`, Pandas, OpenPyXL, and optional Tesseract OCR for scanned pages.
- **Automatic Document Classification**: Classifies corporate (`income_statement`, `balance_sheet`, `cash_flow_statement`, `annual_report`) and personal (`bank_statement`, `transaction_history`, `expense_report`) documents with manual confirmation fallback when confidence is low.
- **Programmatic Financial Ratios**: Computes Gross Profit Margin, Net Profit Margin, Current Ratio, Quick Ratio, Debt-to-Equity Ratio, and Return on Assets in Python with explicit formulas, calculations, and missing-data limitations.
- **RAG AI Financial Assistant**: Indexes document chunks with FAISS (`IndexFlatIP`) and retrieves relevant pages/tables with source citations for conversational Q&A.
- **Transaction Anomaly Detection**: Combines rule-based checks (duplicates, daily frequency spikes, recurring expense deviations), statistical Z-scores, and Scikit-Learn `IsolationForest`.
- **Interactive Visualizations & Comparisons**: Recharts dashboards for corporate and personal trends plus side-by-side multi-document period comparisons.
- **PDF & Excel Report Export**: Generates downloadable ReportLab PDF executive briefings and OpenPyXL Excel workbooks.

---

## Project Structure

```text
finsych AI/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers (auth, dashboard, documents, analysis, settings)
│   │   ├── core/           # Configuration, SQLAlchemy DB, JWT & bcrypt security
│   │   ├── models/         # ORM models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Modular extractor, classifier, calculator, RAG, AI, anomaly, reports
│   │   └── main.py         # FastAPI entry point
│   ├── tests/              # End-to-end pytest suite
│   ├── .env.example        # Environment variable template
│   └── requirements.txt    # Python dependencies
└── frontend/
    ├── src/
    │   ├── api/            # Typed fetch client
    │   ├── components/     # Persistent sidebar layout & UI primitives
    │   ├── context/        # Authentication context
    │   ├── pages/          # All 13+ application screens
    │   └── types/          # TypeScript definitions
    └── package.json
```

---

## Setup & Execution

### Prerequisites

- **Python 3.12+**
- **Node.js 20+** and **npm**
- *(Optional)* **Tesseract OCR** binary installed on PATH (or configured via `TESSERACT_CMD`) for scanned image-only PDFs.
- *(Optional)* An **LLM API Key** (`OPENAI_API_KEY` / `GEMINI_API_KEY` via `LLM_API_KEY`) for generative AI prose. Without an API key, deterministic Python ratios, FAISS TF-IDF RAG retrieval, anomaly detection, visualizations, comparisons, and PDF/Excel exports all continue to function accurately.

### 1. Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `backend\.env` to configure your `SECRET_KEY` and optional `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_MODEL`:
- `LLM_PROVIDER`: `openai`, `openai_compatible`, or `gemini`
- `LLM_API_KEY`: Your provider API key (never committed or exposed to the frontend)
- `LLM_MODEL`: e.g., `gpt-4o-mini` or `gemini-2.5-flash`

Start the FastAPI server:

```powershell
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. Vite proxies `/api/*` requests directly to `http://127.0.0.1:8000`.

---

## Free-Tier Deployment (Vercel + Supabase)

The production setup uses two Vercel projects: one for the Vite frontend and one for the FastAPI backend. Supabase provides PostgreSQL and a private Storage bucket. Local development continues to use SQLite and the local `backend/uploads` directory.

### 1. Create Supabase resources

1. Create a Supabase project and copy its project URL.
2. In **Connect**, choose the **Transaction pooler** connection string and keep SSL enabled. Use that URI as `DATABASE_URL`; SQLAlchemy adapts `postgresql://` URIs to psycopg.
3. In **Storage**, create a private bucket named `finsight-private`. Do not make it public.
4. Copy the project service-role key for the backend environment only. Never put it in frontend variables or source control.

The API creates the SQLAlchemy tables at startup. Existing SQLite records and uploaded files are not automatically copied; a new deployment starts with an empty database.

### 2. Deploy the backend

Import the repository as a Vercel project and set its **Root Directory** to `backend`. Add these environment variables for Production:

| Variable | Value |
| --- | --- |
| `APP_ENV` | `production` |
| `SECRET_KEY` | A unique random string, at least 32 characters |
| `DATABASE_URL` | Supabase Transaction pooler URI |
| `MAX_UPLOAD_SIZE_MB` | `25` |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service-role key |
| `SUPABASE_STORAGE_BUCKET` | `finsight-private` |
| `CORS_ORIGINS` | Exact frontend origin, e.g. `https://your-site.vercel.app` |

Add optional LLM variables only if you use conversational AI. Do not set wildcard or localhost CORS origins in the Vercel deployment. Redeploy after setting or changing environment variables. Once deployed, check `/api/health`.

### 3. Deploy the frontend

Create another Vercel project from the same repository and set its **Root Directory** to `frontend`. Add:

```text
VITE_API_BASE_URL=https://your-backend.vercel.app/api
```

Deploy, then ensure the frontend's exact origin is included in the backend's `CORS_ORIGINS`. The frontend `.env.example` documents the local/deployed API setting.

### Free-tier limits and data handling

- The frontend uploads files directly to a short-lived Supabase Storage signed URL, then asks the backend to process the stored file. The backend verifies the uploaded size and supports files up to 25 MB; set the private bucket's per-file limit to at least 25 MB.
- Serverless filesystem storage is not persistent; production documents and reports are stored in the private Supabase bucket.
- Free-tier service quotas and availability can change. Supabase Free projects may pause after inactivity and do not include downloadable database backups. This setup is suitable for a low-traffic demo, not a production availability or backup guarantee.
- The backend uses Supabase's transaction pooler and one SQLAlchemy connection per function instance. Heavy document processing can still exceed free-tier function execution or memory limits.

---

## Running Tests

Run the end-to-end backend test suite:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```

Build the frontend TypeScript & Vite bundle:

```powershell
cd frontend
npm run build
```
