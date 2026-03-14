"use client";

import { NotificationBell } from "@/components/reminders/notification-bell";

interface HeaderProps {
  title?: string;
}

export function Header({ title }: HeaderProps) {
  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6" role="banner">
      <h1 className="text-lg font-semibold text-gray-900">{title}</h1>
      <div className="flex items-center gap-3">
        <NotificationBell />
      </div>
    </header>
  );
}
