import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Head from 'next/head'
import { useRouter } from 'next/router'
import Link from 'next/link'
import {
  Check,
  ChefHat,
  CircleDot,
  Clock3,
  MapPin,
  MessageCircleMore,
  PackageCheck,
  Phone,
  RefreshCw,
  RotateCcw,
  ShoppingBag,
  Store,
  Star,
  Truck,
  Utensils,
} from 'lucide-react'
import { RESTAURANT } from '@/lib/menuData'
import { trackEvent } from '@/lib/analytics'

type OrderStatus =
  | 'new'
  | 'confirmed'
  | 'preparing'
  | 'ready'
  | 'out_for_delivery'
  | 'delayed'
  | 'delivered'
  | 'cancel_requested'
  | 'cancelled'
  | 'rejected'

interface TrackingItem {
  item_id: string
  name: string
  quantity: number
  unit_price: number
  total_price: number
  selections?: Array<{
    group_id: string
    option_id: string
    name?: string | null
    price?: number | null
  }>
}

interface TrackingEvent {
  event_type: string
  status?: OrderStatus | null
  status_label: string
  created_at: string
}

interface TrackingOrder {
  tracking_code: string
  order_number?: string | null
  status: OrderStatus
  status_label: string
  placed_at: string
  customer_name?: string | null
  branch_name?: string | null
  branch_slug?: string | null
  branch_phone?: string | null
  eta_min_minutes?: number | null
  eta_max_minutes?: number | null
  accepted_eta_minutes?: number | null
  items: TrackingItem[]
  subtotal_amount: number
  delivery_fee: number
  total_amount: number
  payment_status: string
  timeline: TrackingEvent[]
}

const PIPELINE: Array<{
  value: OrderStatus
  label: string
  detail: string
  icon: typeof CircleDot
}> = [
  {
    value: 'new',
    label: 'Order placed',
    detail: 'Your order reached the branch.',
    icon: CircleDot,
  },
  {
    value: 'confirmed',
    label: 'Accepted',
    detail: 'The kitchen confirmed your order.',
    icon: Check,
  },
  {
    value: 'preparing',
    label: 'Preparing',
    detail: 'Your food is being made fresh.',
    icon: ChefHat,
  },
  {
    value: 'ready',
    label: 'Ready',
    detail: 'Packed and ready for dispatch.',
    icon: PackageCheck,
  },
  {
    value: 'out_for_delivery',
    label: 'Out for delivery',
    detail: 'Your food is on the way.',
    icon: Truck,
  },
  {
    value: 'delivered',
    label: 'Delivered',
    detail: 'Your order has arrived.',
    icon: ShoppingBag,
  },
]

