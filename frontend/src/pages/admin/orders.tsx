import { useEffect, useMemo, useState } from 'react'
import Head from 'next/head'
import { AlertCircle, Clock3, PackageCheck, RefreshCw, ShoppingBag, Truck } from 'lucide-react'

type OrderStatus =
  | 'new'
  | 'confirmed'
  | 'preparing'
  | 'ready'
  | 'out_for_delivery'
  | 'delivered'
  | 'cancel_requested'
  | 'cancelled'
  | 'rejected'

interface OrderListItem {
  id: string
  order_number?: string | null
  tracking_code?: string | null
  customer_name?: string | null
  customer_phone: string
  branch_id?: string | null
  status: OrderStatus
  payment_status: string
  total_amount: number
  channel: string
  created_at: string
}

interface OrderItem {
  item_id: string
  name: string
  quantity: number
  unit_price: number
  total_price: number
}

interface OrderEvent {
  id: string
  event_type: string
  from_status?: OrderStatus | null
  to_status?: OrderStatus | null
  actor_type: string
  actor_label?: string | null
  reason_code?: string | null
  reason_note?: string | null
  created_at: string
}

interface OrderDetail extends OrderListItem {
  tenant_id?: string | null
  customer_id?: string | null
  customer_phone: string
  customer_name?: string | null
  delivery_address: string
  items: OrderItem[]
  subtotal_amount: number
  notes?: string | null
  allowed_next_statuses: OrderStatus[]
  events: OrderEvent[]
}

const STATUS_OPTIONS: Array<{ value: '' | OrderStatus; label: string }> = [
  { value: '', label: 'All statuses' },
  { value: 'new', label: 'New' },
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'preparing', label: 'Preparing' },
  { value: 'ready', label: 'Ready' },
  { value: 'out_for_delivery', label: 'Out for delivery' },
  { value: 'delivered', label: 'Delivered' },
  { value: 'cancel_requested', label: 'Cancel requested' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'rejected', label: 'Rejected' },
]

const CANCELLATION_REASONS = [
  'customer_changed_mind',
  'duplicate_order',
  'out_of_stock',
  'branch_overloaded',
  'payment_failed',
  'invalid_address',
  'customer_unreachable',
  'delivery_issue',
  'fraud_suspected',
  'other',
]

function formatStatusLabel(status: string) {
  return status.replace(/_/g, ' ')
}

function formatMoney(amount: number) {
  return `GHS ${Number(amount || 0).toFixed(2)}`
}

