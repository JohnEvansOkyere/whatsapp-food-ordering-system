import { useEffect, useMemo, useState } from 'react'
import Head from 'next/head'
import Link from 'next/link'
import {
  Bike,
  CheckCircle2,
  ChefHat,
  Clock3,
  MapPin,
  PackageCheck,
  PhoneCall,
  Receipt,
  RefreshCw,
  ShoppingBag,
  Store,
  TimerReset,
  Truck,
  UtensilsCrossed,
} from 'lucide-react'
import { RESTAURANT } from '@/lib/menuData'

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

interface OrderDetail {
  id: string
  order_number?: string | null
  tracking_code?: string | null
  customer_name?: string | null
  customer_phone: string
  delivery_address: string
  branch_id?: string | null
  status: OrderStatus
  payment_status: string
  total_amount: number
  subtotal_amount: number
  channel: string
  created_at: string
  notes?: string | null
  items: OrderItem[]
  allowed_next_statuses: OrderStatus[]
  events: OrderEvent[]
}

const KANBAN_STATUSES: Array<{ value: OrderStatus; label: string; accent: string }> = [
  { value: 'new', label: 'Incoming', accent: 'border-amber-300 bg-amber-50' },
  { value: 'confirmed', label: 'Accepted', accent: 'border-sky-300 bg-sky-50' },
  { value: 'preparing', label: 'Cooking', accent: 'border-orange-300 bg-orange-50' },
  { value: 'ready', label: 'Ready', accent: 'border-emerald-300 bg-emerald-50' },
  { value: 'out_for_delivery', label: 'On The Road', accent: 'border-blue-300 bg-blue-50' },
  { value: 'delivered', label: 'Completed', accent: 'border-lime-300 bg-lime-50' },
]

const STATUS_PROGRESS: Record<OrderStatus, number> = {
  new: 1,
  confirmed: 2,
  preparing: 3,
  ready: 4,
  out_for_delivery: 5,
  delivered: 6,
  cancel_requested: 2,
  cancelled: 2,
  rejected: 1,
}

