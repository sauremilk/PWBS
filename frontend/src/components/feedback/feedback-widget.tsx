"use client";

import { useState, useCallback } from "react";
import { MessageSquarePlus, X, Bug, Lightbulb, ThumbsUp } from "lucide-react";
import { submitFeedback } from "@/lib/api/feedback";
import type { SubmitFeedbackRequest } from "@/lib/api/feedback";

type FeedbackType = SubmitFeedbackRequest["feedback_type"];

const FEEDBACK_TYPES: {
  value: FeedbackType;
  label: string;
  icon: typeof Bug;
}[] = [
  { value: "bug", label: "Bug melden", icon: Bug },
  { value: "feature", label: "Feature-Wunsch", icon: Lightbulb },
  { value: "praise", label: "Lob", icon: ThumbsUp },
];

function getContextMeta() {
  return {
    url: typeof window !== "undefined" ? window.location.href : "",
    browser_info: typeof navigator !== "undefined" ? navigator.userAgent : "",
    viewport_size:
      typeof window !== "undefined"
        ? `${window.innerWidth}x${window.innerHeight}`
        : "",
  };
}

export function FeedbackWidget() {
  const [open, setOpen] = useState(false);
  const [feedbackType, setFeedbackType] = useState<FeedbackType>("bug");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setMessage("");
    setFeedbackType("bug");
    setError(null);
    setSubmitted(false);
  }, []);

  const handleClose = useCallback(() => {
    setOpen(false);
    // Reset after animation
    setTimeout(reset, 200);
  }, [reset]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!message.trim()) return;

      setSubmitting(true);
      setError(null);

      try {
        await submitFeedback({
          feedback_type: feedbackType,
          message: message.trim(),
          context: getContextMeta(),
        });
        setSubmitted(true);
        setTimeout(handleClose, 1500);
      } catch {
        setError(
          "Feedback konnte nicht gesendet werden. Bitte versuche es erneut.",
        );
      } finally {
        setSubmitting(false);
      }
    },
    [feedbackType, message, handleClose],
  );

  return (
    <>
      {/* Floating trigger button */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-600 text-white shadow-lg transition-transform hover:scale-105 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        aria-label="Feedback geben"
      >
        <MessageSquarePlus className="h-5 w-5" />
      </button>

      {/* Dialog overlay */}
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-end p-6 sm:items-center sm:justify-center"
          role="presentation"
        >
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/30"
            onClick={handleClose}
            onKeyDown={(e) => e.key === "Escape" && handleClose()}
            role="button"
            tabIndex={-1}
            aria-label="Schließen"
          />

          {/* Dialog */}
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Feedback senden"
            className="relative z-10 w-full max-w-md rounded-xl bg-surface p-6 shadow-2xl"
          >
            {/* Header */}
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-text">Feedback</h2>
              <button
                type="button"
                onClick={handleClose}
                className="rounded-lg p-1.5 text-text-tertiary hover:bg-surface-secondary hover:text-text-secondary"
                aria-label="Schließen"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {submitted ? (
              <div className="py-8 text-center">
                <ThumbsUp className="mx-auto mb-3 h-8 w-8 text-green-500" />
                <p className="text-sm text-text-secondary">
                  Danke für dein Feedback!
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit}>
                {/* Type selector */}
                <div className="mb-4 flex gap-2">
                  {FEEDBACK_TYPES.map(({ value, label, icon: Icon }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setFeedbackType(value)}
                      className={`flex flex-1 flex-col items-center gap-1 rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
                        feedbackType === value
                          ? "border-indigo-500 bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300"
                          : "border-border text-text-tertiary hover:border-indigo-200"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      {label}
                    </button>
                  ))}
                </div>

                {/* Message */}
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Dein Feedback..."
                  rows={4}
                  maxLength={5000}
                  required
                  className="mb-3 w-full resize-none rounded-lg border border-border bg-surface-secondary p-3 text-sm text-text placeholder:text-text-tertiary focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />

                {error && (
                  <p className="mb-3 text-sm text-red-600 dark:text-red-400">
                    {error}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={submitting || !message.trim()}
                  className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {submitting ? "Wird gesendet..." : "Absenden"}
                </button>

                <p className="mt-2 text-center text-xs text-text-tertiary">
                  Kontext (URL, Browser) wird automatisch angehängt
                </p>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}
