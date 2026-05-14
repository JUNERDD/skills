'use client';

import { motion } from 'motion/react';
import { CopyAgentInstallButton } from '@/components/install/CopyAgentInstallButton';
import { AGENT_INSTALL_INSTRUCTION } from '@/lib/content/urls';

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
            className="overflow-hidden rounded-lg border border-white/14 bg-[linear-gradient(180deg,rgba(255,255,255,0.055),rgba(255,255,255,0.018))] shadow-[0_24px_80px_rgba(0,0,0,0.34),inset_0_1px_0_rgba(255,255,255,0.08)]"
          >
            <div className="flex items-center justify-between gap-4 border-b border-white/10 bg-black/24 px-4 py-3 sm:px-5">
              <span className="font-sans text-[11px] font-bold uppercase text-white/46">
                Prompt
              </span>
              <CopyAgentInstallButton
                idleLabel="Copy"
                copiedLabel="Copied"
                className="shrink-0"
                variant="compact"
              />
            </div>
            <pre tabIndex={0} className="px-4 py-5 text-[13px] leading-7 text-white sm:px-5 md:text-[14px]">
              <code className="block whitespace-pre-wrap break-words">
                {AGENT_INSTALL_INSTRUCTION}
              </code>
            </pre>
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
