/**
 * Type-safe API client using generated OpenAPI types.
 *
 * This file imports the generated types from api-types.ts and provides
 * typed wrappers around the base API client.
 */

import { api, ApiError } from "./api";

// Re-export generated types so consumers can import them from here
export type { paths, components } from "./api-types";
export { ApiError };

/**
 * Auth API calls
 */
export const authApi = {
  /** Check if authentication is required */
  check: () => api.get<{ required: boolean }>("/v2/auth/check"),

  /** Login with password, returns session token */
  login: (password: string) =>
    api.post<{ token: string }>("/v2/auth/login", { password }),
};

/**
 * Platforms API calls
 */
export const platformsApi = {
  /** List all available platforms */
  list: () => api.get<unknown[]>("/v2/platforms"),
};

/**
 * Stats API calls
 */
export const statsApi = {
  /** Get global stats overview */
  overview: () =>
    api.get<{
      total_registrations: number;
      success: number;
      failed: number;
      success_rate: number;
      total_accounts: number;
      account_distribution: Record<string, number>;
    }>("/v2/stats/overview"),
};
