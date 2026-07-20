export const PAGE_SIZE = 120
export const ROW_HEIGHT_DESKTOP = 52
export const ROW_HEIGHT_MOBILE = 76
export const COLLECTOR_REFRESH_INTERVAL_MS = 1000

export const STATUS_COLOR = {
  loading: 'text-ghost',
  running: 'text-accent',
  frozen: 'text-warn',
  stopping: 'text-warn',
  stopped: 'text-ghost',
  error: 'text-danger',
}

export const STATUS_BG = {
  loading: 'bg-ghost/10 border-ghost/20',
  running: 'bg-accent/10 border-accent/20',
  frozen: 'bg-warn/10 border-warn/20',
  stopping: 'bg-warn/10 border-warn/20',
  stopped: 'bg-ghost/10 border-ghost/20',
  error: 'bg-danger/10 border-danger/20',
}

export const STATUS_LABEL = {
  loading: 'LOADING',
  running: 'LIVE',
  frozen: 'FROZEN',
  stopping: 'STOPPING',
  stopped: 'STOPPED',
  error: 'DISCONNECTED',
}

export const STATUS_DOT_COLOR = {
  loading: 'bg-ghost',
  running: 'bg-accent',
  frozen: 'bg-warn',
  stopping: 'bg-warn',
  stopped: 'bg-ghost',
  error: 'bg-danger',
}

export function deriveCollectorStatus({
  error = false,
  shutdownComplete = false,
  stopped = false,
  serviceStatus = '',
  recordingFrozen = false,
  hasData = false,
} = {}) {
  if (error) return 'error'
  if (shutdownComplete) return 'stopped'
  if (stopped || serviceStatus === 'stopping') return 'stopping'
  if ((recordingFrozen || serviceStatus === 'frozen') && hasData) return 'frozen'
  return hasData ? 'running' : 'loading'
}

export function getFreezeControl(status, frozen = status === 'frozen', busy = false) {
  return {
    label: frozen ? 'Resume' : 'Freeze',
    pressed: frozen,
    disabled: busy || (status !== 'running' && status !== 'frozen'),
    title: frozen
      ? 'Resume writing new debug events.'
      : 'Freeze writing new debug events; existing logs can still be cleared.',
  }
}

export function getStableLogPageRequest(totalEntries, pageStart, pageSize = PAGE_SIZE) {
  const safeTotal = Math.max(0, Number(totalEntries) || 0)
  const safeStart = Math.min(Math.max(0, Number(pageStart) || 0), safeTotal)
  const safePageSize = Math.max(1, Number(pageSize) || PAGE_SIZE)
  const limit = Math.min(safePageSize, safeTotal - safeStart)
  return {
    offset: Math.max(safeTotal - safeStart - limit, 0),
    limit,
    order: 'asc',
  }
}

export function toDescendingLogPage(entries) {
  return Array.isArray(entries) ? entries.slice().reverse() : []
}

export const METRICS = [
  {
    key: 'totalEntries',
    label: 'Entries',
    value: (s) => String(s.totalEntries ?? 0),
  },
  {
    key: 'invalidLines',
    label: 'Invalid',
    value: (s) => String(s.invalidLines ?? 0),
  },
  {
    key: 'fileSizeBytes',
    label: 'Size',
    value: (s) => formatBytes(s.fileSizeBytes ?? 0),
  },
  {
    key: 'fileUpdatedAt',
    label: 'Updated',
    value: (s) => formatClock(s.fileUpdatedAt),
  },
]

export function cx(...values) {
  return values.filter(Boolean).join(' ')
}

export function getLogEntrySummary(entry) {
  for (const value of [entry?.message, entry?.event, entry?.probeId]) {
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return 'No message'
}

export function formatClock(timestamp) {
  if (!timestamp) return '--:--:--'
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(timestamp))
}

export function formatDateTime(timestamp) {
  if (!timestamp) return 'N/A'
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(timestamp))
}

export function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = bytes
  let unit = units[0]
  for (const nextUnit of units) {
    unit = nextUnit
    if (value < 1024 || nextUnit === units[units.length - 1]) break
    value /= 1024
  }
  return `${value >= 10 || unit === 'B' ? value.toFixed(0) : value.toFixed(1)} ${unit}`
}

/** Returns true when viewport width < breakpoint */
export function isMobile() {
  return window.innerWidth < 768
}
