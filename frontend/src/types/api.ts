/**
 * TypeScript-Typen für die PWBS-API.
 * Abgeleitet aus den Backend Pydantic-Schemas.
 */

// ---------------------------------------------------------------------------
// Common
// ---------------------------------------------------------------------------

export type SourceType =
  | "google_calendar"
  | "google_drive"
  | "gmail"
  | "notion"
  | "obsidian"
  | "outlook_mail"
  | "zoom_transcript"
  | "slack"
  | "manual";

export interface ApiError {
  code: string;
  message: string;
  detail?: unknown;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  has_more: boolean;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
}

export interface RegisterResponse {
  user_id: string;
  access_token: string;
  refresh_token: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LogoutRequest {
  refresh_token: string;
}

export interface LogoutResponse {
  message: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface RefreshResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface MeResponse {
  user_id: string;
  email: string;
  display_name: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Connectors
// ---------------------------------------------------------------------------

export interface ConnectorType {
  type: string;
  name: string;
  description: string;
  auth_method: string;
  status: string | null;
}

export interface ConnectorListResponse {
  connectors: ConnectorType[];
}

export interface ConnectionStatus {
  type: string;
  status: string;
  doc_count: number;
  last_sync: string | null;
  error: string | null;
}

export interface ConnectionStatusResponse {
  connections: ConnectionStatus[];
}

export interface AuthUrlResponse {
  auth_url: string;
  state: string;
}

export interface CallbackRequest {
  code: string;
  state: string;
}

export interface CallbackResponse {
  connection_id: string;
  status: string;
  initial_sync_started: boolean;
}

export interface ConfigRequest {
  vault_path: string;
}

export interface ConfigResponse {
  connection_id: string;
  status: string;
  file_count: number;
}

export interface DisconnectResponse {
  message: string;
  deleted_doc_count: number;
}

export interface SyncResponse {
  status: string;
  docs_synced: number;
}

// ---------------------------------------------------------------------------
// Sync History (TASK-184)
// ---------------------------------------------------------------------------

export interface SyncRunItem {
  id: string;
  status: "pending" | "running" | "success" | "failed";
  started_at: string | null;
  completed_at: string | null;
  document_count: number;
  error_count: number;
  errors_json: Array<{ step: string; message: string }> | null;
  duration_seconds: number | null;
}

export interface SyncHistoryResponse {
  runs: SyncRunItem[];
  total: number;
  has_more: boolean;
}

// ---------------------------------------------------------------------------
// Consent (TASK-173)
// ---------------------------------------------------------------------------

export interface ConsentGrantRequest {
  consent_version: number;
}

export interface ConsentStatusResponse {
  connector_type: string;
  consented: boolean;
  consent_version: number | null;
  consented_at: string | null;
  data_types: string[];
  processing_purpose: string;
  llm_providers: string[];
}

export interface ConsentRevokeResponse {
  message: string;
  deleted_doc_count: number;
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

export interface SearchFilters {
  source_types?: SourceType[];
  date_from?: string;
  date_to?: string;
  entity_ids?: string[];
}

export interface SearchRequest {
  query: string;
  filters?: SearchFilters;
  limit?: number;
}

export interface SearchResult {
  chunk_id: string;
  doc_title: string;
  source_type: SourceType;
  date: string;
  content: string;
  score: number;
  entities: string[];
}

export interface SearchResponse {
  results: SearchResult[];
  answer: string | null;
}

// ---------------------------------------------------------------------------
// Briefings
// ---------------------------------------------------------------------------

export type BriefingType = "morning" | "meeting" | "project" | "weekly";

export interface BriefingListItem {
  id: string;
  briefing_type: BriefingType;
  title: string;
  generated_at: string;
  expires_at: string | null;
}

export interface BriefingListResponse {
  briefings: BriefingListItem[];
  total: number;
  has_more: boolean;
}

export interface SourceRefResponse {
  chunk_id: string;
  doc_title: string;
  source_type: string;
  date: string;
  relevance: number;
}

export interface BriefingDetailResponse {
  id: string;
  briefing_type: BriefingType;
  title: string;
  content: string;
  source_chunks: string[];
  source_entities: string[];
  trigger_context: Record<string, unknown> | null;
  generated_at: string;
  expires_at: string | null;
  sources: SourceRefResponse[];
}

export interface GenerateRequest {
  briefing_type: BriefingType;
  trigger_context?: Record<string, unknown>;
}

export interface GenerateResponse {
  briefing_id: string;
  status: string;
}

export interface FeedbackRequest {
  rating: "positive" | "negative";
  comment?: string;
}

export interface FeedbackResponse {
  briefing_id: string;
  rating: string;
  message: string;
}

// ---------------------------------------------------------------------------
// Knowledge
// ---------------------------------------------------------------------------

export interface EntityListItem {
  id: string;
  type: string;
  name: string;
  mention_count: number;
  last_seen: string | null;
}

export interface EntityListResponse {
  entities: EntityListItem[];
  total: number;
}

export interface RelatedEntityItem {
  id: string;
  type: string;
  name: string;
  mention_count: number;
  relation: string | null;
}

export interface EntityDetailResponse {
  id: string;
  type: string;
  name: string;
  normalized_name: string;
  mention_count: number;
  first_seen: string | null;
  last_seen: string | null;
  metadata: Record<string, unknown> | null;
  related_entities: RelatedEntityItem[];
}

export interface EntityDocumentItem {
  id: string;
  title: string | null;
  source_type: string;
  created_at: string;
}

export interface EntityDocumentsResponse {
  documents: EntityDocumentItem[];
  total: number;
}

export interface GraphNode {
  id: string;
  type: string;
  name: string;
  size: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  weight: number;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface PatternSourceRef {
  document_id: string;
  title: string;
  source_type: string;
  date: string;
}

export interface DetectedPattern {
  pattern_type: string;
  entity_id: string;
  entity_name: string;
  summary: string;
  context_count: number;
  first_seen: string;
  last_seen: string;
  sources: PatternSourceRef[];
}

export interface PatternListResponse {
  patterns: DetectedPattern[];
  total: number;
}

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

export interface DocumentListItem {
  id: string;
  title: string | null;
  source_type: string;
  source_id: string;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  documents: DocumentListItem[];
  total: number;
}

export interface ChunkEntity {
  entity_id: string;
  name: string;
  entity_type: string;
  confidence: number;
}

export interface ChunkDetail {
  id: string;
  index: number;
  content_preview: string | null;
  entities: ChunkEntity[];
}

export interface DocumentDetailResponse {
  id: string;
  title: string | null;
  source_type: string;
  source_id: string;
  chunk_count: number;
  language: string;
  processing_status: string;
  created_at: string;
  updated_at: string;
  chunks: ChunkDetail[];
}

// ---------------------------------------------------------------------------
// Reminders (TASK-132)
// ---------------------------------------------------------------------------

export type ReminderType = "follow_up" | "inactive_topic" | "open_question";
export type ReminderStatus =
  | "pending"
  | "acknowledged"
  | "dismissed"
  | "snoozed";
export type ReminderUrgency = "high" | "medium" | "low";
export type ReminderFrequency = "daily" | "weekly" | "off";

export interface Reminder {
  id: string;
  reminder_type: ReminderType;
  title: string;
  description: string;
  status: ReminderStatus;
  urgency: ReminderUrgency;
  due_at: string | null;
  responsible_person: string | null;
  source_document_id: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface ReminderListResponse {
  items: Reminder[];
  count: number;
}

export interface UpdateReminderStatusRequest {
  status: ReminderStatus;
}

// ---------------------------------------------------------------------------
// User / Settings
// ---------------------------------------------------------------------------

export interface UserSettingsResponse {
  user_id: string;
  email: string;
  display_name: string;
  timezone: string;
  language: string;
  briefing_auto_generate: boolean;
  reminder_frequency: ReminderFrequency;
}

export interface UserSettingsUpdate {
  timezone?: string;
  language?: string;
  briefing_auto_generate?: boolean;
  display_name?: string;
  reminder_frequency?: ReminderFrequency;
}

export interface ExportStartResponse {
  export_id: string;
  status: string;
}

export interface ExportStatusResponse {
  export_id: string;
  status: string;
  download_url: string | null;
  created_at: string | null;
}

export interface AccountDeletionRequest {
  password: string;
  confirmation: "DELETE";
}

export interface AccountDeletionResponse {
  message: string;
  deletion_scheduled_at: string | null;
}

export interface CancelDeletionResponse {
  message: string;
}

export interface AuditLogEntry {
  id: number;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  created_at: string;
}

export interface AuditLogResponse {
  entries: AuditLogEntry[];
  total: number;
}

export interface StorageLayerStatus {
  layer: string;
  encrypted: boolean;
  encryption_type: string | null;
  note: string | null;
}

export interface SecurityStatusResponse {
  storage_layers: StorageLayerStatus[];
  data_location: string;
  llm_usage: string;
}

// ---------------------------------------------------------------------------
// Decisions (TASK-130)
// ---------------------------------------------------------------------------

export type DecisionStatus = "pending" | "made" | "revised";

export interface DecisionListItem {
  id: string;
  summary: string;
  status: DecisionStatus;
  decided_by: string | null;
  decided_at: string | null;
  created_at: string;
}

export interface DecisionListResponse {
  decisions: DecisionListItem[];
  total: number;
}

export interface DecisionDetailResponse {
  id: string;
  summary: string;
  pro_arguments: string[];
  contra_arguments: string[];
  assumptions: string[];
  dependencies: string[];
  status: DecisionStatus;
  decided_by: string | null;
  decided_at: string | null;
  source_document_id: string | null;
  neo4j_node_id: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DecisionCreateRequest {
  summary: string;
  pro_arguments?: string[];
  contra_arguments?: string[];
  assumptions?: string[];
  dependencies?: string[];
  status?: DecisionStatus;
  decided_by?: string | null;
  decided_at?: string | null;
  source_document_id?: string | null;
  expires_at?: string | null;
}

export interface DecisionUpdateRequest {
  summary?: string;
  pro_arguments?: string[];
  contra_arguments?: string[];
  assumptions?: string[];
  dependencies?: string[];
  status?: DecisionStatus;
  decided_by?: string | null;
  decided_at?: string | null;
  expires_at?: string | null;
}

// ---------------------------------------------------------------------------
// Data Transparency Report (TASK-172)
// ---------------------------------------------------------------------------

export interface SourceStats {
  source_type: string;
  document_count: number;
  oldest_document: string | null;
  newest_document: string | null;
}

export interface ConnectionInfo {
  source_type: string;
  status: string;
  last_sync: string | null;
}

export interface LlmProviderUsage {
  provider: string;
  model: string;
  total_input_tokens: number;
  total_output_tokens: number;
  call_count: number;
}

export interface DataReportResponse {
  total_documents: number;
  sources: SourceStats[];
  connections: ConnectionInfo[];
  llm_provider_usage: LlmProviderUsage[];
}

export interface LlmUsageEntry {
  id: string;
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  purpose: string;
  created_at: string;
}

export interface LlmUsageResponse {
  entries: LlmUsageEntry[];
  total: number;
}
