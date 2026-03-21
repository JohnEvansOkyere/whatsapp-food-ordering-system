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
    <div className="food-card bg-white rounded-2xl overflow-hidden shadow-lg border border-orange-50 flex flex-col w-full hover:shadow-xl transition-shadow duration-300">
      {/* Image — taller height for better appetite appeal */}
      <div className="relative h-48 sm:h-56 w-full overflow-hidden flex-shrink-0 group">
        <Image
          src={item.image}
          alt={item.name}
          fill
          className="object-cover transition-transform duration-500 group-hover:scale-105"
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          priority={false}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent" />

        {/* Badge */}
        {item.popular && (
          <span className="absolute top-3 left-3 bg-brand-yellow text-brand-dark font-black px-3 py-1 rounded-full text-xs shadow-md">
            🔥 Popular
          </span>
        )}
        {item.spicy && !item.popular && (
          <span className="absolute top-3 left-3 bg-brand-red text-white font-bold px-3 py-1 rounded-full text-xs flex items-center gap-1 shadow-md">
            <Flame size={12} /> Spicy
          </span>
        )}

        {/* Add/Remove */}
        <div className="absolute bottom-3 right-3">
          {quantity === 0 ? (
            <button
              onClick={onAdd}
              className="bg-brand-orange text-white w-10 h-10 rounded-full flex items-center justify-center hover:bg-orange-600 active:scale-90 transition-all shadow-lg"
            >
              <Plus size={20} strokeWidth={3} />
            </button>
          ) : (
            <div className="flex items-center gap-2 bg-brand-dark rounded-full px-2 py-1.5 shadow-lg">
              <button onClick={onRemove} className="text-white hover:text-gray-200 active:scale-90 transition-all p-1">
                <Minus size={16} strokeWidth={3} />
              </button>
              <span className="text-white font-black text-base w-5 text-center">{quantity}</span>
              <button onClick={onAdd} className="text-brand-yellow hover:text-yellow-400 active:scale-90 transition-all p-1">
                <Plus size={16} strokeWidth={3} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Text */}
      <div className="p-4 flex flex-col flex-1 bg-white">
        <h3 className="font-extrabold text-brand-dark leading-tight line-clamp-2 text-base sm:text-lg flex-1 mb-1">
          {item.name}
        </h3>
        <span className="text-brand-orange font-black text-sm sm:text-base mt-auto block">
          GHS {item.price}
        </span>
      </div>
    </div>
  )
}