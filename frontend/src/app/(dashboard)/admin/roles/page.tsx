"use client";

import { useState, useEffect, useCallback } from "react";

// ---- Types ------------------------------------------------------------------

interface RolePermission {
  role: string;
  rank: number;
  permissions: string[];
}

interface MemberPermissions {
  user_id: string;
  org_id: string;
  role: string | null;
  permissions: string[];
}

interface MemberDetail {
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  joined_at: string;
}

interface AuditEntry {
  id: number;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  metadata_: Record<string, string>;
  created_at: string;
}

// ---- Role labels & styling --------------------------------------------------

const ROLE_LABELS: Record<string, string> = {
  owner: "Eigentümer",
  admin: "Administrator",
  manager: "Manager",
  member: "Mitglied",
  viewer: "Betrachter",
};

const ROLE_COLORS: Record<string, string> = {
  owner: "bg-purple-100 text-purple-800",
  admin: "bg-red-100 text-red-800",
  manager: "bg-amber-100 text-amber-800",
  member: "bg-indigo-100 text-indigo-800",
  viewer: "bg-surface-secondary text-text",
};

const PERM_LABELS: Record<string, string> = {
  "org:delete": "Organisation löschen",
  "org:edit": "Organisation bearbeiten",
  "org:view": "Organisation anzeigen",
  "members:invite": "Mitglieder einladen",
  "members:remove": "Mitglieder entfernen",
  "members:change_role": "Rollen ändern",
  "members:view": "Mitglieder anzeigen",
  "connectors:manage": "Konnektoren verwalten",
  "connectors:share": "Konnektoren teilen",
  "connectors:view": "Konnektoren anzeigen",
  "documents:manage_visibility": "Sichtbarkeit verwalten",
  "documents:view_team": "Team-Dokumente anzeigen",
  "briefings:generate": "Briefings erstellen",
  "briefings:view": "Briefings anzeigen",
  "audit:view": "Audit-Log anzeigen",
};

// ---- Component --------------------------------------------------------------

