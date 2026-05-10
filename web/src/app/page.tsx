import { Hero } from '@/components/sections/Hero';
import { Support } from '@/components/sections/Support';
import { SkillsList } from '@/components/sections/SkillsList';
import { FinalCta } from '@/components/sections/FinalCta';

export default function Home() {
  return (
    <div className="relative isolate min-h-screen overflow-x-hidden">
      <div className="relative z-10">
        <Hero />
        <Support />
        <SkillsList />
        <FinalCta />
      </div>
    </div>
  );
}
