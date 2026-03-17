import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Datenschutzerklärung – PWBS",
  description:
    "Datenschutzerklärung des Persönlichen Wissens-Betriebssystems (PWBS).",
};

export default function DatenschutzPage() {
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
          Datenschutzerklärung
        </h1>
        <p className="mt-2 text-sm text-text-tertiary">Stand: Juli 2025</p>

        <div className="mt-8 space-y-10 text-text-secondary leading-relaxed">
          {/* 1 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              1. Verantwortlicher
            </h2>
            <p className="mt-2">
              Verantwortlich im Sinne der DSGVO:
              <br />
              Mick Gajewski
              <br />
              E-Mail:{" "}
              <a
                href="mailto:kontakt@pwbs.app"
                className="text-indigo-600 hover:underline"
              >
                kontakt@pwbs.app
              </a>
            </p>
          </section>

          {/* 2 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              2. Überblick über die Datenverarbeitung
            </h2>
            <p className="mt-2">
              PWBS (Persönliches Wissens-Betriebssystem) ist eine KI-gestützte
              Plattform, die Ihre persönlichen Wissensdaten (Kalender, Notizen,
              Meeting-Transkripte) zusammenführt, semantisch analysiert und als
              kontextbezogene Briefings aufbereitet.
            </p>
            <p className="mt-2">
              Wir verarbeiten Ihre Daten ausschließlich zur Erbringung des
              Dienstes. Ihre Daten werden <strong>niemals</strong> für das
              Training von KI-Modellen verwendet.
            </p>
          </section>

          {/* 3 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              3. Rechtsgrundlagen (Art. 6 DSGVO)
            </h2>
            <ul className="mt-2 list-disc pl-6 space-y-1">
              <li>
                <strong>Vertragserfüllung (Art. 6 Abs. 1 lit. b):</strong>{" "}
                Verarbeitung Ihrer Wissensdaten zur Erbringung des PWBS-Dienstes
              </li>
              <li>
                <strong>Einwilligung (Art. 6 Abs. 1 lit. a):</strong> Anbindung
                externer Datenquellen über OAuth (jederzeit widerrufbar)
              </li>
              <li>
                <strong>Berechtigtes Interesse (Art. 6 Abs. 1 lit. f):</strong>{" "}
                Sicherheit, Missbrauchsschutz, anonymisierte Nutzungsstatistiken
              </li>
            </ul>
          </section>

          {/* 4 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              4. Welche Daten wir verarbeiten
            </h2>

            <h3 className="mt-4 font-semibold text-text">
              4.1 Registrierung und Authentifizierung
            </h3>
            <p className="mt-1">
              E-Mail-Adresse, gehashtes Passwort (Argon2id), OAuth-Tokens
              (AES-256-GCM verschlüsselt). Aufbewahrung: bis zur
              Kontolöschung.
            </p>

            <h3 className="mt-4 font-semibold text-text">
              4.2 Waitlist (vor der Registrierung)
            </h3>
            <p className="mt-1">
              Wenn Sie sich auf die Warteliste eintragen, speichern wir Ihre
              E-Mail-Adresse auf Grundlage Ihrer Einwilligung (Art. 6 Abs. 1
              lit. a DSGVO). Die E-Mail wird ausschließlich genutzt, um Sie
              über den Start von PWBS zu informieren. Sie können Ihre
              Einwilligung jederzeit per E-Mail an{" "}
              <a
                href="mailto:kontakt@pwbs.app"
                className="text-indigo-600 hover:underline"
              >
                kontakt@pwbs.app
              </a>{" "}
              widerrufen.
            </p>

            <h3 className="mt-4 font-semibold text-text">
              4.3 Wissensdaten (nach Anbindung)
            </h3>
            <div className="mt-2 overflow-x-auto">
              <table className="min-w-full text-sm border border-border rounded">
                <thead className="bg-surface-secondary">
                  <tr>
                    <th className="px-4 py-2 text-left font-semibold text-text">
                      Datenquelle
                    </th>
                    <th className="px-4 py-2 text-left font-semibold text-text">
                      Daten
                    </th>
                    <th className="px-4 py-2 text-left font-semibold text-text">
                      Aufbewahrung
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  <tr>
                    <td className="px-4 py-2">Google Calendar</td>
                    <td className="px-4 py-2">
                      Termine, Teilnehmer, Beschreibungen
                    </td>
                    <td className="px-4 py-2">365 Tage</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-2">Notion</td>
                    <td className="px-4 py-2">
                      Seiteninhalte, Datenbanken, Kommentare
                    </td>
                    <td className="px-4 py-2">730 Tage</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-2">Zoom</td>
                    <td className="px-4 py-2">
                      Meeting-Transkripte, Aufnahmen
                    </td>
                    <td className="px-4 py-2">365 Tage</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-2">Obsidian</td>
                    <td className="px-4 py-2">
                      Markdown-Notizen, Vault-Struktur
                    </td>
                    <td className="px-4 py-2">730 Tage</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <h3 className="mt-4 font-semibold text-text">
              4.4 Abgeleitete Daten
            </h3>
            <ul className="mt-1 list-disc pl-6 space-y-1">
              <li>
                <strong>Embeddings (Vektoren):</strong> Mathematische
                Repräsentationen Ihrer Texte für die semantische Suche.
                Löschung kaskadiert mit dem Quelldokument.
              </li>
              <li>
                <strong>LLM-generierte Inhalte:</strong> Briefings,
                Zusammenfassungen, Antworten. Aufbewahrung: 90 Tage.
              </li>
              <li>
                <strong>Knowledge Graph:</strong> Extrahierte Entitäten
                (Personen, Projekte, Entscheidungen). Löschung kaskadiert mit
                dem Quelldokument.
              </li>
            </ul>
          </section>

          {/* 5 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              5. KI-Verarbeitung und LLM-Nutzung
            </h2>
            <p className="mt-2">
              PWBS nutzt große Sprachmodelle (LLMs) zur Analyse und
              Aufbereitung Ihrer Daten. Dabei gelten folgende Prinzipien:
            </p>
            <ul className="mt-2 list-disc pl-6 space-y-1">
              <li>
                Ihre Daten werden <strong>nicht</strong> zum Training von
                KI-Modellen verwendet
              </li>
              <li>
                LLM-Anfragen enthalten nur den notwendigen Kontext (minimale
                Datenweitergabe)
              </li>
              <li>
                Alle LLM-generierten Aussagen werden mit Quellenreferenzen
                versehen
              </li>
              <li>
                LLM-Audit-Logs dokumentieren jede Anfrage für Transparenz
              </li>
            </ul>
            <p className="mt-2">
              <strong>Eingesetzte LLM-Anbieter:</strong>
            </p>
            <ul className="mt-1 list-disc pl-6 space-y-1">
              <li>
                Anthropic (Claude) – primäres Sprachmodell,
                Auftragsverarbeitungsvertrag (AVV) geschlossen
              </li>
              <li>
                OpenAI (GPT-4, Ada) – Fallback-Modell und Embeddings, AVV
                geschlossen
              </li>
            </ul>
          </section>

          {/* 6 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              6. Auftragsverarbeiter und Drittländer
            </h2>
            <p className="mt-2">Wir setzen folgende Auftragsverarbeiter ein:</p>
            <div className="mt-2 overflow-x-auto">
              <table className="min-w-full text-sm border border-border rounded">
                <thead className="bg-surface-secondary">
                  <tr>
                    <th className="px-4 py-2 text-left font-semibold text-text">
                      Anbieter
                    </th>
                    <th className="px-4 py-2 text-left font-semibold text-text">
                      Zweck
                    </th>
                    <th className="px-4 py-2 text-left font-semibold text-text">
                      Standort
                    </th>
                    <th className="px-4 py-2 text-left font-semibold text-text">
                      Grundlage
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  <tr>
                    <td className="px-4 py-2">AWS (Frankfurt)</td>
                    <td className="px-4 py-2">
                      Hosting, Datenbanken, Verschlüsselung
                    </td>
                    <td className="px-4 py-2">EU (eu-central-1)</td>
                    <td className="px-4 py-2">AVV</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-2">Vercel</td>
                    <td className="px-4 py-2">Frontend-Hosting</td>
                    <td className="px-4 py-2">EU / USA</td>
                    <td className="px-4 py-2">
                      AVV + EU-Standardvertragsklauseln
                    </td>
                  </tr>
                  <tr>
                    <td className="px-4 py-2">Anthropic</td>
                    <td className="px-4 py-2">KI-Sprachmodell</td>
                    <td className="px-4 py-2">USA</td>
                    <td className="px-4 py-2">
                      AVV + EU-Standardvertragsklauseln
                    </td>
                  </tr>
                  <tr>
                    <td className="px-4 py-2">OpenAI</td>
                    <td className="px-4 py-2">KI-Modell und Embeddings</td>
                    <td className="px-4 py-2">USA</td>
                    <td className="px-4 py-2">
                      AVV + EU-Standardvertragsklauseln
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* 7 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              7. Technische und organisatorische Maßnahmen
            </h2>
            <ul className="mt-2 list-disc pl-6 space-y-1">
              <li>
                <strong>Verschlüsselung:</strong> AES-256-GCM für OAuth-Tokens
                und sensible Daten (Envelope Encryption mit AWS KMS)
              </li>
              <li>
                <strong>Transport:</strong> TLS 1.3 für alle Verbindungen
              </li>
              <li>
                <strong>Passwort-Hashing:</strong> Argon2id
              </li>
              <li>
                <strong>Mandantentrennung:</strong> Strikte Datenisolation pro
                Nutzer (owner_id-Filter auf allen Datenbankabfragen)
              </li>
              <li>
                <strong>Zugriffskontrolle:</strong> JWT-basierte
                Authentifizierung mit Token-Rotation
              </li>
              <li>
                <strong>Audit-Logging:</strong> Alle sicherheitsrelevanten
                Aktionen werden protokolliert
              </li>
            </ul>
          </section>

          {/* 8 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              8. Ihre Rechte
            </h2>
            <p className="mt-2">
              Sie haben gegenüber uns folgende Rechte hinsichtlich Ihrer
              personenbezogenen Daten:
            </p>
            <ul className="mt-2 list-disc pl-6 space-y-1">
              <li>
                <strong>Auskunft (Art. 15 DSGVO):</strong> Sie können jederzeit
                Auskunft über Ihre gespeicherten Daten anfordern
              </li>
              <li>
                <strong>Berichtigung (Art. 16 DSGVO):</strong> Anspruch auf
                Korrektur unrichtiger Daten
              </li>
              <li>
                <strong>Löschung (Art. 17 DSGVO):</strong> Recht auf Löschung
                Ihrer Daten – eine vollständige Kontolöschung entfernt alle
                Daten kaskadierend (Dokumente, Embeddings, Knowledge Graph)
              </li>
              <li>
                <strong>
                  Einschraenkung der Verarbeitung (Art. 18 DSGVO):
                </strong>{" "}
                Recht auf eingeschränkte Verarbeitung unter bestimmten
                Voraussetzungen
              </li>
              <li>
                <strong>Datenportabilität (Art. 20 DSGVO):</strong> Export
                Ihrer Daten in einem maschinenlesbaren Format (JSON)
              </li>
              <li>
                <strong>Widerspruch (Art. 21 DSGVO):</strong> Recht auf
                Widerspruch gegen die Verarbeitung
              </li>
              <li>
                <strong>Widerruf der Einwilligung:</strong> Jede erteilte
                Einwilligung (z.B. OAuth-Anbindung) kann jederzeit widerrufen
                werden
              </li>
            </ul>
            <p className="mt-2">
              Zur Ausübung Ihrer Rechte wenden Sie sich an:{" "}
              <a
                href="mailto:kontakt@pwbs.app"
                className="text-indigo-600 hover:underline"
              >
                kontakt@pwbs.app
              </a>
            </p>
          </section>

          {/* 9 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              9. Webanalyse
            </h2>
            <p className="mt-2">
              Wir verwenden{" "}
              <a
                href="https://plausible.io"
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-600 hover:underline"
              >
                Plausible Analytics
              </a>
              , ein datenschutzfreundliches Analysetool. Plausible setzt{" "}
              <strong>keine Cookies</strong>, speichert keine personenbezogenen
              Daten und ist vollständig DSGVO-konform. Es werden nur
              aggregierte Nutzungsstatistiken erhoben.
            </p>
          </section>

          {/* 10 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              10. Beschwerderecht
            </h2>
            <p className="mt-2">
              Sie haben das Recht, sich bei einer Datenschutz-Aufsichtsbehörde
              über unsere Verarbeitung personenbezogener Daten zu beschweren.
            </p>
          </section>

          {/* 11 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              11. Änderungen
            </h2>
            <p className="mt-2">
              Diese Datenschutzerklärung kann von Zeit zu Zeit aktualisiert
              werden. Die jeweils aktuelle Fassung finden Sie auf dieser Seite.
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
              <Link
                href="/impressum"
                className="hover:text-text transition-colors"
              >
                Impressum
              </Link>
              <Link href="/datenschutz" className="font-medium text-text">
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
