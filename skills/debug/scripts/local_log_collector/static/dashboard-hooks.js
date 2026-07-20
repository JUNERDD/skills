import { API_ROUTES, buildLogDetailUrl, buildLogsUrl, fetchJson } from './dashboard-api.js'
import {
  PAGE_SIZE,
  ROW_HEIGHT_DESKTOP,
  ROW_HEIGHT_MOBILE,
  COLLECTOR_REFRESH_INTERVAL_MS,
  deriveCollectorStatus,
  getStableLogPageRequest,
  isMobile,
  toDescendingLogPage,
} from './dashboard-utils.js'
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  useSWR,
  useVirtualizer,
} from './dashboard-deps.js'

export function useCollectorState() {
  const [actionStatus, setActionStatus] = useState(null)
  const [actionBusy, setActionBusy] = useState(false)
  const actionBusyRef = useRef(false)
  const [stopped, setStopped] = useState(false)
  const [shutdownComplete, setShutdownComplete] = useState(false)
  const dashboardOpenRecordAttemptedRef = useRef(false)
  const { data, error, mutate } = useSWR(
    stopped ? null : API_ROUTES.state,
    (url) => fetchJson(url),
    {
      refreshInterval: COLLECTOR_REFRESH_INTERVAL_MS,
      revalidateOnFocus: false,
      keepPreviousData: true,
    },
  )
  const service = data?.service ?? null
  const summary = data?.summary ?? null
  const logsVersion = `${summary?.totalEntries ?? 0}:${summary?.fileUpdatedAt ?? 0}:${summary?.invalidLines ?? 0}`
  const status = deriveCollectorStatus({
    error: Boolean(error),
    shutdownComplete,
    stopped,
    serviceStatus: data?.status,
    recordingFrozen: Boolean(service?.recordingFrozen),
    hasData: Boolean(data),
  })

  useEffect(() => {
    if (!stopped || shutdownComplete) return
    const timer = setTimeout(() => setShutdownComplete(true), 1200)
    return () => clearTimeout(timer)
  }, [stopped, shutdownComplete])

  useEffect(() => {
    if (stopped || dashboardOpenRecordAttemptedRef.current || !service?.dashboardToken) return
    if (service.dashboardFrontendOpenRecorded) {
      dashboardOpenRecordAttemptedRef.current = true
      return
    }

    dashboardOpenRecordAttemptedRef.current = true
    fetchJson(service.dashboardFrontendOpenedUrl || API_ROUTES.dashboardOpened, {
      method: 'POST',
      headers: { 'X-Debug-Dashboard-Token': service.dashboardToken },
      body: '{}',
    })
      .then((nextState) => mutate(nextState, { revalidate: false }))
      .catch(() => {})
  }, [mutate, service, stopped])

  async function invoke(url, successMessage, stopAfter = false, dashboardToken = '') {
    if (actionBusyRef.current) return
    actionBusyRef.current = true
    setActionBusy(true)
    setActionStatus({ kind: 'busy', text: 'Working...' })
    try {
      const nextState = await fetchJson(url, {
        method: 'POST',
        headers: { 'X-Debug-Dashboard-Token': dashboardToken },
        body: '{}',
      })
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
    } finally {
      actionBusyRef.current = false
      setActionBusy(false)
    }
  }

  return {
    service,
    summary,
    error: error ? error.message || 'Failed to fetch collector state.' : '',
    status,
    logsVersion,
    actionStatus,
    actionBusy,
    clearLogs: () => actionBusyRef.current
      ? undefined
      : invoke(service?.clearUrl ?? API_ROUTES.clear, 'Log cleared.', false, service?.dashboardToken),
    setRecordingFrozen: (nextFrozen) => invoke(
      nextFrozen
        ? service?.freezeRecordingUrl ?? API_ROUTES.freezeRecording
        : service?.resumeRecordingUrl ?? API_ROUTES.resumeRecording,
      nextFrozen ? 'Recording frozen.' : 'Recording resumed.',
      false,
      service?.dashboardToken,
    ),
    shutdown: () => invoke(service?.shutdownUrl ?? API_ROUTES.shutdown, 'Shutting down.', true, service?.dashboardToken),
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
    setLoading(false)
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
        const request = getStableLogPageRequest(totalEntries, pageStart)
        const payload = await fetchJson(buildLogsUrl(logsUrl, request))
        return { pageStart, entries: toDescendingLogPage(payload.entries) }
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

export function useCollectorConfig(configUrl = API_ROUTES.config, dashboardToken = '') {
  const [actionStatus, setActionStatus] = useState(null)
  const { data, error, mutate } = useSWR(
    configUrl || null,
    (url) => fetchJson(url),
    {
      revalidateOnFocus: false,
      keepPreviousData: true,
    },
  )

  const setSelectedIde = useCallback(async (selectedIde) => {
    if (!configUrl) return
    setActionStatus({ kind: 'busy', text: 'Saving IDE...' })
    try {
      const nextConfig = await fetchJson(configUrl, {
        method: 'POST',
        headers: { 'X-Debug-Dashboard-Token': dashboardToken },
        body: JSON.stringify({ selectedIde }),
      })
      setActionStatus({ kind: 'ok', text: 'IDE saved.' })
      await mutate(nextConfig, { revalidate: false })
    } catch (nextError) {
      setActionStatus({
        kind: 'error',
        text: nextError.message || 'Failed to save IDE.',
      })
    }
  }, [configUrl, dashboardToken, mutate])

  return {
    configFile: data?.configFile || '',
    ide: data?.ide || { selected: '', selectedAvailable: false, selectedSource: 'none', options: [] },
    error: data?.configError || (error ? error.message || 'Failed to load config.' : ''),
    actionStatus,
    setSelectedIde,
  }
}

export function useLocationState(
  locationsUrl = API_ROUTES.locations,
  openLocationUrl = API_ROUTES.openLocation,
  dashboardToken = '',
) {
  const [actionStatus, setActionStatus] = useState(null)
  const { data, error } = useSWR(
    locationsUrl || null,
    (url) => fetchJson(url),
    {
      refreshInterval: COLLECTOR_REFRESH_INTERVAL_MS,
      revalidateOnFocus: false,
      keepPreviousData: true,
    },
  )

  const openLocation = useCallback(async (location, ide) => {
    if (!openLocationUrl) return
    setActionStatus({ kind: 'busy', text: 'Opening...' })
    try {
      const payload = {
        location,
      }
      if (ide) {
        payload.ide = ide
      }
      const response = await fetchJson(openLocationUrl, {
        method: 'POST',
        headers: { 'X-Debug-Dashboard-Token': dashboardToken },
        body: JSON.stringify(payload),
      })
      const resolvedLocation = response?.location?.displayPath || response?.location?.location || location
      const launchStatus = response?.launchStatus === 'requested' ? 'requested' : 'confirmed'
      setActionStatus({
        kind: 'ok',
        text: launchStatus === 'requested'
          ? `Launch requested for ${resolvedLocation}`
          : `Opened ${resolvedLocation}`,
      })
    } catch (nextError) {
      setActionStatus({
        kind: 'error',
        text: nextError.message || 'Failed to open location.',
      })
    }
  }, [dashboardToken, openLocationUrl])

  return {
    locations: data?.locations || [],
    workspaceRoot: data?.workspaceRoot || '',
    isLoading: !data && !error,
    error: error ? error.message || 'Failed to load locations.' : '',
    actionStatus,
    openLocation,
  }
}
