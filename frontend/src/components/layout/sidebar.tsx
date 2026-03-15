"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileText,
  Search,
  Network,
  Scale,
  FolderKanban,
  Cable,
  Shield,
  Settings,
  X,
} from "lucide-react";
import { useMobileNav } from "@/components/layout/mobile-nav-context";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/briefings", label: "Briefings", icon: FileText },
  { href: "/projects", label: "Projekte", icon: FolderKanban },
  { href: "/search", label: "Suche", icon: Search },
  { href: "/knowledge", label: "Knowledge", icon: Network },
  { href: "/decisions", label: "Entscheidungen", icon: Scale },
  { href: "/connectors", label: "Konnektoren", icon: Cable },
  { href: "/admin", label: "Admin", icon: Shield },
  { href: "/settings", label: "Einstellungen", icon: Settings },
] as const;

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <>
      <div className="flex h-16 items-center justify-between border-b border-gray-200 px-6">
        <span className="text-xl font-bold text-gray-900">PWBS</span>
        {onNavigate && (
          <button
            onClick={onNavigate}
            className="flex h-11 w-11 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 md:hidden"
            aria-label="Navigation schliessen"
          >
            <X aria-hidden="true" className="h-5 w-5" />
          </button>
        )}
      </div>
      <nav className="flex-1 space-y-1 px-3 py-4" aria-label="Hauptnavigation">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              aria-current={isActive ? "page" : undefined}
              className={`flex min-h-[44px] items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-gray-100 text-gray-900"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              }`}
            >
              <Icon className="h-5 w-5" aria-hidden="true" />
              {label}
            </Link>
          );
        })}
      </nav>
    </>
  );
}

export function Sidebar() {
  const { isOpen, close } = useMobileNav();
  const pathname = usePathname();

  // Close mobile nav on route change
  useEffect(() => {
    close();
  }, [pathname, close]);

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className="hidden h-screen w-64 flex-col border-r border-gray-200 bg-white md:flex"
        aria-label="Seitennavigation"
      >
        <SidebarContent />
      </aside>

      {/* Mobile Overlay */}
      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/50 md:hidden"
            onClick={close}
            aria-hidden="true"
          />
          <aside
            className="fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-white shadow-xl md:hidden"
            aria-label="Seitennavigation"
            role="dialog"
            aria-modal="true"
          >
            <SidebarContent onNavigate={close} />
          </aside>
        </>
      )}
    </>
  );
}
