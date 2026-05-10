'use client';

import { motion } from 'motion/react';
import Link from 'next/link';
import { SKILLS } from '@/lib/skills-data';

export function SkillsList() {
  return (
    <section aria-labelledby="skills-heading" className="border-t border-white/10 bg-[color:var(--surface-0)]">
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
            Every local installable gets a field manual. Open a guide for the workflow,
            boundaries, outputs, and source entry points.
          </p>
        </motion.div>

        <ul className="mt-10 grid gap-3 sm:mt-14 md:grid-cols-2">
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
              className="rounded-lg border border-white/10 bg-[color:var(--surface-1)]"
            >
              <Link
                href={`/skills/${skill.slug}`}
                className="group flex h-full min-h-40 flex-col rounded-lg p-5 transition-colors hover:bg-white/6 active:bg-white/[0.08] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-white sm:min-h-52 md:p-10"
              >
                <p className="font-sans text-xs font-bold uppercase tracking-[0.16em] text-white/38">
                  {skill.category}
                </p>
                <h3 className="mt-3 font-mono text-sm font-semibold text-white">
                  {skill.title}
                </h3>
                <p className="mt-2 font-mono text-sm leading-relaxed text-[color:var(--crt-dim)]">
                  {skill.blurb}
                </p>
                <span className="mt-auto pt-5 font-mono text-xs text-white/38 transition-colors group-hover:text-white/70">
                  Open guide
                </span>
              </Link>
            </motion.li>
          ))}
        </ul>
      </div>
    </section>
  );
}
