import { ShoppingBag } from 'lucide-react'

interface FloatingCartProps {
  totalItems: number
  totalPrice: number
  onOpen: () => void
}

export default function FloatingCart({ totalItems, totalPrice, onOpen }: FloatingCartProps) {
  if (totalItems === 0) return null

  return (
    <div className="fixed bottom-6 left-4 right-4 z-40 animate-slide-up">
      <button
        onClick={onOpen}
        className="w-full bg-brand-dark text-white rounded-2xl px-5 py-4 flex items-center justify-between shadow-2xl active:scale-98 transition-transform"
      >
        <div className="flex items-center gap-3">
          <div className="bg-brand-orange rounded-xl w-8 h-8 flex items-center justify-center">
            <ShoppingBag size={16} />
          </div>
          <span className="font-bold">
            {totalItems} item{totalItems > 1 ? 's' : ''} in cart
          </span>
        </div>
        <span className="font-black text-brand-yellow text-lg">
          GHS {totalPrice.toFixed(2)}
        </span>
      </button>
    </div>
  )
}
