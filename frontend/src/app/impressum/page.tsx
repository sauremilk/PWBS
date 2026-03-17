import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Impressum – PWBS",
  description: "Impressum und Anbieterkennzeichnung gemäß § 5 TMG.",
};

export default function ImpressumPage() {
  return (
    <div className="min-h-screen bg-surface">
      <nav className="border-b border-border">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4 sm:px-6">
          <Link href="/" className="text-xl font-bold text-text">
            PWBS
          </Link>
          <Link
            href="/"
            className="text-sm text-text-tertiary hover:text-text transition-colors"
          >
            Zurück zur Startseite
          </Link>
        </div>
      </nav>

      <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6 sm:py-16">
        <h1 className="text-3xl font-bold text-text sm:text-4xl">
          Impressum
        </h1>
        <p className="mt-2 text-sm text-text-tertiary">Angaben gemäß § 5 TMG</p>

        <div className="mt-8 space-y-8 text-text-secondary leading-relaxed">
          <section>
            <h2 className="text-lg font-semibold text-text">Anbieter</h2>
            <p className="mt-2">
              PWBS – Persönliches Wissens-Betriebssystem
              <br />
              Mick Gajewski
              <br />
              [Straße und Hausnummer]
              <br />
              [PLZ Ort]
              <br />
              Deutschland
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-text">Kontakt</h2>
            <p className="mt-2">
              E-Mail:{" "}
              <a
                href="mailto:kontakt@pwbs.app"
                className="text-indigo-600 hover:underline"
              >
                kontakt@pwbs.app
              </a>
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-text">
              Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV
            </h2>
            <p className="mt-2">
              Mick Gajewski
              <br />
              [Straße und Hausnummer]
              <br />
              [PLZ Ort]
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-text">
              EU-Streitschlichtung
            </h2>
            <p className="mt-2">
              Die Europäische Kommission stellt eine Plattform zur
              Online-Streitbeilegung (OS) bereit:{" "}
              <a
                href="https://ec.europa.eu/consumers/odr/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-600 hover:underline"
              >
                https://ec.europa.eu/consumers/odr/
              </a>
              . Wir sind nicht bereit oder verpflichtet, an
              Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle
              teilzunehmen.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-text">
              Haftung für Inhalte
            </h2>
            <p className="mt-2">
              Als Diensteanbieter sind wir gemäß § 7 Abs. 1 TMG für eigene
              Inhalte auf diesen Seiten nach den allgemeinen Gesetzen
              verantwortlich. Nach §§ 8 bis 10 TMG sind wir als Diensteanbieter
              jedoch nicht verpflichtet, übermittelte oder gespeicherte fremde
              Informationen zu überwachen oder nach Umständen zu forschen, die
              auf eine rechtswidrige Tätigkeit hinweisen.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-text">
              Haftung für Links
            </h2>
            <p className="mt-2">
              Unser Angebot enthält Links zu externen Websites Dritter, auf
              deren Inhalte wir keinen Einfluss haben. Für die Inhalte der
              verlinkten Seiten ist stets der jeweilige Anbieter oder Betreiber
              der Seiten verantwortlich.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-text">
              Urheberrecht
            </h2>
            <p className="mt-2">
              Die durch die Seitenbetreiber erstellten Inhalte und Werke auf
              diesen Seiten unterliegen dem deutschen Urheberrecht. Die
              Vervielfältigung, Bearbeitung, Verbreitung und jede Art der
              Verwertung außerhalb der Grenzen des Urheberrechtes bedürfen der
              schriftlichen Zustimmung des jeweiligen Autors bzw. Erstellers.
            </p>
          </section>
        </div>
      </main>

      <footer className="border-t border-border py-8">
        <div className="mx-auto max-w-4xl px-4 sm:px-6">
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <span className="text-sm text-text-tertiary">
              &copy; {new Date().getFullYear()} PWBS. Alle Rechte vorbehalten.
            </span>
            <div className="flex gap-6 text-sm text-text-tertiary">
              <Link href="/impressum" className="font-medium text-text">
                Impressum
              </Link>
              <Link
                href="/datenschutz"
                className="hover:text-text transition-colors"
              >
                Datenschutz
              </Link>
              <Link
                href="/agb"
                className="hover:text-text transition-colors"
              >
                AGB
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
