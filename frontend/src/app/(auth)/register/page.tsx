"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Sparkles, Loader2 } from "lucide-react";
import { register } from "@/lib/api/auth";
import { ApiClientError } from "@/lib/api-client";
import { trackSignup } from "@/lib/analytics";

interface PasswordCriteria {
  minLength: boolean;
  uppercase: boolean;
  digit: boolean;
}

function checkPassword(pw: string): PasswordCriteria {
  return {
    minLength: pw.length >= 12,
    uppercase: /[A-Z]/.test(pw),
    digit: /\d/.test(pw),
  };
}

function CriterionLine({ met, label }: { met: boolean; label: string }) {
  return (
    <li className={`text-sm ${met ? "text-emerald-400" : "text-slate-500"}`}>
      <span className="mr-1">{met ? "\u2713" : "\u2022"}</span>
      {label}
    </li>
  );
}

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);

  const criteria = checkPassword(password);
  const allMet = criteria.minLength && criteria.uppercase && criteria.digit;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!allMet) return;
    setError(null);
    setLoading(true);

    try {
      await register({ email, password, display_name: displayName });
      trackSignup();
      setShowWelcome(true);
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 409) {
          setError("Diese E-Mail-Adresse wird bereits verwendet.");
        } else if (err.status >= 500) {
          setError("Verbindungsfehler. Bitte prüfe deine Internetverbindung.");
        } else {
          const msg = err.data?.message ?? "Registrierung fehlgeschlagen.";
          setError(msg);
        }
      } else {
        setError("Verbindungsfehler. Bitte prüfe deine Internetverbindung.");
      }
    } finally {
      setLoading(false);
    }
  }

  if (showWelcome) {
    return (
      <div className="w-full max-w-md px-4">
        <div className="rounded-2xl border border-white/10 bg-surface/5 p-8 text-center shadow-xl backdrop-blur-xl">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/20">
            <Sparkles className="h-7 w-7 text-emerald-400" />
          </div>
          <h1 className="mb-2 text-2xl font-bold text-white">
            Willkommen bei PWBS!
          </h1>
          <p className="mb-6 text-sm text-slate-400">
            Dein Konto wurde erstellt. Verbinde jetzt deine ersten Datenquellen,
            damit PWBS dir personalisierte Briefings erstellen kann.
          </p>
          <div className="space-y-3">
            <button
              onClick={() => router.push("/connectors")}
              className="w-full rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/25 hover:bg-indigo-500"
            >
              Konnektoren einrichten
            </button>
            <button
              onClick={() => router.push("/")}
              className="w-full rounded-xl border border-white/10 bg-surface/5 px-4 py-2.5 text-sm font-medium text-slate-300 hover:bg-surface/10"
            >
              Später einrichten
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md px-4">
      <div className="mb-8 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-500 shadow-lg shadow-indigo-500/25">
          <Sparkles className="h-6 w-6 text-white" />
        </div>
        <h1 className="text-2xl font-bold text-white">Konto erstellen</h1>
        <p className="mt-1 text-sm text-slate-400">
          Starte mit deinem persönlichen Wissens-Betriebssystem
        </p>
      </div>

      <div className="rounded-2xl border border-white/10 bg-surface/5 p-8 shadow-xl backdrop-blur-xl">
        {error && (
          <div className="mb-4 rounded-xl bg-red-500/10 border border-red-500/20 p-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="display-name"
              className="block text-sm font-medium text-slate-300"
            >
              Anzeigename
            </label>
            <input
              id="display-name"
              type="text"
              required
              autoComplete="name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="mt-1 block w-full rounded-xl border border-white/10 bg-surface/5 px-4 py-2.5 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              placeholder="Max Mustermann"
            />
          </div>

          <div>
            <label
              htmlFor="reg-email"
              className="block text-sm font-medium text-slate-300"
            >
              E-Mail
            </label>
            <input
              id="reg-email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-xl border border-white/10 bg-surface/5 px-4 py-2.5 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              placeholder="name@example.com"
            />
          </div>

          <div>
            <label
              htmlFor="reg-password"
              className="block text-sm font-medium text-slate-300"
            >
              Passwort
            </label>
            <input
              id="reg-password"
              type="password"
              required
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full rounded-xl border border-white/10 bg-surface/5 px-4 py-2.5 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            {password.length > 0 && (
              <ul className="mt-2 space-y-1">
                <CriterionLine
                  met={criteria.minLength}
                  label="Mindestens 12 Zeichen"
                />
                <CriterionLine
                  met={criteria.uppercase}
                  label="Ein Großbuchstabe"
                />
                <CriterionLine met={criteria.digit} label="Eine Zahl" />
              </ul>
            )}
          </div>

          <button
            type="submit"
            disabled={loading || !allMet}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/25 hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {loading ? "Registrieren…" : "Registrieren"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-400">
          Bereits registriert?{" "}
          <Link
            href="/login"
            className="font-medium text-indigo-400 hover:text-indigo-300"
          >
            Anmelden
          </Link>
        </p>
      </div>
    </div>
  );
}
