import { apiClient } from "@/lib/api-client";

export interface SubmitFeedbackRequest {
  feedback_type: "bug" | "feature" | "praise";
  message: string;
  context: {
    url: string;
    browser_info: string;
    viewport_size: string;
  };
}

export interface SubmitFeedbackResponse {
  id: string;
  message: string;
}

export async function submitFeedback(
  data: SubmitFeedbackRequest,
): Promise<SubmitFeedbackResponse> {
  return apiClient.post<SubmitFeedbackResponse>("/feedback", data);
}
