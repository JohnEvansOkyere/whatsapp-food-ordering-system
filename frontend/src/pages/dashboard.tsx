import { useEffect, useMemo, useRef, useState } from 'react'
import Head from 'next/head'
import Link from 'next/link'
import {
  Bike,
  BellRing,
  ChevronRight,
  CheckCircle2,
  ChefHat,
  CircleAlert,
  MapPin,
  PackageCheck,
  PhoneCall,
  RefreshCw,
  Search,
  X,
} from 'lucide-react'
import { RESTAURANT } from '@/lib/menuData'
import { clearStaffSession, getStaffSession, staffFetch } from '@/lib/staffAuth'
import { Branch, FALLBACK_BRANCHES } from '@/lib/branches'

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

interface OrderItem {
  item_id: string
  name: string
  quantity: number
  unit_price: number
  total_price: number
  selections?: Array<{ name?: string | null; option_id: string }>
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

interface OrderDetail extends OrderListItem {
  delivery_address: string
  delivery_latitude?: number | null
  delivery_longitude?: number | null
  payment_method?: 'momo' | 'cash'
  subtotal_amount: number
  notes?: string | null
  items: OrderItem[]
  allowed_next_statuses: OrderStatus[]
  events: OrderEvent[]
}

type BoardView = 'live' | 'attention' | 'closed'

interface BoardColumn {
  value: OrderStatus
  label: string
  dot: string
}

const BOARD_VIEWS: Record<BoardView, BoardColumn[]> = {
  live: [
    { value: 'new', label: 'New', dot: 'bg-amber-500' },
    { value: 'confirmed', label: 'Accepted', dot: 'bg-sky-500' },
    { value: 'preparing', label: 'Preparing', dot: 'bg-orange-500' },
    { value: 'ready', label: 'Ready', dot: 'bg-emerald-500' },
    { value: 'out_for_delivery', label: 'Delivery', dot: 'bg-indigo-500' },
  ],
  attention: [
    { value: 'delayed', label: 'Delayed', dot: 'bg-rose-500' },
    { value: 'cancel_requested', label: 'Cancel requests', dot: 'bg-red-500' },
  ],
  closed: [
    { value: 'delivered', label: 'Delivered', dot: 'bg-emerald-600' },
    { value: 'cancelled', label: 'Cancelled', dot: 'bg-gray-500' },
    { value: 'rejected', label: 'Rejected', dot: 'bg-slate-600' },
  ],
}

const STATUS_PROGRESS: Record<OrderStatus, number> = {
  new: 1,
  confirmed: 2,
  preparing: 3,
  ready: 4,
  out_for_delivery: 5,
  delayed: 3,
  delivered: 6,
  cancel_requested: 2,
  cancelled: 2,
  rejected: 1,
}

const CLOSED_PAGE_SIZE = 15

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
    case 'delayed':
      return 'Delayed'
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
    case 'order_delayed':
      return 'Order delayed'
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

function needsAcceptanceAlert(order: OrderListItem) {
  return (
    order.status === 'new' &&
    Date.now() - new Date(order.created_at).getTime() > 5 * 60 * 1000
  )
}

function operationalProgressStatus(order: OrderDetail): OrderStatus {
  if (!['delayed', 'cancel_requested'].includes(order.status)) return order.status
  const exceptionEvent = [...order.events]
    .reverse()
    .find(event => event.to_status === order.status && event.from_status)
  return exceptionEvent?.from_status || order.status
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

function channelBadge(channel: string) {
  if (channel === 'whatsapp') {
    return 'bg-[#E8FFF0] text-[#157347]'
  }
  if (channel === 'web') {
    return 'bg-[#EEF4FF] text-[#2457C5]'
  }
  return 'bg-[#F3EEE8] text-black/60'
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
    case 'delayed':
      return 'bg-rose-100 text-rose-800'
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
  const [liveOrders, setLiveOrders] = useState<OrderListItem[]>([])
  const [attentionOrders, setAttentionOrders] = useState<OrderListItem[]>([])
  const [closedOrders, setClosedOrders] = useState<OrderListItem[]>([])
  const [orderTotals, setOrderTotals] = useState({ live: 0, attention: 0, closed: 0 })
  const [selectedId, setSelectedId] = useState('')
  const [selectedOrder, setSelectedOrder] = useState<OrderDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [mutating, setMutating] = useState(false)
  const [error, setError] = useState('')
  const [selectedBranchId, setSelectedBranchId] = useState('')
  const [alertsEnabled, setAlertsEnabled] = useState(false)
  const [operationalBranches, setOperationalBranches] = useState<Branch[]>([])
  const [branchBusy, setBranchBusy] = useState(false)
  const [boardView, setBoardView] = useState<BoardView>('live')
  const [search, setSearch] = useState('')
  const [closedPage, setClosedPage] = useState(1)
  const [etaMinutes, setEtaMinutes] = useState('40')
  const [exceptionStatus, setExceptionStatus] = useState<OrderStatus | ''>('')
  const [exceptionReason, setExceptionReason] = useState('')
  const previousIncomingIds = useRef<Set<string> | null>(null)
  const audioContext = useRef<AudioContext | null>(null)
  const closedRequestId = useRef(0)
  const detailRequestId = useRef(0)

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const session = getStaffSession()
  const staffRole = session?.staff.role || ''
  const canManageBranch = ['tenant_owner', 'manager'].includes(staffRole)
  const canManagePayments = ['tenant_owner', 'manager', 'cashier'].includes(staffRole)
  const canRetryNotifications = ['tenant_owner', 'manager', 'support'].includes(staffRole)
  const branchSource = operationalBranches.length > 0
    ? operationalBranches
    : FALLBACK_BRANCHES
  const staffBranches = branchSource.filter(branch =>
    session?.staff.branch_ids.includes(branch.id)
  )
  const selectedBranch = staffBranches.find(branch => branch.id === selectedBranchId)

  const playNewOrderSound = () => {
    const context = audioContext.current
    if (!context) return
    const oscillator = context.createOscillator()
    const gain = context.createGain()
    oscillator.frequency.setValueAtTime(740, context.currentTime)
    gain.gain.setValueAtTime(0.0001, context.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.22, context.currentTime + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.45)
    oscillator.connect(gain)
    gain.connect(context.destination)
    oscillator.start()
    oscillator.stop(context.currentTime + 0.5)
  }

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

  const toggleBranchOrdering = async () => {
    if (!selectedBranch) return
    setBranchBusy(true)
    setError('')
    try {
      const response = await staffFetch(
        `${apiUrl}/admin/branches/${selectedBranch.id}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            accepting_orders: !selectedBranch.accepting_orders,
          }),
        }
      )
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to update branch ordering')
      }
      setOperationalBranches(current =>
        current.map(branch => branch.id === data.id ? data : branch)
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update branch ordering')
    } finally {
      setBranchBusy(false)
    }
  }

  const fetchOperationalOrders = async () => {
    if (!selectedBranchId) return
    setLoading(true)
    setError('')

    try {
      const liveParams = new URLSearchParams({ scope: 'live', limit: '200', branch_id: selectedBranchId })
      const attentionParams = new URLSearchParams({ scope: 'attention', limit: '200', branch_id: selectedBranchId })
      const [liveResponse, attentionResponse] = await Promise.all([
        staffFetch(`${apiUrl}/admin/orders?${liveParams.toString()}`),
        staffFetch(`${apiUrl}/admin/orders?${attentionParams.toString()}`),
      ])
      if (!liveResponse.ok || !attentionResponse.ok) throw new Error('Failed to load live orders')
      const [liveData, attentionData] = await Promise.all([
        liveResponse.json(),
        attentionResponse.json(),
      ])
      const nextLiveOrders: OrderListItem[] = Array.isArray(liveData.items) ? liveData.items : []
      const nextAttentionOrders: OrderListItem[] = Array.isArray(attentionData.items) ? attentionData.items : []
      setLiveOrders(nextLiveOrders)
      setAttentionOrders(nextAttentionOrders)
      setOrderTotals(current => ({
        ...current,
        live: Number(liveData.total || 0),
        attention: Number(attentionData.total || 0),
      }))
      const incomingIds = new Set(
        nextLiveOrders
          .filter((order: OrderListItem) => order.status === 'new')
          .map((order: OrderListItem) => order.id)
      )
      const hasNewArrival =
        previousIncomingIds.current !== null &&
        Array.from(incomingIds).some(id => !previousIncomingIds.current?.has(id))
      if (hasNewArrival) playNewOrderSound()
      previousIncomingIds.current = incomingIds
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load dashboard'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const fetchClosedOrders = async () => {
    if (!selectedBranchId) return
    const requestId = ++closedRequestId.current
    const params = new URLSearchParams({
      scope: 'closed',
      limit: String(CLOSED_PAGE_SIZE),
      offset: String((closedPage - 1) * CLOSED_PAGE_SIZE),
      branch_id: selectedBranchId,
    })
    if (search.trim()) params.set('q', search.trim())
    try {
      const response = await staffFetch(`${apiUrl}/admin/orders?${params.toString()}`)
      if (!response.ok) throw new Error('Failed to load completed orders')
      const data = await response.json()
      if (requestId !== closedRequestId.current) return
      setClosedOrders(Array.isArray(data.items) ? data.items : [])
      setOrderTotals(current => ({ ...current, closed: Number(data.total || 0) }))
    } catch (err) {
      if (requestId !== closedRequestId.current) return
      setError(err instanceof Error ? err.message : 'Failed to load completed orders')
    }
  }

  const fetchOrderDetail = async (orderId: string) => {
    const requestId = ++detailRequestId.current
    setLoadingDetail(true)
    setError('')
    try {
      const response = await staffFetch(`${apiUrl}/admin/orders/${orderId}`)
      if (!response.ok) throw new Error('Failed to load order details')
      const data = await response.json()
      if (requestId !== detailRequestId.current) return
      setSelectedOrder(data)
    } catch (err) {
      if (requestId !== detailRequestId.current) return
      setSelectedOrder(null)
      setError(err instanceof Error ? err.message : 'Failed to load order details')
    } finally {
      if (requestId === detailRequestId.current) setLoadingDetail(false)
    }
  }

  const refreshDashboard = async () => {
    await Promise.all([fetchOperationalOrders(), fetchClosedOrders()])
  }

  useEffect(() => {
    const currentSession = getStaffSession()
    if (!currentSession) {
      window.location.assign('/admin/login')
      return
    }
    setSelectedBranchId(currentSession.staff.branch_ids[0] || '')
    void loadStaffBranches()
  }, [])

  useEffect(() => {
    if (!selectedBranchId) return
    previousIncomingIds.current = null
    setSelectedId('')
    setSelectedOrder(null)
    void fetchOperationalOrders()
  }, [selectedBranchId])

  useEffect(() => {
    if (!selectedBranchId) return
    const interval = window.setInterval(() => {
      void refreshDashboard()
    }, 15000)
    return () => window.clearInterval(interval)
  }, [selectedBranchId, closedPage, search])

  useEffect(() => {
    const timeout = window.setTimeout(() => void fetchClosedOrders(), 300)
    return () => window.clearTimeout(timeout)
  }, [selectedBranchId, closedPage, search])

  useEffect(() => {
    if (!selectedId) {
      detailRequestId.current += 1
      setSelectedOrder(null)
      setLoadingDetail(false)
      return
    }
    setEtaMinutes('40')
    setExceptionStatus('')
    setExceptionReason('')
    setSelectedOrder(null)
    void fetchOrderDetail(selectedId)
  }, [selectedId])

  useEffect(() => {
    if (staffRole === 'support') setBoardView('attention')
  }, [staffRole])

  const summary = useMemo(
    () => ({
      live: orderTotals.live,
      incoming: liveOrders.filter(order => order.status === 'new').length,
      preparing: liveOrders.filter(order => order.status === 'preparing').length,
      ready: liveOrders.filter(order => order.status === 'ready').length,
      inDelivery: liveOrders.filter(order => order.status === 'out_for_delivery').length,
      attention: orderTotals.attention,
      closed: orderTotals.closed,
    }),
    [liveOrders, orderTotals]
  )

  const groupedOrders = useMemo(
    () => {
      const sourceOrders = boardView === 'attention' ? attentionOrders : liveOrders
      let columns = BOARD_VIEWS[boardView]
      if (boardView === 'live' && staffRole === 'kitchen') {
        columns = columns.filter(column => ['new', 'confirmed', 'preparing', 'ready'].includes(column.value))
      }
      if (boardView === 'live' && staffRole === 'dispatch') {
        columns = columns.filter(column => ['ready', 'out_for_delivery'].includes(column.value))
      }
      return columns.map(column => ({
        ...column,
        items: sourceOrders.filter(order => {
          if (order.status !== column.value) return false
          const query = search.trim().toLowerCase()
          if (!query) return true
          return [order.order_number, order.customer_name, order.customer_phone]
            .filter(Boolean)
            .join(' ')
            .toLowerCase()
            .includes(query)
        }),
      }))
    },
    [attentionOrders, boardView, liveOrders, search, staffRole]
  )

  const closedPageCount = Math.max(1, Math.ceil(orderTotals.closed / CLOSED_PAGE_SIZE))

  useEffect(() => {
    setClosedPage(1)
  }, [search, selectedBranchId])

  useEffect(() => {
    if (closedPage > closedPageCount) setClosedPage(closedPageCount)
  }, [closedPage, closedPageCount])

  const advanceOrder = async (
    nextStatus: OrderStatus,
    options: { etaMinutes?: number; reasonNote?: string } = {}
  ) => {
    if (!selectedOrder) return

    const actionEta = options.etaMinutes ?? null
    const reasonNote = options.reasonNote?.trim() || null
    const needsReason = ['delayed', 'rejected', 'cancel_requested', 'cancelled'].includes(nextStatus)
    if (nextStatus === 'confirmed' && selectedOrder.status === 'new') {
      if (actionEta == null || !Number.isFinite(actionEta) || actionEta < 10 || actionEta > 240) {
        setError('Enter an ETA between 10 and 240 minutes')
        return
      }
    }
    if (needsReason && !reasonNote) {
      setError(`Enter a reason for ${displayStatus(nextStatus).toLowerCase()}`)
      return
    }

    setMutating(true)
    setError('')
    try {
      const res = await staffFetch(`${apiUrl}/admin/orders/${selectedOrder.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: nextStatus,
          reason_code: needsReason ? 'staff_exception' : null,
          reason_note: reasonNote,
          eta_minutes: actionEta,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to update order')
      }

      setSelectedOrder(data)
      setExceptionStatus('')
      setExceptionReason('')
      await refreshDashboard()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update order'
      setError(message)
    } finally {
      setMutating(false)
    }
  }

  const markCashCollected = async () => {
    if (!selectedOrder || selectedOrder.payment_method !== 'cash') return
    setMutating(true)
    setError('')
    try {
      const response = await staffFetch(
        `${apiUrl}/admin/orders/${selectedOrder.id}/payment`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 'paid', provider: 'manual' }),
        }
      )
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to update payment')
      }
      setSelectedOrder(data)
      await refreshDashboard()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update payment')
    } finally {
      setMutating(false)
    }
  }

  const retryWhatsAppUpdate = async () => {
    if (!selectedOrder) return
    setMutating(true)
    setError('')
    try {
      const response = await staffFetch(
        `${apiUrl}/admin/orders/${selectedOrder.id}/notifications/retry`,
        { method: 'POST' }
      )
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !data.sent) {
        throw new Error(data.detail || 'WhatsApp update could not be sent')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'WhatsApp retry failed')
    } finally {
      setMutating(false)
    }
  }

  return (
    <>
      <Head>
        <title>{`${RESTAURANT.name} Order Dashboard`}</title>
        <meta
          name="description"
          content="Protected branch-scoped kitchen dashboard for restaurant staff."
        />
      </Head>

      <div className="min-h-screen bg-[#f6f5f2] text-[#1f1f1f]">
        <header className="sticky top-0 z-30 border-b border-black/[0.07] bg-white/95 backdrop-blur">
          <div className="mx-auto flex h-16 max-w-[1600px] items-center gap-3 px-4 md:px-6">
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
              <button className="rounded-lg bg-[#f4eee7] px-3 py-2 text-sm font-bold text-[#6b3b1e]">
                Orders
              </button>
              <Link
                href="/dashboard/settings"
                className="rounded-lg px-3 py-2 text-sm font-semibold text-black/55 hover:bg-black/[0.04] hover:text-black"
              >
                Menu & settings
              </Link>
              <Link
                href="/"
                className="rounded-lg px-3 py-2 text-sm font-semibold text-black/55 hover:bg-black/[0.04] hover:text-black"
              >
                Customer menu
              </Link>
            </nav>

            <div className="ml-auto flex items-center gap-2">
              {staffBranches.length > 1 ? (
                <select
                  aria-label="Select branch"
                  value={selectedBranchId}
                  onChange={event => {
                    setSelectedId('')
                    setSelectedBranchId(event.target.value)
                  }}
                  className="max-w-[110px] rounded-xl border border-black/10 bg-white px-3 py-2 text-sm font-bold outline-none focus:border-[#c56a2d] sm:max-w-[150px] md:max-w-none"
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
                aria-label={alertsEnabled ? 'Order sound enabled' : 'Enable order sound'}
                title={alertsEnabled ? 'Order sound enabled' : 'Enable order sound'}
                onClick={() => {
                  if (!audioContext.current) audioContext.current = new AudioContext()
                  setAlertsEnabled(true)
                  playNewOrderSound()
                }}
                className={`grid h-10 w-10 place-items-center rounded-xl border ${alertsEnabled ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-black/10 bg-white text-black/55'}`}
              >
                <BellRing size={17} />
              </button>
              <button
                type="button"
                aria-label="Refresh orders"
                title="Refresh orders"
                onClick={() => void refreshDashboard()}
                className="grid h-10 w-10 place-items-center rounded-xl border border-black/10 bg-white text-black/55 hover:text-black"
              >
                <RefreshCw size={17} className={loading ? 'animate-spin' : ''} />
              </button>
              <button
                type="button"
                onClick={() => {
                  clearStaffSession()
                  window.location.assign('/admin/login')
                }}
                className="hidden rounded-xl border border-black/10 px-3 py-2 text-sm font-bold text-black/55 hover:text-black sm:block"
              >
                Sign out
              </button>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-[1600px] px-4 py-6 md:px-6 md:py-8">
          {!selectedBranch?.accepting_orders && selectedBranch && (
            <div className="mb-5 flex items-center justify-between gap-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              <span className="flex items-center gap-2 font-semibold">
                <CircleAlert size={17} /> New orders are paused for {selectedBranch.name}.
              </span>
              {canManageBranch && (
                <button onClick={() => void toggleBranchOrdering()} className="shrink-0 font-black underline">
                  Resume
                </button>
              )}
            </div>
          )}

          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-bold text-[#b15c25]">Live operations</p>
              <h1 className="mt-1 text-3xl font-black tracking-tight md:text-4xl">Orders</h1>
              <p className="mt-2 text-sm text-black/50">Open a card to view details and move it to the next stage.</p>
            </div>
            <div className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-black/[0.07] bg-black/[0.07] shadow-sm sm:grid-cols-4">
              {[
                ['New', summary.incoming],
                ['Preparing', summary.preparing],
                ['Ready', summary.ready],
                ['Delivery', summary.inDelivery],
              ].map(([label, value]) => (
                <div key={String(label)} className="min-w-[105px] bg-white px-3 py-3">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-black/40">{label}</p>
                  <p className="mt-1 text-xl font-black">{value}</p>
                </div>
              ))}
            </div>
          </div>

          {error && (
            <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-900">
              {error}
            </div>
          )}

          <section className="mt-7" aria-label="Order board">
            <div className="flex flex-col gap-3 border-b border-black/[0.08] pb-4 lg:flex-row lg:items-center">
              <div className="flex gap-1 overflow-x-auto rounded-xl bg-black/[0.04] p-1">
                {([
                  ['live', 'Live orders', summary.live],
                  ['attention', 'Needs attention', summary.attention],
                  ['closed', 'Completed', summary.closed],
                ] as Array<[BoardView, string, number]>).map(([value, label, count]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setBoardView(value)}
                    className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm font-bold transition ${boardView === value ? 'bg-white text-black shadow-sm' : 'text-black/50 hover:text-black'}`}
                  >
                    {label} <span className="ml-1 text-black/35">{count}</span>
                  </button>
                ))}
              </div>
              <label className="relative lg:ml-auto lg:w-72">
                <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-black/35" />
                <input
                  value={search}
                  onChange={event => setSearch(event.target.value)}
                  placeholder="Search order or customer"
                  className="h-11 w-full rounded-xl border border-black/10 bg-white pl-10 pr-4 text-sm outline-none transition focus:border-[#c56a2d] focus:ring-2 focus:ring-orange-100"
                />
              </label>
              <Link
                href="/dashboard/settings"
                className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-black/10 bg-white px-4 text-sm font-bold hover:border-black/25 md:hidden"
              >
                Menu & settings
              </Link>
            </div>

            {boardView === 'closed' ? (
              <div className="mt-5 overflow-hidden rounded-2xl border border-black/[0.08] bg-white shadow-sm">
                <div className="max-h-[650px] overflow-auto">
                  <table className="w-full min-w-[920px] border-collapse text-left">
                    <thead className="sticky top-0 z-10 bg-[#f1f0ed] text-xs font-black uppercase tracking-[0.08em] text-black/45">
                      <tr>
                        <th className="px-5 py-3.5">Order</th>
                        <th className="px-5 py-3.5">Customer</th>
                        <th className="px-5 py-3.5">Status</th>
                        <th className="px-5 py-3.5">Payment</th>
                        <th className="px-5 py-3.5">Channel</th>
                        <th className="px-5 py-3.5 text-right">Total</th>
                        <th className="px-5 py-3.5">Date</th>
                        <th className="w-20 px-5 py-3.5"><span className="sr-only">Action</span></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-black/[0.06]">
                      {closedOrders.length === 0 ? (
                        <tr>
                          <td colSpan={8} className="px-5 py-16 text-center text-sm text-black/40">
                            No completed orders match your search.
                          </td>
                        </tr>
                      ) : closedOrders.map(order => (
                        <tr key={order.id} className="transition hover:bg-[#faf9f7]">
                          <td className="whitespace-nowrap px-5 py-4">
                            <p className="text-sm font-black">#{order.order_number || order.id.slice(0, 8).toUpperCase()}</p>
                            <p className="mt-1 text-xs text-black/40">{formatTimeSince(order.created_at)}</p>
                          </td>
                          <td className="px-5 py-4">
                            <p className="text-sm font-bold">{order.customer_name || 'No customer name'}</p>
                            <p className="mt-1 text-xs text-black/40">{order.customer_phone}</p>
                          </td>
                          <td className="px-5 py-4">
                            <span className={`inline-flex rounded-lg px-2.5 py-1.5 text-[11px] font-black uppercase ${statusBadge(order.status)}`}>
                              {order.status === 'delivered' ? 'Delivered' : displayStatus(order.status)}
                            </span>
                          </td>
                          <td className="whitespace-nowrap px-5 py-4 text-sm font-semibold text-black/60">
                            {paymentLabel(order.payment_status)}
                          </td>
                          <td className="px-5 py-4">
                            <span className={`inline-flex rounded-md px-2 py-1 text-[10px] font-black uppercase ${channelBadge(order.channel)}`}>
                              {channelLabel(order.channel)}
                            </span>
                          </td>
                          <td className="whitespace-nowrap px-5 py-4 text-right text-sm font-black">
                            {formatMoney(order.total_amount)}
                          </td>
                          <td className="whitespace-nowrap px-5 py-4">
                            <p className="text-sm font-semibold text-black/65">{formatDate(order.created_at)}</p>
                            <p className="mt-1 text-xs text-black/40">{formatTimeSince(order.created_at)}</p>
                          </td>
                          <td className="px-5 py-4 text-right">
                            <button
                              type="button"
                              onClick={() => setSelectedId(order.id)}
                              className="inline-flex items-center gap-1 rounded-lg border border-black/10 px-3 py-2 text-xs font-black hover:border-black/25"
                            >
                              View <ChevronRight size={14} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="flex flex-col gap-3 border-t border-black/[0.07] px-5 py-4 text-sm sm:flex-row sm:items-center sm:justify-between">
                  <p className="text-black/45">
                    {orderTotals.closed === 0
                      ? '0 orders'
                      : `Showing ${(closedPage - 1) * CLOSED_PAGE_SIZE + 1}–${Math.min(closedPage * CLOSED_PAGE_SIZE, orderTotals.closed)} of ${orderTotals.closed}`}
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={closedPage === 1}
                      onClick={() => setClosedPage(page => Math.max(1, page - 1))}
                      className="rounded-lg border border-black/10 px-3 py-2 text-xs font-black disabled:cursor-not-allowed disabled:opacity-35"
                    >
                      Previous
                    </button>
                    <span className="min-w-20 text-center text-xs font-bold text-black/50">
                      Page {closedPage} of {closedPageCount}
                    </span>
                    <button
                      type="button"
                      disabled={closedPage === closedPageCount}
                      onClick={() => setClosedPage(page => Math.min(closedPageCount, page + 1))}
                      className="rounded-lg border border-black/10 px-3 py-2 text-xs font-black disabled:cursor-not-allowed disabled:opacity-35"
                    >
                      Next
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-5 grid auto-cols-[minmax(270px,1fr)] grid-flow-col gap-4 overflow-x-auto pb-5">
                {groupedOrders.map(column => (
                  <div key={column.value} className="min-h-[460px] rounded-2xl bg-[#ebeae6] p-3">
                    <div className="flex items-center gap-2 px-1 py-1">
                      <span className={`h-2.5 w-2.5 rounded-full ${column.dot}`} />
                      <h2 className="text-sm font-black">{column.label}</h2>
                      <span className="ml-auto rounded-full bg-white px-2.5 py-1 text-xs font-black text-black/50">
                        {column.items.length}
                      </span>
                    </div>

                    <div className="mt-3 space-y-3">
                      {column.items.length === 0 ? (
                        <div className="rounded-xl border border-dashed border-black/10 px-4 py-8 text-center text-sm text-black/35">
                          No orders
                        </div>
                      ) : column.items.map(order => (
                        <button
                          key={order.id}
                          type="button"
                          onClick={() => setSelectedId(order.id)}
                          className={`group w-full rounded-2xl border bg-white p-4 text-left shadow-[0_2px_10px_rgba(0,0,0,0.04)] transition hover:-translate-y-0.5 hover:border-black/20 hover:shadow-md ${needsAcceptanceAlert(order) ? 'border-red-300' : 'border-black/[0.06]'}`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="text-sm font-black">#{order.order_number || order.id.slice(0, 8).toUpperCase()}</p>
                              <p className="mt-1 text-xs text-black/40">{formatTimeSince(order.created_at)}</p>
                            </div>
                            <p className="text-sm font-black">{formatMoney(order.total_amount)}</p>
                          </div>
                          <p className="mt-4 truncate text-sm font-semibold text-black/70">
                            {order.customer_name || order.customer_phone}
                          </p>
                          <p className="mt-1 text-xs text-black/40">{paymentLabel(order.payment_status)}</p>
                          {needsAcceptanceAlert(order) && (
                            <p className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-red-50 px-2 py-1 text-xs font-bold text-red-700">
                              <CircleAlert size={13} /> Waiting over 5 min
                            </p>
                          )}
                          <div className="mt-4 flex items-center gap-2 border-t border-black/[0.06] pt-3">
                            <span className={`rounded-md px-2 py-1 text-[10px] font-black uppercase ${channelBadge(order.channel)}`}>
                              {channelLabel(order.channel)}
                            </span>
                            <span className="rounded-md bg-black/[0.04] px-2 py-1 text-[10px] font-black uppercase text-black/45">
                              {paymentLabel(order.payment_status)}
                            </span>
                            <ChevronRight size={16} className="ml-auto text-black/30 transition group-hover:translate-x-0.5 group-hover:text-black" />
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </main>

        {loadingDetail && selectedId && !selectedOrder && (
          <div className="fixed inset-0 z-50 bg-black/30" role="presentation" onMouseDown={() => setSelectedId('')}>
            <aside onMouseDown={event => event.stopPropagation()} className="ml-auto flex h-full w-full max-w-[500px] items-center justify-center bg-white shadow-2xl">
              <p className="text-sm font-bold text-black/45">Loading order details…</p>
            </aside>
          </div>
        )}

        {selectedOrder && (
          <div className="fixed inset-0 z-50 bg-black/30" role="presentation" onMouseDown={() => setSelectedId('')}>
            <aside
              role="dialog"
              aria-modal="true"
              aria-label="Order details"
              onMouseDown={event => event.stopPropagation()}
              className="ml-auto h-full w-full max-w-[500px] overflow-y-auto bg-white shadow-2xl"
            >
              <div className="sticky top-0 z-10 flex items-center justify-between border-b border-black/[0.07] bg-white/95 px-5 py-4 backdrop-blur">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-black/40">Order details</p>
                  <h2 className="mt-1 text-xl font-black">#{selectedOrder.order_number || selectedOrder.id.slice(0, 8).toUpperCase()}</h2>
                </div>
                <button onClick={() => setSelectedId('')} aria-label="Close order details" className="grid h-10 w-10 place-items-center rounded-xl bg-black/[0.05] hover:bg-black/[0.09]">
                  <X size={19} />
                </button>
              </div>

              <div className="space-y-6 p-5 pb-10">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-lg px-2.5 py-1.5 text-xs font-black uppercase ${statusBadge(selectedOrder.status)}`}>{displayStatus(selectedOrder.status)}</span>
                  <span className={`rounded-lg px-2.5 py-1.5 text-xs font-black uppercase ${channelBadge(selectedOrder.channel)}`}>{channelLabel(selectedOrder.channel)}</span>
                  <span className="text-sm text-black/45">{formatTimeSince(selectedOrder.created_at)}</span>
                </div>

                <div>
                  <div className="mb-2 flex items-center justify-between text-xs font-bold text-black/45">
                    <span>
                      Order progress
                      {operationalProgressStatus(selectedOrder) !== selectedOrder.status && (
                        <> · paused from {displayStatus(operationalProgressStatus(selectedOrder))}</>
                      )}
                    </span>
                    <span>{STATUS_PROGRESS[operationalProgressStatus(selectedOrder)]}/6</span>
                  </div>
                  <div className="grid grid-cols-6 gap-1.5">
                    {Array.from({ length: 6 }).map((_, index) => (
                      <span key={index} className={`h-2 rounded-full ${STATUS_PROGRESS[operationalProgressStatus(selectedOrder)] >= index + 1 ? 'bg-[#c56a2d]' : 'bg-black/[0.08]'}`} />
                    ))}
                  </div>
                </div>

                <section className="rounded-2xl bg-[#f6f5f2] p-4">
                  <p className="text-xs font-black uppercase tracking-[0.14em] text-black/40">Next step</p>
                  {selectedOrder.allowed_next_statuses.filter(status => !['delayed', 'cancel_requested', 'cancelled', 'rejected'].includes(status)).length === 0 ? (
                    <p className="mt-3 text-sm text-black/50">No normal status action is available.</p>
                  ) : (
                    <div className="mt-3 grid gap-2">
                      {selectedOrder.allowed_next_statuses
                        .filter(status => !['delayed', 'cancel_requested', 'cancelled', 'rejected'].includes(status))
                        .map(nextStatus => {
                          const needsEta = nextStatus === 'confirmed' && selectedOrder.status === 'new'
                          const isResume = ['delayed', 'cancel_requested'].includes(selectedOrder.status)
                          return (
                            <div key={nextStatus} className="grid gap-2">
                              {needsEta && (
                                <label className="text-sm font-bold text-black/65">
                                  Ready or dispatch ETA (minutes)
                                  <input
                                    type="number"
                                    min={10}
                                    max={240}
                                    value={etaMinutes}
                                    onChange={event => setEtaMinutes(event.target.value)}
                                    className="mt-2 h-11 w-full rounded-xl border border-black/10 bg-white px-3 outline-none focus:border-[#c56a2d]"
                                  />
                                </label>
                              )}
                              <button
                                onClick={() => void advanceOrder(nextStatus, needsEta ? { etaMinutes: Number(etaMinutes) } : {})}
                                disabled={mutating}
                                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#1d1109] px-4 text-sm font-black text-white hover:bg-[#b15c25] disabled:opacity-50"
                              >
                                {nextStatus === 'confirmed' && <CheckCircle2 size={17} />}
                                {nextStatus === 'preparing' && <ChefHat size={17} />}
                                {nextStatus === 'ready' && <PackageCheck size={17} />}
                                {nextStatus === 'out_for_delivery' && <Bike size={17} />}
                                {isResume
                                  ? `Return to ${displayStatus(nextStatus)}`
                                  : nextStatus === 'confirmed'
                                    ? 'Accept order'
                                    : nextStatus === 'preparing'
                                      ? 'Start preparing'
                                      : nextStatus === 'ready'
                                        ? 'Mark ready'
                                        : nextStatus === 'out_for_delivery'
                                          ? 'Send for delivery'
                                          : nextStatus === 'delivered'
                                            ? 'Mark delivered'
                                            : displayStatus(nextStatus)}
                              </button>
                            </div>
                          )
                        })}
                    </div>
                  )}
                </section>

                <section>
                  <div className="flex items-end justify-between gap-4">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-[0.14em] text-black/40">Customer</p>
                      <p className="mt-1 font-black">{selectedOrder.customer_name || 'No customer name'}</p>
                      <p className="text-sm text-black/50">{selectedOrder.customer_phone}</p>
                    </div>
                    <div className="flex gap-2">
                      <a href={`tel:+${selectedOrder.customer_phone}`} aria-label="Call customer" className="grid h-10 w-10 place-items-center rounded-xl border border-black/10 hover:border-black/30"><PhoneCall size={17} /></a>
                      <a href={`https://wa.me/${selectedOrder.customer_phone}`} target="_blank" rel="noreferrer" aria-label="Open WhatsApp" className="grid h-10 w-10 place-items-center rounded-xl border border-black/10 hover:border-black/30"><MessageIcon /></a>
                    </div>
                  </div>
                </section>

                <section className="border-t border-black/[0.07] pt-5">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-bold uppercase tracking-[0.14em] text-black/40">Items</p>
                    <p className="text-lg font-black">{formatMoney(selectedOrder.total_amount)}</p>
                  </div>
                  <div className="mt-3 divide-y divide-black/[0.06]">
                    {selectedOrder.items.map(item => (
                      <div key={`${selectedOrder.id}-${item.item_id}`} className="flex justify-between gap-4 py-3 first:pt-0">
                        <div>
                          <p className="text-sm font-bold">{item.quantity} × {item.name}</p>
                          {item.selections && item.selections.length > 0 && <p className="mt-1 text-xs text-black/45">{item.selections.map(selection => selection.name || selection.option_id).join(', ')}</p>}
                        </div>
                        <p className="shrink-0 text-sm font-black">{formatMoney(item.total_price)}</p>
                      </div>
                    ))}
                  </div>
                </section>

                <section className="rounded-2xl border border-black/[0.07] p-4">
                  <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-black/40"><MapPin size={14} /> Delivery address</p>
                  <p className="mt-2 text-sm font-semibold leading-6 text-black/70">{selectedOrder.delivery_address}</p>
                  {selectedOrder.delivery_latitude != null && selectedOrder.delivery_longitude != null ? (
                    <a href={`https://www.google.com/maps/search/?api=1&query=${selectedOrder.delivery_latitude},${selectedOrder.delivery_longitude}`} target="_blank" rel="noreferrer" className="mt-2 inline-flex text-sm font-black text-[#a94f1b] hover:underline">Open in Google Maps</a>
                  ) : (
                    <p className="mt-2 text-xs text-black/40">No map pin — call the customer for directions.</p>
                  )}
                </section>

                {selectedOrder.notes && (
                  <section className="rounded-2xl bg-amber-50 p-4">
                    <p className="text-xs font-bold uppercase tracking-[0.14em] text-amber-800/60">Customer note</p>
                    <p className="mt-2 text-sm font-medium leading-6 text-amber-950">{selectedOrder.notes}</p>
                  </section>
                )}

                <section className="flex items-center justify-between gap-3 rounded-2xl border border-black/[0.07] p-4">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.14em] text-black/40">Payment</p>
                    <p className="mt-1 text-sm font-black">{paymentLabel(selectedOrder.payment_status)}</p>
                  </div>
                  {canManagePayments && selectedOrder.payment_method === 'cash' && selectedOrder.payment_status !== 'paid' && (
                    <button disabled={mutating} onClick={() => void markCashCollected()} className="rounded-xl bg-emerald-600 px-3 py-2 text-xs font-black text-white disabled:opacity-50">Mark cash collected</button>
                  )}
                </section>

                {selectedOrder.allowed_next_statuses.some(status => ['delayed', 'cancel_requested', 'cancelled', 'rejected'].includes(status)) && (
                  <details className="rounded-2xl border border-red-100 bg-red-50/50 p-4">
                    <summary className="cursor-pointer text-sm font-black text-red-800">Exception actions</summary>
                    <div className="mt-3 grid gap-3">
                      <div className="flex flex-wrap gap-2">
                      {selectedOrder.allowed_next_statuses.filter(status => ['delayed', 'cancel_requested', 'cancelled', 'rejected'].includes(status)).map(status => (
                        <button
                          key={status}
                          type="button"
                          onClick={() => setExceptionStatus(status)}
                          className={`rounded-lg border px-3 py-2 text-xs font-bold ${exceptionStatus === status ? 'border-red-600 bg-red-600 text-white' : 'border-red-200 bg-white text-red-700'}`}
                        >
                          {displayStatus(status)}
                        </button>
                      ))}
                      </div>
                      {exceptionStatus && (
                        <>
                          <label className="text-sm font-bold text-red-900/70">
                            Reason
                            <textarea
                              rows={3}
                              value={exceptionReason}
                              onChange={event => setExceptionReason(event.target.value)}
                              placeholder={`Why is this order being marked ${displayStatus(exceptionStatus).toLowerCase()}?`}
                              className="mt-2 w-full rounded-xl border border-red-200 bg-white px-3 py-2 text-sm outline-none focus:border-red-500"
                            />
                          </label>
                          <button
                            type="button"
                            disabled={mutating || !exceptionReason.trim()}
                            onClick={() => void advanceOrder(exceptionStatus, { reasonNote: exceptionReason })}
                            className="rounded-xl bg-red-600 px-4 py-3 text-sm font-black text-white disabled:opacity-40"
                          >
                            Confirm {displayStatus(exceptionStatus).toLowerCase()}
                          </button>
                        </>
                      )}
                    </div>
                  </details>
                )}

                <details className="rounded-2xl border border-black/[0.07] p-4">
                  <summary className="cursor-pointer text-sm font-black">Order timeline ({selectedOrder.events.length})</summary>
                  <div className="mt-4 space-y-4 border-l border-black/10 pl-4">
                    {selectedOrder.events.map(event => (
                      <div key={event.id}>
                        <p className="text-sm font-bold">{displayEvent(event.event_type)}</p>
                        <p className="mt-1 text-xs text-black/45">{formatDate(event.created_at)} · {event.actor_label || event.actor_type}</p>
                        {event.reason_note && <p className="mt-1 text-sm text-black/60">{event.reason_note}</p>}
                      </div>
                    ))}
                  </div>
                </details>

                {canRetryNotifications && (
                  <button type="button" onClick={() => void retryWhatsAppUpdate()} disabled={mutating} className="w-full rounded-xl border border-black/10 px-4 py-3 text-sm font-bold text-black/60 hover:text-black disabled:opacity-50">Retry latest WhatsApp update</button>
                )}
              </div>
            </aside>
          </div>
        )}

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
