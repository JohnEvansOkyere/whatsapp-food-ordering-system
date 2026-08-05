import { useEffect, useMemo, useState } from 'react'
import Head from 'next/head'
import Link from 'next/link'
import { ArrowLeft, RefreshCw, Search, ShoppingBag, Store } from 'lucide-react'
import { Branch, FALLBACK_BRANCHES } from '@/lib/branches'
import { RESTAURANT } from '@/lib/menuData'
import { clearStaffSession, getStaffSession, staffFetch, type StaffSession } from '@/lib/staffAuth'

interface MenuAvailabilityItem {
  id: string
  name: string
  category: string
  sold_out: boolean
  active: boolean
}

function restaurantInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part[0]?.toUpperCase() || '')
    .join('')
}

export default function DashboardSettingsPage() {
  const [session, setSession] = useState<StaffSession | null>(null)
  const [menuItems, setMenuItems] = useState<MenuAvailabilityItem[]>([])
  const [operationalBranches, setOperationalBranches] = useState<Branch[]>([])
  const [selectedBranchId, setSelectedBranchId] = useState('')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [branchBusy, setBranchBusy] = useState(false)
  const [menuBusyId, setMenuBusyId] = useState('')
  const [error, setError] = useState('')

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const staffRole = session?.staff.role || ''
  const canManageBranch = ['tenant_owner', 'manager'].includes(staffRole)
  const canManageMenu = ['tenant_owner', 'manager', 'kitchen'].includes(staffRole)
  const branchSource = operationalBranches.length > 0
    ? operationalBranches
    : FALLBACK_BRANCHES
  const staffBranches = branchSource.filter(branch =>
    session?.staff.branch_ids.includes(branch.id)
  )
  const selectedBranch = staffBranches.find(branch => branch.id === selectedBranchId)

  const loadStaffBranches = async () => {
    try {
      const response = await staffFetch(`${apiUrl}/admin/branches`)
      if (!response.ok) throw new Error('Failed to load staff branches')
      const data = await response.json()
      if (Array.isArray(data.items) && data.items.length > 0) {
        setOperationalBranches(data.items)
        setSelectedBranchId(current =>
          data.items.some((branch: Branch) => branch.id === current)
            ? current
            : data.items[0].id
        )
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load staff branches')
    }
  }

  const loadMenuAvailability = async () => {
    if (!selectedBranchId) return
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams({ branch_id: selectedBranchId })
      const response = await staffFetch(`${apiUrl}/admin/menu?${params.toString()}`)
      if (!response.ok) throw new Error('Failed to load menu availability')
      const data = await response.json()
      const items = Array.isArray(data.items) ? data.items : []
      setMenuItems(
        items
          .filter((item: { active?: boolean }) => item.active !== false)
          .map((item: { id: string; name: string; category?: string; sold_out?: boolean; active?: boolean }) => ({
            id: item.id,
            name: item.name,
            category: item.category || 'other',
            sold_out: Boolean(item.sold_out),
            active: item.active !== false,
          }))
      )
    } catch (err) {
      setMenuItems([])
      setError(err instanceof Error ? err.message : 'Failed to load menu availability')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const currentSession = getStaffSession()
    if (!currentSession) {
      window.location.assign('/admin/login')
      return
    }
    setSession(currentSession)
    setSelectedBranchId(currentSession.staff.branch_ids[0] || '')
    void loadStaffBranches()
  }, [])

  useEffect(() => {
    void loadMenuAvailability()
  }, [selectedBranchId])

  const filteredMenuItems = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return menuItems
    return menuItems.filter(item =>
      `${item.name} ${item.category}`.toLowerCase().includes(query)
    )
  }, [menuItems, search])

  const availabilitySummary = useMemo(() => ({
    available: menuItems.filter(item => !item.sold_out).length,
    soldOut: menuItems.filter(item => item.sold_out).length,
  }), [menuItems])

  const toggleBranchOrdering = async () => {
    if (!selectedBranch) return
    setBranchBusy(true)
    setError('')
    try {
      const response = await staffFetch(`${apiUrl}/admin/branches/${selectedBranch.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accepting_orders: !selectedBranch.accepting_orders }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail || 'Failed to update branch ordering')
      setOperationalBranches(current =>
        current.map(branch => branch.id === data.id ? data : branch)
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update branch ordering')
    } finally {
      setBranchBusy(false)
    }
  }

  const toggleSoldOut = async (item: MenuAvailabilityItem) => {
    if (!selectedBranchId) return
    setMenuBusyId(item.id)
    setError('')
    try {
      const params = new URLSearchParams({ branch_id: selectedBranchId })
      const response = await staffFetch(`${apiUrl}/admin/menu/${item.id}?${params.toString()}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sold_out: !item.sold_out }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail || 'Failed to update menu availability')
      setMenuItems(current =>
        current.map(entry =>
          entry.id === item.id ? { ...entry, sold_out: Boolean(data.sold_out) } : entry
        )
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update menu availability')
    } finally {
      setMenuBusyId('')
    }
  }

  return (
    <>
      <Head>
        <title>{`Menu & Settings | ${RESTAURANT.name}`}</title>
        <meta name="description" content="Branch ordering and menu availability controls." />
      </Head>

      <div className="min-h-screen bg-[#f6f5f2] text-[#1f1f1f]">
        <header className="sticky top-0 z-30 border-b border-black/[0.07] bg-white/95 backdrop-blur">
          <div className="mx-auto flex h-16 max-w-[1400px] items-center gap-3 px-4 md:px-6">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#1d1109] text-xs font-black text-[#f7b32b]">
                {restaurantInitials(RESTAURANT.name)}
              </div>
              <div className="hidden min-w-0 sm:block">
                <p className="truncate text-sm font-black">{RESTAURANT.name}</p>
                <p className="text-xs text-black/45">Order desk</p>
              </div>
            </div>

            <nav className="ml-4 hidden items-center gap-1 md:flex" aria-label="Dashboard navigation">
              <Link href="/dashboard" className="rounded-lg px-3 py-2 text-sm font-semibold text-black/55 hover:bg-black/[0.04] hover:text-black">
                Orders
              </Link>
              <span className="rounded-lg bg-[#f4eee7] px-3 py-2 text-sm font-bold text-[#6b3b1e]">
                Menu & settings
              </span>
              <Link href="/" className="rounded-lg px-3 py-2 text-sm font-semibold text-black/55 hover:bg-black/[0.04] hover:text-black">
                Customer menu
              </Link>
            </nav>

            <div className="ml-auto flex items-center gap-2">
              {staffBranches.length > 1 ? (
                <select
                  aria-label="Select branch"
                  value={selectedBranchId}
                  onChange={event => setSelectedBranchId(event.target.value)}
                  className="max-w-[120px] rounded-xl border border-black/10 bg-white px-3 py-2 text-sm font-bold outline-none focus:border-[#c56a2d] sm:max-w-none"
                >
                  {staffBranches.map(branch => (
                    <option key={branch.id} value={branch.id}>{branch.name}</option>
                  ))}
                </select>
              ) : (
                <span className="hidden text-sm font-semibold text-black/55 lg:inline">
                  {selectedBranch?.name || 'Assigned branch'}
                </span>
              )}
              <button
                type="button"
                onClick={() => {
                  clearStaffSession()
                  window.location.assign('/admin/login')
                }}
                className="rounded-xl border border-black/10 px-3 py-2 text-sm font-bold text-black/55 hover:text-black"
              >
                Sign out
              </button>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-[1400px] px-4 py-6 md:px-6 md:py-8">
          <Link href="/dashboard" className="inline-flex items-center gap-2 text-sm font-bold text-black/50 hover:text-black">
            <ArrowLeft size={16} /> Back to orders
          </Link>

          <div className="mt-5 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm font-bold text-[#b15c25]">Restaurant controls</p>
              <h1 className="mt-1 text-3xl font-black tracking-tight md:text-4xl">Menu & settings</h1>
              <p className="mt-2 text-sm text-black/50">Manage ordering and item availability for the selected branch.</p>
            </div>
            <Link href="/" className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-black/10 bg-white px-4 text-sm font-black hover:border-black/25">
              <ShoppingBag size={16} /> View customer menu
            </Link>
          </div>

          {error && (
            <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-900">
              {error}
            </div>
          )}

          <div className="mt-7 grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
            <section className="rounded-2xl border border-black/[0.08] bg-white shadow-sm">
              <div className="flex flex-col gap-4 border-b border-black/[0.07] p-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.14em] text-black/40">Menu availability</p>
                  <h2 className="mt-1 text-xl font-black">Items</h2>
                  <p className="mt-1 text-sm text-black/45">{availabilitySummary.available} available · {availabilitySummary.soldOut} sold out</p>
                </div>
                <div className="flex gap-2">
                  <label className="relative min-w-0 flex-1 sm:w-64">
                    <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-black/35" />
                    <input
                      value={search}
                      onChange={event => setSearch(event.target.value)}
                      placeholder="Search menu"
                      className="h-11 w-full rounded-xl border border-black/10 pl-10 pr-3 text-sm outline-none focus:border-[#c56a2d]"
                    />
                  </label>
                  <button
                    type="button"
                    aria-label="Refresh menu"
                    onClick={() => void loadMenuAvailability()}
                    className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-black/10 text-black/50 hover:text-black"
                  >
                    <RefreshCw size={17} className={loading ? 'animate-spin' : ''} />
                  </button>
                </div>
              </div>

              <div className="divide-y divide-black/[0.06]">
                {loading && menuItems.length === 0 ? (
                  <p className="px-5 py-14 text-center text-sm text-black/40">Loading menu…</p>
                ) : filteredMenuItems.length === 0 ? (
                  <p className="px-5 py-14 text-center text-sm text-black/40">No menu items match your search.</p>
                ) : filteredMenuItems.map(item => (
                  <div key={item.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center">
                    <div className="min-w-0 flex-1">
                      <p className="font-bold">{item.name}</p>
                      <p className="mt-1 text-xs font-bold uppercase tracking-[0.1em] text-black/35">{item.category}</p>
                    </div>
                    <span className={`self-start rounded-lg px-2.5 py-1.5 text-xs font-black sm:self-auto ${item.sold_out ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'}`}>
                      {item.sold_out ? 'Sold out' : 'Available'}
                    </span>
                    <button
                      type="button"
                      onClick={() => void toggleSoldOut(item)}
                      disabled={!canManageMenu || menuBusyId === item.id}
                      className={`min-w-28 rounded-xl px-3 py-2.5 text-xs font-black ${item.sold_out ? 'bg-emerald-600 text-white' : 'border border-red-200 bg-white text-red-700'} disabled:opacity-50`}
                    >
                      {!canManageMenu ? 'View only' : menuBusyId === item.id ? 'Saving…' : item.sold_out ? 'Restock' : 'Mark sold out'}
                    </button>
                  </div>
                ))}
              </div>
            </section>

            <aside className="order-first lg:order-last">
              <section className="rounded-2xl border border-black/[0.08] bg-white p-5 shadow-sm lg:sticky lg:top-24">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-black/40"><Store size={14} /> Ordering status</p>
                    <h2 className="mt-3 text-xl font-black">{selectedBranch?.accepting_orders ? 'Accepting orders' : 'Orders paused'}</h2>
                    <p className="mt-1 text-sm text-black/45">{selectedBranch?.hours_label || 'Provisional hours'}</p>
                  </div>
                  <span className={`mt-1 h-3 w-3 rounded-full ${selectedBranch?.accepting_orders ? 'bg-emerald-500' : 'bg-red-500'}`} />
                </div>
                <button
                  type="button"
                  disabled={!canManageBranch || branchBusy || !selectedBranch}
                  onClick={() => void toggleBranchOrdering()}
                  className={`mt-5 w-full rounded-xl px-4 py-3 text-sm font-black ${selectedBranch?.accepting_orders ? 'border border-red-200 bg-white text-red-700' : 'bg-emerald-600 text-white'} disabled:opacity-50`}
                >
                  {!canManageBranch ? 'View only' : branchBusy ? 'Saving…' : selectedBranch?.accepting_orders ? 'Pause new orders' : 'Resume new orders'}
                </button>
                <p className="mt-3 text-xs leading-5 text-black/40">This affects only {selectedBranch?.name || 'the selected branch'}.</p>
              </section>
            </aside>
          </div>
        </main>
      </div>
    </>
  )
}
