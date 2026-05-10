'use client';

import { motion } from 'motion/react';
import Link from 'next/link';
import { SiteHeader } from '@/components/sections/SiteHeader';
import { REPO_URL, getSkillInstallCommand } from '@/lib/skills-data';
import type { SkillDetail } from '@/lib/skills-data';

type SkillDetailPageProps = {
  next?: Pick<SkillDetail, 'slug' | 'title' | 'blurb'>;
  previous?: Pick<SkillDetail, 'slug' | 'title' | 'blurb'>;
  skill: SkillDetail;
};

const ease = [0.22, 1, 0.36, 1] as const;

const group = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.07,
      delayChildren: 0.12,
    },
  },
};

const item = {
  hidden: { opacity: 0, y: 18 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.52, ease },
  },
};

function entryHref(path: string) {
  const mode = path.endsWith('/') ? 'tree' : 'blob';
  return `${REPO_URL}/${mode}/main/${path.replace(/\/$/, '')}`;
}

function DetailSection({
  children,
  eyebrow,
  id,
  title,
}: {
  children: React.ReactNode;
  eyebrow: string;
  id: string;
  title: string;
}) {
  return (
    <motion.section
      id={id}
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-64px' }}
      transition={{ duration: 0.48, ease }}
      className="scroll-mt-28 border-t border-white/12 py-12 md:py-16"
    >
      <p className="font-sans text-xs font-bold uppercase tracking-[0.18em] text-white/46">
        {eyebrow}
      </p>
      <h2 className="mt-3 font-sans text-2xl font-extrabold leading-tight text-white md:text-[2rem]">
        {title}
      </h2>
      <div className="mt-7">{children}</div>
    </motion.section>
  );
}

function TextList({ items }: { items: string[] }) {
  return (
    <ul className="divide-y divide-white/10 border-y border-white/10">
      {items.map((text) => (
        <li
          key={text}
          className="grid gap-3 py-5 font-mono text-sm leading-relaxed text-[color:var(--crt-dim)] md:grid-cols-[9rem_1fr] md:text-[0.95rem]"
        >
          <span className="font-sans text-xs font-bold uppercase tracking-[0.16em] text-white/40">
            Signal
          </span>
          <span>{text}</span>
        </li>
      ))}
    </ul>
  );
}

function WorkflowList({ items }: { items: string[] }) {
  return (
    <ol className="divide-y divide-white/10 border-y border-white/10">
      {items.map((text, index) => (
        <li
          key={text}
          className="grid gap-3 py-5 md:grid-cols-[4rem_1fr]"
        >
          <span className="font-sans text-2xl font-extrabold text-white/28">
            {String(index + 1).padStart(2, '0')}
          </span>
          <p className="font-mono text-sm leading-relaxed text-[color:var(--crt-dim)] md:text-[0.95rem]">
            {text}
          </p>
        </li>
      ))}
    </ol>
  );
}

function NeighborLink({
  label,
  skill,
}: {
  label: string;
  skill?: Pick<SkillDetail, 'slug' | 'title' | 'blurb'>;
}) {
  if (!skill) return null;

  return (
    <Link
      href={`/skills/${skill.slug}`}
      className="group block border-t border-white/12 py-6 transition-colors hover:border-white/38 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white"
    >
      <span className="font-sans text-xs font-bold uppercase tracking-[0.18em] text-white/40">
        {label}
      </span>
      <span className="mt-3 block font-mono text-base font-semibold text-white transition-colors group-hover:text-white/82">
        {skill.title}
      </span>
      <span className="mt-2 block font-mono text-sm leading-relaxed text-[color:var(--crt-dim)]">
        {skill.blurb}
      </span>
    </Link>
  );
}

