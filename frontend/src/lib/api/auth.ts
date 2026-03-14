import { apiClient, setTokens, clearTokens } from "@/lib/api-client";
import type {
  RegisterRequest,
  RegisterResponse,
  LoginRequest,
  LoginResponse,
  LogoutResponse,
  RefreshResponse,
  MeResponse,
} from "@/types/api";

export async function register(data: RegisterRequest): Promise<RegisterResponse> {
  const res = await apiClient.post<RegisterResponse>("/auth/register", data, {
    skipAuth: true,
  });
  setTokens(res.access_token, res.refresh_token);
  return res;
}

export async function login(data: LoginRequest): Promise<LoginResponse> {
  const res = await apiClient.post<LoginResponse>("/auth/login", data, {
    skipAuth: true,
  });
  setTokens(res.access_token, res.refresh_token);
  return res;
}

export async function logout(refreshToken: string): Promise<LogoutResponse> {
  const res = await apiClient.post<LogoutResponse>("/auth/logout", {
    refresh_token: refreshToken,
  });
  clearTokens();
  return res;
}

export async function refreshTokens(
  refreshToken: string,
): Promise<RefreshResponse> {
  const res = await apiClient.post<RefreshResponse>(
    "/auth/refresh",
    { refresh_token: refreshToken },
    { skipAuth: true },
  );
  setTokens(res.access_token, res.refresh_token);
  return res;
}

export async function getMe(): Promise<MeResponse> {
  return apiClient.get<MeResponse>("/auth/me");
}
