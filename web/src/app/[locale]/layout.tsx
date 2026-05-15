import type { Metadata } from "next";
import { NextIntlClientProvider, hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { IBM_Plex_Mono, Syne } from "next/font/google";
import { notFound } from "next/navigation";
import { routing } from "@/i18n/routing";
import { AppToaster } from "@/components/ui/AppToaster";
import { REPO_URL } from "@/lib/content/urls";
import {
  getLanguageAlternates,
  localizePath,
  openGraphLocales,
} from "@/lib/i18n/config";
import { getDictionary } from "@/lib/i18n/dictionaries";
import { getMetadataBase, getSiteOrigin } from "@/lib/site-url";
import "../globals.css";

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

type LocaleParams = {
  params: Promise<{ locale: string }>;
};

type LocaleLayoutProps = Readonly<
  LocaleParams & {
    children: React.ReactNode;
  }
>;

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({
  params,
}: LocaleParams): Promise<Metadata> {
  const { locale } = await params;

  if (!hasLocale(routing.locales, locale)) {
    return {};
  }

  const dictionary = await getDictionary(locale);
  const canonical = localizePath("/", locale);
  const origin = getSiteOrigin();
  const image = `${origin}/-/opengraph-image`;

  return {
    metadataBase: getMetadataBase(),
    title: {
      default: dictionary.metadata.titleDefault,
      template: dictionary.metadata.titleTemplate,
    },
    description: dictionary.metadata.description,
    keywords: dictionary.metadata.keywords,
    alternates: {
      canonical,
      languages: getLanguageAlternates("/"),
    },
    openGraph: {
      title: "JUNERDD Skills",
      description: dictionary.metadata.ogDescription,
      url: `${origin}${canonical}`,
      siteName: "JUNERDD Skills",
      type: "website",
      locale: openGraphLocales[locale],
      alternateLocale: routing.locales
        .filter((candidate) => candidate !== locale)
        .map((candidate) => openGraphLocales[candidate]),
      images: [
        {
          alt: dictionary.metadata.srOnlyBrand,
          height: 630,
          url: image,
          width: 1200,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: "JUNERDD Skills",
      description: dictionary.metadata.ogDescription,
      images: [image],
    },
    robots: {
      index: true,
      follow: true,
    },
  };
};

export default async function LocaleLayout({
  children,
  params,
}: LocaleLayoutProps) {
  const { locale } = await params;

  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  setRequestLocale(locale);

  const dictionary = await getDictionary(locale);
  const siteJsonLd = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    description: dictionary.metadata.siteJsonLdDescription,
    inLanguage: locale,
    name: "JUNERDD Skills",
    sameAs: [REPO_URL],
    url: `${getSiteOrigin()}${localizePath("/", locale)}`,
  };

  return (
    <html
      lang={locale}
      className={`${syne.variable} ${ibmMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-[var(--surface-0)] text-[color:var(--ink)] font-mono">
        <NextIntlClientProvider>
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(siteJsonLd) }}
          />
          <span className="sr-only">{dictionary.metadata.srOnlyBrand}</span>
          <div className="app-root">{children}</div>
          <AppToaster closeLabel={dictionary.toaster.close} />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
