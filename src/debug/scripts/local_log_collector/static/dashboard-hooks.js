import { API_ROUTES, buildLogDetailUrl, buildLogsUrl, fetchJson } from './dashboard-api.js'
import { PAGE_SIZE, ROW_HEIGHT_DESKTOP, ROW_HEIGHT_MOBILE, isMobile } from './dashboard-utils.js'
import { useCallback, useEffect, useRef, useState, useSWR, useVirtualizer } from './dashboard-deps.js'

export function useCollectorState() {
  const [actionStatus, setActionStatus] = useState(null)
  const [stopped, setStopped] = useState(false)
  const [shutdownComplete, setShutdownComplete] = useState(false)
  const { data, error, mutate } = useSWR(
    stopped ? null : API_ROUTES.state,
    (url) => fetchJson(url),
    {
      refreshInterval: 1000,
      revalidateOnFocus: false,
      keepPreviousData: true,
    },
  )

  const service = data?.service ?? null
  const summary = data?.summary ?? null
  const logsVersion = `${summary?.totalEntries ?? 0}:${summary?.fileUpdatedAt ?? 0}:${summary?.invalidLines ?? 0}`
  const status = error
    ? 'error'
    : shutdownComplete
      ? 'stopped'
      : stopped || data?.status === 'stopping'
        ? 'stopping'
        : data
          ? 'running'
          : 'loading'

  useEffect(() => {
    if (!stopped || shutdownComplete) return
    const timer = setTimeout(() => setShutdownComplete(true), 1200)
    return () => clearTimeout(timer)
  }, [stopped, shutdownComplete])

  async function invoke(url, successMessage, stopAfter = false) {
    setActionStatus({ kind: 'busy', text: 'Working...' })
    try {
      const nextState = await fetchJson(url, { method: 'POST', body: '{}' })
      setActionStatus({ kind: 'ok', text: successMessage })
      if (stopAfter) {
        setStopped(true)
        return
      }
      await mutate(nextState, { revalidate: false })
    } catch (nextError) {
      setActionStatus({
        kind: 'error',
        text: nextError.message || 'Action failed.',
      })
    }
  }

  return {
    service,
    summary,
    error: error ? error.message || 'Failed to fetch collector state.' : '',
    status,
    logsVersion,
    actionStatus,
    clearLogs: () => invoke(service?.clearUrl ?? API_ROUTES.clear, 'Log cleared.'),
    shutdown: () => invoke(service?.shutdownUrl ?? API_ROUTES.shutdown, 'Shutting down.', true),
  }
}

export function useResponsiveRowHeight() {
  const [mobile, setMobile] = useState(isMobile)
  useEffect(() => {
    const mql = window.matchMedia('(max-width: 767px)')
    const handler = (e) => setMobile(e.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [])
  return mobile ? ROW_HEIGHT_MOBILE : ROW_HEIGHT_DESKTOP
}

export function useVirtualLogs(totalEntries, logsVersion, logsUrl = API_ROUTES.logs) {
  const parentRef = useRef(null)
  const requestedPagesRef = useRef(new Set())
  const [entryMap, setEntryMap] = useState(() => new Map())
  const [loading, setLoading] = useState(false)
  const rowHeight = useResponsiveRowHeight()

  useEffect(() => {
    setEntryMap(new Map())
    requestedPagesRef.current.clear()
    if (parentRef.current) parentRef.current.scrollTop = 0
  }, [logsVersion])

  const virtualizer = useVirtualizer({
    count: totalEntries,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowHeight,
    overscan: 8,
  })

  const rows = virtualizer.getVirtualItems()
  const firstVisibleIndex = rows[0]?.index ?? 0
  const lastVisibleIndex = rows[rows.length - 1]?.index ?? 0

  useEffect(() => {
    if (!rows.length || !totalEntries) return

    const first = Math.max(0, firstVisibleIndex - 18)
    const last = Math.min(totalEntries - 1, lastVisibleIndex + 30)
    const pageStarts = []

    for (
      let pageStart = Math.floor(first / PAGE_SIZE) * PAGE_SIZE;
      pageStart <= last;
      pageStart += PAGE_SIZE
    ) {
      if (!requestedPagesRef.current.has(pageStart)) {
        requestedPagesRef.current.add(pageStart)
        pageStarts.push(pageStart)
      }
    }

    if (!pageStarts.length) return

    let cancelled = false
    setLoading(true)

    Promise.all(
      pageStarts.map(async (pageStart) => {
        const limit = Math.min(PAGE_SIZE, totalEntries - pageStart)
        const payload = await fetchJson(buildLogsUrl(logsUrl, { offset: pageStart, limit, order: 'desc' }))
        return { pageStart, entries: payload.entries ?? [] }
      }),
    )
      .then((pages) => {
        if (cancelled) return
        setEntryMap((previous) => {
          const next = new Map(previous)
          pages.forEach(({ pageStart, entries }) => {
            entries.forEach((entry, index) => next.set(pageStart + index, entry))
          })
          return next
        })
      })
      .catch(() => {
        if (cancelled) return
        pageStarts.forEach((pageStart) => requestedPagesRef.current.delete(pageStart))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [firstVisibleIndex, lastVisibleIndex, logsUrl, logsVersion, rows.length, totalEntries])

  return {
    parentRef,
    rows,
    virtualizer,
    entryMap,
    loading,
  }
}

export function useEntryDetail(entryIndex, logsVersion, logDetailUrl = API_ROUTES.logDetail) {
  const key = entryIndex == null
    ? null
    : buildLogDetailUrl(logDetailUrl, {
        entryIndex,
        v: logsVersion,
      })

  const { data, isLoading } = useSWR(key, (url) => fetchJson(url), {
    revalidateOnFocus: false,
    keepPreviousData: true,
  })

  return {
    detail: entryIndex == null ? null : (data?.entry ?? null),
    isLoading: entryIndex == null ? false : isLoading,
  }
}

export function useCollapsible(defaultOpen = true) {
  const [open, setOpen] = useState(defaultOpen)
  const toggle = useCallback(() => setOpen((v) => !v), [])
  return { open, toggle }
}
