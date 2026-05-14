import { Hero } from '@/components/sections/Hero';
import { Support } from '@/components/sections/Support';
import { SkillsList } from '@/components/sections/SkillsList';
import { FinalCta } from '@/components/sections/FinalCta';
import { SiteHeader } from '@/components/sections/SiteHeader';
import { listSkillListItems } from '@/lib/content/provider';

export default async function Home() {
  const skills = await listSkillListItems();

  return (
    <div className="relative isolate min-h-screen overflow-x-hidden">
      <SiteHeader />
      <div className="relative z-10">
        <Hero />
        <Support />
        <SkillsList skills={skills} />
        <FinalCta />
      </div>
    </div>
  );
}
