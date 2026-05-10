'use client';

import { motion } from 'motion/react';
import Link from 'next/link';
import { INSTALL_DOC_RAW, REPO_URL } from '@/lib/skills-data';
import { SiteHeader } from './SiteHeader';

const group = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.085,
      delayChildren: 0.15,
    },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.52, ease: [0.22, 1, 0.36, 1] as const },
  },
};

export function Hero() {
  return (
    <section
      aria-labelledby="brand-heading"
      className="relative min-h-svh w-full"
    >
      <SiteHeader />
      <div className="mx-auto flex min-h-svh max-w-2xl flex-col justify-end gap-8 px-6 pb-14 pt-28 sm:items-start sm:px-10 sm:pb-24">
        <motion.div
          variants={group}
          initial="hidden"
          animate="show"
          className="flex w-full flex-col gap-5"
        >
          <motion.p
            variants={item}
            className="font-sans text-[11px] uppercase tracking-[0.35em] text-[color:var(--crt-dim)]"
          >
            Collection
          </motion.p>
          <motion.h1
            id="brand-heading"
            variants={item}
            className="font-sans text-[clamp(2.4rem,6vw,3.75rem)] font-extrabold leading-[1.02] tracking-tight text-[color:var(--crt-fg)] drop-shadow-[0_0_40px_var(--crt-glow)]"
          >
            JUNERDD Skills
          </motion.h1>
          <motion.p
            variants={item}
            className="max-w-xl text-base leading-relaxed text-[color:var(--crt-dim)] sm:text-lg"
          >
            Reusable AI agent skills published from a single repository.
          </motion.p>
          <motion.div
            variants={item}
            className="flex flex-col gap-3 sm:flex-row sm:items-center"
          >
            <Link
              href={INSTALL_DOC_RAW}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex min-h-11 items-center justify-center border border-[color:var(--crt-accent)] bg-[color:color-mix(in_srgb,var(--crt-accent)_16%,transparent)] px-6 py-3 text-sm font-semibold text-[color:var(--crt-accent)] transition hover:bg-[color:color-mix(in_srgb,var(--crt-accent)_28%,transparent)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--crt-accent)]"
            >
              Installation guide
            </Link>
            <Link
              href={REPO_URL}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex min-h-11 items-center px-4 py-2 text-sm text-[color:var(--crt-accent)] underline-offset-[6px] transition hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--crt-accent)] sm:justify-center"
            >
              View repository
            </Link>
          </motion.div>
        </motion.div>
      </div>
      <motion.div
        className="pointer-events-none absolute bottom-8 left-1/2 hidden -translate-x-1/2 sm:block"
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.5 }}
        transition={{ delay: 1.05, duration: 0.5 }}
        aria-hidden
      >
        <span className="font-mono text-[10px] tracking-[0.52em] text-[color:var(--crt-dim)]">
          SCROLL
        </span>
      </motion.div>
    </section>
  );
}
