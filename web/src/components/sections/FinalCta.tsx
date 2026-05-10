'use client';

import { motion } from 'motion/react';
import Link from 'next/link';
import { INSTALL_DOC_RAW, REPO_URL } from '@/lib/skills-data';

export function FinalCta() {
  const exampleCommand = 'npx skills@latest add JUNERDD/skills --skill debug';

  return (
    <section aria-labelledby="install-heading" className="border-t border-white/15">
      <div className="mx-auto max-w-3xl px-6 py-24 sm:px-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-64px' }}
          transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] as const }}
          className="space-y-6"
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
            className="overflow-x-auto border border-[color:color-mix(in_srgb,var(--crt-accent)_45%,transparent)] bg-black/62 p-6 text-[13px] leading-relaxed text-[color:var(--crt-accent)] shadow-[inset_0_0_0_1px_rgba(255,255,255,0.05)] md:text-[14px]"
          >
            <code>{exampleCommand}</code>
          </pre>
          <div className="flex flex-wrap gap-4">
            <Link
              href={INSTALL_DOC_RAW}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex min-h-11 items-center justify-center border border-[color:var(--crt-accent)] px-5 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-[color:var(--crt-accent)] transition hover:bg-[color:color-mix(in_srgb,var(--crt-accent)_12%,transparent)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[color:var(--crt-accent)] focus-visible:outline-offset-4"
            >
              Open install checklist
            </Link>
            <Link
              href={`${REPO_URL}/releases`}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex min-h-11 items-center justify-center px-4 py-2 text-xs uppercase tracking-[0.18em] text-[color:var(--crt-dim)] underline-offset-[6px] transition hover:text-[color:var(--crt-accent)] hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-[color:var(--crt-accent)] focus-visible:outline-offset-4"
            >
              Releases feed
            </Link>
          </div>
        </motion.div>

        <footer className="mt-20 flex flex-wrap items-center justify-between gap-3 border-t border-white/14 pt-10 text-[11px] uppercase tracking-[0.42em] text-[color:var(--crt-dim)]">
          <span className="font-sans font-semibold tracking-[0.32em]">JUNERDD</span>
          <span className="font-mono text-[10px] text-[color:var(--crt-dim)]/80">
            skills · collection
          </span>
        </footer>
      </div>
    </section>
  );
}
