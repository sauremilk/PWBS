import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { WebSocketProvider } from "@/components/layout/websocket-provider";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <WebSocketProvider>
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex flex-1 flex-col">
            <Header />
            <main className="flex-1 p-6">{children}</main>
          </div>
        </div>
      </WebSocketProvider>
    </ProtectedRoute>
  );
}
