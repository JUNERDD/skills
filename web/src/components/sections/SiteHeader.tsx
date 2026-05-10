'use client';

import { motion } from 'motion/react';
import Link from 'next/link';
import { REPO_URL } from '@/lib/skills-data';

export function SiteHeader() {
  return (
    <motion.header
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] as const }}
      className="pointer-events-auto fixed inset-x-0 top-0 z-30 flex items-center justify-between px-5 py-4 sm:px-10"
    >
      <span className="font-sans text-xs font-extrabold uppercase tracking-[0.35em] text-[color:var(--crt-accent)] drop-shadow-[0_0_12px_var(--crt-glow)]">
        JUNERDD
      </span>
      <Link
        href={REPO_URL}
        target="_blank"
        rel="noreferrer noopener"
        className="font-mono text-[11px] uppercase tracking-[0.28em] text-[color:var(--crt-dim)] transition-colors hover:text-[color:var(--crt-accent)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[color:var(--crt-accent)] focus-visible:outline-offset-4"
      >
        GitHub
      </Link>
    </motion.header>
  );
}
