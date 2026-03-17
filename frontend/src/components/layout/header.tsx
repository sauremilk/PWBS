"use client";

import { Menu } from "lucide-react";
import { NotificationBell } from "@/components/reminders/notification-bell";
import { ChangelogButton } from "@/components/layout/changelog";
import { useMobileNav } from "@/components/layout/mobile-nav-context";

interface HeaderProps {
  title?: string;
}

export function Header({ title }: HeaderProps) {
  const { toggle } = useMobileNav();

  return (
    <header
      className="flex h-14 items-center justify-between border-b border-border bg-surface px-4 sm:px-6"
      role="banner"
    >
      <div className="flex items-center gap-3">
        <button
          onClick={toggle}
          className="flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary hover:bg-surface-secondary hover:text-text md:hidden"
          aria-label="Navigation oeffnen"
        >
          <Menu aria-hidden="true" className="h-5 w-5" />
        </button>
        {title && (
          <h1 className="text-base font-semibold text-text">{title}</h1>
        )}
      </div>
      <div className="flex items-center gap-1">
        <ChangelogButton />
        <NotificationBell />
      </div>
    </header>
  );
}
