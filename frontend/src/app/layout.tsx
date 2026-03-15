import "./globals.css";
import "@/styles/a11y.css";

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Script from "next/script";
import { Providers } from "@/lib/providers";

const inter = Inter({ subsets: ["latin"] });

const plausibleDomain = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN;
const plausibleSrc =
  process.env.NEXT_PUBLIC_PLAUSIBLE_SRC ?? "https://plausible.io/js/script.js";

export const metadata: Metadata = {
  title: "PWBS – Persönliches Wissens-Betriebssystem",
  description:
    "Kognitive Infrastruktur für Wissensarbeiter: Briefings, semantische Suche und Knowledge Graph.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="de">
      <body className={inter.className}>
        {plausibleDomain && (
          <Script
            defer
            data-domain={plausibleDomain}
            src={plausibleSrc}
            strategy="afterInteractive"
          />
        )}
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
