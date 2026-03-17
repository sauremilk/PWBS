import { requestUrl } from "obsidian";

export interface SourceRef {
  chunk_id: string;
  doc_title: string;
  source_type: string;
  date: string;
  relevance: number;
}

export interface BriefingResponse {
  id: string;
  briefing_type: string;
  title: string;
  content: string;
  source_chunks: string[];
  source_entities: string[];
  trigger_context: Record<string, unknown> | null;
  generated_at: string;
  expires_at: string | null;
  sources: SourceRef[];
}

interface BriefingListItem {
  id: string;
  briefing_type: string;
  title: string;
  generated_at: string;
  expires_at: string | null;
}

interface BriefingListResponse {
  briefings: BriefingListItem[];
  total: number;
  has_more: boolean;
}

export interface UploadResponse {
  connection_id: string;
  document_count: number;
  error_count: number;
  deleted_count: number;
  errors: { source_id: string; error: string }[];
}

export interface UserInfo {
  user_id: string;
  email: string;
  display_name: string;
}

export class PwbsAPI {
  constructor(
    private baseUrl: string,
    private token: string,
  ) {}

  updateConfig(baseUrl: string, token: string): void {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.token = token;
  }

  get isConfigured(): boolean {
    return this.baseUrl.length > 0 && this.token.length > 0;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: ArrayBuffer | string,
    contentType?: string,
  ): Promise<T> {
    const headers: Record<string, string> = {
      Authorization: `Bearer ${this.token}`,
    };
    if (contentType) {
      headers["Content-Type"] = contentType;
    }

    const response = await requestUrl({
      url: `${this.baseUrl}${path}`,
      method,
      headers,
      body: body,
      throw: false,
    });

    if (response.status === 401) {
      throw new PwbsAuthError("API-Token ungültig oder abgelaufen");
    }
    if (response.status >= 400) {
      const msg =
        response.json?.detail ?? response.text ?? `HTTP ${response.status}`;
      throw new PwbsAPIError(
        typeof msg === "string" ? msg : JSON.stringify(msg),
        response.status,
      );
    }

    return response.json as T;
  }

  async getMe(): Promise<UserInfo> {
    return this.request<UserInfo>("GET", "/api/v1/user/settings");
  }

  async uploadVault(zipData: ArrayBuffer): Promise<UploadResponse> {
    const boundary = "----PWBSUpload" + Date.now().toString(36);
    const encoder = new TextEncoder();

    const header = encoder.encode(
      `--${boundary}\r\n` +
        `Content-Disposition: form-data; name="file"; filename="vault.zip"\r\n` +
        `Content-Type: application/zip\r\n\r\n`,
    );
    const footer = encoder.encode(`\r\n--${boundary}--\r\n`);

    const combined = new Uint8Array(
      header.length + zipData.byteLength + footer.length,
    );
    combined.set(header, 0);
    combined.set(new Uint8Array(zipData), header.length);
    combined.set(footer, header.length + zipData.byteLength);

    return this.request<UploadResponse>(
      "POST",
      "/api/v1/connectors/obsidian/upload",
      combined.buffer,
      `multipart/form-data; boundary=${boundary}`,
    );
  }

  async getLatestBriefing(): Promise<BriefingResponse | null> {
    try {
      const briefings = await this.request<BriefingResponse[]>(
        "GET",
        "/api/v1/briefings/latest",
      );
      if (!briefings || briefings.length === 0) {
        return null;
      }
      // Return the most recent briefing (first in array)
      return briefings[0];
    } catch (e) {
      if (e instanceof PwbsAPIError && e.status === 404) {
        return null;
      }
      throw e;
    }
  }

  async getBriefings(limit = 5): Promise<BriefingListItem[]> {
    const response = await this.request<BriefingListResponse>(
      "GET",
      `/api/v1/briefings?limit=${limit}`,
    );
    return response.briefings;
  }
}

export class PwbsAuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PwbsAuthError";
  }
}

export class PwbsAPIError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "PwbsAPIError";
  }
}
