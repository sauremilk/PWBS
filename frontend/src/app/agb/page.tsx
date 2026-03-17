import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Allgemeine Geschaeftsbedingungen – PWBS",
  description: "Allgemeine Geschaeftsbedingungen fuer die Nutzung von PWBS.",
};

export default function AGBPage() {
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
            Zurueck zur Startseite
          </Link>
        </div>
      </nav>

      <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6 sm:py-16">
        <h1 className="text-3xl font-bold text-text sm:text-4xl">
          Allgemeine Geschaeftsbedingungen
        </h1>
        <p className="mt-2 text-sm text-text-tertiary">Stand: Juli 2025</p>

        <div className="mt-8 space-y-10 text-text-secondary leading-relaxed">
          {/* 1 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              1. Geltungsbereich
            </h2>
            <p className="mt-2">
              Diese Allgemeinen Geschaeftsbedingungen (AGB) gelten fuer die
              Nutzung des Dienstes &quot;PWBS – Persoenliches
              Wissens-Betriebssystem&quot;, betrieben von Mick Gajewski
              (nachfolgend &quot;Anbieter&quot;).
            </p>
            <p className="mt-2">
              Mit der Registrierung oder Nutzung des Dienstes erkennen Sie diese
              AGB an.
            </p>
          </section>

          {/* 2 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              2. Leistungsbeschreibung
            </h2>
            <p className="mt-2">
              PWBS ist eine KI-gestuetzte Plattform, die persoenliche
              Wissensdaten aus verschiedenen Quellen (Kalender, Notizen,
              Meeting-Transkripte) zusammenfuehrt, semantisch analysiert und als
              kontextbezogene Briefings aufbereitet.
            </p>
            <p className="mt-2">
              Der Dienst befindet sich derzeit in der{" "}
              <strong>Beta-Phase</strong>. Funktionsumfang und Verfuegbarkeit
              koennen sich aendern.
            </p>
          </section>

          {/* 3 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              3. Registrierung und Konto
            </h2>
            <ul className="mt-2 list-disc pl-6 space-y-1">
              <li>
                Sie muessen wahrheitsgemäße Angaben bei der Registrierung machen
              </li>
              <li>
                Sie sind fuer die Sicherheit Ihrer Zugangsdaten verantwortlich
              </li>
              <li>
                Ein Konto ist persoenlich und darf nicht an Dritte weitergegeben
                werden
              </li>
              <li>
                Der Anbieter kann Konten bei Verstoss gegen diese AGB sperren
              </li>
            </ul>
          </section>

          {/* 4 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              4. Beta-Bedingungen
            </h2>
            <p className="mt-2">Waehrend der Beta-Phase gilt zusaetzlich:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1">
              <li>
                Der Dienst wird &quot;wie besehen&quot; (as-is) bereitgestellt
              </li>
              <li>
                Es besteht kein Anspruch auf eine bestimmte Verfuegbarkeit oder
                Funktionalitaet
              </li>
              <li>
                Der Anbieter kann den Dienst jederzeit aendern, einschraenken
                oder einstellen
              </li>
              <li>
                Ihre Daten werden auch bei Einstellung des Dienstes nicht ohne
                Vorankuendigung geloescht – Sie erhalten mindestens 30 Tage Zeit
                fuer einen Export
              </li>
            </ul>
          </section>

          {/* 5 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              5. Nutzungsrechte und -pflichten
            </h2>
            <p className="mt-2">Der Nutzer verpflichtet sich:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1">
              <li>Den Dienst nicht fuer rechtswidrige Zwecke zu verwenden</li>
              <li>
                Keine automatisierten Massenabfragen (Scraping, Bots)
                durchzufuehren
              </li>
              <li>
                Keine Sicherheitsmechanismen zu umgehen oder zu manipulieren
              </li>
              <li>
                Nur eigene Daten oder Daten, fuer die eine
                Verarbeitungsberechtigung besteht, zu uebermitteln
              </li>
            </ul>
          </section>

          {/* 6 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              6. Geistiges Eigentum
            </h2>
            <p className="mt-2">
              Alle Rechte an der Software, dem Design und den Inhalten von PWBS
              liegen beim Anbieter. Die vom Nutzer eingebrachten Daten
              verbleiben im Eigentum des Nutzers.
            </p>
            <p className="mt-2">
              Der Anbieter erhaelt kein Nutzungsrecht an den Inhalten des
              Nutzers ueber die zur Diensterbringung notwendige Verarbeitung
              hinaus.
            </p>
          </section>

          {/* 7 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              7. Haftungsbeschraenkung
            </h2>
            <p className="mt-2">
              Der Anbieter haftet unbeschraenkt fuer Vorsatz und grobe
              Fahrlaessigkeit. Bei leichter Fahrlaessigkeit haftet der Anbieter
              nur bei Verletzung wesentlicher Vertragspflichten und nur bis zur
              Hoehe des vorhersehbaren, vertragstypischen Schadens.
            </p>
            <p className="mt-2">Der Anbieter haftet nicht fuer:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1">
              <li>
                Inhaltliche Richtigkeit der KI-generierten Briefings und
                Zusammenfassungen
              </li>
              <li>
                Datenverlust durch hoehe Gewalt, Serverausfaelle Dritter oder
                Handlungen des Nutzers
              </li>
              <li>
                Entscheidungen, die auf Basis der bereitgestellten Informationen
                getroffen werden
              </li>
            </ul>
          </section>

          {/* 8 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              8. Datenschutz
            </h2>
            <p className="mt-2">
              Die Verarbeitung personenbezogener Daten erfolgt gemaess unserer{" "}
              <Link
                href="/datenschutz"
                className="text-indigo-600 hover:underline"
              >
                Datenschutzerklaerung
              </Link>
              , die Bestandteil dieser AGB ist.
            </p>
          </section>

          {/* 9 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              9. Kuendigung
            </h2>
            <ul className="mt-2 list-disc pl-6 space-y-1">
              <li>
                Sie koennen Ihr Konto jederzeit in den Einstellungen loeschen
              </li>
              <li>
                Bei Kontoloeschung werden alle Ihre Daten unwiderruflich
                entfernt (Dokumente, Embeddings, Knowledge Graph, Audit-Logs)
              </li>
              <li>
                Der Anbieter kann den Zugang bei schwerwiegenden Verstoessen
                gegen diese AGB mit sofortiger Wirkung kuendigen
              </li>
            </ul>
          </section>

          {/* 10 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              10. Aenderungen der AGB
            </h2>
            <p className="mt-2">
              Der Anbieter behaelt sich vor, diese AGB zu aendern. Aenderungen
              werden per E-Mail oder in-App-Benachrichtigung mitgeteilt.
              Widerspricht der Nutzer nicht innerhalb von 30 Tagen, gelten die
              geaenderten AGB als angenommen.
            </p>
          </section>

          {/* 11 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              11. Anwendbares Recht und Gerichtsstand
            </h2>
            <p className="mt-2">
              Es gilt das Recht der Bundesrepublik Deutschland unter Ausschluss
              des UN-Kaufrechts. Gerichtsstand ist, soweit gesetzlich zulaessig,
              der Wohnsitz des Anbieters.
            </p>
          </section>

          {/* 12 */}
          <section>
            <h2 className="text-xl font-semibold text-text">
              12. Salvatorische Klausel
            </h2>
            <p className="mt-2">
              Sollte eine Bestimmung dieser AGB unwirksam sein oder werden, so
              bleibt die Wirksamkeit der uebrigen Bestimmungen unberuehrt. An
              die Stelle der unwirksamen Bestimmung tritt eine wirksame
              Regelung, die dem wirtschaftlichen Zweck am naechsten kommt.
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
              <Link
                href="/datenschutz"
                className="hover:text-text transition-colors"
              >
                Datenschutz
              </Link>
              <Link href="/agb" className="font-medium text-text">
                AGB
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
