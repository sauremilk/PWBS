import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { WebSocketProvider } from "@/components/layout/websocket-provider";
import { SkipLink } from "@/components/ui/skip-link";
import { OnboardingGate } from "@/components/onboarding/onboarding-gate";
import { OnboardingSkipBanner } from "@/components/onboarding/skip-banner";
import { MobileNavProvider } from "@/components/layout/mobile-nav-context";
import { FeedbackWidget } from "@/components/feedback/feedback-widget";
import { ErrorBoundary } from "@/components/ui/error-boundary";

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
          <div className="flex min-h-screen bg-surface-secondary">
            <Sidebar />
            <div className="flex min-w-0 flex-1 flex-col">
              <Header />
              <main
                id="main-content"
                className="flex-1 overflow-x-hidden p-4 sm:p-6 lg:p-8"
                tabIndex={-1}
              >
                <div className="mx-auto max-w-7xl animate-fade-in">
                  <OnboardingSkipBanner />
                  <ErrorBoundary>{children}</ErrorBoundary>
                </div>
              </main>
              <FeedbackWidget />
            </div>
          </div>
        </MobileNavProvider>
      </WebSocketProvider>
    </ProtectedRoute>
  );
}
