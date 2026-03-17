"use client";

import { useEffect, useState, useRef } from "react";
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
  LogOut,
  ChevronDown,
  Sparkles,
} from "lucide-react";
import { useMobileNav } from "@/components/layout/mobile-nav-context";
import { useAuth } from "@/lib/providers";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/briefings", label: "Briefings", icon: FileText },
  { href: "/projects", label: "Projekte", icon: FolderKanban },
  { href: "/search", label: "Suche", icon: Search },
  { href: "/knowledge", label: "Knowledge", icon: Network },
  { href: "/decisions", label: "Entscheidungen", icon: Scale },
  { href: "/connectors", label: "Konnektoren", icon: Cable },
  { href: "/admin", label: "Admin", icon: Shield },
] as const;

function UserAvatar({
  name,
  size = "sm",
}: {
  name: string;
  size?: "sm" | "md";
}) {
  const initials = name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
  const sizeClass = size === "md" ? "h-9 w-9 text-sm" : "h-7 w-7 text-xs";

  return (
    <div
      className={`flex ${sizeClass} items-center justify-center rounded-full bg-brand/20 font-semibold text-brand-light`}
    >
      {initials}
    </div>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        userMenuRef.current &&
        !userMenuRef.current.contains(e.target as Node)
      ) {
        setUserMenuOpen(false);
      }
    }
    if (userMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [userMenuOpen]);

  return (
    <div className="flex h-full flex-col">
      {/* Logo */}
      <div className="flex h-16 items-center justify-between px-5">
        <Link
          href="/"
          className="flex items-center gap-2.5"
          onClick={onNavigate}
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight text-sidebar-text-active">
            PWBS
          </span>
        </Link>
        {onNavigate && (
          <button
            onClick={onNavigate}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-sidebar-text hover:bg-sidebar-hover md:hidden"
            aria-label="Navigation schliessen"
          >
            <X aria-hidden="true" className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav
        className="flex-1 space-y-0.5 px-3 py-3"
        aria-label="Hauptnavigation"
      >
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              aria-current={isActive ? "page" : undefined}
              className={`group flex min-h-[40px] items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all ${
                isActive
                  ? "bg-sidebar-active text-sidebar-text-active shadow-sm"
                  : "text-sidebar-text hover:bg-sidebar-hover hover:text-sidebar-text-active"
              }`}
            >
              <Icon
                className={`h-[18px] w-[18px] transition-colors ${
                  isActive
                    ? "text-brand-light"
                    : "text-sidebar-text group-hover:text-sidebar-text-active"
                }`}
                aria-hidden="true"
              />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Settings Link */}
      <div className="px-3 pb-2">
        <Link
          href="/settings"
          onClick={onNavigate}
          className={`group flex min-h-[40px] items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all ${
            pathname.startsWith("/settings")
              ? "bg-sidebar-active text-sidebar-text-active shadow-sm"
              : "text-sidebar-text hover:bg-sidebar-hover hover:text-sidebar-text-active"
          }`}
        >
          <Settings
            className={`h-[18px] w-[18px] transition-colors ${
              pathname.startsWith("/settings")
                ? "text-brand-light"
                : "text-sidebar-text group-hover:text-sidebar-text-active"
            }`}
            aria-hidden="true"
          />
          Einstellungen
        </Link>
      </div>

      {/* User section */}
      <div
        className="relative border-t border-white/10 px-3 py-3"
        ref={userMenuRef}
      >
        <button
          onClick={() => setUserMenuOpen((prev) => !prev)}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all hover:bg-sidebar-hover"
          aria-expanded={userMenuOpen}
          aria-haspopup="true"
        >
          <UserAvatar name={user?.display_name ?? "U"} size="md" />
          <div className="min-w-0 flex-1 text-left">
            <p className="truncate text-sm font-medium text-sidebar-text-active">
              {user?.display_name ?? "Benutzer"}
            </p>
            <p className="truncate text-xs text-sidebar-text">
              {user?.email ?? ""}
            </p>
          </div>
          <ChevronDown
            className={`h-4 w-4 text-sidebar-text transition-transform ${
              userMenuOpen ? "rotate-180" : ""
            }`}
            aria-hidden="true"
          />
        </button>

        {/* User dropdown menu */}
        {userMenuOpen && (
          <div className="absolute bottom-full left-3 right-3 mb-1 animate-scale-in rounded-lg border border-white/10 bg-sidebar-hover p-1 shadow-xl">
            <Link
              href="/settings"
              onClick={() => {
                setUserMenuOpen(false);
                onNavigate?.();
              }}
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-sidebar-text hover:bg-sidebar-active hover:text-sidebar-text-active"
            >
              <Settings className="h-4 w-4" aria-hidden="true" />
              Einstellungen
            </Link>
            <button
              onClick={() => {
                setUserMenuOpen(false);
                logout();
              }}
              className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-red-400 hover:bg-sidebar-active hover:text-red-300"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              Abmelden
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export function Sidebar() {
  const { isOpen, close } = useMobileNav();
  const pathname = usePathname();

  useEffect(() => {
    close();
  }, [pathname, close]);

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className="hidden h-screen w-[260px] flex-shrink-0 flex-col bg-sidebar md:flex"
        aria-label="Seitennavigation"
      >
        <SidebarContent />
      </aside>

      {/* Mobile Overlay */}
      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
            onClick={close}
            aria-hidden="true"
          />
          <aside
            className="fixed inset-y-0 left-0 z-50 flex w-[280px] flex-col bg-sidebar shadow-2xl md:hidden"
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
