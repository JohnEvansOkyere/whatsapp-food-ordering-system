import { ShoppingBag, Clock, MapPin } from 'lucide-react'
import { RESTAURANT } from '../lib/menuData'

interface HeaderProps {
  totalItems: number
  onCartOpen: () => void
}

export default function Header({ totalItems, onCartOpen }: HeaderProps) {
  return (
    <header className="sticky top-0 z-40 bg-brand-dark shadow-lg">
      {/* Top bar */}
      <div className="px-4 py-3 flex items-center justify-between">
        <div>
          <h1
            className="text-2xl font-black text-brand-yellow leading-none"
            style={{ fontFamily: 'var(--font-display)' }}
          >
            {RESTAURANT.name}
          </h1>
          <p className="text-xs text-orange-300 mt-0.5 font-medium">
            {RESTAURANT.tagline}
          </p>
        </div>

        {/* Cart button */}
        <button
          onClick={onCartOpen}
          className="relative flex items-center gap-2 bg-brand-orange text-white px-4 py-2.5 rounded-xl font-semibold text-sm active:scale-95 transition-transform"
        >
          <ShoppingBag size={18} />
          <span>Cart</span>
          {totalItems > 0 && (
            <span className="absolute -top-2 -right-2 bg-brand-yellow text-brand-dark text-xs font-black w-5 h-5 rounded-full flex items-center justify-center animate-bounce-in">
              {totalItems}
            </span>
          )}
        </button>
      </div>

      {/* Info strip */}
      <div className="px-4 pb-2.5 flex items-center gap-4 text-xs text-orange-200">
        <span className="flex items-center gap-1">
          <MapPin size={12} />
          {RESTAURANT.address}
        </span>
        <span className="flex items-center gap-1">
          <Clock size={12} />
          {RESTAURANT.hours}
        </span>
      </div>
    </header>
  )
}