const DEMO_ORDERS: OrderDetail[] = [
  {
    id: 'demo-order-1',
    order_number: 'ORD-8A41BC2D',
    tracking_code: 'TRK-DEMO1001',
    customer_name: 'Adwoa Mensah',
    customer_phone: '233244123456',
    delivery_address: 'House 14, East Legon, near A&C Mall',
    status: 'new',
    payment_status: 'unpaid',
    total_amount: 97,
    subtotal_amount: 97,
    channel: 'whatsapp',
    created_at: '2026-04-25T09:10:00+00:00',
    notes: 'Customer asked for extra pepper and no onions in the salad.',
    items: [
      { item_id: 'jollof-chicken', name: 'Jollof Rice + Chicken', quantity: 2, unit_price: 45, total_price: 90 },
      { item_id: 'water', name: 'Voltic Water (1.5L)', quantity: 1, unit_price: 7, total_price: 7 },
    ],
    allowed_next_statuses: ['confirmed', 'rejected', 'cancel_requested', 'cancelled'],
    events: [
      {
        id: 'demo-evt-1',
        event_type: 'order_created',
        to_status: 'new',
        actor_type: 'customer',
        actor_label: 'whatsapp',
        created_at: '2026-04-25T09:10:00+00:00',
      },
    ],
  },
  {
    id: 'demo-order-2',
    order_number: 'ORD-CA1F0A83',
    tracking_code: 'TRK-DEMO1002',
    customer_name: 'Richie B',
    customer_phone: '233201112223',
    delivery_address: 'Spintex Shell, Block C, gate 2',
    status: 'new',
    payment_status: 'pending',
    total_amount: 122,
    subtotal_amount: 122,
    channel: 'web',
    created_at: '2026-04-25T09:05:00+00:00',
    notes: 'Please call when rider gets to the gate.',
    items: [
      { item_id: 'chicken-pizza', name: 'BBQ Chicken Pizza', quantity: 1, unit_price: 85, total_price: 85 },
      { item_id: 'chips', name: 'Chips (Large)', quantity: 1, unit_price: 20, total_price: 20 },
      { item_id: 'malt', name: 'Malta Guinness', quantity: 1, unit_price: 17, total_price: 17 },
    ],
    allowed_next_statuses: ['confirmed', 'rejected', 'cancel_requested', 'cancelled'],
    events: [
      {
        id: 'demo-evt-2',
        event_type: 'order_created',
        to_status: 'new',
        actor_type: 'customer',
        actor_label: 'web',
        created_at: '2026-04-25T09:05:00+00:00',
      },
    ],
  },
  {
    id: 'demo-order-3',
    order_number: 'ORD-1F53AC20',
    tracking_code: 'TRK-DEMO1003',
    customer_name: 'Kwesi Arthur',
    customer_phone: '233277700111',
    delivery_address: 'Airport Residential, opposite Marina Mall',
    status: 'confirmed',
    payment_status: 'pending',
    total_amount: 52,
    subtotal_amount: 52,
    channel: 'web',
    created_at: '2026-04-25T08:48:00+00:00',
    notes: null,
    items: [
      { item_id: 'waakye', name: 'Waakye Special', quantity: 1, unit_price: 40, total_price: 40 },
      { item_id: 'sobolo', name: 'Sobolo (Zobo)', quantity: 1, unit_price: 12, total_price: 12 },
    ],
    allowed_next_statuses: ['preparing', 'cancel_requested', 'cancelled'],
    events: [
      {
        id: 'demo-evt-3',
        event_type: 'order_created',
        to_status: 'new',
        actor_type: 'customer',
        actor_label: 'web',
        created_at: '2026-04-25T08:48:00+00:00',
      },
      {
        id: 'demo-evt-4',
        event_type: 'order_confirmed',
        from_status: 'new',
        to_status: 'confirmed',
        actor_type: 'staff',
        actor_label: 'cashier',
        created_at: '2026-04-25T08:52:00+00:00',
      },
    ],
  },
  {
    id: 'demo-order-4',
    order_number: 'ORD-55AF1182',
    tracking_code: 'TRK-DEMO1004',
    customer_name: 'Nhyira Ofori',
    customer_phone: '233549001122',
    delivery_address: 'Adabraka, near ECG office',
    status: 'preparing',
    payment_status: 'paid',
    total_amount: 90,
    subtotal_amount: 90,
    channel: 'whatsapp',
    created_at: '2026-04-25T08:36:00+00:00',
    notes: 'Customer already paid by MoMo.',
    items: [
      { item_id: 'jollof-chicken', name: 'Jollof Rice + Chicken', quantity: 2, unit_price: 45, total_price: 90 },
    ],
    allowed_next_statuses: ['ready', 'cancel_requested'],
    events: [
      {
        id: 'demo-evt-5',
        event_type: 'order_created',
        to_status: 'new',
        actor_type: 'customer',
        actor_label: 'whatsapp',
        created_at: '2026-04-25T08:36:00+00:00',
      },
      {
        id: 'demo-evt-6',
        event_type: 'order_confirmed',
        from_status: 'new',
        to_status: 'confirmed',
        actor_type: 'staff',
        actor_label: 'cashier',
        created_at: '2026-04-25T08:39:00+00:00',
      },
      {
        id: 'demo-evt-7',
        event_type: 'order_preparing',
        from_status: 'confirmed',
        to_status: 'preparing',
        actor_type: 'staff',
        actor_label: 'kitchen',
        created_at: '2026-04-25T08:44:00+00:00',
      },
    ],
  },
  {
    id: 'demo-order-5',
    order_number: 'ORD-70CA88AA',
    tracking_code: 'TRK-DEMO1005',
    customer_name: 'Naa Okailey',
    customer_phone: '233277776666',
    delivery_address: 'Osu Oxford Street, near Papaye',
    status: 'ready',
    payment_status: 'paid',
    total_amount: 85,
    subtotal_amount: 85,
    channel: 'whatsapp',
    created_at: '2026-04-25T08:22:00+00:00',
    notes: 'Call on arrival.',
    items: [
      { item_id: 'chicken-pizza', name: 'BBQ Chicken Pizza', quantity: 1, unit_price: 85, total_price: 85 },
    ],
    allowed_next_statuses: ['out_for_delivery', 'delivered', 'cancel_requested'],
    events: [
      {
        id: 'demo-evt-8',
        event_type: 'order_created',
        to_status: 'new',
        actor_type: 'customer',
        actor_label: 'whatsapp',
        created_at: '2026-04-25T08:22:00+00:00',
      },
      {
        id: 'demo-evt-9',
        event_type: 'order_confirmed',
        from_status: 'new',
        to_status: 'confirmed',
        actor_type: 'staff',
        actor_label: 'cashier',
        created_at: '2026-04-25T08:25:00+00:00',
      },
      {
        id: 'demo-evt-10',
        event_type: 'order_preparing',
        from_status: 'confirmed',
        to_status: 'preparing',
        actor_type: 'staff',
        actor_label: 'kitchen',
        created_at: '2026-04-25T08:30:00+00:00',
      },
      {
        id: 'demo-evt-11',
        event_type: 'order_ready',
        from_status: 'preparing',
        to_status: 'ready',
        actor_type: 'staff',
        actor_label: 'kitchen',
        created_at: '2026-04-25T08:39:00+00:00',
      },
    ],
  },
  {
    id: 'demo-order-6',
    order_number: 'ORD-F3A78D19',
    tracking_code: 'TRK-DEMO1006',
    customer_name: 'Kojo Tandoh',
    customer_phone: '233202223334',
    delivery_address: 'Labone, fifth avenue, blue gate',
    status: 'out_for_delivery',
    payment_status: 'paid',
    total_amount: 63,
    subtotal_amount: 63,
    channel: 'web',
    created_at: '2026-04-25T08:00:00+00:00',
    notes: 'Rider should call before entering the compound.',
    items: [
      { item_id: 'grilled-chicken', name: 'Grilled Chicken (2 pcs)', quantity: 1, unit_price: 55, total_price: 55 },
      { item_id: 'water', name: 'Voltic Water (1.5L)', quantity: 1, unit_price: 8, total_price: 8 },
    ],
    allowed_next_statuses: ['delivered', 'cancel_requested'],
    events: [
      {
        id: 'demo-evt-12',
        event_type: 'order_created',
        to_status: 'new',
        actor_type: 'customer',
        actor_label: 'web',
        created_at: '2026-04-25T08:00:00+00:00',
      },
      {
        id: 'demo-evt-13',
        event_type: 'order_confirmed',
        from_status: 'new',
        to_status: 'confirmed',
        actor_type: 'staff',
        actor_label: 'cashier',
        created_at: '2026-04-25T08:06:00+00:00',
      },
      {
        id: 'demo-evt-14',
        event_type: 'order_preparing',
        from_status: 'confirmed',
        to_status: 'preparing',
        actor_type: 'staff',
        actor_label: 'kitchen',
        created_at: '2026-04-25T08:13:00+00:00',
      },
      {
        id: 'demo-evt-15',
        event_type: 'order_ready',
        from_status: 'preparing',
        to_status: 'ready',
        actor_type: 'staff',
        actor_label: 'kitchen',
        created_at: '2026-04-25T08:25:00+00:00',
      },
      {
        id: 'demo-evt-16',
        event_type: 'order_dispatched',
        from_status: 'ready',
        to_status: 'out_for_delivery',
        actor_type: 'staff',
        actor_label: 'dispatch',
        created_at: '2026-04-25T08:33:00+00:00',
      },
    ],
  },
  {
    id: 'demo-order-7',
    order_number: 'ORD-921ACF65',
    tracking_code: 'TRK-DEMO1007',
    customer_name: 'Akosua Addo',
    customer_phone: '233244331111',
    delivery_address: 'Ridge, Roman Ridge road',
    status: 'delivered',
    payment_status: 'paid',
    total_amount: 30,
    subtotal_amount: 30,
    channel: 'whatsapp',
    created_at: '2026-04-25T07:40:00+00:00',
    notes: null,
    items: [
      { item_id: 'chips', name: 'Chips (Large)', quantity: 1, unit_price: 20, total_price: 20 },
      { item_id: 'malt', name: 'Malta Guinness', quantity: 1, unit_price: 10, total_price: 10 },
    ],
    allowed_next_statuses: [],
    events: [
      {
        id: 'demo-evt-17',
        event_type: 'order_created',
        to_status: 'new',
        actor_type: 'customer',
        actor_label: 'whatsapp',
        created_at: '2026-04-25T07:40:00+00:00',
      },
      {
        id: 'demo-evt-18',
        event_type: 'order_confirmed',
        from_status: 'new',
        to_status: 'confirmed',
        actor_type: 'staff',
        actor_label: 'cashier',
        created_at: '2026-04-25T07:43:00+00:00',
      },
      {
        id: 'demo-evt-19',
        event_type: 'order_preparing',
        from_status: 'confirmed',
        to_status: 'preparing',
        actor_type: 'staff',
        actor_label: 'kitchen',
        created_at: '2026-04-25T07:48:00+00:00',
      },
      {
        id: 'demo-evt-20',
        event_type: 'order_ready',
        from_status: 'preparing',
        to_status: 'ready',
        actor_type: 'staff',
        actor_label: 'kitchen',
        created_at: '2026-04-25T07:57:00+00:00',
      },
      {
        id: 'demo-evt-21',
        event_type: 'order_dispatched',
        from_status: 'ready',
        to_status: 'out_for_delivery',
        actor_type: 'staff',
        actor_label: 'dispatch',
        created_at: '2026-04-25T08:02:00+00:00',
      },
      {
        id: 'demo-evt-22',
        event_type: 'order_delivered',
        from_status: 'out_for_delivery',
        to_status: 'delivered',
        actor_type: 'staff',
        actor_label: 'dispatch',
        created_at: '2026-04-25T08:18:00+00:00',
      },
    ],
  },
]