export function SkillDetailPage({ next, previous, skill }: SkillDetailPageProps) {
  const installCommand = getSkillInstallCommand(skill.slug);

  return (
    <div className="relative isolate min-h-screen overflow-x-hidden bg-[color:var(--surface-0)]">
      <section className="relative isolate border-b border-white/12 bg-[color:var(--surface-0)]">
        <SiteHeader />
        <div className="relative z-10 mx-auto max-w-6xl px-6 pb-10 pt-28 sm:px-10 md:pb-12 md:pt-32">
          <motion.div
            variants={group}
            initial="hidden"
            animate="show"
            className="max-w-3xl"
          >
            <motion.p
              variants={item}
              className="font-sans text-xs font-bold uppercase tracking-[0.2em] text-white/46"
            >
              {skill.category}
            </motion.p>
            <motion.h1
              variants={item}
              className="mt-4 max-w-3xl break-words font-sans text-4xl font-extrabold leading-[0.95] text-white sm:text-5xl lg:text-[4.6rem]"
            >
              {skill.title}
            </motion.h1>
            <motion.p
              variants={item}
              className="mt-6 max-w-2xl text-base leading-relaxed text-[color:var(--crt-dim)] sm:text-lg"
            >
              {skill.lead}
            </motion.p>
          </motion.div>
        </div>
      </section>

      <main className="relative z-10 mx-auto grid max-w-6xl gap-10 px-6 py-14 sm:px-10 lg:grid-cols-[16rem_1fr] lg:py-20">
        <aside className="lg:sticky lg:top-24 lg:h-fit">
          <div className="border-y border-white/12 py-6">
            <p className="font-sans text-xs font-bold uppercase tracking-[0.18em] text-white/40">
              Contents
            </p>
            <nav className="mt-5 flex flex-col gap-3 font-mono text-sm text-white/64">
              <a className="transition hover:text-white" href="#overview">
                Overview
              </a>
              <a className="transition hover:text-white" href="#best-for">
                Best for
              </a>
              <a className="transition hover:text-white" href="#workflow">
                Workflow
              </a>
              <a className="transition hover:text-white" href="#outputs">
                Outputs
              </a>
              <a className="transition hover:text-white" href="#guardrails">
                Guardrails
              </a>
              <a className="transition hover:text-white" href="#entry-points">
                Entry points
              </a>
            </nav>
          </div>
          <div className="mt-8">
            <p className="font-sans text-xs font-bold uppercase tracking-[0.18em] text-white/40">
              Install
            </p>
            <code className="mt-4 block break-words border-y border-white/12 py-4 font-mono text-xs leading-relaxed text-white/72">
              {installCommand}
            </code>
          </div>
        </aside>

        <article>
          <DetailSection eyebrow="01" id="overview" title="What this skill does">
            <p className="max-w-3xl text-base leading-8 text-[color:var(--crt-dim)] md:text-lg">
              {skill.overview}
            </p>
          </DetailSection>

          <DetailSection eyebrow="02" id="best-for" title="When to use it">
            <TextList items={skill.bestFor} />
          </DetailSection>

          <DetailSection eyebrow="03" id="workflow" title="How it works">
            <WorkflowList items={skill.workflow} />
          </DetailSection>

          <DetailSection eyebrow="04" id="outputs" title="What you get back">
            <TextList items={skill.outputs} />
          </DetailSection>

          <DetailSection eyebrow="05" id="guardrails" title="Important boundaries">
            <TextList items={skill.guardrails} />
          </DetailSection>

          <DetailSection eyebrow="06" id="entry-points" title="Files worth opening">
            <div className="divide-y divide-white/10 border-y border-white/10">
              {skill.entryPoints.map((entry) => (
                <Link
                  key={entry.path}
                  href={entryHref(entry.path)}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="group grid gap-3 py-5 transition-colors hover:bg-white/[0.035] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-white md:grid-cols-[11rem_1fr]"
                >
                  <span className="font-mono text-sm font-semibold text-white">
                    {entry.label}
                  </span>
                  <span>
                    <span className="block break-words font-mono text-xs text-white/46">
                      {entry.path}
                    </span>
                    <span className="mt-2 block font-mono text-sm leading-relaxed text-[color:var(--crt-dim)] transition-colors group-hover:text-white/76">
                      {entry.description}
                    </span>
                  </span>
                </Link>
              ))}
            </div>
          </DetailSection>

          <section className="grid gap-6 border-t border-white/12 py-12 md:grid-cols-2">
            <NeighborLink label="Previous skill" skill={previous} />
            <NeighborLink label="Next skill" skill={next} />
          </section>
        </article>
      </main>
    </div>
  );
}
