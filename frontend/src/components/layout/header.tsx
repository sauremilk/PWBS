"use client";

import { Menu } from "lucide-react";
import { NotificationBell } from "@/components/reminders/notification-bell";
import { useMobileNav } from "@/components/layout/mobile-nav-context";

interface HeaderProps {
  title?: string;
}

export function Header({ title }: HeaderProps) {
  const { toggle } = useMobileNav();

  return (
    <header
      className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-4 sm:px-6"
      role="banner"
    >
      <div className="flex items-center gap-3">
        <button
          onClick={toggle}
          className="flex h-11 w-11 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 md:hidden"
          aria-label="Navigation oeffnen"
        >
          <Menu aria-hidden="true" className="h-5 w-5" />
        </button>
        <h1 className="text-lg font-semibold text-gray-900">{title}</h1>
      </div>
      <div className="flex items-center gap-3">
        <NotificationBell />
      </div>
    </header>
  );
}
