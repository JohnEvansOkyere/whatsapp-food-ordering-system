export interface StaffIdentity {
  username: string
  display_name: string
  role: string
  branch_ids: string[]
}

export interface StaffSession {
  access_token: string
  token_type: string
  expires_in: number
  staff: StaffIdentity
}

const SESSION_KEY = 'restaurant-staff-session-v1'

export function getStaffSession(): StaffSession | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(SESSION_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    window.localStorage.removeItem(SESSION_KEY)
    return null
  }
}

export function saveStaffSession(session: StaffSession) {
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

export function clearStaffSession() {
  window.localStorage.removeItem(SESSION_KEY)
}

export async function staffFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const session = getStaffSession()
  const headers = new Headers(init.headers)
  if (session?.access_token) {
    headers.set('Authorization', `Bearer ${session.access_token}`)
  }
  const response = await fetch(input, { ...init, headers })
  if (response.status === 401 && typeof window !== 'undefined') {
    clearStaffSession()
    window.location.assign('/admin/login')
  }
  return response
}
