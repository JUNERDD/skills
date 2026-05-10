'use client';

import { motion } from 'motion/react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { cx } from '@/lib/classnames';
import { REPO_URL } from '@/lib/skills-data';

export function SiteHeader() {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const updateHeader = () => setIsScrolled(window.scrollY > 12);

    updateHeader();
    window.addEventListener('scroll', updateHeader, { passive: true });

    return () => window.removeEventListener('scroll', updateHeader);
  }, []);

  return (
    <motion.header
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] as const }}
      className={cx(
        'pointer-events-auto fixed inset-x-0 top-0 z-30 border-b px-5 py-4 transition-[background-color,border-color,box-shadow,backdrop-filter] duration-300 sm:px-10',
        isScrolled
          ? 'border-white/10 bg-black/[0.42] shadow-[0_10px_36px_rgba(0,0,0,0.36)] backdrop-blur-xl'
          : 'border-transparent bg-transparent shadow-none backdrop-blur-none',
      )}
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