export default function RolesPage() {
  const [orgId, setOrgId] = useState<string>("");
  const [roles, setRoles] = useState<RolePermission[]>([]);
  const [members, setMembers] = useState<MemberDetail[]>([]);
  const [selectedMember, setSelectedMember] = useState<MemberPermissions | null>(null);
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([]);
  const [activeTab, setActiveTab] = useState<"roles" | "members" | "audit">("roles");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // In a real app, orgId would come from route params or context
  // For MVP, we use a simple input
  const fetchRoles = useCallback(async () => {
    if (!orgId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/rbac/org/${orgId}/roles`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("token") ?? ""}` },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRoles(data.roles);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler beim Laden");
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  const fetchMembers = useCallback(async () => {
    if (!orgId) return;
    try {
      const res = await fetch(`/api/v1/admin/org/${orgId}/members`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("token") ?? ""}` },
      });
      if (!res.ok) return;
      const data = await res.json();
      setMembers(data.members);
    } catch {
      // Silently fail for members tab
    }
  }, [orgId]);

  const fetchAuditLog = useCallback(async () => {
    if (!orgId) return;
    try {
      const res = await fetch(`/api/v1/rbac/org/${orgId}/audit-log?limit=50`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("token") ?? ""}` },
      });
      if (!res.ok) return;
      const data = await res.json();
      setAuditLog(data.entries);
    } catch {
      // Silently fail for audit tab
    }
  }, [orgId]);

  const fetchMemberPermissions = async (userId: string) => {
    if (!orgId) return;
    try {
      const res = await fetch(`/api/v1/rbac/org/${orgId}/members/${userId}/permissions`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("token") ?? ""}` },
      });
      if (!res.ok) return;
      const data: MemberPermissions = await res.json();
      setSelectedMember(data);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    if (orgId) {
      fetchRoles();
      fetchMembers();
      fetchAuditLog();
    }
  }, [orgId, fetchRoles, fetchMembers, fetchAuditLog]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold text-text">
        Rollen & Berechtigungen
      </h1>

      {/* Org selector */}
      <div className="mb-6 flex items-center gap-3">
        <label htmlFor="org-id" className="text-sm font-medium text-text-secondary">
          Organisations-ID:
        </label>
        <input
          id="org-id"
          type="text"
          value={orgId}
          onChange={(e) => setOrgId(e.target.value.trim())}
          placeholder="UUID der Organisation"
          className="rounded-md border border-border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div role="tablist" aria-label="Berechtigungsverwaltung" className="mb-6 flex gap-1 rounded-lg bg-surface-secondary p-1">
        {(["roles", "members", "audit"] as const).map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={activeTab === tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab
                ? "bg-surface text-text shadow-sm"
                : "text-text-secondary hover:text-text"
            }`}
          >
            {tab === "roles" ? "Rollenübersicht" : tab === "members" ? "Mitglieder" : "Audit-Log"}
          </button>
        ))}
      </div>

      {loading && <p role="status" className="text-sm text-text-tertiary">Laden</p>}

      {/* Roles tab */}
      {activeTab === "roles" && (
        <div className="space-y-4">
          {roles.map((r) => (
            <div key={r.role} className="rounded-lg border border-border p-4">
              <div className="mb-2 flex items-center gap-2">
                <span
                  className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${
                    ROLE_COLORS[r.role] ?? "bg-surface-secondary text-text"
                  }`}
                >
                  {ROLE_LABELS[r.role] ?? r.role}
                </span>
                <span className="text-xs text-text-tertiary">Rang {r.rank}</span>
              </div>
              <div className="flex flex-wrap gap-1">
                {r.permissions.map((p) => (
                  <span
                    key={p}
                    className="rounded bg-surface-secondary px-2 py-0.5 text-xs text-text-secondary"
                  >
                    {PERM_LABELS[p] ?? p}
                  </span>
                ))}
              </div>
            </div>
          ))}
          {roles.length === 0 && !loading && (
            <p className="text-sm text-text-tertiary">
              Gib eine Organisations-ID ein, um Rollen zu laden.
            </p>
          )}
        </div>
      )}

      {/* Members tab */}
      {activeTab === "members" && (
        <div className="space-y-3">
          {members.map((m) => (
            <div
              key={m.user_id}
              className="flex items-center justify-between rounded-lg border border-border p-4"
            >
              <div>
                <p className="font-medium text-text">{m.display_name}</p>
                <p className="text-sm text-text-tertiary">{m.email}</p>
              </div>
              <div className="flex items-center gap-3">
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    ROLE_COLORS[m.role] ?? "bg-surface-secondary text-text"
                  }`}
                >
                  {ROLE_LABELS[m.role] ?? m.role}
                </span>
                <button
                  onClick={() => fetchMemberPermissions(m.user_id)}
                  className="rounded-md border border-border px-3 py-1 text-xs text-text-secondary hover:bg-surface-secondary"
                >
                  Berechtigungen
                </button>
              </div>
            </div>
          ))}

          {/* Selected member permissions */}
          {selectedMember && (
            <div className="mt-4 rounded-lg border-2 border-indigo-200 bg-indigo-50 p-4">
              <h3 className="mb-2 font-medium text-text">
                Berechtigungen für {selectedMember.user_id.slice(0, 8)}
              </h3>
              <p className="mb-2 text-sm text-text-secondary">
                Rolle:{" "}
                <span className="font-medium">
                  {ROLE_LABELS[selectedMember.role ?? ""] ?? selectedMember.role ?? "Kein Mitglied"}
                </span>
              </p>
              <div className="flex flex-wrap gap-1">
                {selectedMember.permissions.map((p) => (
                  <span
                    key={p}
                    className="rounded bg-surface px-2 py-0.5 text-xs text-text-secondary shadow-sm"
                  >
                    {PERM_LABELS[p] ?? p}
                  </span>
                ))}
              </div>
              <button
                onClick={() => setSelectedMember(null)}
                className="mt-2 text-xs text-indigo-600 hover:underline"
              >
                Schließen
              </button>
            </div>
          )}

          {members.length === 0 && !loading && (
            <p className="text-sm text-text-tertiary">Keine Mitglieder gefunden.</p>
          )}
        </div>
      )}

      {/* Audit log tab */}
      {activeTab === "audit" && (
        <div className="space-y-2">
          {auditLog.map((e) => (
            <div
              key={e.id}
              className="rounded-lg border border-border px-4 py-3"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-text">
                  {e.action.replace("_", " ")}
                </span>
                <span className="text-xs text-text-tertiary">
                  {new Date(e.created_at).toLocaleString("de-DE")}
                </span>
              </div>
              <div className="mt-1 text-xs text-text-tertiary">
                {e.metadata_?.old_role && (
                  <span>
                    {ROLE_LABELS[e.metadata_.old_role] ?? e.metadata_.old_role} {" "}
                  </span>
                )}
                <span className="font-medium">
                  {ROLE_LABELS[e.metadata_?.new_role ?? ""] ?? e.metadata_?.new_role ?? ""}
                </span>
                {e.metadata_?.target_user_id && (
                  <span className="ml-2 text-text-tertiary">
                    Nutzer: {e.metadata_.target_user_id.slice(0, 8)}
                  </span>
                )}
              </div>
            </div>
          ))}
          {auditLog.length === 0 && !loading && (
            <p className="text-sm text-text-tertiary">Keine Einträge im Audit-Log.</p>
          )}
        </div>
      )}
    </div>
  );
}