/** Nothing more will happen to these orders, so polling can stop. */
const TERMINAL_STATUSES = new Set<OrderStatus>([
  'delivered',
  'cancelled',
  'rejected',
])

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString('en-GH', {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function paymentLabel(status: string) {
  return status.replace(/_/g, ' ').replace(/\b\w/g, letter => letter.toUpperCase())
}

export default function TrackOrderPage() {
  const router = useRouter()
  const [order, setOrder] = useState<TrackingOrder | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [rating, setRating] = useState(0)
  const [ratingSent, setRatingSent] = useState(false)
  const [ratingError, setRatingError] = useState('')
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const token = typeof router.query.token === 'string' ? router.query.token : ''

  const loadOrder = useCallback(
    async (quiet = false) => {
      if (!token) return
      if (quiet) setRefreshing(true)
      else setLoading(true)

      try {
        const res = await fetch(
          `${apiUrl}/public/orders/${encodeURIComponent(token)}`,
          { cache: 'no-store' }
        )
        if (res.status === 404) {
          throw new Error('This tracking link was not found.')
        }
        if (!res.ok) {
          throw new Error('We could not refresh this order right now.')
        }
        const data = await res.json()
        setOrder(data)
        if (!quiet) {
          trackEvent(apiUrl, 'tracking_opened', undefined, {
            status: data.status,
          })
        }
        setError('')
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to load this order.')
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [apiUrl, token]
  )

  // Polling is read through a ref so the interval is never torn down and
  // rebuilt on every refresh.
  const pollable = useRef(true)
  pollable.current = !order || !TERMINAL_STATUSES.has(order.status)

  useEffect(() => {
    if (!router.isReady || !token) return
    void loadOrder()

    // A backgrounded tab and a finished order are both reasons not to spend a
    // customer's mobile data every 10 seconds. Coming back to the page pulls a
    // fresh copy immediately, so nothing is stale on return.
    const interval = window.setInterval(() => {
      if (document.hidden || !pollable.current) return
      void loadOrder(true)
    }, 10000)

    const onVisible = () => {
      if (!document.hidden && pollable.current) void loadOrder(true)
    }
    document.addEventListener('visibilitychange', onVisible)

    return () => {
      window.clearInterval(interval)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [loadOrder, router.isReady, token])

  const completedStatuses = useMemo(
    () =>
      new Set(
        (order?.timeline || [])
          .map(event => event.status)
          .filter((status): status is OrderStatus => Boolean(status))
      ),
    [order]
  )

  const currentNormalIndex = useMemo(() => {
    if (!order) return 0
    const direct = PIPELINE.findIndex(step => step.value === order.status)
    if (direct >= 0) return direct
    let lastIndex = 0
    order.timeline.forEach(event => {
      const index = PIPELINE.findIndex(step => step.value === event.status)
      if (index >= 0) lastIndex = Math.max(lastIndex, index)
    })
    return lastIndex
  }, [order])

  const eta = order?.accepted_eta_minutes
    ? `${order.accepted_eta_minutes} min kitchen estimate`
    : order?.eta_min_minutes && order?.eta_max_minutes
      ? `${order.eta_min_minutes}–${order.eta_max_minutes} min`
      : 'Confirmed by the kitchen'

  const supportNumber = (order?.branch_phone || RESTAURANT.whatsapp).replace(/\D/g, '')
  const supportMessage = encodeURIComponent(
    `Hi, I need help with order ${order?.order_number || order?.tracking_code || ''}.`
  )
  const pageTitle = `${order?.order_number ? `${order.order_number} · ` : ''}Track order | ${RESTAURANT.name}`

  const submitRating = async (value: number) => {
    setRating(value)
    setRatingError('')
    try {
      const response = await fetch(
        `${apiUrl}/public/orders/${encodeURIComponent(token)}/feedback`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ rating: value }),
        }
      )
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail || 'Could not save rating')
      setRatingSent(true)
    } catch (err) {
      setRatingError(err instanceof Error ? err.message : 'Could not save rating')
    }
  }

  return (
    <>
      <Head>
        <title>{pageTitle}</title>
        <meta
          name="description"
          content="Follow your food from the kitchen to delivery."
        />
      </Head>

      <div className="min-h-[100svh] bg-[#fff8ef] text-[#1b0b04]">
        <header className="pt-safe border-b border-black/[0.06] bg-white/90 backdrop-blur-xl">
          <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4 sm:px-6">
            <Link href="/" className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#1b0b04] text-[#f7b32b]">
                <Utensils size={19} />
              </span>
              <div>
                <p
                  className="text-lg font-black leading-none"
                  style={{ fontFamily: 'var(--font-display)' }}
                >
                  {RESTAURANT.name}
                </p>
                <p className="mt-1 text-[11px] font-bold uppercase tracking-[0.15em] text-black/38">
                  Live order tracking
                </p>
              </div>
            </Link>
            <button
              type="button"
              disabled={refreshing}
              onClick={() => void loadOrder(true)}
              className="flex h-10 w-10 items-center justify-center rounded-full border border-black/10 bg-white text-black/55 transition hover:text-[#d95d20] disabled:opacity-50"
              aria-label="Refresh order"
            >
              <RefreshCw size={17} className={refreshing ? 'animate-spin' : ''} />
            </button>
          </div>
        </header>

        <main className="mx-auto max-w-4xl px-4 pb-[calc(2rem+env(safe-area-inset-bottom))] pt-8 sm:px-6 sm:pb-12 sm:pt-12">
          {loading && (
            <div className="space-y-4">
              <div className="h-52 animate-pulse rounded-[32px] bg-[#eadbc9]" />
              <div className="h-96 animate-pulse rounded-[32px] bg-white" />
            </div>
          )}

          {!loading && error && !order && (
            <section className="rounded-[32px] border border-red-100 bg-white p-8 text-center shadow-xl">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-red-50 text-2xl">
                !
              </div>
              <h1 className="mt-5 text-2xl font-black">Tracking unavailable</h1>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-black/50">
                {error}
              </p>
              <button
                type="button"
                onClick={() => void loadOrder()}
                className="mt-6 rounded-full bg-[#1b0b04] px-5 py-3 text-sm font-black text-white"
              >
                Try again
              </button>
            </section>
          )}

          {order && (
            <>
              <section className="overflow-hidden rounded-[32px] bg-[#1b0b04] p-6 text-white shadow-[0_26px_80px_rgba(48,20,6,0.2)] sm:p-8">
                <div className="flex flex-col gap-7 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <p className="text-xs font-black uppercase tracking-[0.2em] text-[#f7b32b]">
                      {order.order_number || order.tracking_code}
                    </p>
                    <h1
                      className="mt-3 text-4xl font-black sm:text-5xl"
                      style={{ fontFamily: 'var(--font-display)' }}
                    >
                      {order.status_label}
                    </h1>
                    <p className="mt-3 flex items-center gap-2 text-sm text-white/60">
                      <MapPin size={15} className="text-[#f7b32b]" />
                      {order.branch_name || 'Your selected branch'}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/[0.07] px-4 py-3">
                    <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-white/45">
                      <Clock3 size={14} />
                      Estimated time
                    </p>
                    <p className="mt-1 text-sm font-black text-[#f7b32b]">{eta}</p>
                  </div>
                </div>
              </section>

              {['delayed', 'cancel_requested', 'cancelled', 'rejected'].includes(order.status) && (
                <section className="mt-5 rounded-[24px] border border-red-200 bg-red-50 p-5">
                  <p className="font-black text-red-800">{order.status_label}</p>
                  <p className="mt-1 text-sm leading-6 text-red-700/75">
                    This order is outside the normal delivery pipeline. Contact
                    the branch if you need help.
                  </p>
                </section>
              )}

              {error && (
                <p className="mt-4 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  Showing the last update. {error}
                </p>
              )}

              <section className="mt-5 rounded-[32px] border border-black/[0.06] bg-white p-5 shadow-[0_20px_70px_rgba(55,24,7,0.08)] sm:p-8">
                <div className="mb-7 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-black uppercase tracking-[0.2em] text-[#d95d20]">
                      From kitchen to you
                    </p>
                    <h2
                      className="mt-1 text-2xl font-black"
                      style={{ fontFamily: 'var(--font-display)' }}
                    >
                      Order progress
                    </h2>
                  </div>
                  <span className="hidden rounded-full bg-emerald-50 px-3 py-2 text-xs font-bold text-emerald-700 sm:inline-flex">
                    Auto-updates every 10s
                  </span>
                </div>

                <ol>
                  {PIPELINE.map((step, index) => {
                    const event = [...order.timeline]
                      .reverse()
                      .find(item => item.status === step.value)
                    const complete =
                      completedStatuses.has(step.value) || index < currentNormalIndex
                    const current = index === currentNormalIndex
                    const StepIcon = step.icon

                    return (
                      <li
                        key={step.value}
                        className="relative grid grid-cols-[48px_1fr_auto] gap-3"
                      >
                        {index < PIPELINE.length - 1 && (
                          <span
                            className={`absolute left-[23px] top-11 h-[calc(100%-28px)] w-0.5 ${
                              index < currentNormalIndex
                                ? 'bg-[#f7b32b]'
                                : 'bg-black/[0.08]'
                            }`}
                          />
                        )}
                        <span
                          className={`relative z-10 flex h-12 w-12 items-center justify-center rounded-full border-2 ${
                            complete || current
                              ? 'border-[#f7b32b] bg-[#1b0b04] text-[#f7b32b]'
                              : 'border-black/[0.08] bg-[#fff8ef] text-black/25'
                          }`}
                        >
                          <StepIcon size={19} />
                        </span>
                        <div className="pb-8 pt-1">
                          <p
                            className={`font-black ${
                              complete || current ? 'text-[#1b0b04]' : 'text-black/28'
                            }`}
                          >
                            {step.label}
                          </p>
                          <p className="mt-1 text-sm text-black/42">{step.detail}</p>
                        </div>
                        <p className="pt-2 text-xs font-bold text-black/35">
                          {event ? formatTime(event.created_at) : ''}
                        </p>
                      </li>
                    )
                  })}
                </ol>
              </section>

              <section className="mt-5 grid gap-5 md:grid-cols-[1.35fr_0.65fr]">
                <div className="rounded-[28px] border border-black/[0.06] bg-white p-5 sm:p-6">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#fff1dc] text-[#d95d20]">
                      <ShoppingBag size={18} />
                    </span>
                    <div>
                      <p className="font-black">Your order</p>
                      <p className="text-xs text-black/40">
                        Placed at {formatTime(order.placed_at)}
                      </p>
                    </div>
                  </div>
                  <div className="mt-5 space-y-3">
                    {order.items.map(item => (
                      <div
                        key={`${item.item_id}-${item.name}`}
                        className="flex items-start justify-between gap-4 text-sm"
                      >
                        <span className="text-black/65">
                          <strong className="text-[#1b0b04]">{item.quantity}×</strong>{' '}
                          {item.name}
                          {item.selections && item.selections.length > 0 && (
                            <small className="block pl-5 text-black/38">
                              {item.selections
                                .map(selection => selection.name || selection.option_id)
                                .join(', ')}
                            </small>
                          )}
                        </span>
                        <span className="font-bold">
                          GHS {item.total_price.toFixed(2)}
                        </span>
                      </div>
                    ))}
                    <div className="border-t border-black/[0.07] pt-3 text-sm">
                      <div className="flex justify-between text-black/48">
                        <span>Delivery</span>
                        <span>GHS {order.delivery_fee.toFixed(2)}</span>
                      </div>
                      <div className="mt-2 flex justify-between text-base font-black">
                        <span>Total</span>
                        <span className="text-[#d95d20]">
                          GHS {order.total_amount.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-[28px] border border-black/[0.06] bg-white p-5">
                    <p className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.15em] text-black/35">
                      <Store size={15} />
                      Branch
                    </p>
                    <p className="mt-2 font-black">
                      {order.branch_name || 'Selected kitchen'}
                    </p>
                    <p className="mt-1 text-sm text-black/45">
                      Payment: {paymentLabel(order.payment_status)}
                    </p>
                  </div>
                  {supportNumber && (
                    <a
                      href={`https://wa.me/${supportNumber}?text=${supportMessage}`}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center justify-center gap-2 rounded-[22px] bg-[#25D366] px-4 py-4 text-sm font-black text-white shadow-[0_18px_45px_rgba(37,211,102,0.2)]"
                    >
                      <MessageCircleMore size={18} />
                      Need help?
                    </a>
                  )}
                  {order.branch_phone && (
                    <a
                      href={`tel:${order.branch_phone}`}
                      className="flex items-center justify-center gap-2 rounded-[22px] border border-black/10 bg-white px-4 py-4 text-sm font-black text-[#1b0b04]"
                    >
                      <Phone size={18} />
                      Call branch
                    </a>
                  )}
                </div>
              </section>

              {order.status === 'delivered' && (
                <section className="mt-5 rounded-[28px] border border-black/[0.06] bg-white p-6 text-center">
                  <p className="text-xs font-black uppercase tracking-[0.18em] text-[#d95d20]">
                    Enjoyed your meal?
                  </p>
                  <h2 className="mt-2 text-2xl font-black">Rate this order</h2>
                  {ratingSent ? (
                    <p className="mt-3 text-sm font-bold text-emerald-700">
                      Thank you—your rating has been saved.
                    </p>
                  ) : (
                    <div className="mt-4 flex justify-center gap-2">
                      {[1, 2, 3, 4, 5].map(value => (
                        <button
                          key={value}
                          type="button"
                          onClick={() => void submitRating(value)}
                          aria-label={`Rate ${value} out of 5`}
                          className={`flex h-11 w-11 items-center justify-center rounded-full ${
                            value <= rating
                              ? 'bg-[#f7b32b] text-[#1b0b04]'
                              : 'bg-[#fff4df] text-[#d95d20]'
                          }`}
                        >
                          <Star size={19} fill={value <= rating ? 'currentColor' : 'none'} />
                        </button>
                      ))}
                    </div>
                  )}
                  {ratingError && (
                    <p className="mt-3 text-sm text-red-600">{ratingError}</p>
                  )}
                  <Link
                    href={`/?branch=${encodeURIComponent(order.branch_slug || '')}`}
                    className="mt-5 inline-flex items-center gap-2 rounded-full bg-[#1b0b04] px-5 py-3 text-sm font-black text-white"
                  >
                    <RotateCcw size={16} />
                    Order again
                  </Link>
                </section>
              )}
            </>
          )}
        </main>
      </div>
    </>
  )
}
