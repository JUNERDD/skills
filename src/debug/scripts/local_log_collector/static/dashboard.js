import { createRoot, html, useCallback, useEffect, useMemo, useRef, useState } from './dashboard-deps.js'
import {
  DetailPanel,
  LogPanel,
  MetricBar,
  MobileTabBar,
  PressureList,
  StoppedOverlay,
  Toolbar,
} from './dashboard-components.js'
import { useCollectorState, useEntryDetail, useVirtualLogs } from './dashboard-hooks.js'
import { METRICS } from './dashboard-utils.js'

function App() {
  const { service, summary, error, status, logsVersion, actionStatus, clearLogs, shutdown } = useCollectorState()
  const totalEntries = summary?.totalEntries ?? 0
  const [selectedEntryId, setSelectedEntryId] = useState(null)
  const [mobileTab, setMobileTab] = useState('logs')
  const [hasDetailUpdate, setHasDetailUpdate] = useState(false)
  const activeEntryId = totalEntries > 0 ? selectedEntryId : null

  const isMobileRef = useRef(window.innerWidth < 1280)
  useEffect(() => {
    const mql = window.matchMedia('(max-width: 1279px)')
    const handler = (e) => { isMobileRef.current = e.matches }
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [])

  useEffect(() => {
    if (!totalEntries) {
      setSelectedEntryId(null)
      return
    }
    setSelectedEntryId((current) => (current == null || current >= totalEntries ? totalEntries - 1 : current))
  }, [totalEntries])

  const { parentRef, rows, virtualizer, entryMap, loading } = useVirtualLogs(totalEntries, logsVersion, service?.logsUrl)
  const { detail, isLoading } = useEntryDetail(activeEntryId, logsVersion, service?.logDetailUrl)
  const runCounts = summary?.runCounts ?? []
  const hypothesisCounts = summary?.hypothesisCounts ?? []
  const metrics = useMemo(
    () => METRICS.map((m) => ({ ...m, value: summary ? m.value(summary) : '...' })),
    [summary],
  )

  const handleSelectEntry = useCallback((entryIndex) => {
    setSelectedEntryId(entryIndex)
    if (isMobileRef.current) {
      setMobileTab('detail')
      setHasDetailUpdate(false)
    }
  }, [])

  useEffect(() => {
    if (isMobileRef.current && mobileTab === 'logs' && selectedEntryId != null) {
      setHasDetailUpdate(true)
    }
  }, [selectedEntryId])

  const handleTabChange = useCallback((tab) => {
    setMobileTab(tab)
    if (tab === 'detail') setHasDetailUpdate(false)
  }, [])

  // On mobile, each panel is shown/hidden via CSS class.
  // On desktop (xl+), all panels are always visible in a 3-col grid.
  // "mobile-panel" class hides via display:none; xl:always shows via xl:flex.
  // mobileTab controls which mobile-panel is visible.

  return html`
    <div className="flex flex-col h-screen">
      ${status === 'stopped' ? html`
        <${StoppedOverlay}
          sessionId=${service?.sessionId}
          logFile=${service?.logFile}
        />
      ` : null}
      <${Toolbar}
        service=${service}
        summary=${summary}
        status=${status}
        error=${error}
        actionStatus=${actionStatus}
        onClear=${clearLogs}
        onShutdown=${shutdown}
      />

      <!-- Mobile tab bar (hidden on xl via component) -->
      <${MobileTabBar}
        activeTab=${mobileTab}
        onTabChange=${handleTabChange}
        hasDetailUpdate=${hasDetailUpdate}
      />

      <!-- Main area: on xl it's a 3-col row; on <xl it's stacked tab panels -->
      <div className="flex-1 min-h-0 flex flex-col xl:flex-row">

        <!-- Left sidebar / Stats tab -->
        <aside
          className=${`shrink-0 bg-surface-1/30 border-b border-border xl:border-b-0 xl:border-r xl:w-[220px] 2xl:w-[260px] xl:flex xl:flex-col ${mobileTab === 'stats' ? 'flex flex-col flex-1' : 'hidden xl:flex'}`}
        >
          <div className="flex-1 overflow-auto scroll-thin">
            <${PressureList}
              title="Run Distribution"
              items=${runCounts}
              emptyText="No runId values yet."
              defaultOpen=${true}
            />
            <${PressureList}
              title="Hypothesis Activity"
              items=${hypothesisCounts}
              emptyText="No hypothesis values yet."
              defaultOpen=${true}
            />
          </div>
        </aside>

        <!-- Center: Logs tab -->
        <main
          className=${`flex-1 min-w-0 min-h-0 flex flex-col ${mobileTab === 'logs' ? '' : 'hidden xl:flex'}`}
        >
          <!-- MetricBar: only visible on mobile logs tab -->
          <div className="xl:hidden">
            <${MetricBar} metrics=${metrics} />
          </div>
          <${LogPanel}
            totalEntries=${totalEntries}
            selectedEntryId=${activeEntryId}
            onSelectEntry=${handleSelectEntry}
            loading=${loading}
            parentRef=${parentRef}
            rows=${rows}
            virtualizer=${virtualizer}
            entryMap=${entryMap}
          />
        </main>

        <!-- Right: Detail tab -->
        <aside
          className=${`shrink-0 min-h-0 flex flex-col xl:w-[320px] 2xl:w-[380px] xl:border-l xl:border-border ${mobileTab === 'detail' ? 'flex-1' : 'hidden xl:flex'}`}
        >
          <${DetailPanel} detail=${detail} isLoading=${isLoading} />
        </aside>

      </div>
    </div>
  `
}

createRoot(document.getElementById('app')).render(html`<${App} />`)
