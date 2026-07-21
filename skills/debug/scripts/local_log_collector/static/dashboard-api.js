export const API_ROUTES = {
  state: '/api/state',
  logs: '/api/logs',
  logDetail: '/api/logs/detail',
  locations: '/api/locations',
  config: '/api/config',
  dashboardOpenFailed: '/api/dashboard-open-failed',
  dashboardOpened: '/api/dashboard-opened',
  openLocation: '/api/open-location',
  clear: '/api/clear',
  freezeRecording: '/api/recording/freeze',
  resumeRecording: '/api/recording/resume',
  shutdown: '/api/shutdown',
}

export async function fetchJson(url, options) {
  const { headers, ...rest } = options || {}
  const response = await fetch(url, {
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      ...(headers || {}),
    },
    ...rest,
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(payload.error || `Request failed with ${response.status}`)
  }
  return payload
}

export function buildLogsUrl(baseUrl, searchParams) {
  const url = new URL(baseUrl, window.location.origin)
  url.search = new URLSearchParams(searchParams).toString()
  return url.toString()
}

export function buildLogDetailUrl(baseUrl, searchParams) {
  const url = new URL(baseUrl, window.location.origin)
  url.search = new URLSearchParams(searchParams).toString()
  return url.toString()
}
