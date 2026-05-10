import type { Metadata } from "next";
import { IBM_Plex_Mono, Syne } from "next/font/google";
import { REPO_URL } from "@/lib/skills-data";
import { getMetadataBase, getSiteOrigin } from "@/lib/site-url";
import "./globals.css";

const syne = Syne({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["500", "700", "800"],
});

const ibmMono = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  metadataBase: getMetadataBase(),
  title: {
    default: "JUNERDD Skills · Reusable agent skills",
    template: "%s · JUNERDD Skills",
  },
  description:
    "Reusable AI agent skills published from a single repository — install independently or as a curated collection.",
  keywords: [
    "AI agents",
    "agent skills",
    "Cursor",
    "Claude",
    "reusable prompts",
    "developer tools",
    "JUNERDD",
  ],
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "JUNERDD Skills",
    description:
      "Reusable AI agent skills published from a single repository.",
    url: `${getSiteOrigin()}/`,
    siteName: "JUNERDD Skills",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "JUNERDD Skills",
    description:
      "Reusable AI agent skills published from a single repository.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

const siteJsonLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "JUNERDD Skills",
  url: getSiteOrigin(),
  description:
    "Reusable AI agent skills published from a single repository — install independently or as a curated collection.",
  sameAs: [REPO_URL],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${syne.variable} ${ibmMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-[var(--crt-bg)] text-[color:var(--crt-fg)] font-mono">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(siteJsonLd) }}
        />
        <span className="sr-only">JUNERDD Skills — reusable AI agent skills</span>
        <div className="crt-overlay" aria-hidden />
        <div className="crt-noise" aria-hidden />
        <div className="crt-vignette" aria-hidden />
        {children}
      </body>
    </html>
  );
}
