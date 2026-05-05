export type RequestStatus =
  | "draft"
  | "landscape"
  | "gaps"
  | "studies"
  | "iep"
  | "in_review"
  | "approved"
  | "rejected";

export interface RequestSummary {
  request_id: string;
  created_at: string;
  updated_at: string;
  title: string;
  drug_id: string;
  therapy_area_id: string;
  geography_id: string;
  lifecycle_stage: string;
  status: RequestStatus | string;
}

export interface Citation {
  cite_id: string;
  source_type: string;
  label: string;
  detail: string;
  url?: string | null;
  confidence: number;
}

export interface RequestDetail extends RequestSummary {
  tpp_summary: string;
  drug_name?: string | null;
  therapy_area_name?: string | null;
  geography_name?: string | null;
  landscape?: LandscapePayload | null;
  gaps?: GapPayload | null;
  studies?: StudiesPayload | null;
  iep?: IepPayload | null;
}

export interface LandscapePayload {
  literature: Record<string, unknown>[];
  hta_decisions: Record<string, unknown>[];
  rwe_studies: Record<string, unknown>[];
  narrative: string;
  citations: Citation[];
}

export interface GapPayload {
  matrix: Record<string, unknown>[];
  narrative: string;
  citations: Citation[];
}

export interface StudiesPayload {
  recommendations: Record<string, unknown>[];
  narrative: string;
  citations: Citation[];
}

export interface IepPayload {
  sections: {
    heading: string;
    paragraphs: { text: string; cite_ids: string[]; confidence: number }[];
  }[];
  citations: Citation[];
}

export interface KpiRow {
  kpi_id: string;
  name: string;
  baseline: string;
  target: string;
  unit: string;
}

export interface ChatMessage {
  message_id: string;
  request_id: string;
  role: string;
  content: string;
  timestamp: string;
}
