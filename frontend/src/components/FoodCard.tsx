import Image from 'next/image'
import { Plus, Minus, Flame } from 'lucide-react'
import { MenuItem } from '../lib/menuData'

interface FoodCardProps {
  item: MenuItem
  quantity: number
  onAdd: () => void
  onRemove: () => void
}

export default function FoodCard({ item, quantity, onAdd, onRemove }: FoodCardProps) {
  return (
    <div className="food-card bg-white rounded-xl overflow-hidden shadow-sm border border-orange-50 max-w-[260px] mx-auto">
      {/* Image */}
      <div className="relative w-full aspect-square overflow-hidden">
        <Image
          src={item.image}
          alt={item.name}
          fill
          className="object-cover hover:scale-105 transition-transform duration-500"
          sizes="33vw"
          priority={false}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/30 via-transparent to-transparent" />

        {/* Badge */}
        {item.popular && (
          <span className="absolute top-1.5 left-1.5 bg-brand-yellow text-brand-dark font-black px-1.5 py-0.5 rounded-full text-[9px] shadow">
            🔥
          </span>
        )}
        {item.spicy && !item.popular && (
          <span className="absolute top-1.5 left-1.5 bg-brand-red text-white font-bold px-1.5 py-0.5 rounded-full flex items-center gap-0.5 shadow">
            <Flame size={8} />
          </span>
        )}

        {/* Add/Remove */}
        <div className="absolute bottom-1.5 right-1.5">
          {quantity === 0 ? (
            <button
              onClick={onAdd}
              className="bg-brand-orange text-white w-7 h-7 rounded-full flex items-center justify-center active:scale-90 transition-transform shadow-md"
            >
              <Plus size={14} strokeWidth={3} />
            </button>
          ) : (
            <div className="flex items-center gap-1 bg-brand-dark rounded-full px-1.5 py-1 shadow-md">
              <button onClick={onRemove} className="text-white active:scale-90 transition-transform">
                <Minus size={10} strokeWidth={3} />
              </button>
              <span className="text-white font-black text-xs w-3 text-center">{quantity}</span>
              <button onClick={onAdd} className="text-brand-yellow active:scale-90 transition-transform">
                <Plus size={10} strokeWidth={3} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Text */}
      <div className="p-3">
        <h3 className="font-bold text-brand-dark leading-tight line-clamp-2 text-sm mb-1">
          {item.name}
        </h3>
        <span className="text-brand-orange font-black text-sm">GHS {item.price}</span>
      </div>
    </div>
  )
}