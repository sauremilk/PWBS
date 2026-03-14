"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { register } from "@/lib/api/auth";
import { ApiClientError } from "@/lib/api-client";

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
    <li className={`text-sm ${met ? "text-green-600" : "text-gray-500"}`}>
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
      setShowWelcome(true);
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 409) {
          setError("Diese E-Mail-Adresse wird bereits verwendet.");
        } else if (err.status >= 500) {
          setError("Verbindungsfehler. Bitte pr\u00fcfe deine Internetverbindung.");
        } else {
          const msg = err.data?.message ?? "Registrierung fehlgeschlagen.";
          setError(msg);
        }
      } else {
        setError("Verbindungsfehler. Bitte pr\u00fcfe deine Internetverbindung.");
      }
    } finally {
      setLoading(false);
    }
  }

  if (showWelcome) {
    return (
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-md">
        <h1 className="mb-4 text-2xl font-bold text-gray-900">
          Willkommen bei PWBS!
        </h1>
        <p className="mb-6 text-gray-600">
          Dein Konto wurde erstellt. Verbinde jetzt deine ersten Datenquellen,
          damit PWBS dir personalisierte Briefings erstellen kann.
        </p>
        <div className="space-y-3">
          <button
            onClick={() => router.push("/connectors")}
            className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Konnektoren einrichten
          </button>
          <button
            onClick={() => router.push("/")}
            className="w-full rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Sp\u00e4ter einrichten
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-md">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Registrieren</h1>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="display-name" className="block text-sm font-medium text-gray-700">
            Anzeigename
          </label>
          <input
            id="display-name"
            type="text"
            required
            autoComplete="name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div>
          <label htmlFor="reg-email" className="block text-sm font-medium text-gray-700">
            E-Mail
          </label>
          <input
            id="reg-email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div>
          <label htmlFor="reg-password" className="block text-sm font-medium text-gray-700">
            Passwort
          </label>
          <input
            id="reg-password"
            type="password"
            required
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {password.length > 0 && (
            <ul className="mt-2 space-y-1">
              <CriterionLine met={criteria.minLength} label="Mindestens 12 Zeichen" />
              <CriterionLine met={criteria.uppercase} label="Ein Gro\u00dfbuchstabe" />
              <CriterionLine met={criteria.digit} label="Eine Zahl" />
            </ul>
          )}
        </div>

        <button
          type="submit"
          disabled={loading || !allMet}
          className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
        >
          {loading ? "Registrieren\u2026" : "Registrieren"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-gray-600">
        Bereits registriert?{" "}
        <Link href="/login" className="font-medium text-blue-600 hover:text-blue-500">
          Anmelden
        </Link>
      </p>
    </div>
  );
}
