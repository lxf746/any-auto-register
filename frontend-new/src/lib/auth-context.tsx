"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useRouter, usePathname } from "next/navigation";
import { authApi } from "@/lib/api-client";
import { getToken, removeToken, setToken } from "@/lib/auth";
import { getWebSocketClient } from "@/lib/websocket";

interface AuthState {
  /** Whether auth check has completed */
  ready: boolean;
  /** Whether a password is required */
  authRequired: boolean;
  /** Whether the user is authenticated */
  authenticated: boolean;
  /** Login with password */
  login: (password: string) => Promise<void>;
  /** Logout and clear token */
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [authRequired, setAuthRequired] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);

  // Check auth status on mount
  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const data = await authApi.check();
        if (cancelled) return;
        setAuthRequired(data.required);

        if (!data.required) {
          // No password required → always authenticated
          setAuthenticated(true);
          // Connect WebSocket (no auth needed)
          const ws = getWebSocketClient();
          ws.connect("");
        } else {
          // Password required → check if we have a token
          const token = getToken();
          setAuthenticated(token !== null);
          // Connect WebSocket with token if available
          if (token) {
            const ws = getWebSocketClient();
            ws.connect(token);
          }
        }
      } catch {
        // Backend unreachable or error → assume no auth required
        if (!cancelled) {
          setAuthRequired(false);
          setAuthenticated(true);
        }
      } finally {
        if (!cancelled) setReady(true);
      }
    }

    check();
    return () => { cancelled = true; };
  }, []);

  const login = useCallback(
    async (password: string) => {
      const data = await authApi.login(password);
      setToken(data.token);
      setAuthenticated(true);
      // Connect WebSocket with new token
      const ws = getWebSocketClient();
      ws.connect(data.token);
    },
    []
  );

  const logout = useCallback(() => {
    removeToken();
    setAuthenticated(false);
    router.push("/login");
  }, [router]);

  return (
    <AuthContext.Provider value={{ ready, authRequired, authenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
