import { X, Plus, Minus, ShoppingBag, MessageCircle } from 'lucide-react'
import { CartItem } from '../hooks/useCart'
import { RESTAURANT } from '../lib/menuData'
import Image from 'next/image'

interface CartDrawerProps {
  isOpen: boolean
  items: CartItem[]
  totalItems: number
  totalPrice: number
  onClose: () => void
  onAdd: (item: CartItem) => void
  onRemove: (id: string) => void
  buildWhatsAppMessage: (whatsapp: string) => string
}

export default function CartDrawer({
  isOpen,
  items,
  totalItems,
  totalPrice,
  onClose,
  onAdd,
  onRemove,
  buildWhatsAppMessage,
}: CartDrawerProps) {
  const handleOrder = () => {
    if (items.length === 0) return
    const url = buildWhatsAppMessage(RESTAURANT.whatsapp)
    window.open(url, '_blank')
  }

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-50 backdrop-blur-sm"
          onClick={onClose}
        />
      )}

      {/* Drawer */}
      <div
        className={`fixed bottom-0 left-0 right-0 z-50 bg-white rounded-t-3xl shadow-2xl transition-transform duration-300 ease-out ${
          isOpen ? 'translate-y-0' : 'translate-y-full'
        }`}
        style={{ maxHeight: '85vh' }}
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
              Your Order
            </h2>
            {totalItems > 0 && (
              <span className="bg-brand-orange text-white text-xs font-bold px-2 py-0.5 rounded-full">
                {totalItems} items
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center"
          >
            <X size={16} />
          </button>
        </div>

        {/* Items */}
        <div className="overflow-y-auto px-5 py-3" style={{ maxHeight: '45vh' }}>
          {items.length === 0 ? (
            <div className="py-12 text-center">
              <div className="text-5xl mb-3">🍽️</div>
              <p className="text-gray-400 font-medium">Your cart is empty</p>
              <p className="text-gray-300 text-sm mt-1">Add items from the menu</p>
            </div>
          ) : (
            <div className="space-y-3">
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
                    <p className="font-semibold text-sm text-brand-dark truncate">
                      {item.name}
                    </p>
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
                    <span className="font-black text-sm w-4 text-center">
                      {item.quantity}
                    </span>
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
          )}
        </div>

        {/* Footer */}
        {items.length > 0 && (
          <div className="px-5 pb-8 pt-3 border-t border-gray-100">
            {/* Total */}
            <div className="flex justify-between items-center mb-4">
              <span className="text-gray-600 font-medium">Total</span>
              <span className="font-black text-xl text-brand-dark">
                GHS {totalPrice.toFixed(2)}
              </span>
            </div>

            {/* WhatsApp Order Button */}
            <button
              onClick={handleOrder}
              className="whatsapp-btn w-full text-white font-black py-4 rounded-2xl flex items-center justify-center gap-3 text-base shadow-lg active:scale-98 transition-transform"
            >
              <MessageCircle size={22} />
              Order on WhatsApp
            </button>
            <p className="text-center text-xs text-gray-400 mt-2">
              You'll be taken to WhatsApp to confirm your order
            </p>
          </div>
        )}
      </div>
    </>
  )
}
