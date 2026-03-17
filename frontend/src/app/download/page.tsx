import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Download – PWBS Desktop App",
  description:
    "Laden Sie die PWBS Desktop-App herunter – verfuegbar fuer Windows, macOS und Linux.",
};

const GITHUB_RELEASE = "https://github.com/sauremilk/PWBS/releases/latest";

const PLATFORMS = [
  {
    name: "Windows",
    arch: "x64",
    icon: "🪟",
    file: ".exe",
    description: "Windows 10/11 (64-Bit)",
    requirements: "WebView2 (in Windows 10/11 enthalten)",
  },
  {
    name: "macOS",
    arch: "Universal",
    icon: "🍎",
    file: ".dmg",
    description: "macOS 12+ (Intel & Apple Silicon)",
    requirements: "Xcode Command Line Tools",
  },
  {
    name: "Linux",
    arch: "x64",
    icon: "🐧",
    file: ".AppImage",
    description: "Ubuntu 22.04+, Fedora 38+, Arch",
    requirements: "WebKitGTK 4.1",
  },
] as const;

export default function DownloadPage() {
  return (
    <div className="min-h-screen bg-surface">
      {/* Navigation */}
      <nav className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
          <Link href="/" className="text-xl font-bold text-text">
            PWBS
          </Link>
          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="text-sm text-text-secondary hover:text-text transition-colors"
            >
              Web-App
            </Link>
            <Link
              href="/login"
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white
                hover:bg-indigo-700 transition-colors"
            >
              Anmelden
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-4 py-16 text-center sm:px-6 sm:py-24">
        <h1 className="text-4xl font-extrabold tracking-tight text-text sm:text-5xl">
          PWBS Desktop App
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-text-secondary">
          Ihr Wissens-Betriebssystem als native App – mit System-Tray, nativen
          Benachrichtigungen und Offline-Modus.
        </p>
        <p className="mt-2 text-sm text-text-tertiary">
          Aktuell in der Beta. Kostenlos fuer alle registrierten Nutzer.
        </p>
      </section>

      {/* Platform Cards */}
      <section className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
        <div className="grid gap-6 sm:grid-cols-3">
          {PLATFORMS.map((platform) => (
            <div
              key={platform.name}
              className="flex flex-col rounded-xl border border-border bg-surface p-6 shadow-sm"
            >
              <div className="text-4xl" aria-hidden="true">
                {platform.icon}
              </div>
              <h2 className="mt-4 text-xl font-semibold text-text">
                {platform.name}
              </h2>
              <p className="mt-1 text-sm text-text-tertiary">
                {platform.description}
              </p>
              <p className="mt-2 text-xs text-text-tertiary">
                Voraussetzung: {platform.requirements}
              </p>
              <div className="mt-auto pt-6">
                <a
                  href={GITHUB_RELEASE}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full rounded-lg bg-indigo-600 px-4 py-3 text-center text-sm
                    font-medium text-white hover:bg-indigo-700 transition-colors"
                >
                  Download fuer {platform.name} ({platform.file})
                </a>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-border bg-surface-secondary py-16 sm:py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <h2 className="text-center text-2xl font-bold text-text sm:text-3xl">
            Warum die Desktop-App?
          </h2>
          <div className="mt-12 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            <div className="text-center">
              <div className="text-3xl" aria-hidden="true">
                🔔
              </div>
              <h3 className="mt-3 font-semibold text-text">
                Native Benachrichtigungen
              </h3>
              <p className="mt-1 text-sm text-text-secondary">
                Briefings und Erinnerungen direkt auf dem Desktop.
              </p>
            </div>
            <div className="text-center">
              <div className="text-3xl" aria-hidden="true">
                📡
              </div>
              <h3 className="mt-3 font-semibold text-text">Offline-Modus</h3>
              <p className="mt-1 text-sm text-text-secondary">
                Briefings und Suche funktionieren auch ohne Internetverbindung.
              </p>
            </div>
            <div className="text-center">
              <div className="text-3xl" aria-hidden="true">
                ⚡
              </div>
              <h3 className="mt-3 font-semibold text-text">System-Tray</h3>
              <p className="mt-1 text-sm text-text-secondary">
                Schnellzugriff auf Dashboard, Suche und Briefings.
              </p>
            </div>
            <div className="text-center">
              <div className="text-3xl" aria-hidden="true">
                🪶
              </div>
              <h3 className="mt-3 font-semibold text-text">~10 MB</h3>
              <p className="mt-1 text-sm text-text-secondary">
                Schlankes Binary dank Tauri – kein Chromium-Overhead.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Web-App Alternative */}
      <section className="py-16 sm:py-24">
        <div className="mx-auto max-w-3xl px-4 text-center sm:px-6">
          <h2 className="text-2xl font-bold text-text">
            Keine Installation noetig?
          </h2>
          <p className="mt-4 text-text-secondary">
            PWBS laeuft auch komplett im Browser. Nutzen Sie die Web-App ohne
            Download.
          </p>
          <Link
            href="/login"
            className="mt-6 inline-block rounded-lg border border-border px-6 py-3 text-sm
              font-medium text-text-secondary hover:bg-surface-secondary transition-colors"
          >
            Zur Web-App →
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <span className="text-sm text-text-tertiary">
              &copy; {new Date().getFullYear()} PWBS. Alle Rechte vorbehalten.
            </span>
            <div className="flex gap-6 text-sm text-text-tertiary">
              <Link
                href="/impressum"
                className="hover:text-text transition-colors"
              >
                Impressum
              </Link>
              <Link
                href="/datenschutz"
                className="hover:text-text transition-colors"
              >
                Datenschutz
              </Link>
              <Link href="/agb" className="hover:text-text transition-colors">
                AGB
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
