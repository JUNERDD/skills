'use client';

import { motion } from 'motion/react';
import Link from 'next/link';
import { INSTALL_DOC_RAW, REPO_URL } from '@/lib/skills-data';

export function FinalCta() {
  const exampleCommand = 'npx skills@latest add JUNERDD/skills --skill debug';

  return (
    <section aria-labelledby="install-heading" className="border-t border-white/10 bg-[color:var(--surface-0)]">
      <div className="mx-auto w-full max-w-6xl px-6 py-24 sm:px-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-64px' }}
          transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] as const }}
          className="max-w-3xl space-y-6"
        >
          <h2
            id="install-heading"
            className="font-sans text-2xl font-bold text-[color:var(--crt-fg)]"
          >
            Wire it into your agents
          </h2>
          <p className="font-mono text-sm leading-relaxed text-[color:var(--crt-dim)] sm:text-[0.95rem]">
            Paste the reproducible installer when onboarding a teammate, mirror the checklist from the
            raw install markdown, or start with one skill and expand outward.
          </p>
          <pre
            tabIndex={0}
            role="figure"
            aria-label="Example install command"
            className="overflow-x-auto rounded-lg border border-white/12 bg-[color:var(--surface-1)] p-6 text-[13px] leading-relaxed text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] md:text-[14px]"
          >
            <code>{exampleCommand}</code>
          </pre>
          <div className="flex flex-wrap gap-4">
            <Link
              href={INSTALL_DOC_RAW}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex min-h-11 items-center justify-center rounded-lg border border-white/70 px-5 py-2 text-xs font-semibold text-white transition hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white focus-visible:outline-offset-4"
            >
              Open install checklist
            </Link>
            <Link
              href={`${REPO_URL}/releases`}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex min-h-11 items-center justify-center rounded-lg px-4 py-2 text-xs text-[color:var(--crt-dim)] underline-offset-[6px] transition hover:bg-white/6 hover:text-white hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-white focus-visible:outline-offset-4"
            >
              Releases feed
            </Link>
          </div>
        </motion.div>

        <footer className="mt-20 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-10 text-xs text-[color:var(--crt-dim)]">
          <span className="font-sans font-semibold">JUNERDD</span>
          <span className="font-mono text-[10px] text-[color:var(--crt-dim)]/80">
            skills · collection
          </span>
        </footer>
      </div>
    </section>
  );
}
