'use client';

import { motion } from 'motion/react';
import { COLLECTION_VERSION } from '@/lib/skills-data';

export function Support() {
  return (
    <section
      aria-labelledby="what-ships"
      className="border-t border-white/15 bg-[#030504]/82 backdrop-blur-md"
    >
      <div className="mx-auto max-w-3xl px-6 py-20 sm:px-10">
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.58, ease: [0.22, 1, 0.36, 1] as const }}
          className="space-y-4"
        >
          <h2
            id="what-ships"
            className="font-sans text-xs font-semibold uppercase tracking-[0.32em] text-[color:var(--crt-dim)]"
          >
            What ships
          </h2>
          <p className="max-w-prose font-mono text-[1rem] leading-8 text-[color:var(--crt-fg)] sm:text-[1.05rem]">
            Installables live under{' '}
            <span className="text-[color:var(--crt-accent)]">skills/&lt;name&gt;</span>
            , each bundled with prompts and docs. Root{' '}
            <span className="text-[color:var(--crt-accent)]">VERSION</span> tracks the curated
            collection (
            <span className="text-[color:var(--crt-accent)]">v{COLLECTION_VERSION}</span> today)
            while tooling can pin their own runtime revisions when necessary.
          </p>
        </motion.div>
      </div>
    </section>
  );
}