function formatDate(value: string) {
  return new Date(value).toLocaleString('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function statusTone(status: string) {
  switch (status) {
    case 'new':
      return 'bg-amber-100 text-amber-800'
    case 'confirmed':
      return 'bg-blue-100 text-blue-800'
    case 'preparing':
      return 'bg-orange-100 text-orange-800'
    case 'ready':
      return 'bg-emerald-100 text-emerald-800'
    case 'out_for_delivery':
      return 'bg-sky-100 text-sky-800'
    case 'delivered':
      return 'bg-green-100 text-green-800'
    case 'cancel_requested':
      return 'bg-rose-100 text-rose-800'
    case 'cancelled':
    case 'rejected':
      return 'bg-gray-200 text-gray-700'
    default:
      return 'bg-gray-100 text-gray-700'
  }
}

export default function AdminOrdersPage() {
  const [orders, setOrders] = useState<OrderListItem[]>([])
  const [selectedOrderId, setSelectedOrderId] = useState<string>('')
  const [selectedOrder, setSelectedOrder] = useState<OrderDetail | null>(null)
  const [statusFilter, setStatusFilter] = useState<'' | OrderStatus>('')
  const [branchFilter, setBranchFilter] = useState('')
  const [search, setSearch] = useState('')
  const [loadingList, setLoadingList] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [mutating, setMutating] = useState(false)
  const [error, setError] = useState('')
  const [detailError, setDetailError] = useState('')
  const [cancelReason, setCancelReason] = useState('customer_changed_mind')
  const [cancelNote, setCancelNote] = useState('')

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const fetchOrders = async () => {
    setLoadingList(true)
    setError('')

    try {
      const params = new URLSearchParams()
      if (statusFilter) params.set('status', statusFilter)
      if (branchFilter.trim()) params.set('branch_id', branchFilter.trim())
      const query = params.toString()
      const res = await fetch(`${apiUrl}/admin/orders${query ? `?${query}` : ''}`)
      if (!res.ok) {
        throw new Error('Failed to load orders')
      }

      const data = await res.json()
      const nextOrders = Array.isArray(data.items) ? data.items : []
      setOrders(nextOrders)

      if (!selectedOrderId && nextOrders.length > 0) {
        setSelectedOrderId(nextOrders[0].id)
      } else if (selectedOrderId && !nextOrders.some((order: OrderListItem) => order.id === selectedOrderId)) {
        setSelectedOrderId(nextOrders[0]?.id || '')
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load orders'
      setError(message)
    } finally {
      setLoadingList(false)
    }
  }

  const fetchOrderDetail = async (orderId: string) => {
    if (!orderId) {
      setSelectedOrder(null)
      return
    }

    setLoadingDetail(true)
    setDetailError('')
    try {
      const res = await fetch(`${apiUrl}/admin/orders/${orderId}`)
      if (!res.ok) {
        throw new Error('Failed to load order details')
      }
      const data = await res.json()
      setSelectedOrder(data)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load order details'
      setDetailError(message)
    } finally {
      setLoadingDetail(false)
    }
  }

  useEffect(() => {
    void fetchOrders()
  }, [statusFilter, branchFilter])

  useEffect(() => {
    if (!selectedOrderId) {
      setSelectedOrder(null)
      return
    }
    void fetchOrderDetail(selectedOrderId)
  }, [selectedOrderId])

  useEffect(() => {
    const interval = window.setInterval(() => {
      void fetchOrders()
      if (selectedOrderId) {
        void fetchOrderDetail(selectedOrderId)
      }
    }, 15000)

    return () => window.clearInterval(interval)
  }, [statusFilter, branchFilter, selectedOrderId])

  const filteredOrders = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return orders

    return orders.filter(order => {
      const haystack = [
        order.order_number,
        order.tracking_code,
        order.customer_name,
        order.customer_phone,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      return haystack.includes(query)
    })
  }, [orders, search])

  const summary = useMemo(() => {
    return {
      total: orders.length,
      active: orders.filter(order => ['new', 'confirmed', 'preparing', 'ready', 'out_for_delivery'].includes(order.status)).length,
      delivery: orders.filter(order => order.status === 'out_for_delivery').length,
      exceptions: orders.filter(order => ['cancel_requested', 'cancelled', 'rejected'].includes(order.status)).length,
    }
  }, [orders])

  const mutateStatus = async (status: OrderStatus) => {
    if (!selectedOrder) return

    setMutating(true)
    setDetailError('')
    try {
      const res = await fetch(`${apiUrl}/admin/orders/${selectedOrder.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status,
          actor_label: 'dashboard-ui',
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to update order status')
      }

      setSelectedOrder(data)
      await fetchOrders()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update order status'
      setDetailError(message)
    } finally {
      setMutating(false)
    }
  }

  const submitCancellation = async () => {
    if (!selectedOrder) return

    setMutating(true)
    setDetailError('')
    try {
      const res = await fetch(`${apiUrl}/admin/orders/${selectedOrder.id}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reason_code: cancelReason,
          reason_note: cancelNote.trim() || null,
          actor_label: 'dashboard-ui',
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to submit cancellation')
      }

      setSelectedOrder(data)
      setCancelNote('')
      await fetchOrders()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to submit cancellation'
      setDetailError(message)
    } finally {
      setMutating(false)
    }
  }

  return (
    <>
      <Head>
        <title>Operations Dashboard | Live Orders</title>
        <meta
          name="description"
          content="Production operations dashboard for live restaurant orders."
        />
      </Head>

      <div className="min-h-screen bg-brand-dark text-white">
        <div
          className="absolute inset-0 opacity-60"
          style={{
            background:
              'radial-gradient(circle at top left, rgba(242,100,25,0.32), transparent 28%), radial-gradient(circle at top right, rgba(255,190,11,0.16), transparent 24%), linear-gradient(180deg, #1a0a00 0%, #2c1200 100%)',
          }}
        />

        <div className="relative mx-auto max-w-7xl px-4 py-8 md:px-6">
          <section className="mb-8 rounded-[32px] border border-white/10 bg-white/8 p-6 backdrop-blur">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="mb-2 text-xs uppercase tracking-[0.35em] text-orange-200">
                  Operations
                </p>
                <h1
                  className="text-4xl font-black text-white md:text-5xl"
                  style={{ fontFamily: 'var(--font-display)' }}
                >
                  Live Order Queue
                </h1>
                <p className="mt-3 max-w-2xl text-sm text-orange-50/80 md:text-base">
                  First production dashboard pass for staff operations. It covers queue visibility,
                  order detail, status actions, and cancellation handling against the new admin API.
                </p>
              </div>

              <button
                onClick={() => void fetchOrders()}
                className="inline-flex items-center gap-2 self-start rounded-full bg-white px-4 py-2 text-sm font-bold text-brand-dark transition hover:scale-[1.02]"
              >
                <RefreshCw size={16} className={loadingList ? 'animate-spin' : ''} />
                Refresh Queue
              </button>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-4">
              <div className="rounded-3xl bg-white/10 p-4">
                <div className="flex items-center gap-3 text-orange-100">
                  <ShoppingBag size={18} />
                  <span className="text-sm font-semibold">Total Orders</span>
                </div>
                <p className="mt-4 text-3xl font-black">{summary.total}</p>
              </div>
              <div className="rounded-3xl bg-white/10 p-4">
                <div className="flex items-center gap-3 text-orange-100">
                  <Clock3 size={18} />
                  <span className="text-sm font-semibold">Active Queue</span>
                </div>
                <p className="mt-4 text-3xl font-black">{summary.active}</p>
              </div>
              <div className="rounded-3xl bg-white/10 p-4">
                <div className="flex items-center gap-3 text-orange-100">
                  <Truck size={18} />
                  <span className="text-sm font-semibold">Out For Delivery</span>
                </div>
                <p className="mt-4 text-3xl font-black">{summary.delivery}</p>
              </div>
              <div className="rounded-3xl bg-white/10 p-4">
                <div className="flex items-center gap-3 text-orange-100">
                  <AlertCircle size={18} />
                  <span className="text-sm font-semibold">Exceptions</span>
                </div>
                <p className="mt-4 text-3xl font-black">{summary.exceptions}</p>
              </div>
            </div>
          </section>

          <section className="mb-6 grid gap-3 rounded-[28px] border border-white/10 bg-[#2c1200]/70 p-4 md:grid-cols-[1.4fr_1fr_1fr_auto]">
            <input
              type="text"
              value={search}
              onChange={event => setSearch(event.target.value)}
              placeholder="Search by order number, tracking code, or phone"
              className="rounded-2xl border border-white/10 bg-white/8 px-4 py-3 text-sm text-white placeholder:text-orange-100/50 focus:border-orange-300 focus:outline-none"
            />

            <select
              value={statusFilter}
              onChange={event => setStatusFilter(event.target.value as '' | OrderStatus)}
              className="rounded-2xl border border-white/10 bg-white/8 px-4 py-3 text-sm text-white focus:border-orange-300 focus:outline-none"
            >
              {STATUS_OPTIONS.map(option => (
                <option key={option.label} value={option.value} className="text-brand-dark">
                  {option.label}
                </option>
              ))}
            </select>

            <input
              type="text"
              value={branchFilter}
              onChange={event => setBranchFilter(event.target.value)}
              placeholder="Branch ID filter"
              className="rounded-2xl border border-white/10 bg-white/8 px-4 py-3 text-sm text-white placeholder:text-orange-100/50 focus:border-orange-300 focus:outline-none"
            />

            <div className="flex items-center justify-end text-xs uppercase tracking-[0.2em] text-orange-100/70">
              {loadingList ? 'Syncing' : `${filteredOrders.length} visible`}
            </div>
          </section>

          {error && (
            <div className="mb-4 rounded-2xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-100">
              {error}
            </div>
          )}

          <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
            <section className="rounded-[28px] border border-white/10 bg-[#fff8f0] p-3 text-brand-dark shadow-2xl">
              <div className="space-y-3">
                {filteredOrders.length === 0 ? (
                  <div className="rounded-[24px] border border-dashed border-orange-200 bg-white p-10 text-center">
                    <p className="text-lg font-bold">No orders match the current filters.</p>
                    <p className="mt-2 text-sm text-gray-500">
                      Try clearing the search or switching to a wider status view.
                    </p>
                  </div>
                ) : (
                  filteredOrders.map(order => (
                    <button
                      key={order.id}
                      onClick={() => setSelectedOrderId(order.id)}
                      className={`w-full rounded-[24px] border p-4 text-left transition ${
                        selectedOrderId === order.id
                          ? 'border-brand-orange bg-orange-50 shadow-lg'
                          : 'border-orange-100 bg-white hover:border-orange-200 hover:shadow-md'
                      }`}
                    >
                      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <h2 className="text-lg font-black text-brand-dark">
                              #{order.order_number || order.id.slice(0, 8).toUpperCase()}
                            </h2>
                            <span
                              className={`rounded-full px-3 py-1 text-xs font-bold uppercase ${statusTone(order.status)}`}
                            >
                              {formatStatusLabel(order.status)}
                            </span>
                          </div>
                          <p className="mt-2 text-sm font-semibold">
                            {order.customer_name || 'Walk-in customer'} • {order.customer_phone}
                          </p>
                          <p className="mt-1 text-xs uppercase tracking-[0.2em] text-gray-500">
                            {order.channel} • {order.tracking_code || 'No tracking code'}
                          </p>
                        </div>

                        <div className="text-left md:text-right">
                          <p className="text-lg font-black text-brand-dark">
                            {formatMoney(order.total_amount)}
                          </p>
                          <p className="mt-1 text-sm text-gray-500">{formatDate(order.created_at)}</p>
                        </div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </section>

            <aside className="rounded-[28px] border border-white/10 bg-white p-5 text-brand-dark shadow-2xl">
              {!selectedOrderId ? (
                <div className="flex h-full min-h-[420px] items-center justify-center rounded-[24px] border border-dashed border-orange-200 bg-orange-50/60 text-center">
                  <div>
                    <p className="text-lg font-black">Select an order</p>
                    <p className="mt-2 text-sm text-gray-500">
                      Order details, timeline, and actions will appear here.
                    </p>
                  </div>
                </div>
              ) : loadingDetail && !selectedOrder ? (
                <div className="flex h-full min-h-[420px] items-center justify-center text-sm text-gray-500">
                  Loading order details...
                </div>
              ) : detailError ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {detailError}
                </div>
              ) : selectedOrder ? (
                <div className="space-y-6">
                  <div className="border-b border-orange-100 pb-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.25em] text-gray-500">
                          Order Detail
                        </p>
                        <h2
                          className="mt-2 text-3xl font-black"
                          style={{ fontFamily: 'var(--font-display)' }}
                        >
                          #{selectedOrder.order_number || selectedOrder.id.slice(0, 8).toUpperCase()}
                        </h2>
                      </div>
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-bold uppercase ${statusTone(selectedOrder.status)}`}
                      >
                        {formatStatusLabel(selectedOrder.status)}
                      </span>
                    </div>

                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <div className="rounded-2xl bg-orange-50 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-gray-500">Customer</p>
                        <p className="mt-2 font-bold">{selectedOrder.customer_name || 'Unnamed customer'}</p>
                        <p className="text-sm text-gray-600">{selectedOrder.customer_phone}</p>
                      </div>
                      <div className="rounded-2xl bg-orange-50 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-gray-500">Tracking</p>
                        <p className="mt-2 font-bold">{selectedOrder.tracking_code || 'Not assigned'}</p>
                        <p className="text-sm text-gray-600">{formatDate(selectedOrder.created_at)}</p>
                      </div>
                    </div>

                    <div className="mt-4 rounded-2xl border border-orange-100 p-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-gray-500">Delivery Address</p>
                      <p className="mt-2 text-sm font-medium">{selectedOrder.delivery_address}</p>
                    </div>
                  </div>

                  <div>
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-sm font-black uppercase tracking-[0.2em] text-gray-500">
                        Items
                      </h3>
                      <span className="inline-flex items-center gap-2 text-sm font-bold text-brand-orange">
                        <PackageCheck size={16} />
                        {formatMoney(selectedOrder.total_amount)}
                      </span>
                    </div>
                    <div className="space-y-2">
                      {selectedOrder.items.map(item => (
                        <div key={`${selectedOrder.id}-${item.item_id}`} className="rounded-2xl bg-[#fff8f0] p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-bold">
                                {item.quantity}x {item.name}
                              </p>
                              <p className="text-sm text-gray-500">
                                {formatMoney(item.unit_price)} each
                              </p>
                            </div>
                            <p className="font-black text-brand-dark">{formatMoney(item.total_price)}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="mb-3 text-sm font-black uppercase tracking-[0.2em] text-gray-500">
                      Status Actions
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedOrder.allowed_next_statuses.length === 0 ? (
                        <p className="text-sm text-gray-500">No further transitions available.</p>
                      ) : (
                        selectedOrder.allowed_next_statuses.map(status => (
                          <button
                            key={status}
                            onClick={() => void mutateStatus(status)}
                            disabled={mutating}
                            className="rounded-full bg-brand-dark px-4 py-2 text-sm font-bold text-white transition hover:bg-brand-orange disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Move to {formatStatusLabel(status)}
                          </button>
                        ))
                      )}
                    </div>
                  </div>

                  <div className="rounded-[24px] border border-rose-100 bg-rose-50/70 p-4">
                    <h3 className="text-sm font-black uppercase tracking-[0.2em] text-rose-700">
                      Cancellation Workflow
                    </h3>
                    <div className="mt-3 space-y-3">
                      <select
                        value={cancelReason}
                        onChange={event => setCancelReason(event.target.value)}
                        className="w-full rounded-2xl border border-rose-200 bg-white px-4 py-3 text-sm focus:border-rose-400 focus:outline-none"
                      >
                        {CANCELLATION_REASONS.map(reason => (
                          <option key={reason} value={reason}>
                            {formatStatusLabel(reason)}
                          </option>
                        ))}
                      </select>

                      <textarea
                        value={cancelNote}
                        onChange={event => setCancelNote(event.target.value)}
                        rows={3}
                        placeholder="Optional cancellation note for operations history"
                        className="w-full rounded-2xl border border-rose-200 bg-white px-4 py-3 text-sm focus:border-rose-400 focus:outline-none"
                      />

                      <button
                        onClick={() => void submitCancellation()}
                        disabled={mutating}
                        className="rounded-full bg-rose-600 px-4 py-2 text-sm font-bold text-white transition hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Submit Cancellation
                      </button>
                    </div>
                  </div>

                  <div>
                    <h3 className="mb-3 text-sm font-black uppercase tracking-[0.2em] text-gray-500">
                      Timeline
                    </h3>
                    <div className="space-y-3">
                      {selectedOrder.events.map(event => (
                        <div key={event.id} className="rounded-2xl border border-orange-100 p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-bold">{formatStatusLabel(event.event_type)}</p>
                              <p className="mt-1 text-sm text-gray-500">
                                {event.to_status ? `State: ${formatStatusLabel(event.to_status)}` : 'Audit event'}
                              </p>
                              {(event.reason_code || event.reason_note) && (
                                <p className="mt-2 text-sm text-gray-600">
                                  {event.reason_code ? `Reason: ${formatStatusLabel(event.reason_code)}` : ''}
                                  {event.reason_note ? ` • ${event.reason_note}` : ''}
                                </p>
                              )}
                            </div>
                            <div className="text-right text-xs uppercase tracking-[0.15em] text-gray-500">
                              <p>{event.actor_type}</p>
                              <p className="mt-1">{formatDate(event.created_at)}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : null}
            </aside>
          </div>
        </div>
      </div>
    </>
  )
}
