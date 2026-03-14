import { apiClient } from "@/lib/api-client";
import type {
  BriefingListResponse,
  BriefingDetailResponse,
  GenerateRequest,
  GenerateResponse,
  FeedbackRequest,
  FeedbackResponse,
} from "@/types/api";

export async function listBriefings(
  params?: {
    type?: string;
    limit?: number;
    offset?: number;
  },
): Promise<BriefingListResponse> {
  const query = new URLSearchParams();
  if (params?.type) query.set("type", params.type);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));

  const qs = query.toString();
  return apiClient.get<BriefingListResponse>(
    `/briefings${qs ? `?${qs}` : ""}`,
  );
}

export async function getBriefing(id: string): Promise<BriefingDetailResponse> {
  return apiClient.get<BriefingDetailResponse>(
    `/briefings/${encodeURIComponent(id)}`,
  );
}

export async function generateBriefing(
  data: GenerateRequest,
): Promise<GenerateResponse> {
  return apiClient.post<GenerateResponse>("/briefings/generate", data);
}

export async function submitFeedback(
  briefingId: string,
  data: FeedbackRequest,
): Promise<FeedbackResponse> {
  return apiClient.post<FeedbackResponse>(
    `/briefings/${encodeURIComponent(briefingId)}/feedback`,
    data,
  );
}
