import { useEffect, useRef, useState } from 'react'
import { Minus, Plus, ShoppingCart, Trash2, Loader2, MapPin, MessageCircleMore, ShieldCheck, X } from 'lucide-react'
import { CartItem } from '../hooks/useCart'
import Image from 'next/image'
import { Branch, branchEta } from '@/lib/branches'
import { trackEvent } from '@/lib/analytics'
import CustomerAuthSheet from './CustomerAuthSheet'
import {
  CustomerSession,
  formatGhanaPhone,
  getCustomerSession,
} from '@/lib/customerAuth'

interface CartSidebarProps {
  items: CartItem[]
  totalItems: number
  totalPrice: number
  onAdd: (item: CartItem) => void
  onRemove: (id: string) => void
  onClear: () => void
  branch: Branch
  /** Renders a close control — supplied when hosted in the mobile sheet. */
  onClose?: () => void
}

interface CheckoutForm {
  phone: string
  name: string
  address: string
  landmark: string
  payment: 'momo' | 'cash'
}

type Step = 'cart' | 'checkout' | 'success'

export default function CartSidebar({
  items,
  totalItems,
  totalPrice,
  onAdd,
  onRemove,
  onClear,
  branch,
  onClose,
}: CartSidebarProps) {
  const [step, setStep] = useState<Step>('cart')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [orderId, setOrderId] = useState('')
  const [trackingCode, setTrackingCode] = useState('')
  const [trackingUrl, setTrackingUrl] = useState('')
  const [whatsappReceiptSent, setWhatsappReceiptSent] = useState<boolean | null>(null)
  const [confirmedTotal, setConfirmedTotal] = useState(0)
  const [operationalConsent, setOperationalConsent] = useState(false)
  const [rememberDetails, setRememberDetails] = useState(false)
  const [form, setForm] = useState<CheckoutForm>({
    phone: '',
    name: '',
    address: '',
    landmark: '',
    payment: 'momo',
  })
  const [session, setSession] = useState<CustomerSession | null>(null)
  const [authOpen, setAuthOpen] = useState(false)
  const idempotencyKeyRef = useRef('')
  const checkoutTotal = totalPrice + Number(branch.delivery_fee || 0)

  // The verified account phone is the authoritative SMS destination, so the
  // checkout form no longer asks for it.
  useEffect(() => {
    setSession(getCustomerSession())
  }, [])
  const minimumRemaining = Math.max(0, Number(branch.minimum_order || 0) - totalPrice)

  const handleFieldChange = (field: keyof CheckoutForm, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }))
    setError('')
  }

  const validateForm = (): boolean => {
    if (!session) {
      setError('Please sign in to place your order')
      setAuthOpen(true)
      return false
    }
    if (!form.address.trim()) { setError('Please enter your delivery address'); return false }
    if (!operationalConsent) {
      setError('Please allow operational updates for this order')
      return false
    }
    return true
  }

  const normalisePhone = (phone: string): string => {
    const clean = phone.replace(/\s/g, '')
    if (clean.startsWith('0')) return '233' + clean.slice(1)
    if (clean.startsWith('+')) return clean.slice(1)
    return clean
  }

  const handlePlaceOrder = async () => {
    if (!validateForm()) return
    setLoading(true)
    setError('')

    const orderItems = items.map((item: CartItem) => ({
      item_id: item.id,
      name: item.name,
      quantity: item.quantity,
      unit_price: item.price,
      total_price: item.price * item.quantity,
      selections: item.selectedOptions.map(option => ({
        group_id: option.groupId,
        option_id: option.optionId,
        name: option.name,
        price: option.price,
      })),
    }))

    if (!idempotencyKeyRef.current) {
      idempotencyKeyRef.current = window.crypto.randomUUID()
    }

    const payload = {
      customer_phone: session?.customer.phone || normalisePhone(form.phone),
      customer_name: form.name.trim() || null,
      delivery_address: form.address.trim(),
      items: orderItems,
      total_amount: checkoutTotal,
      payment_method: form.payment,
      notes: form.landmark.trim() || null,
      branch_id: branch.id,
      idempotency_key: idempotencyKeyRef.current,
      whatsapp_consent: operationalConsent,
      channel: 'web',
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${apiUrl}/public/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Order failed. Please try again.')
      }

      const data = await res.json()
      setOrderId(data.order_number || data.id?.slice(0, 8).toUpperCase() || 'N/A')
      setTrackingCode(data.tracking_code || '')
      setTrackingUrl(data.tracking_url || '')
      setWhatsappReceiptSent(
        typeof data.whatsapp_receipt_sent === 'boolean'
          ? data.whatsapp_receipt_sent
          : null
      )
      setConfirmedTotal(Number(data.total_amount || checkoutTotal))
      setStep('success')
      trackEvent(apiUrl, 'checkout_completed', branch.id, {
        order_total: Number(data.total_amount || checkoutTotal),
        payment_method: form.payment,
      })
      idempotencyKeyRef.current = ''
      if (rememberDetails) {
        window.localStorage.setItem(
          'restaurant-customer-v1',
          JSON.stringify({ phone: form.phone, name: form.name, address: form.address })
        )
      } else {
        window.localStorage.removeItem('restaurant-customer-v1')
      }
      onClear()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Something went wrong. Please try again.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setStep('cart')
    setOrderId('')
    setTrackingCode('')
    setTrackingUrl('')
    setWhatsappReceiptSent(null)
    setConfirmedTotal(0)
    idempotencyKeyRef.current = ''
    setForm({ phone: '', name: '', address: '', landmark: '', payment: 'momo' })
  }

  return (
    <div className="flex h-full flex-col bg-[#1a1a1a] text-white">
      {/* Cart Header */}
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
        <div className="flex items-center gap-2">
          <ShoppingCart size={18} className="text-[#f7b32b]" />
          <h2 className="text-base font-black tracking-wide">
            {step === 'cart' && 'My Cart'}
            {step === 'checkout' && 'Delivery Details'}
            {step === 'success' && 'Order Placed! 🎉'}
          </h2>
          {totalItems > 0 && step === 'cart' && (
            <span className="ml-1 rounded-full bg-[#f7b32b] px-2 py-0.5 text-xs font-black text-[#1a0a00]">
              {totalItems}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {items.length > 0 && step === 'cart' && (
            <button
              onClick={onClear}
              className="text-xs font-bold text-white/60 transition hover:text-[#f7b32b]"
            >
              Clear all
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              aria-label="Close cart"
              className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-white/80 transition hover:bg-white/20 hover:text-white"
            >
              <X size={16} strokeWidth={2.5} />
            </button>
          )}
        </div>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto">

        {/* ── CART STEP ── */}
        {step === 'cart' && (
          <>
            {items.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-white/5">
                  <ShoppingCart size={36} className="text-white/55" />
                </div>
                <p className="font-bold text-white/65">Empty cart</p>
                <p className="mt-1 text-xs text-white/55">Add items from the menu</p>
              </div>
            ) : (
              <div className="space-y-0 divide-y divide-white/5 px-4 pt-3">
                {items.map(item => (
                  <div key={item.cartKey} className="flex items-center gap-3 py-3">
                    <div className="relative h-12 w-12 flex-shrink-0 overflow-hidden rounded-xl">
                      <Image
                        src={item.image}
                        alt={item.name}
                        fill
                        className="object-cover"
                        sizes="48px"
                      />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-bold text-white">{item.name}</p>
                      {item.selectedOptions.length > 0 && (
                        <p className="truncate text-[10px] text-white/70">
                          {item.selectedOptions.map(o => o.name).join(', ')}
                        </p>
                      )}
                      <p className="mt-0.5 text-xs font-black text-[#f7b32b]">
                        GHS {(item.price * item.quantity).toFixed(2)}
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5 rounded-full bg-white/10 px-2 py-1">
                      <button
                        onClick={() => onRemove(item.cartKey)}
                        className="text-white/60 transition hover:text-white active:scale-90"
                      >
                        <Minus size={11} strokeWidth={3} />
                      </button>
                      <span className="w-4 text-center text-xs font-black">{item.quantity}</span>
                      <button
                        onClick={() => onAdd(item)}
                        className="text-[#f7b32b] transition hover:text-[#ffc852] active:scale-90"
                      >
                        <Plus size={11} strokeWidth={3} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* ── CHECKOUT STEP ── */}
        {step === 'checkout' && (
          <div className="space-y-4 px-4 py-4">
            <p className="text-sm text-white/70">
              Ordering from <strong className="text-white">{branch.name}</strong>. Your receipt and live tracking are sent to your verified number.
            </p>

            {/* Verified account number — no longer retyped at every checkout. */}
            {session && (
              <div className="flex items-center gap-3 rounded-xl border border-[#f7b32b]/25 bg-[#f7b32b]/10 px-3 py-3">
                <ShieldCheck size={18} className="flex-shrink-0 text-[#f7b32b]" />
                <div className="min-w-0">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-white/70">
                    Verified number
                  </p>
                  <p className="truncate text-sm font-black text-white">
                    {formatGhanaPhone(session.customer.phone)}
                  </p>
                </div>
              </div>
            )}

            {[
              { label: 'Your Name (optional)', field: 'name' as const, type: 'text', placeholder: 'e.g. Kofi Mensah', max: 100 },
              { label: 'Landmark / Delivery Note', field: 'landmark' as const, type: 'text', placeholder: 'e.g. Call at main gate', max: 500 },
            ].map(({ label, field, type, placeholder, max }) => (
              <div key={field}>
                <label className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-white/70">{label}</label>
                <input
                  type={type}
                  placeholder={placeholder}
                  maxLength={max}
                  value={form[field]}
                  onChange={e => handleFieldChange(field, e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder-white/50 outline-none transition focus:border-[#f7b32b] focus:ring-1 focus:ring-[#f7b32b]"
                />
              </div>
            ))}

            <div>
              <label className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-white/70">Delivery Address *</label>
              <textarea
                placeholder="e.g. House 5, Kanda Highway, near Total filling station"
                maxLength={500}
                value={form.address}
                onChange={e => handleFieldChange('address', e.target.value)}
                rows={3}
                className="w-full resize-none rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder-white/50 outline-none transition focus:border-[#f7b32b] focus:ring-1 focus:ring-[#f7b32b]"
              />
            </div>

            <div>
              <label className="mb-2 block text-xs font-bold uppercase tracking-wider text-white/70">Payment Method *</label>
              <div className="grid grid-cols-2 gap-2">
                {(['momo', 'cash'] as const).map(method => (
                  <button
                    key={method}
                    onClick={() => handleFieldChange('payment', method)}
                    className={`rounded-xl border py-3 text-xs font-bold transition-all ${
                      form.payment === method
                        ? 'border-[#f7b32b] bg-[#f7b32b]/15 text-[#f7b32b]'
                        : 'border-white/10 text-white/70 hover:border-white/25'
                    }`}
                  >
                    {method === 'momo' ? '📱 Mobile Money' : '💵 Cash on Delivery'}
                  </button>
                ))}
              </div>
            </div>

            {/* Order summary */}
            <div className="rounded-xl bg-white/5 p-3">
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-white/70">Order Summary</p>
              {items.map(item => (
                <div key={item.cartKey} className="flex justify-between py-0.5 text-xs">
                  <span className="text-white/70">{item.quantity}× {item.name}</span>
                  <span className="font-semibold">GHS {(item.price * item.quantity).toFixed(2)}</span>
                </div>
              ))}
              <div className="mt-2 flex justify-between border-t border-white/10 pt-2 text-xs text-white/60">
                <span>Subtotal</span><span>GHS {totalPrice.toFixed(2)}</span>
              </div>
              <div className="flex justify-between py-0.5 text-xs text-white/60">
                <span>Delivery</span><span>GHS {Number(branch.delivery_fee || 0).toFixed(2)}</span>
              </div>
              <div className="mt-1.5 flex justify-between border-t border-white/10 pt-2 text-sm font-black">
                <span>Total</span><span className="text-[#f7b32b]">GHS {checkoutTotal.toFixed(2)}</span>
              </div>
            </div>

            <label className="flex items-start gap-2 rounded-xl border border-white/10 p-3 text-xs text-white/70">
              <input
                type="checkbox"
                checked={operationalConsent}
                onChange={e => setOperationalConsent(e.target.checked)}
                className="mt-0.5 h-3.5 w-3.5 accent-[#f7b32b]"
              />
              <span>Send my receipt and order-status updates to this WhatsApp number.</span>
            </label>

            <label className="flex items-start gap-2 px-1 text-xs text-white/65">
              <input
                type="checkbox"
                checked={rememberDetails}
                onChange={e => setRememberDetails(e.target.checked)}
                className="mt-0.5 h-3.5 w-3.5 accent-[#f7b32b]"
              />
              <span>Remember my contact details on this device for faster checkout.</span>
            </label>

            {error && (
              <p className="rounded-xl bg-red-900/30 px-3 py-2.5 text-xs text-red-400">{error}</p>
            )}
          </div>
        )}

        {/* ── SUCCESS STEP ── */}
        {step === 'success' && (
          <div className="flex flex-col items-center px-4 py-10 text-center">
            <div className="mb-4 text-5xl">🎉</div>
            <h3 className="mb-2 text-xl font-black text-white">Order Confirmed!</h3>
            <p className="mb-6 text-sm text-white/70">
              {whatsappReceiptSent
                ? 'Your receipt and private tracking link have been sent to WhatsApp.'
                : 'Use the tracking button below to follow your order.'}
            </p>
            <div className="mb-6 w-full rounded-xl bg-white/5 p-4 text-left">
              <div className="mb-2 flex items-center gap-2 text-xs text-white/70">
                <MapPin size={12} />
                <span>Preparing at {branch.name}</span>
              </div>
              <p className="mb-3 text-[10px] uppercase tracking-wider text-white/70">Order Number</p>
              <p className="text-2xl font-black text-[#f7b32b]">#{orderId}</p>
              {trackingCode && (
                <>
                  <p className="mt-3 text-[10px] uppercase tracking-wider text-white/70">Tracking Code</p>
                  <p className="font-black text-white">{trackingCode}</p>
                </>
              )}
              <p className="mt-3 text-[10px] uppercase tracking-wider text-white/70">Total</p>
              <p className="font-black text-white">GHS {confirmedTotal.toFixed(2)}</p>
            </div>
            {trackingUrl && (
              <a
                href={trackingUrl}
                className="mb-3 flex w-full items-center justify-center gap-2 rounded-xl bg-[#25D366] py-3.5 text-sm font-black text-white"
              >
                <MessageCircleMore size={16} />
                Track your order live
              </a>
            )}
            <button
              onClick={handleReset}
              className="w-full rounded-xl bg-[#f7b32b] py-3.5 text-sm font-black text-[#1a0a00] transition hover:bg-[#ffc852]"
            >
              Back to Menu
            </button>
          </div>
        )}
      </div>

      {/* ── FOOTER / CTA ── */}
      {step === 'cart' && (
        <div className="border-t border-white/10 px-4 py-4">
          {items.length > 0 && (
            <div className="mb-3 space-y-1.5 text-sm">
              <div className="flex justify-between text-white/70">
                <span>SubTotal</span>
                <span>{totalPrice.toFixed(2)}</span>
              </div>
              <div className="flex justify-between border-t border-white/10 pt-1.5 font-black text-white">
                <span>Total</span>
                <span>{checkoutTotal.toFixed(2)}</span>
              </div>
            </div>
          )}
          {/* Only frame the minimum once there is something to compare against —
              showing a shortfall on an empty cart reads as a barrier. */}
          {items.length > 0 && minimumRemaining > 0 && (
            <div className="mb-2.5">
              <div className="mb-1.5 h-1.5 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-[#f7b32b] transition-all duration-500"
                  style={{
                    width: `${Math.min(100, (totalPrice / Number(branch.minimum_order || 1)) * 100)}%`,
                  }}
                />
              </div>
              <p className="text-xs font-semibold text-[#f7b32b]">
                GHS {minimumRemaining.toFixed(2)} away from checkout
              </p>
            </div>
          )}
          <button
            onClick={() => {
              if (items.length === 0) return
              if (!getCustomerSession()) {
                setAuthOpen(true)
                return
              }
              setStep('checkout')
            }}
            disabled={items.length === 0 || minimumRemaining > 0}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#f7b32b] py-3.5 text-sm font-black text-[#1a0a00] shadow-lg transition hover:bg-[#ffc852] active:scale-[.98] disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Plus size={15} strokeWidth={3} />
            {items.length === 0 ? 'Browse the menu' : 'Proceed to Checkout →'}
          </button>
        </div>
      )}

      {step === 'checkout' && (
        <div className="flex gap-2 border-t border-white/10 px-4 py-4">
          <button
            onClick={() => setStep('cart')}
            disabled={loading}
            className="flex-none rounded-xl border border-white/10 px-4 py-3.5 text-sm font-bold text-white/60 transition hover:border-white/25 hover:text-white"
          >
            ← Back
          </button>
          <button
            onClick={handlePlaceOrder}
            disabled={loading}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-[#f7b32b] py-3.5 text-sm font-black text-[#1a0a00] transition hover:bg-[#ffc852] disabled:opacity-60"
          >
            {loading
              ? <><Loader2 size={16} className="animate-spin" /> Placing order...</>
              : '✅ Place Order'
            }
          </button>
        </div>
      )}

      <CustomerAuthSheet
        open={authOpen}
        onClose={() => setAuthOpen(false)}
        onAuthenticated={next => {
          setSession(next)
          setAuthOpen(false)
          setError('')
          setStep('checkout')
        }}
      />
    </div>
  )
}
