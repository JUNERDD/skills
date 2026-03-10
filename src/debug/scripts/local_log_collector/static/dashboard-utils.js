export const PAGE_SIZE = 120
export const ROW_HEIGHT_DESKTOP = 52
export const ROW_HEIGHT_MOBILE = 76

export const STATUS_COLOR = {
  loading: 'text-ghost',
  running: 'text-accent',
  stopping: 'text-warn',
  stopped: 'text-ghost',
  error: 'text-danger',
}

export const STATUS_BG = {
  loading: 'bg-ghost/10 border-ghost/20',
  running: 'bg-accent/10 border-accent/20',
  stopping: 'bg-warn/10 border-warn/20',
  stopped: 'bg-ghost/10 border-ghost/20',
  error: 'bg-danger/10 border-danger/20',
}

export const STATUS_LABEL = {
  loading: 'LOADING',
  running: 'LIVE',
  stopping: 'STOPPING',
  stopped: 'STOPPED',
  error: 'DISCONNECTED',
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
