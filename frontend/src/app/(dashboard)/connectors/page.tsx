"use client";

import { useState } from "react";
import {
  Plug,
  RefreshCw,
  Trash2,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FolderOpen,
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
} from "@/hooks/use-connectors";
import { ConsentDialog } from "@/components/connectors/consent-dialog";
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
        className="h-4 w-4 animate-spin text-blue-500"
      />
    ),
    label: "Synchronisiert\u2026",
    color: "text-blue-700 bg-blue-50",
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
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100">
            <Plug aria-hidden="true" className="h-5 w-5 text-gray-600" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">
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
            className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
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

      <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
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
              className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-white"
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
              className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-white"
            >
              Abbrechen
            </button>
          </div>
        </div>
      )}
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
  const [vaultPath, setVaultPath] = useState("");
  const [pathError, setPathError] = useState<string | null>(null);
  const configMutation = useConfigureConnector();
  const isObsidian = connector.type === "obsidian";

  function handleObsidianConnect() {
    if (!vaultPath.trim()) {
      setPathError("Bitte gib einen Vault-Pfad ein.");
      return;
    }
    setPathError(null);
    configMutation.mutate(
      { type: connector.type, vault_path: vaultPath.trim() },
      {
        onError: () =>
          setPathError(
            "Ung\u00fcltiger Vault-Pfad. Bitte \u00fcberpr\u00fcfe den Pfad.",
          ),
      },
    );
  }

  return (
    <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white">
            <Plug aria-hidden="true" className="h-5 w-5 text-gray-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              {connector.name}
            </h3>
            <p className="text-xs text-gray-500">{connector.description}</p>
          </div>
        </div>
        {!isObsidian && (
          <button
            onClick={onConnect}
            disabled={isConnecting}
            className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
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
          <label
            htmlFor="vault-path"
            className="flex items-center gap-1 text-xs font-medium text-gray-700"
          >
            <FolderOpen aria-hidden="true" className="h-3.5 w-3.5" />
            Vault-Pfad
          </label>
          <div className="flex gap-2">
            <input
              id="vault-path"
              type="text"
              value={vaultPath}
              onChange={(e) => setVaultPath(e.target.value)}
              placeholder="/pfad/zu/obsidian/vault"
              className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              onClick={handleObsidianConnect}
              disabled={configMutation.isPending}
              className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {configMutation.isPending ? (
                <Loader2
                  aria-hidden="true"
                  className="h-3.5 w-3.5 animate-spin"
                />
              ) : (
                <Plug aria-hidden="true" className="h-3.5 w-3.5" />
              )}
              Verbinden
            </button>
          </div>
          {pathError && <p className="text-xs text-red-600">{pathError}</p>}
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
          className="h-8 w-8 animate-spin text-gray-400"
        />
        <span className="sr-only">Wird geladen</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Konnektoren</h1>

      {/* Connected Connectors */}
      {status && status.connections.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-gray-800">
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
          <h2 className="mb-3 text-lg font-semibold text-gray-800">
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
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center">
          <Plug
            aria-hidden="true"
            className="mx-auto mb-3 h-10 w-10 text-gray-300"
          />
          <h3 className="mb-1 text-sm font-semibold text-gray-900">
            Keine Konnektoren verf&#252;gbar
          </h3>
          <p className="text-sm text-gray-500">
            Konnektoren werden bald hinzugef&#252;gt.
          </p>
        </div>
      )}

      {/* Consent dialog before OAuth redirect */}
      {consentTarget && (
        <ConsentDialog
          connectorType={consentTarget}
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
