import { html, useState, useEffect } from './dashboard-deps.js'
import { useCollapsible } from './dashboard-hooks.js'
import {
  cx,
  formatClock,
  formatDateTime,
  METRICS,
  STATUS_BG,
  STATUS_COLOR,
  STATUS_LABEL,
} from './dashboard-utils.js'

/* ────────────────────────────────────────────
   Toolbar (top bar — always visible)
   ──────────────────────────────────────────── */
export function Toolbar({ service, summary, status, error, actionStatus, onClear, onShutdown }) {
  const dotColor = {
    loading: 'bg-ghost',
    running: 'bg-accent',
    stopping: 'bg-warn',
    stopped: 'bg-ghost',
    error: 'bg-danger',
  }[status]

  return html`
    <header className="flex items-center gap-2 border-b border-border bg-surface-1 px-2 py-1.5 sm:gap-3 sm:px-3 sm:py-2 xl:px-4 shrink-0">
      <!-- Logo -->
      <div className="flex items-center gap-1.5 sm:gap-2.5 mr-1 sm:mr-3 shrink-0">
        <div className="flex h-5 w-5 sm:h-6 sm:w-6 items-center justify-center rounded bg-accent/15">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" className="text-accent">
            <path d="M12 20V10"/><path d="M18 20V4"/><path d="M6 20v-4"/>
          </svg>
        </div>
        <span className="font-mono text-2xs font-semibold text-bright tracking-wide hidden sm:inline">DEBUG CONSOLE</span>
      </div>

      <!-- Status badge -->
      <div className=${cx('flex items-center gap-1 sm:gap-1.5 rounded border px-1.5 sm:px-2 py-0.5 text-2xs font-mono font-semibold tracking-wider shrink-0', STATUS_BG[status])}>
        <span className=${cx('status-dot h-1.5 w-1.5 rounded-full', dotColor)} data-status=${status}></span>
        <span className=${STATUS_COLOR[status]}>${STATUS_LABEL[status]}</span>
      </div>

      <!-- Session info -->
      <div className="hidden lg:flex items-center gap-2 text-2xs font-mono text-ghost truncate ml-1">
        <span className="text-pale">${service?.sessionId || '...'}</span>
        <span className="text-border-bright">|</span>
        <span className="truncate max-w-[280px]">${service?.logFile || '...'}</span>
      </div>

      <div className="flex-1 min-w-0" />

      <!-- Toolbar metrics (md+) -->
      <div className="hidden md:flex items-center gap-3 text-2xs font-mono mr-2">
        ${METRICS.map((m) => html`
          <div key=${m.key} className="flex items-center gap-1.5">
            <span className="text-ghost">${m.label}:</span>
            <span className="metric-val text-pale font-semibold" key=${summary ? m.value(summary) : '...'}>${summary ? m.value(summary) : '...'}</span>
          </div>
        `)}
      </div>

      <!-- Action status -->
      ${(error || actionStatus?.text) ? html`
        <span className=${cx('hidden sm:inline text-2xs font-mono mr-1 truncate max-w-[120px]', error || actionStatus?.kind === 'error' ? 'text-danger' : 'text-ghost')}>
          ${error || actionStatus?.text}
        </span>
      ` : null}

      <!-- Buttons -->
      <div className="flex items-center gap-1 sm:gap-1.5 shrink-0">
        <button
          className="rounded border border-border bg-surface-2 px-2 sm:px-2.5 py-1 text-2xs font-mono font-semibold text-pale hover:bg-surface-3 hover:text-bright transition-colors disabled:opacity-40"
          onClick=${onClear}
          disabled=${status === 'stopping'}
        >Clear</button>
        <button
          className="rounded border border-danger/30 bg-danger/10 px-2 sm:px-2.5 py-1 text-2xs font-mono font-semibold text-danger hover:bg-danger/20 transition-colors disabled:opacity-40"
          onClick=${onShutdown}
          disabled=${status === 'stopping' || status === 'stopped'}
        >Stop</button>
      </div>
    </header>
  `
}

/* ────────────────────────────────────────────
   Mobile Tab Bar
   ──────────────────────────────────────────── */
