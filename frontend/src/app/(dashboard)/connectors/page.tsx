"use client";

import { useRef, useState } from "react";
import {
  Plug,
  RefreshCw,
  Trash2,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Upload,
  ShieldOff,
} from "lucide-react";
import {
  useConnectorTypes,
  useConnectionStatus,
  useConnectOAuth,
  useConfigureConnector,
  useDisconnectConnector,
  useSyncConnector,
  useRevokeConsent,
  useUploadObsidian,
} from "@/hooks/use-connectors";
import { ConsentDialog } from "@/components/connectors/consent-dialog";
import { SyncHistoryAccordion } from "@/components/connectors/sync-history-accordion";
import { trackFirstConnector } from "@/lib/analytics";
import type { ConnectorType, ConnectionStatus } from "@/types/api";

const STATUS_CONFIG: Record<
  string,
  { icon: React.ReactNode; label: string; color: string }
> = {
  active: {
    icon: (
      <CheckCircle2 aria-hidden="true" className="h-4 w-4 text-green-500" />
    ),
    label: "Verbunden",
    color: "text-green-700 bg-green-50",
  },
  syncing: {
    icon: (
      <RefreshCw
        aria-hidden="true"
        className="h-4 w-4 animate-spin text-indigo-500"
      />
    ),
    label: "Synchronisiert\u2026",
    color: "text-indigo-700 bg-indigo-50",
  },
  error: {
    icon: <XCircle aria-hidden="true" className="h-4 w-4 text-red-500" />,
    label: "Fehler",
    color: "text-red-700 bg-red-50",
  },
  paused: {
    icon: (
      <AlertTriangle aria-hidden="true" className="h-4 w-4 text-yellow-500" />
    ),
    label: "Pausiert",
    color: "text-yellow-700 bg-yellow-50",
  },
};

function ConnectedCard({
  connection,
  onSync,
  onDisconnect,
  onRevokeConsent,
  isSyncing,
  isRevoking,
}: {
  connection: ConnectionStatus;
  onSync: () => void;
  onDisconnect: () => void;
  onRevokeConsent: () => void;
  isSyncing: boolean;
  isRevoking: boolean;
}) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [showRevokeConfirm, setShowRevokeConfirm] = useState(false);
  const statusCfg = STATUS_CONFIG[connection.status] ?? STATUS_CONFIG.error;

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50">
            <Plug aria-hidden="true" className="h-5 w-5 text-indigo-600" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text">
              {connection.type}
            </h3>
            <div className="flex items-center gap-1.5 text-xs">
              {statusCfg.icon}
              <span
                className={`rounded px-1.5 py-0.5 font-medium ${statusCfg.color}`}
              >
                {statusCfg.label}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onSync}
            disabled={isSyncing}
            className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs font-medium text-text-secondary hover:bg-surface-secondary disabled:opacity-50"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${isSyncing ? "animate-spin" : ""}`}
              aria-hidden="true"
            />
            Sync
          </button>
          <button
            onClick={() => setShowRevokeConfirm(true)}
            className="inline-flex items-center gap-1 rounded-md border border-orange-200 px-2.5 py-1.5 text-xs font-medium text-orange-600 hover:bg-orange-50"
          >
            <ShieldOff aria-hidden="true" className="h-3.5 w-3.5" />
            Widerruf
          </button>
          <button
            onClick={() => setShowConfirm(true)}
            className="inline-flex items-center gap-1 rounded-md border border-red-200 px-2.5 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
          >
            <Trash2 aria-hidden="true" className="h-3.5 w-3.5" />
            Trennen
          </button>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-text-tertiary">
        <span>{connection.doc_count} Dokumente</span>
        {connection.last_sync && (
          <span>
            Letzter Sync:{" "}
            {new Date(connection.last_sync).toLocaleString("de-DE")}
          </span>
        )}
      </div>

      {connection.error && (
        <div className="mt-2 rounded-md bg-red-50 p-2 text-xs text-red-700">
          {connection.error}
        </div>
      )}

      {/* Disconnect confirmation dialog */}
      {showConfirm && (
        <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-3">
          <p className="text-sm text-red-800">
            Alle importierten Daten dieser Quelle werden unwiderruflich
            gel&#246;scht.
          </p>
          <div className="mt-2 flex items-center gap-2">
            <button
              onClick={() => {
                onDisconnect();
                setShowConfirm(false);
              }}
              className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700"
            >
              Endg&#252;ltig trennen
            </button>
            <button
              onClick={() => setShowConfirm(false)}
              className="rounded-md border border-border px-3 py-1.5 text-xs font-medium text-text-secondary hover:bg-surface"
            >
              Abbrechen
            </button>
          </div>
        </div>
      )}

      {/* Revoke consent confirmation */}
      {showRevokeConfirm && (
        <div className="mt-3 rounded-md border border-orange-200 bg-orange-50 p-3">
          <p className="text-sm text-orange-800">
            Einwilligung widerrufen? Alle importierten Daten und die Verbindung
            werden unwiderruflich gel&#246;scht.
          </p>
          <div className="mt-2 flex items-center gap-2">
            <button
              onClick={() => {
                onRevokeConsent();
                setShowRevokeConfirm(false);
              }}
              disabled={isRevoking}
              className="inline-flex items-center gap-1 rounded-md bg-orange-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-orange-700 disabled:opacity-50"
            >
              {isRevoking && (
                <Loader2 aria-hidden="true" className="h-3 w-3 animate-spin" />
              )}
              Einwilligung widerrufen
            </button>
            <button
              onClick={() => setShowRevokeConfirm(false)}
              className="rounded-md border border-border px-3 py-1.5 text-xs font-medium text-text-secondary hover:bg-surface"
            >
              Abbrechen
            </button>
          </div>
        </div>
      )}

      {/* Sync history (TASK-184) */}
      <SyncHistoryAccordion connectorType={connection.type} />
    </div>
  );
}

