"use client";

import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

/**
 * Wraps protected content. Redirects to /login if auth is required
 * and the user is not authenticated.
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { ready, authRequired, authenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && authRequired && !authenticated) {
      router.replace("/login");
    }
  }, [ready, authRequired, authenticated, router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (authRequired && !authenticated) {
    return null;
  }

  return <>{children}</>;
}
