import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { WebSocketProvider } from "@/components/layout/websocket-provider";
import { SkipLink } from "@/components/ui/skip-link";
import { OnboardingGate } from "@/components/onboarding/onboarding-gate";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <WebSocketProvider>
        <SkipLink />
        <OnboardingGate />
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex flex-1 flex-col">
            <Header />
            <main id="main-content" className="flex-1 p-6" tabIndex={-1}>
              {children}
            </main>
          </div>
        </div>
      </WebSocketProvider>
    </ProtectedRoute>
  );
}
