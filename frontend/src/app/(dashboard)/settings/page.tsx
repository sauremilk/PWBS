"use client";

import { Suspense, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  User,
  Shield,
  Trash2,
  Download,
  Bell,
  Loader2,
  Check,
  AlertTriangle,
  Database,
} from "lucide-react";
import {
  useUserSettings,
  useUpdateSettings,
  useStartExport,
  useExportStatus,
  useRequestDeletion,
  useCancelDeletion,
} from "@/hooks/use-settings";
import { SecurityStatusPanel } from "@/components/settings/security-status-panel";

type TabId = "profile" | "notifications" | "privacy" | "security" | "account";

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  {
    id: "profile",
    label: "Profil",
    icon: <User aria-hidden="true" className="h-4 w-4" />,
  },
  {
    id: "notifications",
    label: "Erinnerungen",
    icon: <Bell aria-hidden="true" className="h-4 w-4" />,
  },
  {
    id: "privacy",
    label: "Datenschutz",
    icon: <Shield aria-hidden="true" className="h-4 w-4" />,
  },
  {
    id: "security",
    label: "Sicherheit",
    icon: <Shield aria-hidden="true" className="h-4 w-4" />,
  },
  {
    id: "account",
    label: "Account",
    icon: <Trash2 aria-hidden="true" className="h-4 w-4" />,
  },
];

export default function SettingsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-12" role="status">
          <Loader2
            aria-hidden="true"
            className="h-8 w-8 animate-spin text-gray-400"
          />
          <span className="sr-only">Wird geladen</span>
        </div>
      }
    >
      <SettingsContent />
    </Suspense>
  );
}

function SettingsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTab = (searchParams.get("tab") as TabId) || "profile";

  function setTab(tab: TabId) {
    router.replace(`/settings?tab=${tab}`, { scroll: false });
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Einstellungen</h1>

      {/* Tab Navigation */}
      <div
        className="flex gap-1 border-b border-gray-200"
        role="tablist"
        aria-label="Einstellungen"
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setTab(tab.id)}
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`inline-flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        {activeTab === "profile" && <ProfileTab />}
        {activeTab === "notifications" && <NotificationsTab />}
        {activeTab === "privacy" && <PrivacyTab />}
        {activeTab === "security" && <SecurityTab />}
        {activeTab === "account" && <AccountTab />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Profile Tab
// ---------------------------------------------------------------------------

function ProfileTab() {
  const { data, isLoading } = useUserSettings();
  const update = useUpdateSettings();
  const [displayName, setDisplayName] = useState("");
  const [timezone, setTimezone] = useState("");
  const [language, setLanguage] = useState("");
  const [autoGenerate, setAutoGenerate] = useState(false);

  useEffect(() => {
    if (data) {
      setDisplayName(data.display_name);
      setTimezone(data.timezone);
      setLanguage(data.language);
      setAutoGenerate(data.briefing_auto_generate);
    }
  }, [data]);

  function handleSave() {
    update.mutate({
      display_name: displayName,
      timezone,
      language,
      briefing_auto_generate: autoGenerate,
    });
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-md">
      <div>
        <label
          htmlFor="display-name"
          className="block text-sm font-medium text-gray-700"
        >
          Anzeigename
        </label>
        <input
          id="display-name"
          type="text"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label
          htmlFor="timezone"
          className="block text-sm font-medium text-gray-700"
        >
          Zeitzone
        </label>
        <select
          id="timezone"
          value={timezone}
          onChange={(e) => setTimezone(e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="Europe/Berlin">Europe/Berlin</option>
          <option value="Europe/Vienna">Europe/Vienna</option>
          <option value="Europe/Zurich">Europe/Zurich</option>
          <option value="UTC">UTC</option>
        </select>
      </div>

      <div>
        <label
          htmlFor="language"
          className="block text-sm font-medium text-gray-700"
        >
          Sprache
        </label>
        <select
          id="language"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="de">Deutsch</option>
          <option value="en">English</option>
        </select>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={autoGenerate}
          onChange={(e) => setAutoGenerate(e.target.checked)}
          className="rounded border-gray-300"
        />
        Briefings automatisch generieren
      </label>

      <button
        onClick={handleSave}
        disabled={update.isPending}
        className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {update.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : update.isSuccess ? (
          <Check className="h-4 w-4" />
        ) : null}
        Speichern
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Notifications Tab (TASK-132)
// ---------------------------------------------------------------------------

function NotificationsTab() {
  const { data, isLoading } = useUserSettings();
  const update = useUpdateSettings();
  const [frequency, setFrequency] = useState("daily");
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [briefingTime, setBriefingTime] = useState("06:30");

  useEffect(() => {
    if (data) {
      setFrequency(data.reminder_frequency);
      setEmailEnabled(data.email_briefing_enabled);
      setBriefingTime(data.briefing_email_time);
    }
  }, [data]);

  function handleSave() {
    update.mutate({
      reminder_frequency: frequency as "daily" | "weekly" | "off",
      email_briefing_enabled: emailEnabled,
      briefing_email_time: briefingTime,
    });
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-md">
      {/* E-Mail Briefing */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900">
          E-Mail Briefings
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          Erhalte tägliche Briefings per E-Mail zu deinem gewünschten Zeitpunkt.
        </p>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={emailEnabled}
          onChange={(e) => setEmailEnabled(e.target.checked)}
          className="rounded border-gray-300"
        />
        E-Mail-Briefings aktiviert
      </label>

      {emailEnabled && (
        <div>
          <label
            htmlFor="briefing-time"
            className="block text-sm font-medium text-gray-700"
          >
            Briefing-Zeitpunkt
          </label>
          <input
            id="briefing-time"
            type="time"
            value={briefingTime}
            onChange={(e) => setBriefingTime(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      )}

      {/* Erinnerungsfrequenz */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900">
          Erinnerungsfrequenz
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          Bestimme, wie oft du proaktive Erinnerungen und
          Follow-up-Benachrichtigungen erhalten möchtest.
        </p>
      </div>

      <fieldset className="space-y-3">
        <legend className="sr-only">Erinnerungsfrequenz</legend>
        {(
          [
            {
              value: "daily",
              label: "Täglich",
              desc: "Jeden Tag eine Zusammenfassung offener Erinnerungen",
            },
            {
              value: "weekly",
              label: "Wöchentlich",
              desc: "Einmal pro Woche (freitags) eine Übersicht",
            },
            {
              value: "off",
              label: "Aus",
              desc: "Keine proaktiven Erinnerungen – nur manuell abrufbar",
            },
          ] as const
        ).map((opt) => (
          <label
            key={opt.value}
            htmlFor={`reminder-freq-${opt.value}`}
            aria-label={opt.label}
            className={`flex cursor-pointer items-start gap-3 rounded-lg border p-4 transition-colors ${
              frequency === opt.value
                ? "border-blue-600 bg-blue-50"
                : "border-gray-200 hover:border-gray-300"
            }`}
          >
            <input
              id={`reminder-freq-${opt.value}`}
              type="radio"
              name="reminder-frequency"
              value={opt.value}
              checked={frequency === opt.value}
              onChange={(e) => setFrequency(e.target.value)}
              className="mt-0.5"
            />
            <div>
              <span className="text-sm font-medium text-gray-900">
                {opt.label}
              </span>
              <p className="text-xs text-gray-500">{opt.desc}</p>
            </div>
          </label>
        ))}
      </fieldset>

      <button
        onClick={handleSave}
        disabled={update.isPending}
        className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {update.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : update.isSuccess ? (
          <Check className="h-4 w-4" />
        ) : null}
        Speichern
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Privacy Tab
// ---------------------------------------------------------------------------

function PrivacyTab() {
  const startExport = useStartExport();
  const [exportId, setExportId] = useState<string | null>(null);
  const { data: exportStatus } = useExportStatus(exportId);

  function handleExport() {
    startExport.mutate(undefined, {
      onSuccess: (res) => setExportId(res.export_id),
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-gray-900">
          Transparenzbericht
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          Detaillierte Übersicht über gespeicherte Daten und KI-Nutzung (DSGVO
          Art. 15).
        </p>
        <div className="mt-3">
          <a
            href="/settings/data"
            className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <Database className="h-4 w-4" />
            Transparenzbericht anzeigen
          </a>
        </div>
      </div>
      <div>
        <h3 className="text-sm font-semibold text-gray-900">Datenexport</h3>
        <p className="mt-1 text-sm text-gray-500">
          Exportiere alle deine Daten als JSON-Datei (DSGVO Art. 20).
        </p>
        <div className="mt-3 flex items-center gap-3">
          <button
            onClick={handleExport}
            disabled={
              startExport.isPending ||
              (!!exportId && exportStatus?.status !== "completed")
            }
            className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {startExport.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Daten exportieren
          </button>
          {exportStatus && exportStatus.status !== "completed" && (
            <span className="text-sm text-gray-500">
              Export wird erstellt\u2026
            </span>
          )}
          {exportStatus?.status === "completed" &&
            exportStatus.download_url && (
              <a
                href={exportStatus.download_url}
                className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:underline"
                download
              >
                <Download className="h-4 w-4" />
                Herunterladen
              </a>
            )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Security Tab
// ---------------------------------------------------------------------------

function SecurityTab() {
  return <SecurityStatusPanel />;
}

// ---------------------------------------------------------------------------
// Account Tab
// ---------------------------------------------------------------------------

function AccountTab() {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const deleteMutation = useRequestDeletion();
  const cancelMutation = useCancelDeletion();

  function handleDelete() {
    if (!confirmed || !password) return;
    deleteMutation.mutate(
      { password, confirmation: "DELETE" },
      { onSuccess: () => setShowDeleteDialog(false) },
    );
  }

  return (
    <div className="space-y-6">
      {/* Deletion scheduled banner */}
      {deleteMutation.data?.deletion_scheduled_at && (
        <div className="rounded-lg border border-yellow-300 bg-yellow-50 p-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-600" />
            <p className="text-sm font-medium text-yellow-800">
              Dein Account wird am{" "}
              {new Date(
                deleteMutation.data.deletion_scheduled_at,
              ).toLocaleDateString("de-DE")}{" "}
              gel\u00f6scht.
            </p>
          </div>
          <button
            onClick={() => cancelMutation.mutate()}
            disabled={cancelMutation.isPending}
            className="mt-2 text-sm font-medium text-yellow-800 underline hover:text-yellow-900"
          >
            L\u00f6schung abbrechen
          </button>
        </div>
      )}

      <div>
        <h3 className="text-sm font-semibold text-red-900">
          Account l\u00f6schen
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          Dein Account und alle Daten werden nach einer 30-Tage-Karenzzeit
          unwiderruflich gel\u00f6scht.
        </p>
        <button
          onClick={() => setShowDeleteDialog(true)}
          className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-red-300 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50"
        >
          <Trash2 className="h-4 w-4" />
          Account l\u00f6schen
        </button>
      </div>

      {/* Full-screen delete dialog */}
      {showDeleteDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-dialog-title"
            className="mx-4 w-full max-w-md rounded-lg bg-white p-6 shadow-xl"
          >
            <h2
              id="delete-dialog-title"
              className="text-lg font-bold text-red-900"
            >
              Account endg\u00fcltig l\u00f6schen
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              Alle deine Daten werden nach 30 Tagen unwiderruflich
              gel\u00f6scht. Innerhalb der Karenzzeit kannst du die
              L\u00f6schung abbrechen.
            </p>

            <label className="mt-4 flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
                className="mt-0.5 rounded border-gray-300"
              />
              Ich verstehe, dass diese Aktion nicht r\u00fcckg\u00e4ngig gemacht
              werden kann.
            </label>

            <div className="mt-3">
              <label
                htmlFor="delete-password"
                className="block text-sm font-medium text-gray-700"
              >
                Passwort zur Best\u00e4tigung
              </label>
              <input
                id="delete-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
                autoComplete="current-password"
              />
            </div>

            <div className="mt-4 flex items-center gap-2">
              <button
                onClick={handleDelete}
                disabled={!confirmed || !password || deleteMutation.isPending}
                className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending
                  ? "L\u00f6sche\u2026"
                  : "Account l\u00f6schen"}
              </button>
              <button
                onClick={() => {
                  setShowDeleteDialog(false);
                  setPassword("");
                  setConfirmed(false);
                }}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Abbrechen
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
