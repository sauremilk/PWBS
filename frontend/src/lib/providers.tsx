"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, createContext, useContext } from "react";

// Auth-Context Placeholder (vollstaendige Implementierung: TASK-117)
interface AuthContextType {
  isAuthenticated: boolean;
  user: { id: string; email: string } | null;
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  user: null,
});

export function useAuth(): AuthContextType {
  return useContext(AuthContext);
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={{ isAuthenticated: false, user: null }}>
        {children}
      </AuthContext.Provider>
    </QueryClientProvider>
  );
}
