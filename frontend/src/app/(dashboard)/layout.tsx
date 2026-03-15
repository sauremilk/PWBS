import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { WebSocketProvider } from "@/components/layout/websocket-provider";
import { SkipLink } from "@/components/ui/skip-link";
import { OnboardingGate } from "@/components/onboarding/onboarding-gate";
import { MobileNavProvider } from "@/components/layout/mobile-nav-context";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <WebSocketProvider>
        <MobileNavProvider>
          <SkipLink />
          <OnboardingGate />
          <div className="flex min-h-screen">
            <Sidebar />
            <div className="flex min-w-0 flex-1 flex-col">
              <Header />
              <main id="main-content" className="flex-1 overflow-x-hidden p-4 sm:p-6" tabIndex={-1}>
                {children}
              </main>
            </div>
          </div>
        </MobileNavProvider>
      </WebSocketProvider>
    </ProtectedRoute>
  );
}
