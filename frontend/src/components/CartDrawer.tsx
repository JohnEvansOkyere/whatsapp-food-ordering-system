import { useEffect, useRef, useState } from 'react'
import { X, Plus, Minus, ShoppingBag, Loader2, MapPin, MessageCircleMore } from 'lucide-react'
import { CartItem } from '../hooks/useCart'
import Image from 'next/image'
import { Branch, branchEta } from '@/lib/branches'
import { trackEvent } from '@/lib/analytics'

interface CartDrawerProps {
  isOpen: boolean
  items: CartItem[]
  totalItems: number
  totalPrice: number
  onClose: () => void
  onAdd: (item: CartItem) => void
  onRemove: (id: string) => void
  onClear: () => void
  branch: Branch
}

interface CheckoutForm {
  phone: string
  name: string
  address: string
  landmark: string
  payment: 'momo' | 'cash'
}

type Step = 'cart' | 'checkout' | 'success'

export default function CartDrawer({
  isOpen,
  items,
  totalItems,
  totalPrice,
  onClose,
  onAdd,
  onRemove,
  onClear,
  branch,
}: CartDrawerProps) {
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
  const idempotencyKeyRef = useRef('')
  const checkoutTotal = totalPrice + Number(branch.delivery_fee || 0)
  const minimumRemaining = Math.max(0, Number(branch.minimum_order || 0) - totalPrice)

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem('restaurant-customer-v1')
      if (!stored) return
      const details = JSON.parse(stored)
      setForm(current => ({
        ...current,
        phone: details.phone || '',
        name: details.name || '',
        address: details.address || '',
      }))
      setRememberDetails(true)
    } catch {
      window.localStorage.removeItem('restaurant-customer-v1')
    }
  }, [])

  const handleFieldChange = (field: keyof CheckoutForm, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }))
    setError('')
  }

  const validateForm = (): boolean => {
    if (!form.phone.trim()) { setError('Please enter your WhatsApp number'); return false }
    if (!form.address.trim()) { setError('Please enter your delivery address'); return false }
    if (!operationalConsent) {
      setError('Please allow operational WhatsApp updates for this order')
      return false
    }
    const phoneClean = form.phone.replace(/\s/g, '')
    if (!/^(0|\+?233)[0-9]{9}$/.test(phoneClean)) {
      setError('Please enter a valid Ghana phone number (e.g. 0244123456)')
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
      customer_phone: normalisePhone(form.phone),
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
          JSON.stringify({
            phone: form.phone,
            name: form.name,
            address: form.address,
          })
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

  const handleClose = () => {
    if (step === 'success') {
      setStep('cart')
      setOrderId('')
      setTrackingCode('')
      setTrackingUrl('')
      setWhatsappReceiptSent(null)
      setConfirmedTotal(0)
      idempotencyKeyRef.current = ''
      setForm({ phone: '', name: '', address: '', landmark: '', payment: 'momo' })
    }
    onClose()
  }

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-50 backdrop-blur-sm"
          onClick={handleClose}
        />
      )}

      <div
        className={`fixed bottom-0 left-0 right-0 z-50 bg-white rounded-t-3xl shadow-2xl transition-transform duration-300 ease-out ${
          isOpen ? 'translate-y-0' : 'translate-y-full'
        }`}
        style={{ maxHeight: '90vh' }}
      >
        {/* Handle */}
        <div className="flex justify-center pt-3 pb-1">
          <div className="w-10 h-1 bg-gray-200 rounded-full" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <ShoppingBag size={20} className="text-brand-orange" />
            <h2 className="font-black text-brand-dark text-lg">
              {step === 'cart' && 'Your Order'}
              {step === 'checkout' && 'Delivery Details'}
              {step === 'success' && 'Order Placed! 🎉'}
            </h2>
          </div>
          <button
            onClick={handleClose}
            className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center"
          >
            <X size={16} />
          </button>
        </div>

        <div className="overflow-y-auto px-5 py-4" style={{ maxHeight: '70vh' }}>

          {/* CART STEP */}
          {step === 'cart' && (
            <>
              {items.length === 0 ? (
                <div className="py-12 text-center">
                  <div className="text-5xl mb-3">🍽️</div>
                  <p className="text-gray-400 font-medium">Your cart is empty</p>
                  <p className="text-gray-300 text-sm mt-1">Add items from the menu</p>
                </div>
              ) : (
                <>
                  <div className="space-y-3 mb-6">
                    {items.map(item => (
                      <div key={item.cartKey} className="flex items-center gap-3">
                        <div className="relative w-14 h-14 rounded-xl overflow-hidden flex-shrink-0">
                          <Image
                            src={item.image}
                            alt={item.name}
                            fill
                            className="object-cover"
                            sizes="56px"
                          />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold text-sm text-brand-dark truncate">{item.name}</p>
                          {item.selectedOptions.length > 0 && (
                            <p className="truncate text-[11px] text-black/40">
                              {item.selectedOptions.map(option => option.name).join(', ')}
                            </p>
                          )}
                          <p className="text-brand-orange font-bold text-sm">
                            GHS {(item.price * item.quantity).toFixed(2)}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 bg-gray-100 rounded-full px-2 py-1.5">
                          <button
                            onClick={() => onRemove(item.cartKey)}
                            className="text-gray-600 active:scale-90 transition-transform"
                          >
                            <Minus size={13} strokeWidth={3} />
                          </button>
                          <span className="font-black text-sm w-4 text-center">{item.quantity}</span>
                          <button
                            onClick={() => onAdd(item)}
                            className="text-brand-orange active:scale-90 transition-transform"
                          >
                            <Plus size={13} strokeWidth={3} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="border-t border-gray-100 pt-4 pb-6">
                    <div className="mb-4 rounded-2xl bg-[#fff6e8] p-3">
                      <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-[#a8491d]">
                        <MapPin size={14} />
                        Kitchen
                      </p>
                      <p className="mt-1 font-black text-brand-dark">{branch.name}</p>
                      <p className="mt-0.5 text-xs text-black/45">{branchEta(branch)}</p>
                    </div>
                    <div className="mb-4 space-y-2 text-sm">
                      <div className="flex justify-between text-gray-500">
                        <span>Subtotal</span>
                        <span>GHS {totalPrice.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between text-gray-500">
                        <span>Delivery</span>
                        <span>GHS {Number(branch.delivery_fee || 0).toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between border-t border-black/[0.06] pt-2">
                        <span className="font-bold text-gray-700">Total</span>
                        <span className="font-black text-xl text-brand-dark">
                          GHS {checkoutTotal.toFixed(2)}
                        </span>
                      </div>
                    </div>
                    {minimumRemaining > 0 && (
                      <p className="mb-3 rounded-xl bg-amber-50 px-3 py-2 text-xs font-bold text-amber-800">
                        Add GHS {minimumRemaining.toFixed(2)} more to reach the
                        {` ${branch.name}`} minimum.
                      </p>
                    )}
                    <button
                      onClick={() => setStep('checkout')}
                      disabled={minimumRemaining > 0}
                      className="w-full bg-brand-orange text-white font-black py-4 rounded-2xl text-base shadow-lg active:scale-98 transition-transform disabled:cursor-not-allowed disabled:opacity-45"
                    >
                      Proceed to Checkout →
                    </button>
                  </div>
                </>
              )}
            </>
          )}

          {/* CHECKOUT STEP */}
          {step === 'checkout' && (
            <div className="pb-6 space-y-4">
              <p className="text-sm text-gray-500">
                Ordering from <strong>{branch.name}</strong>. Your receipt and
                live tracking link will be sent to WhatsApp.
              </p>

              <div>
                <label className="block text-sm font-semibold text-brand-dark mb-1.5">
                  WhatsApp Number *
                </label>
                <input
                  type="tel"
                  placeholder="e.g. 0244123456"
                  maxLength={20}
                  value={form.phone}
                  onChange={e => handleFieldChange('phone', e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-brand-orange focus:ring-1 focus:ring-brand-orange"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-brand-dark mb-1.5">
                  Landmark or delivery note
                </label>
                <input
                  type="text"
                  placeholder="e.g. Call at the main gate"
                  maxLength={500}
                  value={form.landmark}
                  onChange={e => handleFieldChange('landmark', e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-brand-orange focus:ring-1 focus:ring-brand-orange"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-brand-dark mb-1.5">
                  Your Name <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Kofi Mensah"
                  maxLength={100}
                  value={form.name}
                  onChange={e => handleFieldChange('name', e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-brand-orange focus:ring-1 focus:ring-brand-orange"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-brand-dark mb-1.5">
                  Delivery Address *
                </label>
                <textarea
                  placeholder="e.g. House 5, Kanda Highway, near Total filling station"
                  maxLength={500}
                  value={form.address}
                  onChange={e => handleFieldChange('address', e.target.value)}
                  rows={3}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-brand-orange focus:ring-1 focus:ring-brand-orange resize-none"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-brand-dark mb-2">
                  Payment Method *
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {(['momo', 'cash'] as const).map(method => (
                    <button
                      key={method}
                      onClick={() => handleFieldChange('payment', method)}
                      className={`py-3 rounded-xl border-2 text-sm font-bold transition-all ${
                        form.payment === method
                          ? 'border-brand-orange bg-orange-50 text-brand-orange'
                          : 'border-gray-200 text-gray-500'
                      }`}
                    >
                      {method === 'momo' ? '📱 Mobile Money' : '💵 Cash on Delivery'}
                    </button>
                  ))}
                </div>
              </div>

              <div className="bg-orange-50 rounded-xl p-4">
                <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">
                  Order Summary
                </p>
                {items.map(item => (
                  <div key={item.cartKey} className="flex justify-between text-sm py-0.5">
                    <span className="text-gray-700">
                      {item.quantity}x {item.name}
                      {item.selectedOptions.length > 0 && (
                        <small className="block text-black/40">
                          {item.selectedOptions.map(option => option.name).join(', ')}
                        </small>
                      )}
                    </span>
                    <span className="font-semibold">GHS {(item.price * item.quantity).toFixed(2)}</span>
                  </div>
                ))}
                <div className="mt-2 flex justify-between border-t border-orange-200 pt-2 text-sm text-gray-600">
                  <span>Subtotal</span>
                  <span className="font-semibold">GHS {totalPrice.toFixed(2)}</span>
                </div>
                <div className="flex justify-between py-0.5 text-sm text-gray-600">
                  <span>Delivery</span>
                  <span className="font-semibold">
                    GHS {Number(branch.delivery_fee || 0).toFixed(2)}
                  </span>
                </div>
                <div className="border-t border-orange-200 mt-2 pt-2 flex justify-between font-black">
                  <span>Total</span>
                  <span className="text-brand-orange">GHS {checkoutTotal.toFixed(2)}</span>
                </div>
              </div>

              <label className="flex items-start gap-3 rounded-2xl border border-gray-200 p-4 text-sm text-gray-600">
                <input
                  type="checkbox"
                  checked={operationalConsent}
                  onChange={event => setOperationalConsent(event.target.checked)}
                  className="mt-0.5 h-4 w-4 accent-orange-600"
                />
                <span>
                  Send my receipt and order-status updates to this WhatsApp
                  number. These are operational messages for this order.
                </span>
              </label>

              <label className="flex items-start gap-3 px-1 text-xs text-gray-500">
                <input
                  type="checkbox"
                  checked={rememberDetails}
                  onChange={event => setRememberDetails(event.target.checked)}
                  className="mt-0.5 h-4 w-4 accent-orange-600"
                />
                <span>
                  Remember my contact and address on this device for faster
                  checkout. You can clear browser storage at any time.
                </span>
              </label>

              {error && (
                <p className="text-red-500 text-sm bg-red-50 rounded-xl px-4 py-3">{error}</p>
              )}

              <div className="flex gap-3">
                <button
                  onClick={() => setStep('cart')}
                  disabled={loading}
                  className="flex-1 py-4 rounded-2xl border-2 border-gray-200 text-gray-600 font-bold text-sm"
                >
                  ← Back
                </button>
                <button
                  onClick={handlePlaceOrder}
                  disabled={loading}
                  className="flex-grow py-4 rounded-2xl bg-brand-dark text-white font-black text-sm flex items-center justify-center gap-2 disabled:opacity-60"
                >
                  {loading
                    ? <><Loader2 size={18} className="animate-spin" /> Placing order...</>
                    : '✅ Place Order'
                  }
                </button>
              </div>
            </div>
          )}

          {/* SUCCESS STEP */}
          {step === 'success' && (
            <div className="py-8 text-center">
              <div className="text-6xl mb-4">🎉</div>
              <h3 className="font-black text-brand-dark text-xl mb-2">Order Confirmed!</h3>
              <p className="text-gray-500 text-sm mb-4">
                {whatsappReceiptSent
                  ? 'Your receipt and private tracking link have been sent to WhatsApp.'
                  : 'Your order is confirmed. WhatsApp delivery could not be confirmed, so use the private tracking button below.'}
                {' '}The kitchen will confirm your ETA after accepting the order.
              </p>
              <div className="bg-orange-50 rounded-2xl p-4 mb-6 inline-block">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">
                  Preparing at
                </p>
                <p className="mb-4 font-black text-brand-dark">{branch.name}</p>
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Order Number</p>
                <p className="font-black text-2xl text-brand-orange">#{orderId}</p>
                {trackingCode && (
                  <>
                    <p className="text-xs text-gray-500 uppercase tracking-wide mt-4 mb-1">
                      Tracking Code
                    </p>
                    <p className="font-black text-lg text-brand-dark">{trackingCode}</p>
                  </>
                )}
                <p className="mt-4 text-xs font-bold uppercase tracking-wide text-gray-500">
                  Total
                </p>
                <p className="font-black text-lg text-brand-dark">
                  GHS {confirmedTotal.toFixed(2)}
                </p>
              </div>
              {trackingUrl && (
                <a
                  href={trackingUrl}
                  className="mb-3 flex w-full items-center justify-center gap-2 rounded-2xl bg-[#25D366] py-4 font-black text-white shadow-lg"
                >
                  <MessageCircleMore size={18} />
                  Track your order live
                </a>
              )}
              <button
                onClick={handleClose}
                className="mt-6 w-full bg-brand-orange text-white font-bold py-4 rounded-2xl"
              >
                Back to Menu
              </button>
            </div>
          )}

        </div>
      </div>
    </>
  )
}
