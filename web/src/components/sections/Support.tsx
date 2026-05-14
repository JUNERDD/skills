'use client';

import { motion } from 'motion/react';
import { COLLECTION_VERSION } from '@/lib/content/urls';

export function Support() {
  return (
    <section
      aria-labelledby="what-ships"
      className="border-t border-white/10 bg-[color:var(--surface-0)]"
    >
      <div className="mx-auto w-full max-w-6xl px-6 py-20 sm:px-10">
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.58, ease: [0.22, 1, 0.36, 1] as const }}
          className="max-w-3xl space-y-4"
        >
          <h2
            id="what-ships"
            className="font-sans text-sm font-semibold text-white/72"
          >
            What ships
          </h2>
          <p className="max-w-prose font-mono text-[1rem] leading-8 text-[color:var(--crt-fg)] sm:text-[1.05rem]">
            Installables live under{' '}
            <span className="text-white">skills/&lt;name&gt;</span>
            , each bundled with prompts and docs. Root{' '}
            <span className="text-white">VERSION</span> tracks the curated
            collection (
            <span className="text-white">v{COLLECTION_VERSION}</span> today)
            while tooling can pin their own runtime revisions when necessary.
          </p>
        </motion.div>
      </div>
    </section>
  );
}