function AvailableConnectorCard({
  connector,
  onConnect,
  isConnecting,
}: {
  connector: ConnectorType;
  onConnect: () => void;
  isConnecting: boolean;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<{
    document_count: number;
    deleted_count: number;
  } | null>(null);
  const uploadMutation = useUploadObsidian();
  const isObsidian = connector.type === "obsidian";

  function handleObsidianUpload(file: File) {
    const name = file.name.toLowerCase();
    if (!name.endsWith(".zip") && !name.endsWith(".md")) {
      setUploadError("Nur .zip oder .md Dateien erlaubt.");
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setUploadError("Datei darf maximal 50 MB groß sein.");
      return;
    }
    setUploadError(null);
    setUploadResult(null);
    uploadMutation.mutate(file, {
      onSuccess: (data) => {
        setUploadResult({
          document_count: data.document_count,
          deleted_count: data.deleted_count,
        });
      },
      onError: () => {
        setUploadError("Upload fehlgeschlagen. Bitte versuche es erneut.");
      },
    });
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleObsidianUpload(file);
  }

  return (
    <div className="rounded-xl border border-dashed border-border bg-surface-secondary p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface">
            <Plug aria-hidden="true" className="h-5 w-5 text-text-tertiary" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text">
              {connector.name}
            </h3>
            <p className="text-xs text-text-tertiary">
              {connector.description}
            </p>
          </div>
        </div>
        {!isObsidian && (
          <button
            onClick={onConnect}
            disabled={isConnecting}
            className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {isConnecting ? (
              <Loader2
                aria-hidden="true"
                className="h-3.5 w-3.5 animate-spin"
              />
            ) : (
              <Plug aria-hidden="true" className="h-3.5 w-3.5" />
            )}
            Verbinden
          </button>
        )}
      </div>

      {isObsidian && (
        <div className="mt-3 space-y-2">
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            className="flex cursor-pointer flex-col items-center gap-2 rounded-md border-2 border-dashed border-border p-4 transition-colors hover:border-indigo-400 hover:bg-indigo-50"
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ")
                fileInputRef.current?.click();
            }}
          >
            {uploadMutation.isPending ? (
              <Loader2
                aria-hidden="true"
                className="h-6 w-6 animate-spin text-indigo-500"
              />
            ) : (
              <Upload
                aria-hidden="true"
                className="h-6 w-6 text-text-tertiary"
              />
            )}
            <p className="text-xs text-text-secondary">
              {uploadMutation.isPending
                ? "Wird hochgeladen\u2026"
                : "ZIP-Archiv oder .md-Datei hier ablegen oder klicken"}
            </p>
            <p className="text-xs text-text-tertiary">Maximal 50 MB</p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip,.md"
            className="hidden"
            aria-label="Obsidian Vault hochladen"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleObsidianUpload(file);
              e.target.value = "";
            }}
          />
          {uploadError && <p className="text-xs text-red-600">{uploadError}</p>}
          {uploadResult && (
            <p className="text-xs text-green-600">
              {uploadResult.document_count} Dokument(e) importiert
              {uploadResult.deleted_count > 0 &&
                `, ${uploadResult.deleted_count} gelöscht`}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function ConnectorsPage() {
  const { data: types, isLoading: typesLoading } = useConnectorTypes();
  const { data: status, isLoading: statusLoading } = useConnectionStatus();
  const connectOAuth = useConnectOAuth();
  const disconnectMutation = useDisconnectConnector();
  const syncMutation = useSyncConnector();
  const revokeConsentMutation = useRevokeConsent();
  const [consentTarget, setConsentTarget] = useState<string | null>(null);

  const isLoading = typesLoading || statusLoading;
  const connectedTypes = new Set(status?.connections.map((c) => c.type) ?? []);
  const availableConnectors =
    types?.connectors.filter((c) => !connectedTypes.has(c.type)) ?? [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12" role="status">
        <Loader2
          aria-hidden="true"
          className="h-8 w-8 animate-spin text-text-tertiary"
        />
        <span className="sr-only">Wird geladen</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text">Konnektoren</h1>

      {/* Connected Connectors */}
      {status && status.connections.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-text">
            Verbundene Quellen
          </h2>
          <div className="space-y-3">
            {status.connections.map((conn) => (
              <ConnectedCard
                key={conn.type}
                connection={conn}
                onSync={() => syncMutation.mutate(conn.type)}
                onDisconnect={() => disconnectMutation.mutate(conn.type)}
                onRevokeConsent={() => revokeConsentMutation.mutate(conn.type)}
                isSyncing={
                  syncMutation.isPending && syncMutation.variables === conn.type
                }
                isRevoking={
                  revokeConsentMutation.isPending &&
                  revokeConsentMutation.variables === conn.type
                }
              />
            ))}
          </div>
        </div>
      )}

      {/* Available Connectors */}
      {availableConnectors.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-text">
            Verf\u00fcgbare Quellen
          </h2>
          <div className="space-y-3">
            {availableConnectors.map((connector) => (
              <AvailableConnectorCard
                key={connector.type}
                connector={connector}
                onConnect={() => setConsentTarget(connector.type)}
                isConnecting={
                  connectOAuth.isPending &&
                  connectOAuth.variables === connector.type
                }
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {(!types || types.connectors.length === 0) && (
        <div className="rounded-xl border border-border bg-surface p-8 text-center">
          <Plug
            aria-hidden="true"
            className="mx-auto mb-3 h-10 w-10 text-text-tertiary"
          />
          <h3 className="mb-1 text-sm font-semibold text-text">
            Keine Konnektoren verf\u00fcgbar
          </h3>
          <p className="text-sm text-text-tertiary">
            Konnektoren werden bald hinzugef&#252;gt.
          </p>
        </div>
      )}

      {/* Consent dialog before OAuth redirect */}
      {consentTarget && (
        <ConsentDialog
          connectorType={consentTarget}
          connectorName={
            types?.connectors.find((t) => t.type === consentTarget)?.name ??
            consentTarget
          }
          onConsented={() => {
            trackFirstConnector(consentTarget);
            connectOAuth.mutate(consentTarget);
            setConsentTarget(null);
          }}
          onCancel={() => setConsentTarget(null)}
        />
      )}
    </div>
  );
}
