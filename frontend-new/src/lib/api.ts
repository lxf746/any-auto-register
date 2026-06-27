/**
 * Typed API client for communicating with the backend.
 */

const API_BASE = "/api";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export interface ApiResponse<T = unknown> {
  ok: boolean;
  data: T;
  error?: string;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    throw new ApiError(`Request failed: ${res.statusText}`, res.status);
  }

  const json = await res.json();

  // Handle v2 envelope format: { ok, data, error }
  if (json && typeof json === "object" && "ok" in json && "data" in json) {
    if (!json.ok && json.error) {
      throw new ApiError(json.error, res.status);
    }
    return json.data as T;
  }

  throw new ApiError("Invalid API response format: expected v2 envelope", res.status);
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
