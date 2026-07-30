function anonymousSessionId() {
  const key = 'restaurant-analytics-session-v1'
  let value = window.localStorage.getItem(key)
  if (!value) {
    value = window.crypto.randomUUID()
    window.localStorage.setItem(key, value)
  }
  return value
}

export function trackEvent(
  apiUrl: string,
  eventName: string,
  branchId?: string,
  metadata: Record<string, string | number | boolean> = {}
) {
  if (typeof window === 'undefined' || !window.navigator.onLine) return
  void fetch(`${apiUrl}/public/analytics`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    keepalive: true,
    body: JSON.stringify({
      event_name: eventName,
      branch_id: branchId || null,
      anonymous_session_id: anonymousSessionId(),
      metadata,
    }),
  }).catch(() => undefined)
}
