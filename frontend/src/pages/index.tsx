import { useEffect, useMemo, useRef, useState } from 'react'
import Head from 'next/head'
import Image from 'next/image'
import {
  ChevronDown,
  MapPin,
  Search,
  ShoppingCart,
  WifiOff,
  Utensils,
  Plus,
  Minus,
} from 'lucide-react'
import BranchPicker from '@/components/BranchPicker'
import CartSidebar from '@/components/CartSidebar'
import StoreHero from '@/components/StoreHero'
import ProductSheet from '@/components/ProductSheet'
import { useCart } from '@/hooks/useCart'
import { CATEGORIES, MENU_ITEMS, MenuItem, RESTAURANT } from '@/lib/menuData'
import { Branch, FALLBACK_BRANCHES } from '@/lib/branches'
import { trackEvent } from '@/lib/analytics'

interface ApiMenuItem {
  id: string
  name: string
  description: string
  price: number
  image_url?: string | null
  category: string
  popular?: boolean
  spicy?: boolean
  sold_out?: boolean
  option_groups?: Array<{
    id: string
    name: string
    type: 'single' | 'multiple'
    max_selections?: number
    options: Array<{ id: string; name: string; price: number }>
  }>
}

const FALLBACK_MENU_BY_ID = new Map(MENU_ITEMS.map(item => [item.id, item]))

function toUiMenuItem(item: ApiMenuItem): MenuItem {
  const fallback = FALLBACK_MENU_BY_ID.get(item.id)
  return {
    id: item.id,
    name: item.name,
    description: item.description,
    price: Number(item.price),
    image: fallback?.image || item.image_url || '',
    category: item.category,
    popular: item.popular ?? fallback?.popular,
    spicy: item.spicy ?? fallback?.spicy,
    soldOut: Boolean(item.sold_out),
    optionGroups:
      fallback?.optionGroups ||
      item.option_groups?.map(group => ({
        id: group.id,
        name: group.name,
        type: group.type,
        maxSelections: group.max_selections,
        options: group.options,
      })),
  }
}

