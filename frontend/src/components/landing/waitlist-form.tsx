"use client";

import { useState, FormEvent } from "react";
import { apiClient } from "@/lib/api-client";

interface WaitlistFormProps {
  className?: string;
}

export function WaitlistForm({ className = "" }: WaitlistFormProps) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle");
  const [message, setMessage] = useState("");

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!email.trim()) return;

    setStatus("loading");
    try {
      const res = await apiClient.post<{ success: boolean; message: string }>(
        "/api/v1/waitlist",
        { email: email.trim().toLowerCase(), source: "landing" },
        { skipAuth: true },
      );
      setStatus("success");
      setMessage(res.message);
      setEmail("");
    } catch {
      setStatus("error");
      setMessage("Ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.");
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={`flex flex-col sm:flex-row gap-3 ${className}`}
    >
      <label htmlFor="waitlist-email" className="sr-only">
        E-Mail-Adresse
      </label>
      <input
        id="waitlist-email"
        type="email"
        required
        value={email}
        onChange={(e) => {
          setEmail(e.target.value);
          if (status !== "idle") setStatus("idle");
        }}
        placeholder="ihre@email.de"
        className="flex-1 rounded-lg border border-gray-300 px-4 py-3 text-base
          focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20
          disabled:opacity-60"
        disabled={status === "loading"}
        aria-describedby={status !== "idle" ? "waitlist-status" : undefined}
      />
      <button
        type="submit"
        disabled={status === "loading"}
        className="rounded-lg bg-blue-600 px-6 py-3 text-base font-semibold text-white
          hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/50
          disabled:opacity-60 transition-colors whitespace-nowrap"
      >
        {status === "loading" ? "Wird gesendet..." : "Platz sichern"}
      </button>
      {status !== "idle" && (
        <p
          id="waitlist-status"
          role="status"
          className={`text-sm mt-1 sm:mt-0 sm:self-center ${
            status === "success" ? "text-green-600" : "text-red-600"
          }`}
        >
          {message}
        </p>
      )}
    </form>
  );
}