export function MobileTabBar({ activeTab, onTabChange, hasDetailUpdate }) {
  const tabs = [
    { key: 'logs', label: 'Logs', icon: html`<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>` },
    { key: 'detail', label: 'Detail', icon: html`<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>` },
    { key: 'stats', label: 'Stats', icon: html`<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>` },
  ]

  return html`
    <nav className="flex border-b border-border bg-surface-1/80 backdrop-blur-sm shrink-0 xl:hidden">
      ${tabs.map((t) => html`
        <button
          key=${t.key}
          className=${cx('mobile-tab relative flex-1 flex items-center justify-center gap-1.5 py-2 text-2xs font-mono font-semibold uppercase tracking-wider text-ghost')}
          data-active=${activeTab === t.key ? 'true' : 'false'}
          onClick=${() => onTabChange(t.key)}
        >
          ${t.icon}
          ${t.label}
          ${t.key === 'detail' && hasDetailUpdate ? html`<span className="tab-notify" />` : null}
        </button>
      `)}
    </nav>
  `
}

/* ────────────────────────────────────────────
   Metric cards (mobile — inside Logs tab)
   ──────────────────────────────────────────── */
export function MetricBar({ metrics }) {
  return html`
    <div className="grid grid-cols-4 gap-1 px-2 py-1.5 border-b border-border bg-surface-1/50 sm:gap-2 sm:px-3 sm:py-2 shrink-0">
      ${metrics.map((m) => html`
        <div key=${m.key} className="rounded border border-border bg-surface-1 px-1.5 py-1 sm:px-2.5 sm:py-1.5">
          <div className="text-[9px] sm:text-2xs font-mono text-ghost uppercase tracking-wider leading-tight">${m.label}</div>
          <div className="metric-val mt-0.5 font-mono text-xs sm:text-sm font-bold text-bright" key=${m.value}>${m.value}</div>
        </div>
      `)}
    </div>
  `
}

/* ────────────────────────────────────────────
   Pressure List
   ──────────────────────────────────────────── */
export function PressureList({ title, items, emptyText, defaultOpen }) {
  const { open, toggle } = useCollapsible(defaultOpen != null ? defaultOpen : true)

  return html`
    <div className="border-b border-border last:border-b-0">
      <button
        className="flex w-full items-center justify-between px-3 py-2 text-left hover:bg-surface-2/50 transition-colors"
        onClick=${toggle}
      >
        <div className="flex items-center gap-2">
          <span className="text-2xs font-mono font-semibold uppercase tracking-wider text-ghost">${title}</span>
          <span className="font-mono text-2xs text-border-bright">${items.length}</span>
        </div>
        <svg
          width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          className=${cx('text-ghost transition-transform', open ? 'rotate-0' : '-rotate-90')}
        >
          <path d="M6 9l6 6 6-6"/>
        </svg>
      </button>
      <div className="collapse-body" data-open=${open ? 'true' : 'false'}>
        <div>
          <div className="scroll-thin max-h-[240px] overflow-auto px-2 pb-2 xl:max-h-[calc(50vh-70px)]">
            ${items.length
              ? items.map((item, i) => html`
                  <div key=${`${title}-${item.name}-${i}`} className="flex items-center justify-between gap-2 rounded px-2 py-1.5 hover:bg-surface-2/60 transition-colors">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="font-mono text-2xs text-border-bright w-4 text-right shrink-0">${i + 1}</span>
                      <span className="text-xs text-pale truncate">${item.name}</span>
                    </div>
                    <span className="font-mono text-xs font-bold text-bright shrink-0 tabular-nums">${item.count}</span>
                  </div>
                `)
              : html`<div className="px-2 py-3 text-center text-2xs text-ghost">${emptyText}</div>`
            }
          </div>
        </div>
      </div>
    </div>
  `
}

/* ────────────────────────────────────────────
   Log row — card on mobile, inline on desktop
   ──────────────────────────────────────────── */
