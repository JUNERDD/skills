'use client';

import { motion } from 'motion/react';
import Link from 'next/link';
import { REPO_URL, SKILLS } from '@/lib/skills-data';

export function SkillsList() {
  return (
    <section aria-labelledby="skills-heading" className="border-t border-white/15">
      <div className="mx-auto max-w-6xl px-6 py-20 sm:px-10">
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-56px' }}
          transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] as const }}
          className="max-w-xl space-y-3"
        >
          <h2
            id="skills-heading"
            className="font-sans text-2xl font-bold text-[color:var(--crt-fg)] md:text-[1.85rem]"
          >
            Skills at a glance
          </h2>
          <p className="font-mono text-sm leading-relaxed text-[color:var(--crt-dim)] md:text-[0.95rem]">
            Eight installables surfaced from the catalogue — skim the headings, drill into whichever
            workflow you need inside the repo.
          </p>
        </motion.div>

        <ul className="mt-14 divide-y divide-white/14 border-y border-white/14 md:grid md:grid-cols-2 md:gap-px md:divide-y-0 md:border md:border-white/14 md:bg-white/10 [&>li]:md:border-0">
          {SKILLS.map((skill, index) => (
            <motion.li
              key={skill.slug}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-24px' }}
              transition={{
                duration: 0.45,
                delay: Math.min(index * 0.02, 0.18),
              }}
              className="bg-[color:var(--crt-bg)] md:bg-[#070b09]/95"
            >
              <Link
                href={`${REPO_URL}/tree/main/skills/${skill.slug}`}
                target="_blank"
                rel="noreferrer noopener"
                className="flex h-full flex-col gap-2 px-0 py-6 transition-colors md:p-10 md:hover:bg-white/[0.03] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[color:var(--crt-accent)]"
              >
                <h3 className="font-mono text-sm uppercase tracking-[0.18em] text-[color:var(--crt-accent)]">
                  {skill.title}
                </h3>
                <p className="font-mono text-sm leading-relaxed text-[color:var(--crt-dim)]">
                  {skill.blurb}
                </p>
              </Link>
            </motion.li>
          ))}
        </ul>
      </div>
    </section>
  );
}
