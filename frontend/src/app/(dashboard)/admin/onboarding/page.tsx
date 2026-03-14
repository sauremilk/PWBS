"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Building2,
  Users,
  Cable,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createOrganization } from "@/lib/api/organizations";
import { inviteMember } from "@/lib/api/admin";
import type { InviteRequest } from "@/lib/api/admin";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface InviteEntry {
  email: string;
  role: "owner" | "member" | "viewer";
}

type WizardStep = "org" | "members" | "connectors" | "confirm";

const STEPS: {
  key: WizardStep;
  label: string;
  icon: React.ElementType;
}[] = [
  { key: "org", label: "Organisation", icon: Building2 },
  { key: "members", label: "Team einladen", icon: Users },
  { key: "connectors", label: "Konnektoren", icon: Cable },
  { key: "confirm", label: "Bestätigung", icon: CheckCircle2 },
];

// ---------------------------------------------------------------------------
// Step Indicator
// ---------------------------------------------------------------------------

function StepIndicator({ current }: { current: WizardStep }) {
  const currentIdx = STEPS.findIndex((s) => s.key === current);

  return (
    <nav className="flex items-center gap-2" aria-label="Onboarding-Schritte">
      {STEPS.map((step, idx) => {
        const Icon = step.icon;
        const isDone = idx < currentIdx;
        const isActive = idx === currentIdx;

        return (
          <div key={step.key} className="flex items-center gap-2">
            {idx > 0 && (
              <div
                className={`h-px w-8 ${isDone ? "bg-blue-600" : "bg-gray-200"}`}
              />
            )}
            <div
              className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium ${
                isActive
                  ? "bg-blue-100 text-blue-700"
                  : isDone
                    ? "bg-green-100 text-green-700"
                    : "bg-gray-100 text-gray-500"
              }`}
            >
              <Icon aria-hidden="true" className="h-4 w-4" />
              <span className="hidden sm:inline">{step.label}</span>
            </div>
          </div>
        );
      })}
    </nav>
  );
}

// ---------------------------------------------------------------------------
// Step 1: Organization
// ---------------------------------------------------------------------------

function StepOrg({
  name,
  description,
  onChange,
}: {
  name: string;
  description: string;
  onChange: (field: "name" | "description", value: string) => void;
}) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-900">
        Organisation erstellen
      </h2>
      <p className="text-sm text-gray-500">
        Geben Sie den Namen Ihres Teams oder Unternehmens ein.
      </p>
      <div>
        <label
          htmlFor="org-name"
          className="block text-sm font-medium text-gray-700"
        >
          Name *
        </label>
        <input
          id="org-name"
          type="text"
          required
          maxLength={100}
          value={name}
          onChange={(e) => onChange("name", e.target.value)}
          placeholder="z.B. Acme Consulting"
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
      <div>
        <label
          htmlFor="org-desc"
          className="block text-sm font-medium text-gray-700"
        >
          Beschreibung
        </label>
        <textarea
          id="org-desc"
          rows={3}
          value={description}
          onChange={(e) => onChange("description", e.target.value)}
          placeholder="Kurze Beschreibung der Organisation…"
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 2: Invite Members
// ---------------------------------------------------------------------------

function StepMembers({
  invites,
  onAdd,
  onRemove,
  onChange,
}: {
  invites: InviteEntry[];
  onAdd: () => void;
  onRemove: (idx: number) => void;
  onChange: (idx: number, field: keyof InviteEntry, value: string) => void;
}) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-900">
        Team-Mitglieder einladen
      </h2>
      <p className="text-sm text-gray-500">
        Fügen Sie E-Mail-Adressen Ihrer Kollegen hinzu (3–10 empfohlen).
        Mitglieder müssen bereits einen PWBS-Account besitzen.
      </p>

      <div className="space-y-3">
        {invites.map((inv, idx) => (
          <div key={idx} className="flex items-center gap-3">
            <input
              type="email"
              required
              value={inv.email}
              onChange={(e) => onChange(idx, "email", e.target.value)}
              placeholder="nutzer@firma.de"
              className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <select
              value={inv.role}
              onChange={(e) => onChange(idx, "role", e.target.value)}
              className="rounded-md border border-gray-300 px-2 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              aria-label="Rolle auswählen"
            >
              <option value="member">Mitglied</option>
              <option value="viewer">Betrachter</option>
              <option value="owner">Owner</option>
            </select>
            <button
              type="button"
              onClick={() => onRemove(idx)}
              className="rounded p-1 text-gray-500 hover:bg-red-50 hover:text-red-600"
              aria-label="Eintrag entfernen"
            >
              <Trash2 aria-hidden="true" className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={onAdd}
        disabled={invites.length >= 10}
        className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50"
      >
        <Plus aria-hidden="true" className="h-4 w-4" />
        Weiteres Mitglied
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 3: Connector Selection
// ---------------------------------------------------------------------------

const CONNECTOR_OPTIONS = [
  { id: "gmail", label: "Gmail", description: "E-Mails importieren" },
  { id: "slack", label: "Slack", description: "Channel-Nachrichten" },
  {
    id: "google_docs",
    label: "Google Docs",
    description: "Dokumente indexieren",
  },
  {
    id: "google_calendar",
    label: "Google Calendar",
    description: "Termine & Meetings",
  },
  { id: "notion", label: "Notion", description: "Seiten & Datenbanken" },
] as const;

function StepConnectors({
  selected,
  onToggle,
}: {
  selected: Set<string>;
  onToggle: (id: string) => void;
}) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-900">
        Konnektoren auswählen
      </h2>
      <p className="text-sm text-gray-500">
        Wählen Sie die Datenquellen, die Ihr Team nutzen soll. Die
        OAuth-Verbindung wird nach Abschluss des Wizards hergestellt.
      </p>

      <div className="grid gap-3 sm:grid-cols-2">
        {CONNECTOR_OPTIONS.map((conn) => {
          const isSelected = selected.has(conn.id);
          return (
            <button
              key={conn.id}
              type="button"
              onClick={() => onToggle(conn.id)}
              aria-pressed={isSelected}
              className={`flex flex-col items-start rounded-lg border p-4 text-left transition-colors ${
                isSelected
                  ? "border-blue-300 bg-blue-50"
                  : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
              }`}
            >
              <span className="font-medium text-gray-900">{conn.label}</span>
              <span className="text-sm text-gray-500">{conn.description}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 4: Confirmation
// ---------------------------------------------------------------------------

function StepConfirm({
  orgName,
  inviteCount,
  connectorCount,
}: {
  orgName: string;
  inviteCount: number;
  connectorCount: number;
}) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-900">Zusammenfassung</h2>
      <div className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-5">
        <div className="flex items-center gap-3">
          <Building2 aria-hidden="true" className="h-5 w-5 text-blue-600" />
          <span className="text-sm">
            Organisation: <strong>{orgName}</strong>
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Users aria-hidden="true" className="h-5 w-5 text-blue-600" />
          <span className="text-sm">
            {inviteCount} Mitglied{inviteCount !== 1 ? "er" : ""} einladen
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Cable aria-hidden="true" className="h-5 w-5 text-blue-600" />
          <span className="text-sm">
            {connectorCount} Konnektor{connectorCount !== 1 ? "en" : ""}{" "}
            aktivieren
          </span>
        </div>
      </div>
      <p className="text-sm text-gray-500">
        Klicken Sie auf &quot;Abschließen&quot;, um die Organisation zu
        erstellen und die Einladungen zu versenden.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Wizard
// ---------------------------------------------------------------------------

export default function OnboardingWizardPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  // Wizard state
  const [step, setStep] = useState<WizardStep>("org");
  const [orgName, setOrgName] = useState("");
  const [orgDescription, setOrgDescription] = useState("");
  const [invites, setInvites] = useState<InviteEntry[]>([
    { email: "", role: "member" },
  ]);
  const [selectedConnectors, setSelectedConnectors] = useState<Set<string>>(
    new Set(),
  );
  const [error, setError] = useState<string | null>(null);

  // Finalize mutation
  const finalize = useMutation({
    mutationFn: async () => {
      // 1) Create organization
      const org = await createOrganization({
        name: orgName.trim(),
        description: orgDescription.trim(),
      });

      // 2) Invite members (sequentially to avoid race conditions)
      const validInvites = invites.filter((i) => i.email.trim());
      for (const inv of validInvites) {
        try {
          await inviteMember(org.id, {
            email: inv.email.trim(),
            role: inv.role,
          } as InviteRequest);
        } catch {
          // Skip if user not found or already member — non-critical
        }
      }

      // 3) Connector activation happens via the connectors page
      // (OAuth flow requires browser redirect — can't be done in a mutation)

      return org;
    },
    onSuccess: (org) => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
      router.push(`/admin?org=${org.id}`);
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  // Navigation
  const stepOrder: WizardStep[] = ["org", "members", "connectors", "confirm"];
  const currentIdx = stepOrder.indexOf(step);

  const canProceed = () => {
    if (step === "org") return orgName.trim().length > 0;
    return true;
  };

  const goNext = () => {
    if (currentIdx < stepOrder.length - 1) {
      setStep(stepOrder[currentIdx + 1]);
    }
  };
  const goBack = () => {
    if (currentIdx > 0) {
      setStep(stepOrder[currentIdx - 1]);
    }
  };

  // Invite helpers
  const addInvite = () => {
    setInvites((prev) => [...prev, { email: "", role: "member" }]);
  };
  const removeInvite = (idx: number) => {
    setInvites((prev) => prev.filter((_, i) => i !== idx));
  };
  const updateInvite = (
    idx: number,
    field: keyof InviteEntry,
    value: string,
  ) => {
    setInvites((prev) =>
      prev.map((inv, i) => (i === idx ? { ...inv, [field]: value } : inv)),
    );
  };

  // Connector toggle
  const toggleConnector = (id: string) => {
    setSelectedConnectors((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  return (
    <div className="mx-auto max-w-2xl space-y-8 p-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900">B2B-Onboarding</h1>
        <p className="mt-1 text-sm text-gray-500">
          Richten Sie Ihr Team in wenigen Schritten ein.
        </p>
      </div>

      <StepIndicator current={step} />

      <div className="rounded-lg border border-gray-200 bg-white p-6">
        {step === "org" && (
          <StepOrg
            name={orgName}
            description={orgDescription}
            onChange={(field, value) => {
              if (field === "name") setOrgName(value);
              else setOrgDescription(value);
            }}
          />
        )}

        {step === "members" && (
          <StepMembers
            invites={invites}
            onAdd={addInvite}
            onRemove={removeInvite}
            onChange={updateInvite}
          />
        )}

        {step === "connectors" && (
          <StepConnectors
            selected={selectedConnectors}
            onToggle={toggleConnector}
          />
        )}

        {step === "confirm" && (
          <StepConfirm
            orgName={orgName}
            inviteCount={invites.filter((i) => i.email.trim()).length}
            connectorCount={selectedConnectors.size}
          />
        )}

        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      </div>

      {/* Navigation buttons */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={goBack}
          disabled={currentIdx === 0}
          className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:invisible"
        >
          <ArrowLeft aria-hidden="true" className="h-4 w-4" />
          Zurück
        </button>

        {step === "confirm" ? (
          <button
            type="button"
            onClick={() => finalize.mutate()}
            disabled={finalize.isPending}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {finalize.isPending ? (
              <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
            ) : (
              <CheckCircle2 aria-hidden="true" className="h-4 w-4" />
            )}
            Abschließen
          </button>
        ) : (
          <button
            type="button"
            onClick={goNext}
            disabled={!canProceed()}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Weiter
            <ArrowRight aria-hidden="true" className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
