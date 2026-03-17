"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import {
  ArrowLeft,
  ThumbsUp,
  ThumbsDown,
  FileText,
  Calendar,
  ExternalLink,
  Loader2,
  MessageSquare,
} from "lucide-react";
import { useBriefingDetail, useBriefingFeedback } from "@/hooks/use-briefings";
import type { SourceRefResponse, BriefingType } from "@/types/api";

const BRIEFING_TYPE_LABELS: Record<BriefingType, string> = {
  morning: "Morgen-Briefing",
  meeting: "Meeting-Briefing",
  project: "Projekt-Briefing",
  weekly: "Wochen-Briefing",
};

function SourceCard({ source }: { source: SourceRefResponse }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-border bg-surface-secondary p-3">
      <FileText
        aria-hidden="true"
        className="mt-0.5 h-4 w-4 flex-shrink-0 text-text-tertiary"
      />
      <div className="min-w-0 flex-1">
        <Link
          href={`/documents/${source.chunk_id}`}
          className="text-sm font-medium text-indigo-600 hover:underline"
        >
          {source.doc_title}
        </Link>
        <div className="mt-0.5 flex items-center gap-2 text-xs text-text-tertiary">
          <span className="rounded bg-surface-secondary px-1.5 py-0.5 font-medium">
            {source.source_type}
          </span>
          <Calendar aria-hidden="true" className="h-3 w-3" />
          <span>{new Date(source.date).toLocaleDateString("de-DE")}</span>
          <span className="ml-auto text-xs font-medium text-indigo-700">
            {Math.round(source.relevance * 100)}%
          </span>
        </div>
      </div>
      <a
        href={`/documents/${source.chunk_id}`}
        aria-label="Original öffnen"
        className="flex-shrink-0 text-text-tertiary hover:text-text-secondary"
      >
        <ExternalLink aria-hidden="true" className="h-4 w-4" />
      </a>
    </div>
  );
}

export default function BriefingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: briefing, isLoading } = useBriefingDetail(id);
  const feedback = useBriefingFeedback(id);
  const [feedbackSent, setFeedbackSent] = useState<
    "positive" | "negative" | null
  >(null);
  const [showComment, setShowComment] = useState(false);
  const [comment, setComment] = useState("");

  function handleFeedback(rating: "positive" | "negative") {
    setFeedbackSent(rating);
    if (rating === "negative") {
      setShowComment(true);
    } else {
      feedback.mutate({ rating });
    }
  }

  function submitComment() {
    if (feedbackSent) {
      feedback.mutate({
        rating: feedbackSent,
        comment: comment || undefined,
      });
      setShowComment(false);
    }
  }

  if (isLoading) {
    return (
      <div role="status" className="flex items-center justify-center py-12">
        <Loader2
          aria-hidden="true"
          className="h-8 w-8 animate-spin text-text-tertiary"
        />
        <span className="sr-only">Wird geladen</span>
      </div>
    );
  }

  if (!briefing) {
    return (
      <div className="rounded-lg border border-border bg-surface p-8 text-center">
        <h3 className="text-sm font-semibold text-text">
          Briefing nicht gefunden
        </h3>
        <button
          onClick={() => router.push("/briefings")}
          className="mt-3 text-sm text-indigo-600 hover:underline"
        >
          Zur\u00fcck zur \u00dcbersicht
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => router.push("/briefings")}
          className="mb-3 inline-flex items-center gap-1 text-sm text-text-tertiary hover:text-text-secondary"
        >
          <ArrowLeft aria-hidden="true" className="h-4 w-4" />
          Zur\u00fcck
        </button>
        <h1 className="text-2xl font-bold text-text">{briefing.title}</h1>
        <div className="mt-1 flex items-center gap-2 text-sm text-text-tertiary">
          <span className="rounded bg-surface-secondary px-2 py-0.5 text-xs font-medium">
            {BRIEFING_TYPE_LABELS[briefing.briefing_type]}
          </span>
          <Calendar aria-hidden="true" className="h-4 w-4" />
          <span>
            {new Date(briefing.generated_at).toLocaleDateString("de-DE", {
              weekday: "long",
              year: "numeric",
              month: "long",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
      </div>

      {/* Briefing Content */}
      <div className="rounded-lg border border-border bg-surface p-6">
        <article className="prose prose-sm max-w-none prose-headings:text-text prose-p:text-text-secondary prose-a:text-indigo-600">
          <ReactMarkdown
            components={{
              a: ({ href, children, ...props }) => (
                <Link
                  href={href ?? "#"}
                  className="text-indigo-600 underline hover:text-indigo-800"
                  {...props}
                >
                  {children}
                </Link>
              ),
            }}
          >
            {briefing.content}
          </ReactMarkdown>
        </article>
      </div>

      {/* Feedback */}
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="mb-3 text-sm font-medium text-text-secondary">
          War dieses Briefing hilfreich?
        </p>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleFeedback("positive")}
            disabled={feedback.isPending || feedbackSent !== null}
            className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm transition-colors ${
              feedbackSent === "positive"
                ? "border-green-300 bg-green-50 text-green-700"
                : "border-border text-text-secondary hover:bg-surface-secondary"
            } disabled:opacity-50`}
          >
            <ThumbsUp aria-hidden="true" className="h-4 w-4" />
            Hilfreich
          </button>
          <button
            onClick={() => handleFeedback("negative")}
            disabled={
              feedback.isPending || (feedbackSent !== null && !showComment)
            }
            className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm transition-colors ${
              feedbackSent === "negative"
                ? "border-red-300 bg-red-50 text-red-700"
                : "border-border text-text-secondary hover:bg-surface-secondary"
            } disabled:opacity-50`}
          >
            <ThumbsDown aria-hidden="true" className="h-4 w-4" />
            Nicht hilfreich
          </button>
        </div>
        {showComment && (
          <div className="mt-3 space-y-2">
            <label
              htmlFor="feedback-comment"
              className="flex items-center gap-1 text-sm text-text-secondary"
            >
              <MessageSquare aria-hidden="true" className="h-3.5 w-3.5" />
              Was k\u00f6nnte verbessert werden?
            </label>
            <textarea
              id="feedback-comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              className="w-full rounded-md border border-border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              placeholder="Optionaler Kommentar\u2026"
            />
            <button
              onClick={submitComment}
              disabled={feedback.isPending}
              className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              Absenden
            </button>
          </div>
        )}
        {feedback.isSuccess && (
          <p className="mt-2 text-sm text-green-600">
            Vielen Dank f\u00fcr dein Feedback!
          </p>
        )}
      </div>

      {/* Sources */}
      {briefing.sources.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-text">
            Quellen ({briefing.sources.length})
          </h2>
          <div className="space-y-2">
            {briefing.sources.map((source) => (
              <SourceCard key={source.chunk_id} source={source} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
