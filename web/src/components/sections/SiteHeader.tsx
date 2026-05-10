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
      className="pointer-events-auto fixed inset-x-0 top-0 z-30 px-5 py-4 sm:px-10"
    >
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between">
        <Link
          href="/"
          className="font-sans text-xs font-extrabold text-white drop-shadow-[0_0_12px_var(--crt-glow)] transition-opacity hover:opacity-72 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white focus-visible:outline-offset-4"
        >
          JUNERDD
        </Link>
        <Link
          href={REPO_URL}
          target="_blank"
          rel="noreferrer noopener"
          className="font-mono text-xs text-white/58 transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-white focus-visible:outline-offset-4"
        >
          GitHub
        </Link>
      </div>
    </motion.header>
  );
}
