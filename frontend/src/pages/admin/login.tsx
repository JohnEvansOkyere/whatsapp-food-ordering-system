import { FormEvent, useEffect, useState } from 'react'
import Head from 'next/head'
import { useRouter } from 'next/router'
import { ChefHat, LockKeyhole, Store } from 'lucide-react'
import {
  getStaffSession,
  saveStaffSession,
  StaffSession,
} from '@/lib/staffAuth'
import { RESTAURANT } from '@/lib/menuData'

export default function StaffLoginPage() {
  const router = useRouter()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    if (getStaffSession()) {
      void router.replace('/dashboard')
    }
  }, [router])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${apiUrl}/auth/staff/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(data.detail || 'Sign-in failed')
      }
      saveStaffSession(data as StaffSession)
      await router.replace('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Head>
        <title>Staff sign in | {RESTAURANT.name}</title>
      </Head>
      <main className="grid min-h-screen place-items-center bg-[#1b0b04] px-4 py-10 text-white">
        <div className="w-full max-w-md rounded-[32px] border border-white/10 bg-white/[0.08] p-6 shadow-2xl backdrop-blur-xl sm:p-8">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#f7b32b] text-[#1b0b04]">
            <ChefHat size={27} />
          </span>
          <p className="mt-7 text-xs font-black uppercase tracking-[0.24em] text-[#f7b32b]">
            Protected staff area
          </p>
          <h1 className="mt-2 text-4xl font-black">Kitchen sign in</h1>
          <p className="mt-3 text-sm leading-6 text-white/55">
            Use the account assigned to your branch. Orders are automatically
            restricted to the branches in your staff profile.
          </p>

          <form onSubmit={submit} className="mt-7 space-y-4">
            <label className="block">
              <span className="mb-2 flex items-center gap-2 text-sm font-bold text-white/75">
                <Store size={15} />
                Username
              </span>
              <input
                value={username}
                onChange={event => setUsername(event.target.value)}
                autoComplete="username"
                required
                className="w-full rounded-2xl border border-white/10 bg-white/10 px-4 py-3.5 outline-none focus:border-[#f7b32b]"
              />
            </label>
            <label className="block">
              <span className="mb-2 flex items-center gap-2 text-sm font-bold text-white/75">
                <LockKeyhole size={15} />
                Password
              </span>
              <input
                type="password"
                value={password}
                onChange={event => setPassword(event.target.value)}
                autoComplete="current-password"
                required
                className="w-full rounded-2xl border border-white/10 bg-white/10 px-4 py-3.5 outline-none focus:border-[#f7b32b]"
              />
            </label>
            {error && (
              <p className="rounded-2xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-100">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-2xl bg-[#f7b32b] px-4 py-4 font-black text-[#1b0b04] disabled:opacity-50"
            >
              {loading ? 'Signing in…' : 'Open kitchen dashboard'}
            </button>
          </form>
          <p className="mt-5 text-xs leading-5 text-white/35">
            Provisional accounts are controlled by backend environment variables
            and must be replaced before the public launch.
          </p>
        </div>
      </main>
    </>
  )
}
