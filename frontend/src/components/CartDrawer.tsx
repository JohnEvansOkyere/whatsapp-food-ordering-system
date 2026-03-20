import { useState } from 'react'
import { X, Plus, Minus, ShoppingBag, Loader2 } from 'lucide-react'
import { CartItem } from '@/hooks/useCart'
import Image from 'next/image'

interface CartDrawerProps {
  isOpen: boolean
  items: CartItem[]
  totalItems: number
  totalPrice: number
  onClose: () => void
  onAdd: (item: CartItem) => void
  onRemove: (id: string) => void
  onClear: () => void
}

interface CheckoutForm {
  phone: string
  name: string
  address: string
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
}: CartDrawerProps) {
  const [step, setStep] = useState<Step>('cart')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [orderId, setOrderId] = useState('')
  const [form, setForm] = useState<CheckoutForm>({
    phone: '',
    name: '',
    address: '',
    payment: 'momo',
  })

  const handleFieldChange = (field: keyof CheckoutForm, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }))
    setError('')
  }

  const validateForm = (): boolean => {
    if (!form.phone.trim()) { setError('Please enter your WhatsApp number'); return false }
    if (!form.address.trim()) { setError('Please enter your delivery address'); return false }
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
    }))

    const payload = {
      customer_phone: normalisePhone(form.phone),
      customer_name: form.name.trim() || null,
      delivery_address: form.address.trim(),
      items: orderItems,
      total_amount: totalPrice,
      payment_method: form.payment,
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${apiUrl}/orders/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Order failed. Please try again.')
      }

      const data = await res.json()
      setOrderId(data.id?.slice(0, 8).toUpperCase() || 'N/A')
      setStep('success')
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
      setForm({ phone: '', name: '', address: '', payment: 'momo' })
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
                      <div key={item.id} className="flex items-center gap-3">
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
                          <p className="text-brand-orange font-bold text-sm">
                            GHS {(item.price * item.quantity).toFixed(2)}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 bg-gray-100 rounded-full px-2 py-1.5">
                          <button
                            onClick={() => onRemove(item.id)}
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
                    <div className="flex justify-between items-center mb-4">
                      <span className="text-gray-600 font-medium">Total</span>
                      <span className="font-black text-xl text-brand-dark">
                        GHS {totalPrice.toFixed(2)}
                      </span>
                    </div>
                    <button
                      onClick={() => setStep('checkout')}
                      className="w-full bg-brand-orange text-white font-black py-4 rounded-2xl text-base shadow-lg active:scale-98 transition-transform"
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
                Enter your details. Your receipt will be sent to your WhatsApp automatically.
              </p>

              <div>
                <label className="block text-sm font-semibold text-brand-dark mb-1.5">
                  WhatsApp Number *
                </label>
                <input
                  type="tel"
                  placeholder="e.g. 0244123456"
                  value={form.phone}
                  onChange={e => handleFieldChange('phone', e.target.value)}
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
                  <div key={item.id} className="flex justify-between text-sm py-0.5">
                    <span className="text-gray-700">{item.quantity}x {item.name}</span>
                    <span className="font-semibold">GHS {(item.price * item.quantity).toFixed(2)}</span>
                  </div>
                ))}
                <div className="border-t border-orange-200 mt-2 pt-2 flex justify-between font-black">
                  <span>Total</span>
                  <span className="text-brand-orange">GHS {totalPrice.toFixed(2)}</span>
                </div>
              </div>

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
                Your receipt has been sent to your WhatsApp. We'll deliver within 45–60 minutes.
              </p>
              <div className="bg-orange-50 rounded-2xl p-4 mb-6 inline-block">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Order ID</p>
                <p className="font-black text-2xl text-brand-orange">#{orderId}</p>
              </div>
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