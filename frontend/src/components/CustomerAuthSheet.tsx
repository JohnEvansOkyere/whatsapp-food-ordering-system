import { useEffect, useMemo, useRef, useState } from 'react'
import { Loader2, Lock, Phone, ShieldCheck, User, X } from 'lucide-react'
import {
  CustomerSession,
  errorMessage,
  formatGhanaPhone,
  saveCustomerSession,
} from '@/lib/customerAuth'

type Mode = 'signup' | 'verify' | 'login'

interface CustomerAuthSheetProps {
  open: boolean
  onClose: () => void
  onAuthenticated: (session: CustomerSession) => void
}

const RESEND_SECONDS = 60

export default function CustomerAuthSheet({
  open,
  onClose,
  onAuthenticated,
}: CustomerAuthSheetProps) {
  const [mode, setMode] = useState<Mode>('login')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [cooldown, setCooldown] = useState(0)

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const pendingPhone = useRef('')

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    if (!open) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [open])

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = window.setInterval(() => setCooldown(v => Math.max(0, v - 1)), 1000)
    return () => window.clearInterval(timer)
  }, [cooldown])

  const title = useMemo(() => {
    if (mode === 'signup') return 'Create your account'
    if (mode === 'verify') return 'Verify your phone'
    return 'Welcome back'
  }, [mode])

  const reset = (next: Mode) => {
    setMode(next)
    setError('')
    setNotice('')
  }

  const handleSignup = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${apiUrl}/auth/customer/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          password,
          password_confirmation: passwordConfirmation,
          phone,
        }),
      })
      if (!res.ok) throw new Error(await errorMessage(res, 'Could not create your account'))
      const data = await res.json()
      pendingPhone.current = phone
      setCooldown(RESEND_SECONDS)
      reset('verify')
      setNotice(data.message || 'We sent a 6-digit code to your phone.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${apiUrl}/auth/customer/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: pendingPhone.current || phone, code }),
      })
      if (!res.ok) throw new Error(await errorMessage(res, 'That code did not work'))
      const session: CustomerSession = await res.json()
      saveCustomerSession(session)
      onAuthenticated(session)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  const handleResend = async () => {
    if (cooldown > 0) return
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${apiUrl}/auth/customer/resend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: pendingPhone.current || phone }),
      })
      if (!res.ok) throw new Error(await errorMessage(res, 'Could not resend the code'))
      setCooldown(RESEND_SECONDS)
      setNotice('We sent a new code.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${apiUrl}/auth/customer/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone }),
      })
      if (!res.ok) throw new Error(await errorMessage(res, 'Could not sign you in'))
      const data = await res.json()
      pendingPhone.current = phone
      setCooldown(RESEND_SECONDS)
      reset('verify')
      setNotice(data.message || 'We sent a 6-digit sign-in code to your phone.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  const submit = () => {
    if (loading) return
    if (mode === 'signup') return handleSignup()
    if (mode === 'verify') return handleVerify()
    return handleLogin()
  }

  const canSubmit =
    mode === 'signup'
      ? username.trim().length >= 3 &&
        password.length >= 8 &&
        passwordConfirmation.length >= 8 &&
        phone.trim().length >= 9
      : mode === 'verify'
      ? code.trim().length >= 4
      : phone.trim().length >= 9

  if (!open) return null

  const fieldClass =
    'w-full rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-sm text-white placeholder-white/40 outline-none transition focus:border-[#f7b32b] focus:ring-1 focus:ring-[#f7b32b]'
  const labelClass =
    'mb-1.5 block text-xs font-bold uppercase tracking-wider text-white/70'

  return (
    <>
      <button
        type="button"
        aria-label="Close sign in"
        onClick={onClose}
        className="fixed inset-0 z-[90] bg-black/70 backdrop-blur-sm"
      />
      <section
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="fixed inset-x-0 bottom-0 z-[91] mx-auto max-h-[92svh] w-full max-w-md overflow-y-auto rounded-t-[28px] border-t border-white/10 bg-[#161616] text-white shadow-2xl sm:bottom-auto sm:top-1/2 sm:-translate-y-1/2 sm:rounded-[28px]"
      >
        <div className="flex items-start justify-between gap-4 border-b border-white/10 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#f7b32b] text-[#1a0a00]">
              {mode === 'verify' ? <ShieldCheck size={18} /> : <User size={18} />}
            </span>
            <div>
              <h2 className="text-base font-black leading-tight">{title}</h2>
              <p className="text-xs text-white/70">
                {mode === 'verify'
                  ? `Code sent to ${formatGhanaPhone(pendingPhone.current || phone)}`
                  : mode === 'login'
                  ? 'Sign in with the number that gets your order updates'
                  : 'Your number receives order updates by SMS'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-white/10 text-white/80 transition hover:bg-white/20"
          >
            <X size={16} strokeWidth={2.5} />
          </button>
        </div>

        <form
          className="space-y-4 px-5 py-5"
          onSubmit={event => {
            event.preventDefault()
            submit()
          }}
        >
          {mode === 'signup' && (
            <>
              <div>
                <label className={labelClass} htmlFor="cust-username">
                  Username
                </label>
                <input
                  id="cust-username"
                  autoComplete="username"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder="e.g. kofi.mensah"
                  className={fieldClass}
                />
              </div>
              <div>
                <label className={labelClass} htmlFor="cust-password">
                  Password
                </label>
                <div className="relative">
                  <Lock
                    size={14}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/40"
                  />
                  <input
                    id="cust-password"
                    type="password"
                    autoComplete="new-password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    className={`${fieldClass} pl-9`}
                  />
                </div>
              </div>
              <div>
                <label className={labelClass} htmlFor="cust-password2">
                  Confirm password
                </label>
                <input
                  id="cust-password2"
                  type="password"
                  autoComplete="new-password"
                  value={passwordConfirmation}
                  onChange={e => setPasswordConfirmation(e.target.value)}
                  placeholder="Repeat your password"
                  className={fieldClass}
                />
              </div>
            </>
          )}

          {mode !== 'verify' && (
            <div>
              <label className={labelClass} htmlFor="cust-phone">
                Phone number
              </label>
              <div className="relative">
                <Phone
                  size={14}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/40"
                />
                <input
                  id="cust-phone"
                  type="tel"
                  autoComplete="tel"
                  value={phone}
                  onChange={e => setPhone(e.target.value)}
                  placeholder="e.g. 0244123456"
                  className={`${fieldClass} pl-9`}
                />
              </div>
              <p className="mt-1.5 text-xs text-white/60">
                {mode === 'signup'
                  ? 'We text a 6-digit code here to confirm it is yours.'
                  : 'We text a 6-digit code here — no password to remember.'}
              </p>
            </div>
          )}

          {mode === 'verify' && (
            <div>
              <label className={labelClass} htmlFor="cust-code">
                6-digit code
              </label>
              <input
                id="cust-code"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                value={code}
                onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
                placeholder="••••••"
                className={`${fieldClass} text-center text-2xl font-black tracking-[0.5em]`}
              />
              <button
                type="button"
                onClick={handleResend}
                disabled={cooldown > 0 || loading}
                className="mt-3 text-xs font-bold text-[#f7b32b] transition disabled:text-white/40"
              >
                {cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend code'}
              </button>
            </div>
          )}

          {notice && !error && (
            <p className="rounded-xl bg-[#f7b32b]/10 px-3 py-2.5 text-xs text-[#f7b32b]">
              {notice}
            </p>
          )}
          {error && (
            <p
              role="alert"
              className="rounded-xl bg-red-500/10 px-3 py-2.5 text-xs text-red-300"
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={!canSubmit || loading}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#f7b32b] py-3.5 text-sm font-black text-[#1a0a00] transition hover:bg-[#ffc852] disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading && <Loader2 size={16} className="animate-spin" />}
            {mode === 'signup'
              ? 'Send verification code'
              : mode === 'verify'
              ? 'Verify and continue'
              : 'Text me a sign-in code'}
          </button>

          {mode !== 'verify' && (
            <p className="text-center text-xs text-white/70">
              {mode === 'signup' ? 'Already have an account?' : 'New here?'}{' '}
              <button
                type="button"
                onClick={() => reset(mode === 'signup' ? 'login' : 'signup')}
                className="font-bold text-[#f7b32b]"
              >
                {mode === 'signup' ? 'Sign in' : 'Create one'}
              </button>
            </p>
          )}
        </form>
      </section>
    </>
  )
}
