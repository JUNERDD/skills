import type { Metadata } from 'next';
import { hasLocale } from 'next-intl';
import { setRequestLocale } from 'next-intl/server';
import { notFound } from 'next/navigation';
import { routing } from '@/i18n/routing';
import { SkillDetailPage } from '@/components/skill-detail/SkillDetailPage';
import {
  getSkillBySlug,
  getSkillNeighbors,
  listSkillSlugs,
} from '@/lib/content/provider';
import {
  getLanguageAlternates,
  localizePath,
  openGraphLocales,
} from '@/lib/i18n/config';
import { getDictionary } from '@/lib/i18n/dictionaries';
import { getSiteOrigin } from '@/lib/site-url';

type SkillPageProps = {
  params: Promise<{ locale: string; slug: string }>;
};

export const dynamicParams = false;

export async function generateStaticParams() {
  const slugs = await listSkillSlugs();

  return routing.locales.flatMap((locale) =>
    slugs.map((slug) => ({ locale, slug })),
  );
}

export async function generateMetadata({
  params,
}: SkillPageProps): Promise<Metadata> {
  const { locale, slug } = await params;

  if (!hasLocale(routing.locales, locale)) {
    return {};
  }

  const dictionary = await getDictionary(locale);
  const skill = await getSkillBySlug(slug, locale);

  if (!skill) {
    return {
      title: dictionary.skillDetail.metadataNotFoundTitle,
    };
  }

  const pathname = `/skills/${skill.slug}`;
  const canonical = localizePath(pathname, locale);
  const image = `${getSiteOrigin()}/-/opengraph-image`;
  const title = `${skill.title} ${dictionary.skillDetail.metadataTitleSuffix}`;
  const url = `${getSiteOrigin()}${canonical}`;

  return {
    title,
    description: skill.lead,
    alternates: {
      canonical,
      languages: getLanguageAlternates(pathname),
    },
    openGraph: {
      title,
      description: skill.lead,
      url,
      siteName: 'JUNERDD Skills',
      type: 'article',
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
      card: 'summary_large_image',
      title,
      description: skill.lead,
      images: [image],
    },
  };
}

export default async function SkillPage({ params }: SkillPageProps) {
  const { locale, slug } = await params;

  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  setRequestLocale(locale);

  const dictionary = await getDictionary(locale);
  const skill = await getSkillBySlug(slug, locale);

  if (!skill) {
    notFound();
  }

  const { next, previous } = await getSkillNeighbors(skill.slug, locale);

  return (
    <SkillDetailPage
      labels={dictionary.skillDetail}
      locale={locale}
      navLabels={dictionary.nav}
      next={next}
      previous={previous}
      skill={skill}
    />
  );
}
