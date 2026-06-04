'use client';

import { motion } from 'motion/react';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link } from '@/i18n/navigation';
import { SiteHeader } from '@/components/sections/SiteHeader';
import { notify } from '@/components/ui/AppToaster';
import { cx } from '@/lib/classnames';
import { copyText } from '@/lib/clipboard';
import { REPO_URL, getSkillInstallCommand } from '@/lib/content/urls';
import type { SkillDetail } from '@/lib/content/types';
import type { Locale } from '@/lib/i18n/config';
import type { SiteDictionary } from '@/lib/i18n/dictionaries';

type SkillDetailPageProps = {
  labels: SiteDictionary['skillDetail'];
  locale: Locale;
  navLabels: SiteDictionary['nav'];
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
  flushTop = false,
  id,
  title,
}: {
  children: ReactNode;
  eyebrow: string;
  flushTop?: boolean;
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
      className={cx(
        "scroll-mt-28 pb-12 md:pb-16",
        flushTop ? "pt-0" : "pt-12 md:pt-16",
      )}
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
      {items.map((text, index) => (
        <li
          key={text}
          className="grid gap-3 py-5 font-mono text-sm leading-relaxed text-[color:var(--crt-dim)] md:grid-cols-[9rem_1fr] md:text-[0.95rem]"
        >
          <span className="font-sans text-xs font-bold uppercase tracking-[0.16em] text-white/40">
            {String(index + 1).padStart(2, '0')}
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

function InstallCommandCopyButton({
  command,
  labels,
}: {
  command: string;
  labels: SiteDictionary['skillDetail'];
}) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle');
  const timeoutRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const handleCopy = async () => {
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
    }

    try {
      await copyText(command);
      setState('copied');
      notify({ title: labels.installCommandCopied });
    } catch {
      setState('failed');
      notify({
        title: labels.copyInstallCommandFailed,
        type: 'error',
      });
    }

    timeoutRef.current = window.setTimeout(() => setState('idle'), 1800);
  };

  return (
    <button
      aria-live="polite"
      className="inline-flex min-h-7 min-w-[4.75rem] shrink-0 items-center justify-center border border-white/14 px-2.5 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-white/54 transition hover:border-white/38 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
      onClick={handleCopy}
      type="button"
    >
      {state === 'copied'
        ? labels.copiedInstallCommand
        : state === 'failed'
          ? labels.copyInstallCommandFailed
          : labels.copyInstallCommand}
    </button>
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
      className="group block min-h-40 rounded-lg border border-white/12 bg-[linear-gradient(180deg,rgba(255,255,255,0.045),rgba(255,255,255,0.018))] p-5 transition-[background-color,border-color,box-shadow] hover:border-white/32 hover:bg-white/[0.055] hover:shadow-[0_18px_56px_rgba(0,0,0,0.28),inset_0_1px_0_rgba(255,255,255,0.06)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white md:p-6"
    >
      <span className="font-sans text-xs font-bold uppercase tracking-[0.18em] text-white/40">
        {label}
      </span>
      <span className="mt-5 block font-mono text-base font-semibold text-white transition-colors group-hover:text-white/90">
        {skill.title}
      </span>
      <span className="mt-3 block font-mono text-sm leading-relaxed text-[color:var(--crt-dim)] transition-colors group-hover:text-white/64">
        {skill.blurb}
      </span>
    </Link>
  );
}

export function SkillDetailPage({
  labels,
  locale,
  navLabels,
  next,
  previous,
  skill,
}: SkillDetailPageProps) {
  const installCommand = getSkillInstallCommand(skill.slug);

  return (
    <div className="relative isolate min-h-screen overflow-x-clip bg-[color:var(--surface-0)]">
      <SiteHeader labels={navLabels} locale={locale} />
      <section className="relative isolate border-b border-white/12 bg-[color:var(--surface-0)]">
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
        <aside className="lg:sticky lg:top-24 lg:h-fit lg:self-start">
          <div className="pb-6">
            <p className="font-sans text-xs font-bold uppercase tracking-[0.18em] text-white/40">
              {labels.contents}
            </p>
            <nav className="mt-5 flex flex-col gap-3 font-mono text-sm text-white/64">
              <a className="transition hover:text-white" href="#overview">
                {labels.navOverview}
              </a>
              <a className="transition hover:text-white" href="#best-for">
                {labels.navBestFor}
              </a>
              <a className="transition hover:text-white" href="#workflow">
                {labels.navWorkflow}
              </a>
              <a className="transition hover:text-white" href="#outputs">
                {labels.navOutputs}
              </a>
              <a className="transition hover:text-white" href="#guardrails">
                {labels.navGuardrails}
              </a>
              <a className="transition hover:text-white" href="#entry-points">
                {labels.navEntryPoints}
              </a>
            </nav>
          </div>
          <div className="mt-8">
            <div className="flex items-center justify-between gap-3">
              <p className="font-sans text-xs font-bold uppercase tracking-[0.18em] text-white/40">
                {labels.install}
              </p>
              <InstallCommandCopyButton command={installCommand} labels={labels} />
            </div>
            <code className="mt-4 block break-words border-y border-white/12 py-4 font-mono text-xs leading-relaxed text-white/72">
              {installCommand}
            </code>
          </div>
        </aside>

        <article>
          <DetailSection
            eyebrow="01"
            flushTop
            id="overview"
            title={labels.overview}
          >
            <p className="max-w-3xl text-base leading-8 text-[color:var(--crt-dim)] md:text-lg">
              {skill.overview}
            </p>
          </DetailSection>

          <DetailSection eyebrow="02" id="best-for" title={labels.useCase}>
            <TextList items={skill.bestFor} />
          </DetailSection>

          <DetailSection eyebrow="03" id="workflow" title={labels.workflow}>
            <WorkflowList items={skill.workflow} />
          </DetailSection>

          <DetailSection eyebrow="04" id="outputs" title={labels.outputs}>
            <TextList items={skill.outputs} />
          </DetailSection>

          <DetailSection eyebrow="05" id="guardrails" title={labels.guardrails}>
            <TextList items={skill.guardrails} />
          </DetailSection>

          <DetailSection eyebrow="06" id="entry-points" title={labels.entryPoints}>
            <div className="divide-y divide-white/10 border-y border-white/10">
              {skill.entryPoints.map((entry) => (
                <a
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
                </a>
              ))}
            </div>
          </DetailSection>

          <section
            aria-label={labels.relatedSkills}
            className="mt-8 py-6 sm:py-8"
          >
            <div className="grid gap-3 md:grid-cols-2">
              <NeighborLink label={labels.previous} skill={previous} />
              <NeighborLink label={labels.next} skill={next} />
            </div>
          </section>
        </article>
      </main>
    </div>
  );
}