function formatMoney(amount: number) {
  return `${RESTAURANT.currency} ${Number(amount || 0).toFixed(2)}`
}

function formatStatusLabel(value: string) {
  return value.replace(/_/g, ' ')
}

function displayStatus(status: OrderStatus) {
  switch (status) {
    case 'new':
      return 'Incoming'
    case 'confirmed':
      return 'Accepted'
    case 'preparing':
      return 'Cooking'
    case 'ready':
      return 'Ready'
    case 'out_for_delivery':
      return 'On the road'
    case 'delivered':
      return 'Completed'
    case 'cancel_requested':
      return 'Cancel requested'
    case 'cancelled':
      return 'Cancelled'
    case 'rejected':
      return 'Rejected'
    default:
      return formatStatusLabel(status)
  }
}

function displayEvent(eventType: string) {
  switch (eventType) {
    case 'order_created':
      return 'Order received'
    case 'order_confirmed':
      return 'Order accepted'
    case 'order_preparing':
      return 'Cooking started'
    case 'order_ready':
      return 'Order ready'
    case 'order_dispatched':
      return 'Rider left with order'
    case 'order_delivered':
      return 'Order completed'
    case 'cancellation_requested':
      return 'Cancellation requested'
    case 'order_cancelled':
      return 'Order cancelled'
    case 'order_rejected':
      return 'Order rejected'
    default:
      return formatStatusLabel(eventType)
  }
}

function restaurantInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part[0]?.toUpperCase() || '')
    .join('')
}

function formatDate(value: string) {
  return new Date(value).toLocaleString('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function formatTimeSince(value: string) {
  const then = new Date(value).getTime()
  const now = Date.now()
  const diffMins = Math.max(1, Math.round((now - then) / 60000))

  if (diffMins < 60) {
    return `${diffMins} min ago`
  }

  const hours = Math.floor(diffMins / 60)
  const mins = diffMins % 60
  return mins === 0 ? `${hours}h ago` : `${hours}h ${mins}m ago`
}

function channelLabel(channel: string) {
  if (channel === 'whatsapp') return 'WhatsApp'
  if (channel === 'web') return 'Web'
  return channel
}

function paymentLabel(paymentStatus: string) {
  switch (paymentStatus) {
    case 'paid':
      return 'Paid'
    case 'pending':
      return 'Cash on delivery'
    case 'unpaid':
      return 'Awaiting payment'
    default:
      return formatStatusLabel(paymentStatus)
  }
}

function statusBadge(status: OrderStatus) {
  switch (status) {
    case 'new':
      return 'bg-amber-100 text-amber-800'
    case 'confirmed':
      return 'bg-sky-100 text-sky-800'
    case 'preparing':
      return 'bg-orange-100 text-orange-800'
    case 'ready':
      return 'bg-emerald-100 text-emerald-800'
    case 'out_for_delivery':
      return 'bg-blue-100 text-blue-800'
    case 'delivered':
      return 'bg-lime-100 text-lime-800'
    case 'cancel_requested':
      return 'bg-rose-100 text-rose-800'
    case 'cancelled':
    case 'rejected':
      return 'bg-gray-200 text-gray-700'
    default:
      return 'bg-gray-100 text-gray-700'
  }
}

export default function DashboardPage() {
  const [orders, setOrders] = useState<OrderDetail[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(false)
  const [mutating, setMutating] = useState(false)
  const [usingDemoData, setUsingDemoData] = useState(false)
  const [error, setError] = useState('')

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const fetchDashboard = async () => {
    setLoading(true)
    setError('')

    try {
      const listRes = await fetch(`${apiUrl}/admin/orders?limit=50`)
      if (!listRes.ok) {
        throw new Error('Failed to load live orders')
      }

      const listData = await listRes.json()
      const items = Array.isArray(listData.items) ? listData.items : []

      if (items.length === 0) {
        setOrders(DEMO_ORDERS)
        setUsingDemoData(true)
        setSelectedId(prev => prev || DEMO_ORDERS[0].id)
        return
      }

      const details = await Promise.all(
        items.map(async (order: { id: string }) => {
          const detailRes = await fetch(`${apiUrl}/admin/orders/${order.id}`)
          if (!detailRes.ok) {
            throw new Error(`Failed to load order ${order.id}`)
          }
          return detailRes.json()
        })
      )

      setOrders(details)
      setUsingDemoData(false)
      setSelectedId(prev => {
        if (prev && details.some((order: OrderDetail) => order.id === prev)) {
          return prev
        }
        return details[0]?.id || ''
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load dashboard'
      setError(message)
      setOrders(DEMO_ORDERS)
      setUsingDemoData(true)
      setSelectedId(prev => prev || DEMO_ORDERS[0].id)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchDashboard()
  }, [])

  useEffect(() => {
    const interval = window.setInterval(() => {
      void fetchDashboard()
    }, 15000)
    return () => window.clearInterval(interval)
  }, [])

  const selectedOrder = useMemo(
    () => orders.find(order => order.id === selectedId) || orders[0] || null,
    [orders, selectedId]
  )

  const summary = useMemo(
    () => ({
      total: orders.length,
      active: orders.filter(order =>
        ['new', 'confirmed', 'preparing', 'ready', 'out_for_delivery'].includes(order.status)
      ).length,
      pendingAction: orders.filter(order => ['new', 'ready'].includes(order.status)).length,
      inDelivery: orders.filter(order => order.status === 'out_for_delivery').length,
      averageTicket:
        orders.length > 0
          ? orders.reduce((sum, order) => sum + Number(order.total_amount || 0), 0) / orders.length
          : 0,
    }),
    [orders]
  )

  const groupedOrders = useMemo(
    () =>
      KANBAN_STATUSES.map(column => ({
        ...column,
        items: orders.filter(order => order.status === column.value),
      })),
    [orders]
  )

  const advanceOrder = async (nextStatus: OrderStatus) => {
    if (!selectedOrder || usingDemoData) return

    setMutating(true)
    setError('')
    try {
      const res = await fetch(`${apiUrl}/admin/orders/${selectedOrder.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: nextStatus,
          actor_label: 'simple-dashboard',
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to update order')
      }

      setOrders(prev => prev.map(order => (order.id === data.id ? data : order)))
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update order'
      setError(message)
    } finally {
      setMutating(false)
    }
  }

  return (
    <>
      <Head>
        <title>{RESTAURANT.name} Order Dashboard</title>
        <meta
          name="description"
          content="Simple no-auth order tracking dashboard for restaurant demo use."
        />
      </Head>

      <div className="min-h-screen bg-[#f7efe5] text-brand-dark">
        <div
          className="border-b border-black/5"
          style={{
            background:
              'radial-gradient(circle at top left, rgba(242,100,25,0.2), transparent 28%), linear-gradient(135deg, #fff9f2 0%, #f6ecdf 55%, #f4dfc9 100%)',
          }}
        >
          <div className="mx-auto max-w-7xl px-4 py-8 md:px-6">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex items-start gap-4">
                <div className="flex h-16 w-16 items-center justify-center rounded-[22px] bg-brand-dark text-xl font-black text-brand-yellow shadow-[0_18px_50px_rgba(26,10,0,0.18)]">
                  {restaurantInitials(RESTAURANT.name)}
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.35em] text-brand-orange">
                    Restaurant Screen
                  </p>
                  <h1
                    className="mt-2 text-4xl font-black md:text-5xl"
                    style={{ fontFamily: 'var(--font-display)' }}
                  >
                    Orders Coming In, At A Glance
                  </h1>
                  <p className="mt-3 max-w-3xl text-sm text-black/65 md:text-base">
                    A simple screen a restaurant can keep open to follow WhatsApp and web orders in
                    one place, even when the Meta business chat itself is not usable like a staff
                    inbox.
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => void fetchDashboard()}
                  className="inline-flex items-center gap-2 rounded-full bg-brand-dark px-4 py-2 text-sm font-bold text-white transition hover:opacity-90"
                >
                  <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                  Refresh
                </button>
                <Link
                  href="/"
                  className="inline-flex items-center gap-2 rounded-full border border-brand-dark/15 bg-white px-4 py-2 text-sm font-bold text-brand-dark transition hover:border-brand-orange hover:text-brand-orange"
                >
                  <ShoppingBag size={16} />
                  Open Menu
                </Link>
              </div>
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              <span className="rounded-full bg-white px-4 py-2 text-xs font-bold uppercase tracking-[0.15em] text-brand-dark shadow-sm">
                {usingDemoData ? 'Demo data mode' : 'Live data mode'}
              </span>
              <span className="rounded-full bg-white px-4 py-2 text-xs font-bold uppercase tracking-[0.15em] text-brand-dark shadow-sm">
                {RESTAURANT.name}
              </span>
              <span className="rounded-full bg-white px-4 py-2 text-xs font-bold uppercase tracking-[0.15em] text-brand-dark shadow-sm">
                {RESTAURANT.hours}
              </span>
            </div>

            {error && (
              <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                {error}
              </div>
            )}

            <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              <div className="rounded-[26px] bg-white p-4 shadow-[0_14px_50px_rgba(26,10,0,0.08)]">
                <div className="flex items-center gap-2 text-sm font-semibold text-black/65">
                  <Store size={16} />
                  Branch Status
                </div>
                <p className="mt-4 text-2xl font-black">Open</p>
                <p className="mt-1 text-sm text-black/45">{RESTAURANT.address}</p>
              </div>
              <div className="rounded-[26px] bg-white p-4 shadow-[0_14px_50px_rgba(26,10,0,0.08)]">
                <div className="flex items-center gap-2 text-sm font-semibold text-black/65">
                  <Receipt size={16} />
                  Total Orders
                </div>
                <p className="mt-4 text-3xl font-black">{summary.total}</p>
              </div>
              <div className="rounded-[26px] bg-white p-4 shadow-[0_14px_50px_rgba(26,10,0,0.08)]">
                <div className="flex items-center gap-2 text-sm font-semibold text-black/65">
                  <Clock3 size={16} />
                  Still In Progress
                </div>
                <p className="mt-4 text-3xl font-black">{summary.active}</p>
              </div>
              <div className="rounded-[26px] bg-white p-4 shadow-[0_14px_50px_rgba(26,10,0,0.08)]">
                <div className="flex items-center gap-2 text-sm font-semibold text-black/65">
                  <TimerReset size={16} />
                  Need Attention
                </div>
                <p className="mt-4 text-3xl font-black">{summary.pendingAction}</p>
              </div>
              <div className="rounded-[26px] bg-white p-4 shadow-[0_14px_50px_rgba(26,10,0,0.08)]">
                <div className="flex items-center gap-2 text-sm font-semibold text-black/65">
                  <Truck size={16} />
                  On The Road
                </div>
                <p className="mt-4 text-3xl font-black">{summary.inDelivery}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="mx-auto max-w-7xl px-4 py-8 md:px-6">
          <div className="grid gap-6 xl:grid-cols-[1.45fr_0.95fr]">
            <section>
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-black uppercase tracking-[0.2em] text-black/55">
                  Today&apos;s Order Board
                </h2>
                <p className="text-sm text-black/50">
                  {usingDemoData ? 'Showing sample orders for presentation' : 'Connected to current order data'}
                </p>
              </div>

              <div className="grid gap-4 xl:grid-cols-3">
                {groupedOrders.map(column => (
                  <div
                    key={column.value}
                    className={`rounded-[28px] border p-4 shadow-[0_18px_60px_rgba(26,10,0,0.08)] ${column.accent}`}
                  >
                    <div className="mb-4 flex items-center justify-between">
                      <h3 className="text-sm font-black uppercase tracking-[0.18em] text-black/65">
                        {column.label}
                      </h3>
                      <span className="rounded-full bg-white px-2.5 py-1 text-xs font-bold text-black/60">
                        {column.items.length}
                      </span>
                    </div>

                    <div className="space-y-3">
                      {column.items.length === 0 ? (
                        <div className="rounded-2xl border border-black/5 bg-white/70 px-4 py-6 text-center text-sm text-black/40">
                          No orders here
                        </div>
                      ) : (
                        column.items.map(order => (
                          <button
                            key={order.id}
                            onClick={() => setSelectedId(order.id)}
                            className={`w-full rounded-[22px] border bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 ${
                              selectedOrder?.id === order.id
                                ? 'border-brand-orange ring-2 ring-brand-orange/15'
                                : 'border-black/5'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="text-base font-black text-brand-dark">
                                  #{order.order_number || order.id.slice(0, 8).toUpperCase()}
                                </p>
                                <p className="mt-1 text-sm font-semibold text-black/70">
                                  {order.customer_name || order.customer_phone}
                                </p>
                              </div>
                              <span
                                className={`rounded-full px-2.5 py-1 text-[11px] font-bold uppercase ${statusBadge(order.status)}`}
                              >
                                {displayStatus(order.status)}
                              </span>
                            </div>

                            <div className="mt-3 grid grid-cols-2 gap-2 text-sm text-black/55">
                              <span>{formatMoney(order.total_amount)}</span>
                              <span className="text-right">{channelLabel(order.channel)}</span>
                              <span>{paymentLabel(order.payment_status)}</span>
                              <span className="text-right">{formatTimeSince(order.created_at)}</span>
                            </div>
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <aside className="rounded-[30px] bg-white p-5 shadow-[0_22px_80px_rgba(26,10,0,0.10)]">
              {selectedOrder ? (
                <div className="space-y-6">
                  <div className="border-b border-black/6 pb-5">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-bold uppercase tracking-[0.25em] text-black/40">
                          Selected Order
                        </p>
                        <h2
                          className="mt-2 text-3xl font-black"
                          style={{ fontFamily: 'var(--font-display)' }}
                        >
                          #{selectedOrder.order_number || selectedOrder.id.slice(0, 8).toUpperCase()}
                        </h2>
                        <p className="mt-1 text-sm text-black/50">
                          {channelLabel(selectedOrder.channel)} • {formatTimeSince(selectedOrder.created_at)}
                        </p>
                      </div>
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-bold uppercase ${statusBadge(selectedOrder.status)}`}
                      >
                        {displayStatus(selectedOrder.status)}
                      </span>
                    </div>

                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <div className="rounded-2xl bg-[#f8f2ea] p-4">
                        <p className="text-xs font-bold uppercase tracking-[0.18em] text-black/40">
                          Customer
                        </p>
                        <p className="mt-2 font-bold">{selectedOrder.customer_name || 'No customer name'}</p>
                        <p className="text-sm text-black/55">{selectedOrder.customer_phone}</p>
                      </div>
                      <div className="rounded-2xl bg-[#f8f2ea] p-4">
                        <p className="text-xs font-bold uppercase tracking-[0.18em] text-black/40">
                          Payment
                        </p>
                        <p className="mt-2 font-bold">{paymentLabel(selectedOrder.payment_status)}</p>
                        <p className="text-sm text-black/55">{formatMoney(selectedOrder.total_amount)}</p>
                      </div>
                    </div>

                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <a
                        href={`tel:+${selectedOrder.customer_phone}`}
                        className="inline-flex items-center justify-center gap-2 rounded-2xl border border-black/8 bg-white px-4 py-3 text-sm font-bold text-brand-dark transition hover:border-brand-orange hover:text-brand-orange"
                      >
                        <PhoneCall size={16} />
                        Call Customer
                      </a>
                      <a
                        href={`https://wa.me/${selectedOrder.customer_phone}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center justify-center gap-2 rounded-2xl border border-black/8 bg-white px-4 py-3 text-sm font-bold text-brand-dark transition hover:border-brand-orange hover:text-brand-orange"
                      >
                        <MessageIcon />
                        Open WhatsApp
                      </a>
                    </div>

                    <div className="mt-4 rounded-2xl border border-black/6 p-4">
                      <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-black/40">
                        <MapPin size={14} />
                        Delivery Address
                      </p>
                      <p className="mt-2 text-sm font-medium text-black/70">
                        {selectedOrder.delivery_address}
                      </p>
                    </div>
                  </div>

                  <div>
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-sm font-black uppercase tracking-[0.18em] text-black/40">
                        Order Progress
                      </h3>
                      <p className="text-sm font-bold text-brand-orange">
                        {STATUS_PROGRESS[selectedOrder.status]}/6
                      </p>
                    </div>
                    <div className="grid grid-cols-6 gap-2">
                      {KANBAN_STATUSES.map((status, index) => {
                        const active = STATUS_PROGRESS[selectedOrder.status] >= index + 1
                        return (
                          <div
                            key={status.value}
                            className={`h-2 rounded-full ${active ? 'bg-brand-orange' : 'bg-[#f0e4d6]'}`}
                          />
                        )
                      })}
                    </div>
                  </div>

                  {selectedOrder.notes && (
                    <div className="rounded-[24px] border border-orange-200 bg-orange-50 p-4">
                      <p className="text-xs font-bold uppercase tracking-[0.18em] text-black/40">
                        Customer Note
                      </p>
                      <p className="mt-2 text-sm font-medium text-black/70">{selectedOrder.notes}</p>
                    </div>
                  )}

                  <div>
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-sm font-black uppercase tracking-[0.18em] text-black/40">
                        Items
                      </h3>
                      <p className="text-lg font-black">{formatMoney(selectedOrder.total_amount)}</p>
                    </div>
                    <div className="space-y-2">
                      {selectedOrder.items.map(item => (
                        <div key={`${selectedOrder.id}-${item.item_id}`} className="rounded-2xl bg-[#fff8f0] p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-bold">
                                {item.quantity}x {item.name}
                              </p>
                              <p className="text-sm text-black/50">
                                {formatMoney(item.unit_price)} each
                              </p>
                            </div>
                            <p className="font-black">{formatMoney(item.total_price)}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="mb-3 text-sm font-black uppercase tracking-[0.18em] text-black/40">
                      Quick Actions
                    </h3>
                    {usingDemoData ? (
                      <div className="rounded-2xl border border-dashed border-black/10 bg-[#faf4ed] px-4 py-3 text-sm text-black/45">
                        Demo mode is read-only. Switch to live orders to update statuses here.
                      </div>
                    ) : selectedOrder.allowed_next_statuses.length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-black/10 bg-[#faf4ed] px-4 py-3 text-sm text-black/45">
                        This order has no further status actions.
                      </div>
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        {selectedOrder.allowed_next_statuses.map(nextStatus => (
                          <button
                            key={nextStatus}
                            onClick={() => void advanceOrder(nextStatus)}
                            disabled={mutating}
                            className="rounded-full bg-brand-dark px-4 py-2 text-sm font-bold text-white transition hover:bg-brand-orange disabled:opacity-60"
                          >
                            {nextStatus === 'confirmed' && <CheckCircle2 size={14} className="mr-2 inline" />}
                            {nextStatus === 'preparing' && <ChefHat size={14} className="mr-2 inline" />}
                            {nextStatus === 'ready' && <PackageCheck size={14} className="mr-2 inline" />}
                            {nextStatus === 'out_for_delivery' && <Bike size={14} className="mr-2 inline" />}
                            Move to {displayStatus(nextStatus)}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <h3 className="mb-3 text-sm font-black uppercase tracking-[0.18em] text-black/40">
                      Timeline
                    </h3>
                    <div className="space-y-3">
                      {selectedOrder.events.map(event => (
                        <div key={event.id} className="rounded-2xl border border-black/6 p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-bold">{displayEvent(event.event_type)}</p>
                              <p className="mt-1 text-sm text-black/50">
                                {event.to_status ? `Status: ${displayStatus(event.to_status)}` : 'Order update'}
                              </p>
                              {event.reason_note && (
                                <p className="mt-2 text-sm text-black/60">{event.reason_note}</p>
                              )}
                            </div>
                            <div className="text-right text-xs uppercase tracking-[0.15em] text-black/40">
                              <p>{event.actor_label || event.actor_type}</p>
                              <p className="mt-1">{formatDate(event.created_at)}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex min-h-[520px] items-center justify-center rounded-[24px] border border-dashed border-black/10 bg-[#faf4ed] text-center">
                  <div>
                    <p className="text-lg font-black">No order selected</p>
                    <p className="mt-2 text-sm text-black/45">
                      Once orders are available, details will appear here.
                    </p>
                  </div>
                </div>
              )}
            </aside>
          </div>
        </div>
      </div>
    </>
  )
}

function MessageIcon() {
  return (
    <span
      className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-[#25D366] text-[10px] font-black text-white"
      aria-hidden="true"
    >
      W
    </span>
  )
}