// ── Horizontal menu item card (Pizzaman-style) ─────────────────────────────
function MenuItemRow({
  item,
  quantity,
  onAdd,
  onRemove,
  onView,
}: {
  item: MenuItem
  quantity: number
  onAdd: () => void
  onRemove: () => void
  onView: () => void
}) {
  return (
    <article
      onClick={() => !item.soldOut && onView()}
      className="menu-item-row group relative flex cursor-pointer items-center gap-4 rounded-2xl bg-[#1e1e1e] p-3 transition-all duration-200 hover:bg-[#262626]"
    >
      {/* Image */}
      <div className="relative h-[78px] w-[78px] flex-shrink-0 overflow-hidden rounded-xl bg-[#2a2a2a]">
        <Image
          src={item.image}
          alt={item.name}
          fill
          className={`object-cover transition-transform duration-500 group-hover:scale-105 ${item.soldOut ? 'opacity-40 grayscale' : ''}`}
          sizes="78px"
        />
        {item.soldOut && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="rounded-full bg-black/70 px-2 py-0.5 text-[9px] font-black text-white/70">
              SOLD OUT
            </span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="min-w-0 flex-1">
        <div className="flex items-start gap-1.5">
          <h3 className="flex-1 truncate text-sm font-bold leading-tight text-white">
            {item.name}
          </h3>
          {item.popular && (
            <span className="flex-shrink-0 rounded-full bg-[#e63946]/15 px-1.5 py-0.5 text-[9px] font-black text-[#e63946]">
              ⭐ POPULAR
            </span>
          )}
          {item.spicy && !item.popular && (
            <span className="flex items-center gap-0.5 flex-shrink-0 rounded-full bg-orange-500/15 px-1.5 py-0.5 text-[9px] font-black text-orange-400">
              🌶 SPICY
            </span>
          )}
        </div>
        <p className="mt-0.5 line-clamp-1 text-xs text-white/40">{item.description}</p>
        <p className="mt-1.5 text-sm font-black text-[#e63946]">
          GHS {item.price.toFixed(2)}
        </p>
      </div>

      {/* Add/Remove button */}
      <div className="flex-shrink-0" onClick={e => e.stopPropagation()}>
        {quantity === 0 ? (
          <button
            onClick={onAdd}
            disabled={item.soldOut}
            aria-label={`Add ${item.name}`}
            className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-[#e63946] text-[#e63946] transition-all hover:bg-[#e63946] hover:text-white active:scale-90 disabled:cursor-not-allowed disabled:opacity-30"
          >
            <Plus size={18} strokeWidth={2.5} />
          </button>
        ) : (
          <div className="flex items-center gap-1.5 rounded-full bg-[#e63946] px-2 py-1.5">
            <button
              onClick={onRemove}
              className="text-white transition active:scale-90"
            >
              <Minus size={13} strokeWidth={3} />
            </button>
            <span className="w-5 text-center text-sm font-black text-white">{quantity}</span>
            <button
              onClick={onAdd}
              className="text-white transition active:scale-90"
            >
              <Plus size={13} strokeWidth={3} />
            </button>
          </div>
        )}
      </div>
    </article>
  )
}

export default function MenuPage() {
  const [activeCategory, setActiveCategory] = useState('all')
  const [menuItems, setMenuItems] = useState<MenuItem[]>(MENU_ITEMS)
  const [branches, setBranches] = useState<Branch[]>(FALLBACK_BRANCHES)
  const [selectedBranch, setSelectedBranch] = useState<Branch | null>(null)
  const [branchPickerOpen, setBranchPickerOpen] = useState(true)
  const [loadingBranches, setLoadingBranches] = useState(true)
  const [loadingMenu, setLoadingMenu] = useState(false)
  const [search, setSearch] = useState('')
  const [selectedProduct, setSelectedProduct] = useState<MenuItem | null>(null)
  const [online, setOnline] = useState(true)
  const categoryRefs = useRef<Record<string, HTMLDivElement | null>>({})
  const cart = useCart()
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    setOnline(window.navigator.onLine)
    const handleOnline = () => setOnline(true)
    const handleOffline = () => setOnline(false)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    async function loadBranches() {
      let nextBranches = FALLBACK_BRANCHES
      try {
        const res = await fetch(`${apiUrl}/public/branches`)
        if (!res.ok) throw new Error(`Branch request failed with ${res.status}`)
        const data = await res.json()
        if (Array.isArray(data.items) && data.items.length > 0) nextBranches = data.items
      } catch (error) {
        console.error('Failed to load branches; using launch fallback.', error)
      }
      if (cancelled) return
      setBranches(nextBranches)
      const params = new URLSearchParams(window.location.search)
      const requestedBranch = params.get('branch')
      const storedBranch = window.localStorage.getItem('restaurant-branch-v1')
      const remembered = requestedBranch || storedBranch
      const match = remembered
        ? nextBranches.find(branch =>
            [branch.id, branch.slug, branch.code]
              .map(value => value.toLowerCase())
              .includes(remembered.toLowerCase())
          )
        : null
      if (match?.accepting_orders) {
        setSelectedBranch(match)
        setBranchPickerOpen(false)
      }
      setLoadingBranches(false)
    }
    void loadBranches()
    return () => { cancelled = true }
  }, [apiUrl])

  useEffect(() => {
    if (!selectedBranch) return
    const activeBranch = selectedBranch
    let cancelled = false
    setLoadingMenu(true)
    async function loadMenu() {
      try {
        const params = new URLSearchParams({ branch_id: activeBranch.id })
        const res = await fetch(`${apiUrl}/public/menu?${params.toString()}`)
        if (!res.ok) throw new Error(`Menu request failed with status ${res.status}`)
        const data = await res.json()
        if (!Array.isArray(data.items)) throw new Error('Menu payload is invalid')
        const nextItems = data.items
          .map((item: ApiMenuItem) => toUiMenuItem(item))
          .filter((item: MenuItem) => item.image)
        if (!cancelled && nextItems.length > 0) setMenuItems(nextItems)
      } catch (error) {
        console.error('Failed to load branch menu; using local menu.', error)
        if (!cancelled) setMenuItems(MENU_ITEMS)
      } finally {
        if (!cancelled) setLoadingMenu(false)
      }
    }
    void loadMenu()
    return () => { cancelled = true }
  }, [apiUrl, selectedBranch])

  const chooseBranch = (branch: Branch) => {
    if (
      selectedBranch &&
      selectedBranch.id !== branch.id &&
      cart.totalItems > 0 &&
      !window.confirm('Changing branch will clear your current cart. Continue?')
    ) return
    if (selectedBranch?.id !== branch.id && cart.totalItems > 0) cart.clearCart()
    setSelectedBranch(branch)
    setBranchPickerOpen(false)
    setActiveCategory('all')
    window.localStorage.setItem('restaurant-branch-v1', branch.slug)
    const url = new URL(window.location.href)
    url.searchParams.set('branch', branch.slug)
    window.history.replaceState({}, '', url)
    trackEvent(apiUrl, 'branch_selected', branch.id, { branch: branch.slug })
  }

  const quickAdd = (item: MenuItem) => {
    if (item.soldOut) return
    if (item.optionGroups?.length) {
      setSelectedProduct(item)
      return
    }
    cart.addItem(item)
    trackEvent(apiUrl, 'menu_item_added', selectedBranch?.id, { item_id: item.id })
  }

  const filteredItems = useMemo(() => {
    const query = search.trim().toLowerCase()
    return menuItems.filter(item => {
      const matchesCategory = activeCategory === 'all' || item.category === activeCategory
      const matchesSearch =
        !query ||
        `${item.name} ${item.description} ${item.category}`.toLowerCase().includes(query)
      return matchesCategory && matchesSearch
    })
  }, [activeCategory, menuItems, search])

  const groupedItems = useMemo(() => {
    const groups: Record<string, MenuItem[]> = {}
    filteredItems.forEach(item => {
      if (!groups[item.category]) groups[item.category] = []
      groups[item.category].push(item)
    })
    return groups
  }, [filteredItems])

  const categoryLabels: Record<string, string> = {
    rice: 'Rice Dishes',
    chicken: 'Chicken',
    pizza: 'Pizza',
    sides: 'Sides',
    drinks: 'Cold Drinks',
  }

  const scrollToCategory = (catId: string) => {
    setActiveCategory(catId)
    if (catId === 'all') {
      window.scrollTo({ top: 0, behavior: 'smooth' })
      return
    }
    setTimeout(() => {
      categoryRefs.current[catId]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 50)
  }

  // Popular items for the promo banner highlight
  const popularItem = menuItems.find(item => item.popular && !item.soldOut)

  return (
    <>
      <Head>
        <title>{`${RESTAURANT.name} — Order fresh food online`}</title>
        <meta name="description" content={RESTAURANT.tagline} />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
      </Head>

      {branchPickerOpen && (
        <BranchPicker
          branches={branches}
          loading={loadingBranches}
          onSelect={chooseBranch}
        />
      )}

      {selectedBranch && (
        <div className="min-h-screen bg-[#111111] text-white">

          {/* ── OFFLINE BANNER ── */}
          {!online && (
            <div className="sticky top-0 z-[65] flex items-center justify-center gap-2 bg-amber-500 px-4 py-2 text-center text-xs font-black text-black">
              <WifiOff size={14} />
              You are offline. Your cart is safe, but checkout needs a connection.
            </div>
          )}

          {/* ── CINEMATIC HERO ── */}
          <StoreHero
            branch={selectedBranch}
            onBrowse={() => {
              document.getElementById('menu-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }}
          />

          {/* ── TOP NAVBAR (sticky, appears after scrolling past hero) ── */}
          <header id="menu-section" className="sticky top-0 z-50 bg-[#111111]/95 backdrop-blur-xl border-b border-white/5">
            <div className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
              {/* Logo */}
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-[#e63946] shadow-lg shadow-red-500/20">
                  <Utensils size={18} className="text-white" />
                </div>
                <div>
                  <p className="text-base font-black leading-none text-white" style={{ fontFamily: 'var(--font-display)' }}>
                    {RESTAURANT.name}
                  </p>
                  <button
                    onClick={() => setBranchPickerOpen(true)}
                    className="mt-0.5 flex items-center gap-1 text-xs font-semibold text-white/45 transition hover:text-[#e63946]"
                  >
                    <MapPin size={10} />
                    <span>{selectedBranch.name}</span>
                    <ChevronDown size={10} />
                  </button>
                </div>
              </div>

              {/* Search — center */}
              <div className="relative hidden max-w-xs flex-1 sm:block">
                <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
                <input
                  type="search"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Search the menu…"
                  className="w-full rounded-full border border-white/10 bg-white/5 py-2 pl-9 pr-4 text-sm text-white placeholder-white/30 outline-none transition focus:border-[#e63946]/50 focus:ring-1 focus:ring-[#e63946]/30"
                />
              </div>

              {/* Cart count (mobile only) */}
              <button
                onClick={() => {}}
                className="relative flex items-center gap-2 rounded-full bg-[#e63946] px-4 py-2.5 text-sm font-black text-white shadow-lg shadow-red-500/20 transition hover:bg-red-600 active:scale-95 sm:hidden"
              >
                <ShoppingCart size={16} />
                <span>Cart</span>
                {cart.totalItems > 0 && (
                  <span className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-white text-xs font-black text-[#e63946]">
                    {cart.totalItems}
                  </span>
                )}
              </button>

              {/* Status badge */}
              <div className="hidden items-center gap-1.5 sm:flex">
                <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
                <span className="text-xs font-semibold text-white/40">
                  {selectedBranch.accepting_orders ? 'Open now' : 'Closed'}
                </span>
              </div>
            </div>

            {/* ── CATEGORY TABS ── */}
            <div className="border-t border-white/5">
              <div className="category-nav mx-auto flex max-w-4xl gap-2 overflow-x-auto px-4 py-2.5 sm:px-6">
                {CATEGORIES.map(cat => (
                  <button
                    key={cat.id}
                    onClick={() => scrollToCategory(cat.id)}
                    className={`flex-shrink-0 flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-bold transition-all duration-200 ${
                      activeCategory === cat.id
                        ? 'bg-[#e63946] text-white shadow-lg shadow-red-500/20'
                        : 'border border-white/10 bg-white/5 text-white/60 hover:border-white/20 hover:text-white'
                    }`}
                  >
                    <span>{cat.emoji}</span>
                    <span>{cat.name}</span>
                  </button>
                ))}
              </div>
            </div>
          </header>

          {/* ── MAIN CONTENT (menu left + cart right) ── */}
          <div className="mx-auto flex max-w-4xl gap-6 px-4 pb-10 pt-5 sm:px-6">

            {/* ── LEFT: MENU CONTENT ── */}
            <main className="min-w-0 flex-1">

              {/* Mobile search */}
              <div className="mb-4 sm:hidden">
                <div className="relative">
                  <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
                  <input
                    type="search"
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    placeholder="Search the menu…"
                    className="w-full rounded-full border border-white/10 bg-white/5 py-2 pl-9 pr-4 text-sm text-white placeholder-white/30 outline-none transition focus:border-[#e63946]/50"
                  />
                </div>
              </div>

              {/* ── PROMO BANNER (only on 'All' view) ── */}
              {popularItem && activeCategory === 'all' && (
                <div className="mb-6 overflow-hidden rounded-2xl bg-gradient-to-r from-[#e63946] via-[#c1121f] to-[#9d0208] p-5 shadow-2xl shadow-red-500/20">
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex-1">
                      <p className="mb-1 text-xs font-black uppercase tracking-widest text-white/70">
                        🔥 Most loved right now
                      </p>
                      <h2 className="text-xl font-black leading-tight text-white sm:text-2xl" style={{ fontFamily: 'var(--font-display)' }}>
                        {popularItem.name}
                      </h2>
                      <p className="mt-1 line-clamp-2 text-xs text-white/60">
                        {popularItem.description}
                      </p>
                      <div className="mt-3 flex items-center gap-3">
                        <span className="text-xl font-black text-white">
                          GHS {popularItem.price.toFixed(2)}
                        </span>
                        <button
                          onClick={() => quickAdd(popularItem)}
                          className="rounded-full bg-white px-4 py-1.5 text-xs font-black text-[#e63946] transition hover:bg-white/90 active:scale-95"
                        >
                          Order Now
                        </button>
                      </div>
                    </div>
                    <div className="relative h-28 w-28 flex-shrink-0 overflow-hidden rounded-2xl shadow-xl sm:h-32 sm:w-32">
                      <Image
                        src={popularItem.image}
                        alt={popularItem.name}
                        fill
                        className="object-cover"
                        sizes="128px"
                        priority
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* ── LOADING ── */}
              {loadingMenu && (
                <div className="mb-4 flex items-center gap-2 text-xs font-bold text-white/30">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#e63946]" />
                  Refreshing {selectedBranch.name} menu…
                </div>
              )}

              {/* ── MENU SECTIONS ── */}
              {filteredItems.length === 0 ? (
                <div className="py-20 text-center">
                  <div className="mb-3 text-4xl">🍽️</div>
                  <p className="font-bold text-white/30">Nothing available here yet</p>
                </div>
              ) : (
                Object.entries(groupedItems).map(([category, items]) => (
                  <section
                    key={category}
                    className="mb-8"
                    ref={el => { categoryRefs.current[category] = el }}
                  >
                    {/* Section Header */}
                    <div className="mb-3 flex items-center gap-3">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">
                          {CATEGORIES.find(c => c.id === category)?.emoji || '🍽️'}
                        </span>
                        <h2 className="text-base font-black text-white">
                          {categoryLabels[category] || category}
                        </h2>
                      </div>
                      <div className="h-px flex-1 bg-white/5" />
                      <span className="text-xs font-semibold text-white/25">
                        {items.length} item{items.length !== 1 ? 's' : ''}
                      </span>
                    </div>

                    {/* Items grid — 2 columns on larger screens */}
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      {items.map(item => (
                        <MenuItemRow
                          key={item.id}
                          item={item}
                          quantity={cart.getQuantity(item.id)}
                          onAdd={() => quickAdd(item)}
                          onRemove={() => cart.removeOneByItemId(item.id)}
                          onView={() => setSelectedProduct(item)}
                        />
                      ))}
                    </div>
                  </section>
                ))
              )}

              {/* Footer */}
              <footer className="mt-10 border-t border-white/5 pt-6 text-center">
                <p className="text-xs text-white/20">
                  {RESTAURANT.name} · Fresh food. Clear tracking. Better ordering.
                </p>
              </footer>
            </main>

            {/* ── RIGHT: CART SIDEBAR (desktop only) ── */}
            <aside className="hidden w-[320px] flex-shrink-0 lg:block xl:w-[340px]">
              <div className="sticky top-[108px] overflow-hidden rounded-2xl border border-white/[0.07] bg-[#161616] shadow-2xl shadow-black/50" style={{ maxHeight: 'calc(100vh - 116px)' }}>
                <CartSidebar
                  items={cart.items}
                  totalItems={cart.totalItems}
                  totalPrice={cart.totalPrice}
                  onAdd={cart.addItem}
                  onRemove={cart.removeItem}
                  onClear={cart.clearCart}
                  branch={selectedBranch}
                />
              </div>
            </aside>
          </div>

          {/* ── MOBILE FLOATING CART BUTTON ── */}
          {cart.totalItems > 0 && (
            <div className="fixed bottom-5 left-4 right-4 z-40 lg:hidden">
              <button
                onClick={() => setSelectedProduct(null)}
                className="flex w-full items-center justify-between rounded-2xl bg-[#e63946] px-5 py-4 shadow-2xl shadow-red-500/30 transition active:scale-[.98]"
              >
                <span className="flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white/20 text-xs font-black text-white">
                    {cart.totalItems}
                  </span>
                  <span className="text-sm font-black text-white">View Cart</span>
                </span>
                <span className="text-sm font-black text-white">
                  GHS {(cart.totalPrice + Number(selectedBranch.delivery_fee || 0)).toFixed(2)}
                </span>
              </button>
            </div>
          )}

          {/* Product options sheet */}
          <ProductSheet
            item={selectedProduct}
            onClose={() => setSelectedProduct(null)}
            onAdd={cart.addConfiguredItem}
          />
        </div>
      )}
    </>
  )
}
