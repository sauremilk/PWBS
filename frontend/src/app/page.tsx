import Link from "next/link";
import { WaitlistForm } from "@/components/landing/waitlist-form";

const FEATURES = [
  {
    title: "Kontextbriefings",
    description:
      "Jeden Morgen ein massgeschneidertes Briefing aus all Ihren Datenquellen – automatisch, mit Quellenbelegen.",
    icon: "📋",
  },
  {
    title: "Semantische Suche",
    description:
      "Finden Sie Informationen nach Bedeutung, nicht nur nach Stichworten. Ueber alle Quellen hinweg.",
    icon: "🔍",
  },
  {
    title: "Knowledge Graph",
    description:
      "Automatische Vernetzung Ihrer Notizen, E-Mails, Kalender und Dokumente zu einem persoenlichen Wissensnetz.",
    icon: "🕸️",
  },
  {
    title: "DSGVO by Design",
    description:
      "Ihre Daten gehoeren Ihnen. Verschluesselung, Loeschbarkeit und Transparenz sind Grundstruktur.",
    icon: "🔒",
  },
] as const;

const SOCIAL_PROOF = [
  {
    quote:
      "PWBS hat meine Meetingvorbereitung revolutioniert. Statt 30 Minuten brauche ich jetzt 2 Minuten.",
    author: "Dr. Sabine M.",
    role: "Unternehmensberaterin",
  },
  {
    quote:
      "Endlich ein Tool, das meine Notizen, E-Mails und Kalender zusammenbringt – datenschutzkonform.",
    author: "Thomas K.",
    role: "Forschungsleiter",
  },
  {
    quote:
      "Die semantische Suche findet Zusammenhaenge, die mir vorher entgangen sind.",
    author: "Lisa R.",
    role: "Produktmanagerin",
  },
] as const;

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="border-b border-gray-100">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
          <span className="text-xl font-bold text-gray-900">PWBS</span>
          <Link
            href="/login"
            className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white
              hover:bg-gray-800 transition-colors"
          >
            Anmelden
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="mx-auto max-w-6xl px-4 py-16 text-center sm:px-6 sm:py-24 lg:py-32">
        <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 sm:text-5xl lg:text-6xl">
          Ihr persoenliches{" "}
          <span className="text-blue-600">Wissens-Betriebssystem</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-gray-600 sm:text-xl">
          PWBS verbindet Ihre Datenquellen, erkennt Zusammenhaenge und liefert
          Ihnen taeglich kontextbezogene Briefings – damit Sie bessere
          Entscheidungen treffen.
        </p>
        <div className="mx-auto mt-10 max-w-lg">
          <WaitlistForm />
          <p className="mt-3 text-sm text-gray-500">
            Kostenlos fuer Beta-Tester. Kein Spam, jederzeit abmeldbar.
          </p>
        </div>
      </section>

      {/* Features Section */}
      <section className="bg-gray-50 py-16 sm:py-24" aria-label="Funktionen">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <h2 className="text-center text-3xl font-bold text-gray-900 sm:text-4xl">
            Ihre Daten. Intelligent vernetzt.
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-center text-gray-600">
            PWBS fuehrt heterogene Datenquellen zusammen und macht Wissen
            kontextbezogen verfuegbar.
          </p>
          <div className="mt-12 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map((feature) => (
              <div
                key={feature.title}
                className="rounded-xl bg-white p-6 shadow-sm border border-gray-100"
              >
                <div className="text-3xl" aria-hidden="true">
                  {feature.icon}
                </div>
                <h3 className="mt-4 text-lg font-semibold text-gray-900">
                  {feature.title}
                </h3>
                <p className="mt-2 text-sm text-gray-600 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Social Proof Section */}
      <section className="py-16 sm:py-24" aria-label="Erfahrungen">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <h2 className="text-center text-3xl font-bold text-gray-900 sm:text-4xl">
            Was Wissensarbeiter sagen
          </h2>
          <div className="mt-12 grid gap-8 sm:grid-cols-3">
            {SOCIAL_PROOF.map((item) => (
              <figure
                key={item.author}
                className="rounded-xl bg-gray-50 p-6 border border-gray-100"
              >
                <blockquote className="text-gray-700 leading-relaxed">
                  &ldquo;{item.quote}&rdquo;
                </blockquote>
                <figcaption className="mt-4">
                  <p className="font-semibold text-gray-900">{item.author}</p>
                  <p className="text-sm text-gray-500">{item.role}</p>
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-gray-900 py-16 sm:py-24">
        <div className="mx-auto max-w-3xl px-4 text-center sm:px-6">
          <h2 className="text-3xl font-bold text-white sm:text-4xl">
            Bereit fuer intelligenteres Arbeiten?
          </h2>
          <p className="mt-4 text-gray-300">
            Sichern Sie sich Ihren Platz in der Beta. Begrenzte Plaetze
            verfuegbar.
          </p>
          <div className="mx-auto mt-8 max-w-lg">
            <WaitlistForm />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-8">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <span className="text-sm text-gray-500">
              &copy; {new Date().getFullYear()} PWBS. Alle Rechte vorbehalten.
            </span>
            <div className="flex gap-6 text-sm text-gray-500">
              <Link
                href="/impressum"
                className="hover:text-gray-900 transition-colors"
              >
                Impressum
              </Link>
              <Link
                href="/datenschutz"
                className="hover:text-gray-900 transition-colors"
              >
                Datenschutz
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
