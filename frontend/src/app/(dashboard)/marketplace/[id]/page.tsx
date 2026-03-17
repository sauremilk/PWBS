"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  Download,
  ExternalLink,
  Loader2,
  Puzzle,
  Shield,
  Trash2,
} from "lucide-react";
import {
  usePlugin,
  useInstallPlugin,
  useUninstallPlugin,
  useInstalledPlugins,
  useRatePlugin,
  usePluginRatings,
} from "@/hooks/use-marketplace";
import {
  RatingStars,
  AverageRating,
} from "@/components/marketplace/rating-stars";
import { InstallDialog } from "@/components/marketplace/install-dialog";
import type { RatePluginRequest } from "@/types/marketplace";

const TYPE_LABELS: Record<string, string> = {
  connector: "Konnektor",
  briefing_template: "Briefing-Template",
  processing: "Processing",
  agent: "Agent",
};

export default function PluginDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: plugin, isLoading, isError } = usePlugin(id);
  const { data: installed } = useInstalledPlugins();
  const { data: ratingsData } = usePluginRatings(id, { limit: 20 });
  const installMutation = useInstallPlugin();
  const uninstallMutation = useUninstallPlugin();
  const rateMutation = useRatePlugin();

  const [showInstallDialog, setShowInstallDialog] = useState(false);
  const [reviewScore, setReviewScore] = useState(0);
  const [reviewText, setReviewText] = useState("");

  const isInstalled = installed?.some((i) => i.plugin_id === id) ?? false;

  function handleInstall() {
    installMutation.mutate(
      { pluginId: id },
      { onSuccess: () => setShowInstallDialog(false) },
    );
  }

  function handleUninstall() {
    uninstallMutation.mutate(id);
  }

  function handleRate() {
    if (reviewScore < 1) return;
    const body: RatePluginRequest = {
      score: reviewScore,
      review_text: reviewText.trim() || null,
    };
    rateMutation.mutate(
      { pluginId: id, ...body },
      {
        onSuccess: () => {
          setReviewScore(0);
          setReviewText("");
        },
      },
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20" role="status">
        <Loader2
          aria-hidden="true"
          className="h-8 w-8 animate-spin text-text-tertiary"
        />
        <span className="sr-only">Wird geladen</span>
      </div>
    );
  }

  if (isError || !plugin) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm text-red-700">
          Plugin konnte nicht geladen werden.
        </p>
        <button
          onClick={() => router.push("/marketplace")}
          className="mt-3 text-sm font-medium text-red-600 hover:underline"
        >
          Zurück zum Marketplace
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Back link */}
      <button
        onClick={() => router.push("/marketplace")}
        className="inline-flex items-center gap-1.5 text-sm text-text-tertiary hover:text-text-secondary"
      >
        <ArrowLeft aria-hidden="true" className="h-4 w-4" />
        Zurück zum Marketplace
      </button>

      {/* Header */}
      <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl bg-surface-secondary text-text-tertiary">
            {plugin.icon_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={plugin.icon_url}
                alt=""
                className="h-12 w-12 rounded-lg"
              />
            ) : (
              <Puzzle aria-hidden="true" className="h-8 w-8" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-text">
                {plugin.name}
              </h1>
              {plugin.is_verified && (
                <CheckCircle2
                  aria-label="Verifiziert"
                  className="h-5 w-5 text-indigo-500"
                />
              )}
            </div>
            <p className="mt-1 text-sm text-text-tertiary">
              {TYPE_LABELS[plugin.plugin_type] ?? plugin.plugin_type} · v
              {plugin.version}
            </p>
            <div className="mt-2 flex items-center gap-4">
              <AverageRating
                ratingSum={plugin.rating_sum}
                ratingCount={plugin.rating_count}
              />
              <span className="inline-flex items-center gap-1 text-sm text-text-tertiary">
                <Download aria-hidden="true" className="h-4 w-4" />
                {plugin.install_count} Installationen
              </span>
            </div>
          </div>
        </div>

        {/* Install / Uninstall */}
        <div className="flex gap-3">
          {isInstalled ? (
            <button
              onClick={handleUninstall}
              disabled={uninstallMutation.isPending}
              className="inline-flex items-center gap-2 rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
            >
              {uninstallMutation.isPending ? (
                <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 aria-hidden="true" className="h-4 w-4" />
              )}
              Deinstallieren
            </button>
          ) : (
            <button
              onClick={() => setShowInstallDialog(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              <Download aria-hidden="true" className="h-4 w-4" />
              Installieren
            </button>
          )}
        </div>
      </div>

      {/* Content grid */}
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main content */}
        <div className="space-y-6 lg:col-span-2">
          {/* Description */}
          <section>
            <h2 className="mb-3 text-lg font-semibold text-text">
              Beschreibung
            </h2>
            <p className="whitespace-pre-line text-sm leading-relaxed text-text-secondary">
              {plugin.description || "Keine Beschreibung verfügbar."}
            </p>
          </section>

          {/* Changelog (from manifest) */}
          {plugin.manifest.changelog != null && (
            <section>
              <h2 className="mb-3 text-lg font-semibold text-text">
                Changelog
              </h2>
              <p className="whitespace-pre-line text-sm text-text-secondary">
                {String(plugin.manifest.changelog)}
              </p>
            </section>
          )}

          {/* Ratings & Reviews */}
          <section>
            <h2 className="mb-4 text-lg font-semibold text-text">
              Bewertungen
            </h2>

            {/* Write a review */}
            {isInstalled && (
              <div className="mb-6 rounded-lg border border-border bg-surface-secondary p-4">
                <h3 className="mb-2 text-sm font-medium text-text">
                  Bewertung abgeben
                </h3>
                <div className="mb-3">
                  <RatingStars value={reviewScore} onChange={setReviewScore} />
                </div>
                <textarea
                  value={reviewText}
                  onChange={(e) => setReviewText(e.target.value)}
                  placeholder="Optional: Deine Erfahrung beschreiben…"
                  rows={3}
                  className="mb-3 w-full rounded-md border border-border px-3 py-2 text-sm placeholder:text-text-tertiary focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <button
                  onClick={handleRate}
                  disabled={reviewScore < 1 || rateMutation.isPending}
                  className="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {rateMutation.isPending && (
                    <Loader2
                      aria-hidden="true"
                      className="h-4 w-4 animate-spin"
                    />
                  )}
                  Bewerten
                </button>
              </div>
            )}

            {/* Reviews list */}
            {ratingsData && ratingsData.ratings.length > 0 ? (
              <div className="space-y-4">
                {ratingsData.ratings.map((rating) => (
                  <div
                    key={rating.id}
                    className="rounded-lg border border-border bg-surface p-4"
                  >
                    <div className="mb-1 flex items-center gap-2">
                      <RatingStars value={rating.score} readonly size="sm" />
                      <span className="text-xs text-text-tertiary">
                        {new Date(rating.rated_at).toLocaleDateString("de-DE")}
                      </span>
                    </div>
                    {rating.review_text && (
                      <p className="text-sm text-text-secondary">
                        {rating.review_text}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-text-tertiary">
                Noch keine Bewertungen vorhanden.
              </p>
            )}
          </section>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Permissions */}
          {plugin.permissions.length > 0 && (
            <section className="rounded-lg border border-border bg-surface p-4">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-text">
                <Shield
                  aria-hidden="true"
                  className="h-4 w-4 text-yellow-500"
                />
                Berechtigungen
              </h3>
              <ul className="space-y-1.5">
                {plugin.permissions.map((perm) => (
                  <li key={perm} className="text-sm text-text-secondary">
                    · {perm}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Details */}
          <section className="rounded-lg border border-border bg-surface p-4">
            <h3 className="mb-3 text-sm font-semibold text-text">
              Details
            </h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-text-tertiary">Version</dt>
                <dd className="font-medium text-text">{plugin.version}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-text-tertiary">Status</dt>
                <dd className="font-medium text-text">{plugin.status}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-text-tertiary">Erstellt</dt>
                <dd className="font-medium text-text">
                  {new Date(plugin.created_at).toLocaleDateString("de-DE")}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-text-tertiary">Aktualisiert</dt>
                <dd className="font-medium text-text">
                  {new Date(plugin.updated_at).toLocaleDateString("de-DE")}
                </dd>
              </div>
            </dl>
          </section>

          {/* Repository link */}
          {plugin.repository_url && (
            <a
              href={plugin.repository_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm font-medium text-indigo-600 hover:underline"
            >
              <ExternalLink aria-hidden="true" className="h-4 w-4" />
              Repository
            </a>
          )}
        </div>
      </div>

      {/* Install Dialog */}
      {showInstallDialog && plugin && (
        <InstallDialog
          plugin={plugin}
          onConfirm={handleInstall}
          onCancel={() => setShowInstallDialog(false)}
          isInstalling={installMutation.isPending}
        />
      )}
    </div>
  );
}
