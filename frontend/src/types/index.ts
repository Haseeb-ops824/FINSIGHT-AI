export interface User {
  id: number;
  email: string;
  full_name: string;
  company_or_role?: string | null;
  preferred_currency: string;
  created_at: string;
}

export interface DocumentItem {
  id: number;
  original_filename: string;
  file_type: string;
  file_size_bytes: number;
  document_category: string;
  document_scope: string;
  classification_confidence: number;
  needs_user_classification: boolean;
  reporting_period?: string | null;
  currency: string;
  entity_name?: string | null;
  processing_status: string;
  analysis_status: string;
  extraction_method?: string | null;
  ocr_used: boolean;
  page_count: number;
  error_message?: string | null;
  warnings: string[];
  uploaded_at: string;
  processed_at?: string | null;
}

export interface ExtractedMetric {
  id: number;
  metric_key: string;
  metric_label: string;
  value: number;
  currency: string;
  period?: string | null;
  category?: string | null;
  source_location?: string | null;
  source_snippet?: string | null;
  confidence: number;
}

export interface TransactionItem {
  id: number;
  transaction_date?: string | null;
  description: string;
  debit?: number | null;
  credit?: number | null;
  amount: number;
  running_balance?: number | null;
  category: string;
  source_location?: string | null;
}

export interface DocumentDetail extends DocumentItem {
  metrics: ExtractedMetric[];
  transactions_count: number;
  anomalies_count: number;
  structured_summary: Record<string, unknown>;
  extracted_tables: Array<{
    location: string;
    headers: string[];
    rows: string[][];
  }>;
}

export interface FinancialRatio {
  name: string;
  key: string;
  value: number | null;
  formatted: string;
  formula: string;
  calculation: string;
  interpretation: string;
  status: 'healthy' | 'caution' | 'warning' | 'unavailable';
  inputs: Record<string, number>;
}

export interface FinancialInsight {
  title: string;
  observation: string;
  evidence: string;
  source?: string;
  observation_type: 'confirmed_fact' | 'ai_interpretation';
}

export interface RiskIndicator {
  title: string;
  severity: 'low' | 'medium' | 'high';
  description: string;
  evidence: string;
  kind: 'confirmed' | 'ai_interpretation';
}

export interface AnalysisResult {
  id: number;
  document_id: number;
  executive_summary: string;
  ratios: FinancialRatio[];
  insights: FinancialInsight[];
  risk_indicators: RiskIndicator[];
  limitations: string[];
  chart_data: Record<string, unknown>;
  ai_generated: boolean;
  created_at: string;
}

export interface AnomalyItem {
  id: number;
  document_id: number;
  transaction_id?: number | null;
  anomaly_type: string;
  title: string;
  metric_or_transaction: string;
  detected_amount?: number | null;
  expected_comparison?: string | null;
  reason: string;
  observation: string;
  severity: 'low' | 'medium' | 'high';
  detection_method: string;
  source_location?: string | null;
  reviewed: boolean;
  created_at: string;
}

export interface ChatCitation {
  source_label: string;
  snippet: string;
  score?: number;
}

export interface ChatMessage {
  id: number;
  document_id: number;
  role: 'user' | 'assistant';
  content: string;
  citations: ChatCitation[];
  created_at: string;
}

export interface GeneratedReport {
  id: number;
  document_id?: number | null;
  report_title: string;
  report_format: 'pdf' | 'xlsx';
  created_at: string;
}

export interface DashboardSummary {
  total_documents: number;
  total_reports: number;
  total_anomalies: number;
  recent_activity_count: number;
  recent_documents: DocumentItem[];
  financial_overview: Record<
    string,
    {
      label: string;
      value: number;
      currency: string;
      period?: string | null;
      document_id: number;
      document_name: string;
    }
  >;
  recent_activity: Array<{
    id: string;
    type: string;
    title: string;
    status: string;
    category: string;
    timestamp: string;
    document_id: number;
  }>;
}

export interface SystemStatus {
  llm_configured: boolean;
  llm_provider: string;
  llm_model: string;
  ocr_available: boolean;
  faiss_available: boolean;
  max_upload_size_mb: number;
}
