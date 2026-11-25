from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth & User ---
class UserRegister(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    company_or_role: Optional[str] = None
    password: str = Field(..., min_length=6, max_length=128)
    preferred_currency: str = "PKR"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    company_or_role: Optional[str] = None
    preferred_currency: Optional[str] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    company_or_role: Optional[str] = None
    preferred_currency: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Metrics & Transactions ---
class ExtractedMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    metric_key: str
    metric_label: str
    value: float
    currency: str
    period: Optional[str] = None
    category: Optional[str] = None
    source_location: Optional[str] = None
    source_snippet: Optional[str] = None
    confidence: float


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_date: Optional[str] = None
    description: str
    debit: Optional[float] = None
    credit: Optional[float] = None
    amount: float
    running_balance: Optional[float] = None
    category: str
    source_location: Optional[str] = None


# --- Document ---
class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    file_type: str
    file_size_bytes: int
    document_category: str
    document_scope: str
    classification_confidence: float
    needs_user_classification: bool
    reporting_period: Optional[str] = None
    currency: str
    entity_name: Optional[str] = None
    processing_status: str
    analysis_status: str
    extraction_method: Optional[str] = None
    ocr_used: bool
    page_count: int
    error_message: Optional[str] = None
    warnings: List[str] = []
    uploaded_at: datetime
    processed_at: Optional[datetime] = None


class DocumentDetailOut(DocumentOut):
    metrics: List[ExtractedMetricOut] = []
    transactions_count: int = 0
    anomalies_count: int = 0
    structured_summary: Dict[str, Any] = {}
    extracted_tables: List[Dict[str, Any]] = []


class DocumentClassifyRequest(BaseModel):
    document_category: str
    document_scope: Optional[str] = None
    reporting_period: Optional[str] = None
    currency: Optional[str] = None


# --- Analysis ---
class AnalysisResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    executive_summary: str
    ratios: List[Dict[str, Any]] = []
    insights: List[Dict[str, Any]] = []
    risk_indicators: List[Dict[str, Any]] = []
    limitations: List[str] = []
    chart_data: Dict[str, Any] = {}
    ai_generated: bool
    created_at: datetime


# --- Anomaly ---
class AnomalyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    transaction_id: Optional[int] = None
    anomaly_type: str
    title: str
    metric_or_transaction: str
    detected_amount: Optional[float] = None
    expected_comparison: Optional[str] = None
    reason: str
    observation: str
    severity: str
    detection_method: str
    source_location: Optional[str] = None
    reviewed: bool
    created_at: datetime


# --- Chat ---
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    role: str
    content: str
    citations: List[Dict[str, Any]] = []
    created_at: datetime


# --- Comparison ---
class CompareRequest(BaseModel):
    document_ids: List[int] = Field(..., min_length=2)


# --- Reports ---
class ReportGenerateRequest(BaseModel):
    document_id: int
    report_format: str = Field(..., pattern="^(pdf|xlsx)$")
    report_title: Optional[str] = None


class GeneratedReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: Optional[int] = None
    report_title: str
    report_format: str
    created_at: datetime


# --- Dashboard ---
class DashboardSummaryOut(BaseModel):
    total_documents: int
    total_reports: int
    total_anomalies: int
    recent_activity_count: int
    recent_documents: List[DocumentOut]
    financial_overview: Dict[str, Any]
    recent_activity: List[Dict[str, Any]]


# --- Settings / System status ---
class SystemStatusOut(BaseModel):
    llm_configured: bool
    llm_provider: str
    llm_model: str
    ocr_available: bool
    faiss_available: bool
    max_upload_size_mb: int
