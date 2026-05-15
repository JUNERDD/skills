import { hasLocale } from 'next-intl';
import { setRequestLocale } from 'next-intl/server';
import { notFound } from 'next/navigation';
import { routing } from '@/i18n/routing';
import { Hero } from '@/components/sections/Hero';
import { Support } from '@/components/sections/Support';
import { SkillsList } from '@/components/sections/SkillsList';
import { FinalCta } from '@/components/sections/FinalCta';
import { SiteHeader } from '@/components/sections/SiteHeader';
import { listSkillListItems } from '@/lib/content/provider';
import { getDictionary } from '@/lib/i18n/dictionaries';

type HomeProps = {
  params: Promise<{ locale: string }>;
};

export default async function Home({ params }: HomeProps) {
  const { locale } = await params;

  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  setRequestLocale(locale);

  const dictionary = await getDictionary(locale);
  const skills = await listSkillListItems(locale);

  return (
    <div className="relative isolate min-h-screen overflow-x-hidden">
      <SiteHeader labels={dictionary.nav} locale={locale} />
      <div className="relative z-10">
        <Hero copyLabels={dictionary.copyButton} labels={dictionary.hero} />
        <Support labels={dictionary.support} />
        <SkillsList labels={dictionary.skillsList} skills={skills} />
        <FinalCta
          copyLabels={dictionary.copyButton}
          labels={dictionary.finalCta}
        />
      </div>
    </div>
  );
}
