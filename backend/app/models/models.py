from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    JSON,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    company_or_role = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    preferred_currency = Column(String(16), default="PKR", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    reports = relationship("GeneratedReport", back_populates="owner", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_type = Column(String(32), nullable=False)  # pdf, csv, xlsx
    file_size_bytes = Column(Integer, nullable=False)
    file_hash = Column(String(64), nullable=True)

    # Classification & metadata
    document_category = Column(String(64), default="unknown", nullable=False)
    # e.g., income_statement, balance_sheet, cash_flow_statement, annual_report,
    # bank_statement, transaction_history, expense_report, unknown
    document_scope = Column(String(32), default="corporate", nullable=False)  # corporate | personal
    classification_confidence = Column(Float, default=0.0, nullable=False)
    needs_user_classification = Column(Boolean, default=False, nullable=False)
    reporting_period = Column(String(128), nullable=True)
    currency = Column(String(16), default="PKR", nullable=False)
    entity_name = Column(String(255), nullable=True)

    # Processing status
    processing_status = Column(String(32), default="pending", nullable=False)
    # pending | extracting | analyzing | completed | failed | needs_classification
    analysis_status = Column(String(32), default="pending", nullable=False)
    # pending | completed | partial | failed
    extraction_method = Column(String(64), nullable=True)  # selectable_text | table_parser | ocr | pandas_csv | openpyxl
    ocr_used = Column(Boolean, default=False, nullable=False)
    page_count = Column(Integer, default=1, nullable=False)
    error_message = Column(Text, nullable=True)
    warnings = Column(JSON, default=list)

    # Raw/structured extracted content
    raw_text = Column(Text, nullable=True)
    extracted_tables = Column(JSON, default=list)
    structured_summary = Column(JSON, default=dict)

    uploaded_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", back_populates="documents")
    metrics = relationship("ExtractedMetric", back_populates="document", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="document", cascade="all, delete-orphan")
    analysis = relationship("AnalysisResult", back_populates="document", uselist=False, cascade="all, delete-orphan")
    anomalies = relationship("Anomaly", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="document", cascade="all, delete-orphan")


class ExtractedMetric(Base):
    __tablename__ = "extracted_metrics"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    metric_key = Column(String(128), nullable=False, index=True)  # canonical key e.g. revenue, net_income
    metric_label = Column(String(255), nullable=False)
    value = Column(Float, nullable=False)
    currency = Column(String(16), default="PKR", nullable=False)
    period = Column(String(128), nullable=True)
    category = Column(String(64), nullable=True)  # income_statement, balance_sheet, cash_flow, summary
    source_location = Column(String(255), nullable=True)  # e.g., "Page 2, Table 1, Row 3" or "Sheet 'P&L', Cell B12"
    source_snippet = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)


    document = relationship("Document", back_populates="metrics")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    transaction_date = Column(String(32), nullable=True, index=True)
    description = Column(Text, nullable=False)
    debit = Column(Float, nullable=True)
    credit = Column(Float, nullable=True)
    amount = Column(Float, nullable=False)  # signed: negative for debit/outflow, positive for credit/inflow
    running_balance = Column(Float, nullable=True)
    category = Column(String(64), default="Uncategorized", nullable=False)
    source_location = Column(String(255), nullable=True)

    document = relationship("Document", back_populates="transactions")
    anomalies = relationship("Anomaly", back_populates="transaction")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), unique=True, nullable=False)

    executive_summary = Column(Text, nullable=False)
    ratios = Column(JSON, default=list)  # list of {name, key, value, formatted, formula, calculation, interpretation, status, inputs}
    insights = Column(JSON, default=list)  # list of {title, observation, evidence, source, observation_type}
    risk_indicators = Column(JSON, default=list)  # list of {title, severity, description, evidence, kind: confirmed|ai_interpretation}
    limitations = Column(JSON, default=list)
    chart_data = Column(JSON, default=dict)
    ai_generated = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    document = relationship("Document", back_populates="analysis")


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)

    anomaly_type = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    metric_or_transaction = Column(String(255), nullable=False)
    detected_amount = Column(Float, nullable=True)
    expected_comparison = Column(String(255), nullable=True)
    reason = Column(Text, nullable=False)
    observation = Column(Text, nullable=False)
    severity = Column(String(16), default="medium", nullable=False)  # low | medium | high
    detection_method = Column(String(64), default="statistical", nullable=False)  # rule | statistical | isolation_forest
    source_location = Column(String(255), nullable=True)
    reviewed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    document = relationship("Document", back_populates="anomalies")
    transaction = relationship("Transaction", back_populates="anomalies")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    source_label = Column(String(255), nullable=False)  # e.g., "Page 1" or "Sheet1 Rows 1-25"
    content = Column(Text, nullable=False)
    embedding_json = Column(JSON, nullable=True)

    document = relationship("Document", back_populates="chunks")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    role = Column(String(16), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    citations = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    document = relationship("Document", back_populates="chat_messages")


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)

    report_title = Column(String(255), nullable=False)
    report_format = Column(String(16), nullable=False)  # pdf | xlsx
    stored_filename = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    owner = relationship("User", back_populates="reports")
