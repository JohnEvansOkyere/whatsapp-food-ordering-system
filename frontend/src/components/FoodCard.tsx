import Image from 'next/image'
import { Plus, Minus, Flame } from 'lucide-react'
import { MenuItem } from '@/lib/menuData'
import clsx from 'clsx'

interface FoodCardProps {
  item: MenuItem
  quantity: number
  onAdd: () => void
  onRemove: () => void
}

export default function FoodCard({ item, quantity, onAdd, onRemove }: FoodCardProps) {
  return (
    <div className="food-card bg-white rounded-2xl overflow-hidden shadow-sm border border-orange-50">
      {/* Image */}
      <div className="relative h-44 w-full overflow-hidden">
        <Image
          src={item.image}
          alt={item.name}
          fill
          className="object-cover"
          sizes="(max-width: 768px) 50vw, 33vw"
        />
        {/* Badges */}
        <div className="absolute top-2 left-2 flex gap-1.5">
          {item.popular && (
            <span className="bg-brand-yellow text-brand-dark text-xs font-black px-2 py-0.5 rounded-full">
              🔥 Popular
            </span>
          )}
          {item.spicy && !item.popular && (
            <span className="bg-brand-red text-white text-xs font-bold px-2 py-0.5 rounded-full flex items-center gap-0.5">
              <Flame size={10} /> Spicy
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-3">
        <h3 className="font-bold text-brand-dark text-sm leading-tight mb-1">
          {item.name}
        </h3>
        <p className="text-xs text-gray-500 leading-relaxed mb-3 line-clamp-2">
          {item.description}
        </p>

        {/* Price + Controls */}
        <div className="flex items-center justify-between">
          <span className="text-brand-orange font-black text-base">
            GHS {item.price}
          </span>

          {quantity === 0 ? (
            <button
              onClick={onAdd}
              className="bg-brand-orange text-white w-8 h-8 rounded-full flex items-center justify-center active:scale-90 transition-transform shadow-md"
            >
              <Plus size={16} strokeWidth={3} />
            </button>
          ) : (
            <div className="flex items-center gap-2 bg-brand-dark rounded-full px-2 py-1">
              <button
                onClick={onRemove}
                className="text-white active:scale-90 transition-transform"
              >
                <Minus size={14} strokeWidth={3} />
              </button>
              <span className="text-white font-black text-sm w-4 text-center">
                {quantity}
              </span>
              <button
                onClick={onAdd}
                className="text-brand-yellow active:scale-90 transition-transform"
              >
                <Plus size={14} strokeWidth={3} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
