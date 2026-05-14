import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { SkillDetailPage } from '@/components/skill-detail/SkillDetailPage';
import {
  getSkillBySlug,
  getSkillNeighbors,
  listSkillSlugs,
} from '@/lib/content/provider';
import { getSiteOrigin } from '@/lib/site-url';

type SkillPageProps = {
  params: Promise<{ slug: string }>;
};

export const dynamicParams = false;

export async function generateStaticParams() {
  const slugs = await listSkillSlugs();

  return slugs.map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: SkillPageProps): Promise<Metadata> {
  const { slug } = await params;
  const skill = await getSkillBySlug(slug);

  if (!skill) {
    return {
      title: 'Skill not found',
    };
  }

  const url = `${getSiteOrigin()}/skills/${skill.slug}`;

  return {
    title: `${skill.title} guide`,
    description: skill.lead,
    alternates: {
      canonical: `/skills/${skill.slug}`,
    },
    openGraph: {
      title: `${skill.title} guide`,
      description: skill.lead,
      url,
      siteName: 'JUNERDD Skills',
      type: 'article',
    },
    twitter: {
      card: 'summary_large_image',
      title: `${skill.title} guide`,
      description: skill.lead,
    },
  };
}

export default async function SkillPage({ params }: SkillPageProps) {
  const { slug } = await params;
  const skill = await getSkillBySlug(slug);

  if (!skill) {
    notFound();
  }

  const { next, previous } = await getSkillNeighbors(skill.slug);

  return <SkillDetailPage next={next} previous={previous} skill={skill} />;
}