function LogRow({ row, entry, totalEntries, selectedEntryId, onSelect }) {
  if (!entry) {
    return html`
      <div
        className="absolute left-0 w-full px-1"
        style=${{ height: `${row.size}px`, transform: `translateY(${row.start}px)` }}
      >
        <div className="flex h-full items-center px-3 text-2xs text-ghost font-mono">Loading...</div>
      </div>
    `
  }

  const isActive = entry.entryIndex === selectedEntryId

  return html`
    <div
      className="absolute left-0 w-full"
      style=${{ height: `${row.size}px`, transform: `translateY(${row.start}px)` }}
    >
      <div
        className=${cx(
          'log-row h-full border-l-2 border-transparent',
          'flex flex-col justify-center gap-0.5 px-2.5 py-1',
          'sm:flex-row sm:items-center sm:gap-2 sm:px-3 sm:py-0',
        )}
        data-active=${isActive ? 'true' : 'false'}
        onClick=${() => onSelect(entry.entryIndex)}
      >
        <!-- Desktop inline elements -->
        <span className="hidden sm:inline font-mono text-2xs text-border-bright w-8 text-right shrink-0 tabular-nums">
          ${totalEntries - row.index}
        </span>
        <span className="hidden sm:inline font-mono text-2xs text-ghost w-16 shrink-0">
          ${formatClock(entry.timestamp)}
        </span>

        <!-- Mobile: top line -->
        <div className="flex items-center gap-1.5 sm:hidden">
          <span className="font-mono text-2xs text-border-bright tabular-nums shrink-0">#${totalEntries - row.index}</span>
          <span className="font-mono text-[9px] text-ghost shrink-0">${formatClock(entry.timestamp)}</span>
          <div className="flex items-center gap-1 min-w-0">
            <span className="inline-block rounded bg-accent/12 border border-accent/20 px-1 py-px text-[9px] font-mono text-accent max-w-[72px] truncate">
              ${entry.runId || 'none'}
            </span>
            ${entry.hypothesisId ? html`
              <span className="inline-block rounded bg-warn/12 border border-warn/20 px-1 py-px text-[9px] font-mono text-warn max-w-[64px] truncate">
                ${entry.hypothesisId}
              </span>
            ` : null}
          </div>
        </div>

        <!-- Desktop badges -->
        <div className="hidden sm:flex items-center gap-1 shrink-0">
          <span className="inline-block rounded bg-accent/12 border border-accent/20 px-1.5 py-px text-2xs font-mono text-accent max-w-[100px] truncate">
            ${entry.runId || 'none'}
          </span>
          ${entry.hypothesisId ? html`
            <span className="inline-block rounded bg-warn/12 border border-warn/20 px-1.5 py-px text-2xs font-mono text-warn max-w-[80px] truncate">
              ${entry.hypothesisId}
            </span>
          ` : null}
        </div>

        <!-- Message -->
        <span className="text-[11px] sm:text-xs text-pale truncate min-w-0 flex-1 leading-tight">
          ${entry.message || 'No message'}
        </span>

        <!-- Mobile: location -->
        <span className="text-[9px] font-mono text-ghost truncate sm:hidden leading-tight">
          ${entry.location || ''}${entry.lineNumber != null ? ` :${entry.lineNumber}` : ''}
        </span>

        <!-- Desktop: location + line -->
        <span className="hidden lg:block font-mono text-2xs text-ghost truncate max-w-[160px] shrink-0">
          ${entry.location || ''}
        </span>
        <span className="hidden md:block font-mono text-2xs text-border-bright w-10 text-right shrink-0">
          ${entry.lineNumber != null ? `L${entry.lineNumber}` : ''}
        </span>
      </div>
    </div>
  `
}

/* ────────────────────────────────────────────
   Log Panel
   ──────────────────────────────────────────── */
export function LogPanel({
  totalEntries,
  selectedEntryId,
  onSelectEntry,
  loading,
  parentRef,
  rows,
  virtualizer,
  entryMap,
}) {
  return html`
    <div className="flex flex-col flex-1 min-h-0">
      <!-- Panel header -->
      <div className="section-label flex items-center justify-between border-b border-border bg-surface-1 px-3 py-1.5 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-2xs font-mono font-semibold uppercase tracking-wider text-ghost">Log Stream</span>
          <span className="font-mono text-2xs text-border-bright">${totalEntries} entries</span>
        </div>
        ${loading ? html`
          <div className="load-bar h-0.5 w-16 rounded-full bg-surface-3 overflow-hidden"></div>
        ` : null}
      </div>

      <!-- Virtual list -->
      <div
        className="scroll-thin flex-1 overflow-auto min-h-0 bg-surface-0"
        ref=${parentRef}
      >
        ${totalEntries
          ? html`
              <div className="relative" style=${{ height: `${virtualizer.getTotalSize()}px` }}>
                ${rows.map((row) => html`
                  <${LogRow}
                    key=${row.key}
                    row=${row}
                    entry=${entryMap.get(row.index)}
                    totalEntries=${totalEntries}
                    selectedEntryId=${selectedEntryId}
                    onSelect=${onSelectEntry}
                  />
                `)}
              </div>
            `
          : html`
              <div className="flex h-full items-center justify-center text-xs text-ghost font-mono py-12">
                Waiting for log entries...
              </div>
            `}
      </div>
    </div>
  `
}

/* ────────────────────────────────────────────
   Detail Panel
   ──────────────────────────────────────────── */
