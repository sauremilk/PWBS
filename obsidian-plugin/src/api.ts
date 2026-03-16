import { requestUrl } from "obsidian";

export interface BriefingResponse {
  id: string;
  type: string;
  title: string;
  content: string;
  sources: { title: string; source_type: string; source_id: string }[];
  created_at: string;
}

export interface UploadResponse {
  documents_count: number;
  deleted_count: number;
  message: string;
}

export interface UserInfo {
  id: string;
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
    return this.request<UserInfo>("GET", "/api/v1/user/me");
  }

  async uploadVault(zipData: ArrayBuffer): Promise<UploadResponse> {
    return this.request<UploadResponse>(
      "POST",
      "/api/v1/connectors/obsidian/upload",
      zipData,
      "application/zip",
    );
  }

  async getLatestBriefing(): Promise<BriefingResponse | null> {
    try {
      return await this.request<BriefingResponse>(
        "GET",
        "/api/v1/briefings/latest",
      );
    } catch (e) {
      if (e instanceof PwbsAPIError && e.status === 404) {
        return null;
      }
      throw e;
    }
  }

  async getBriefings(limit = 5): Promise<BriefingResponse[]> {
    return this.request<BriefingResponse[]>(
      "GET",
      `/api/v1/briefings?limit=${limit}`,
    );
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
