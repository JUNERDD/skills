'use client';

import { motion } from 'motion/react';
import Link from 'next/link';
import { AsciiBackdrop } from '@/components/ascii/AsciiBackdrop';
import { CopyAgentInstallButton } from '@/components/install/CopyAgentInstallButton';
import { REPO_URL } from '@/lib/skills-data';
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
      className="relative isolate min-h-[92svh] w-full overflow-hidden bg-[color:var(--surface-0)] sm:min-h-svh"
    >
      <AsciiBackdrop />
      <div
        className="pointer-events-none absolute inset-0 z-[1] bg-[linear-gradient(90deg,rgba(5,5,5,0.92)_0%,rgba(5,5,5,0.62)_34%,rgba(5,5,5,0.12)_70%,rgba(5,5,5,0.42)_100%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 z-[1] h-40 bg-[linear-gradient(to_bottom,transparent,var(--surface-0))]"
        aria-hidden
      />
      <SiteHeader />
      <div className="relative z-10 mx-auto flex min-h-[92svh] w-full max-w-6xl flex-col justify-end gap-8 px-5 pb-10 pt-24 sm:min-h-svh sm:items-start sm:px-10 sm:pb-24">
        <motion.div
          variants={group}
          initial="hidden"
          animate="show"
          className="flex w-full max-w-2xl flex-col gap-5"
        >
          <motion.p
            variants={item}
            className="font-sans text-xs font-semibold text-white/70"
          >
            Agent skill collection
          </motion.p>
          <motion.h1
            id="brand-heading"
            variants={item}
            className="max-w-full font-sans text-[2.65rem] font-extrabold leading-none text-[color:var(--crt-fg)] drop-shadow-[0_0_34px_var(--crt-glow)] sm:text-6xl lg:text-7xl"
          >
            <span className="block">JUNERDD</span>
            <span className="block">Skills</span>
          </motion.h1>
          <motion.p
            variants={item}
            className="max-w-xl text-base leading-relaxed text-[color:var(--crt-dim)] sm:text-lg"
          >
            Reusable AI agent skills packaged as installable workflows.
          </motion.p>
          <motion.div
            variants={item}
            className="flex flex-col gap-3 sm:flex-row sm:items-center"
          >
            <CopyAgentInstallButton
              idleLabel="Copy install prompt"
              copiedLabel="Copied prompt"
              className="w-full sm:w-auto"
            />
            <Link
              href={REPO_URL}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex min-h-11 w-full items-center justify-center rounded-lg border border-white/16 px-5 py-2 text-sm text-[color:var(--crt-fg)] transition hover:border-white/42 hover:bg-white/8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white sm:w-auto"
            >
              View repository
            </Link>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
