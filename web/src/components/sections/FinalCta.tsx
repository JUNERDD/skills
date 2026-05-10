'use client';

import { motion } from 'motion/react';
import { CopyAgentInstallButton } from '@/components/install/CopyAgentInstallButton';
import { AGENT_INSTALL_INSTRUCTION } from '@/lib/skills-data';

export function FinalCta() {
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
            If you want an agent to install this repository for you without copying files, tell it:
          </p>
          <div
            role="figure"
            aria-label="Agent installation instruction"
            className="relative border border-white/10 bg-[color:var(--surface-1)] shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]"
          >
            <pre
              tabIndex={0}
              className="overflow-x-auto px-5 py-5 pr-20 text-[13px] leading-relaxed text-white md:text-[14px]"
            >
              <code>{AGENT_INSTALL_INSTRUCTION}</code>
            </pre>
            <CopyAgentInstallButton
              idleLabel="Copy"
              copiedLabel="Copied"
              className="absolute right-3 top-3 inline-flex min-h-8 items-center justify-center border border-white/16 px-3 font-mono text-[11px] text-white/58 transition hover:border-white/38 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-white focus-visible:outline-offset-2"
            />
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
