export interface CustomerProfile {
  id: string
  username?: string | null
  name?: string | null
  phone: string
  phone_verified: boolean
}

export interface CustomerSession {
  access_token: string
  token_type: string
  expires_in: number
  customer: CustomerProfile
}

const SESSION_KEY = 'restaurant-customer-session-v1'

export function getCustomerSession(): CustomerSession | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(SESSION_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    window.localStorage.removeItem(SESSION_KEY)
    return null
  }
}

export function saveCustomerSession(session: CustomerSession) {
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

export function clearCustomerSession() {
  window.localStorage.removeItem(SESSION_KEY)
}

export async function customerFetch(
  input: RequestInfo | URL,
  init: RequestInit = {}
) {
  const session = getCustomerSession()
  const headers = new Headers(init.headers)
  if (session?.access_token) {
    headers.set('Authorization', `Bearer ${session.access_token}`)
  }
  const response = await fetch(input, { ...init, headers })
  if (response.status === 401) {
    clearCustomerSession()
  }
  return response
}

/** Pull the human-readable message out of a FastAPI error body. */
export async function errorMessage(
  response: Response,
  fallback: string
): Promise<string> {
  try {
    const data = await response.json()
    if (typeof data?.detail === 'string') return data.detail
    if (Array.isArray(data?.detail) && data.detail[0]?.msg) {
      return String(data.detail[0].msg)
    }
  } catch {
    /* fall through to the caller's message */
  }
  return fallback
}

/** Display form for a stored 233XXXXXXXXX number. */
export function formatGhanaPhone(phone: string): string {
  const digits = (phone || '').replace(/\D/g, '')
  if (digits.startsWith('233') && digits.length === 12) {
    return `0${digits.slice(3, 5)} ${digits.slice(5, 8)} ${digits.slice(8)}`
  }
  return phone
}