export function DetailPanel({ detail, isLoading }) {
  const [activeTab, setActiveTab] = useState('payload')

  const facts = detail
    ? [
        { label: 'runId', value: detail.runId || 'none' },
        { label: 'hypothesis', value: detail.hypothesisId || 'none' },
        { label: 'time', value: formatDateTime(detail.timestamp) },
        { label: 'location', value: detail.location || 'N/A' },
        { label: 'session', value: detail.sessionId || 'N/A' },
      ]
    : []

  return html`
    <div className="flex flex-col flex-1 min-h-0">
      <!-- Tabs -->
      <div className="flex items-center gap-0 border-b border-border bg-surface-1 shrink-0">
        <button
          className=${cx('tab-btn px-3 py-1.5 text-2xs font-mono font-semibold uppercase tracking-wider border-b-2 border-transparent', activeTab === 'payload' ? '' : 'text-ghost hover:text-pale')}
          data-active=${activeTab === 'payload' ? 'true' : 'false'}
          onClick=${() => setActiveTab('payload')}
        >Payload</button>
        <button
          className=${cx('tab-btn px-3 py-1.5 text-2xs font-mono font-semibold uppercase tracking-wider border-b-2 border-transparent', activeTab === 'meta' ? '' : 'text-ghost hover:text-pale')}
          data-active=${activeTab === 'meta' ? 'true' : 'false'}
          onClick=${() => setActiveTab('meta')}
        >Meta</button>
      </div>

      <!-- Content -->
      <div className="flex-1 min-h-0 overflow-hidden">
        ${!detail
          ? html`
              <div className="flex h-full items-center justify-center text-xs text-ghost font-mono py-8">
                ${isLoading ? 'Loading...' : 'Select an entry'}
              </div>
            `
          : activeTab === 'meta'
            ? html`
                <div className="scroll-thin h-full overflow-auto p-2">
                  ${facts.map(({ label, value }) => html`
                    <div key=${label} className="flex items-start gap-2 rounded px-2 py-1.5 hover:bg-surface-2/40">
                      <span className="font-mono text-2xs text-ghost uppercase tracking-wider w-20 shrink-0 pt-px">${label}</span>
                      <span className="text-xs text-pale break-all">${value}</span>
                    </div>
                  `)}
                </div>
              `
            : html`
                <pre className="scroll-thin h-full overflow-auto bg-surface-0 p-3 font-mono text-[11px] leading-5 text-pale whitespace-pre-wrap break-all">${detail.payloadText || 'No payload available.'}</pre>
              `
        }
      </div>
    </div>
  `
}

/* ────────────────────────────────────────────
   Stopped Overlay — shown after service shutdown
   ──────────────────────────────────────────── */
export function StoppedOverlay({ sessionId, logFile }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const raf = requestAnimationFrame(() => setVisible(true))
    return () => cancelAnimationFrame(raf)
  }, [])

  return html`
    <div className=${cx('stopped-overlay', visible && 'stopped-overlay--visible')}>
      <div className=${cx('stopped-card', visible && 'stopped-card--visible')}>
        <!-- Terminal-off icon -->
        <div className="stopped-icon-ring">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-ghost">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
            <line x1="8" y1="21" x2="16" y2="21"/>
            <line x1="12" y1="17" x2="12" y2="21"/>
            <line x1="7" y1="8" x2="17" y2="12" className="text-border-bright"/>
            <line x1="7" y1="12" x2="17" y2="8" className="text-border-bright"/>
          </svg>
        </div>

        <div className="mt-4 text-center">
          <h2 className="font-mono text-sm font-semibold text-pale tracking-wide">SERVICE STOPPED</h2>
          <p className="mt-1.5 font-mono text-2xs text-ghost leading-relaxed">
            The debug log collector has been shut down.
          </p>
        </div>

        ${sessionId ? html`
          <div className="mt-4 w-full rounded border border-border bg-surface-0/60 px-3 py-2">
            <div className="flex items-center gap-2 text-2xs font-mono">
              <span className="text-ghost shrink-0">session</span>
              <span className="text-pale truncate">${sessionId}</span>
            </div>
            ${logFile ? html`
              <div className="flex items-center gap-2 text-2xs font-mono mt-1">
                <span className="text-ghost shrink-0">logfile</span>
                <span className="text-border-bright truncate">${logFile}</span>
              </div>
            ` : null}
          </div>
        ` : null}

        <p className="mt-4 font-mono text-[9px] text-ghost/60 tracking-wider uppercase">
          You may close this tab
        </p>
      </div>
    </div>
  `
}
