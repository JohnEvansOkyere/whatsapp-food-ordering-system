import Image from 'next/image'
import { Plus, Minus, Flame } from 'lucide-react'
import { MenuItem } from '../lib/menuData'

interface FoodCardProps {
  item: MenuItem
  quantity: number
  onAdd: () => void
  onRemove: () => void
  onView: () => void
}

export default function FoodCard({ item, quantity, onAdd, onRemove, onView }: FoodCardProps) {
  return (
    <article className="food-card flex w-full flex-col overflow-hidden rounded-[26px] border border-black/[0.06] bg-white shadow-[0_14px_45px_rgba(49,23,9,0.08)] transition-shadow duration-300 hover:shadow-xl">
      {/* Image — taller height for better appetite appeal */}
      <div className="group relative aspect-[4/3] w-full flex-shrink-0 overflow-hidden bg-[#ead8c6]">
        <Image
          src={item.image}
          alt={item.name}
          fill
          className="object-cover transition-transform duration-700 group-hover:scale-105"
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          priority={false}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent" />

        {/* Badge */}
        {item.popular && (
          <span className="absolute left-3 top-3 rounded-full bg-[#f7b32b] px-3 py-1 text-xs font-black text-[#1b0b04] shadow-md">
            Most loved
          </span>
        )}
        {item.spicy && !item.popular && (
          <span className="absolute top-3 left-3 bg-brand-red text-white font-bold px-3 py-1 rounded-full text-xs flex items-center gap-1 shadow-md">
            <Flame size={12} /> Spicy
          </span>
        )}
        {item.soldOut && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#1b0b04]/60 backdrop-blur-[1px]">
            <span className="rounded-full bg-white px-4 py-2 text-sm font-black text-[#1b0b04]">
              Sold out at this branch
            </span>
          </div>
        )}

        {/* Add/Remove */}
        <div className="absolute bottom-3 right-3">
          {quantity === 0 ? (
            <button
              onClick={onAdd}
              disabled={item.soldOut}
              aria-label={`Add ${item.name}`}
              className="bg-brand-orange text-white w-10 h-10 rounded-full flex items-center justify-center hover:bg-orange-600 active:scale-90 transition-all shadow-lg disabled:cursor-not-allowed disabled:opacity-40"
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
      <div className="flex flex-1 flex-col bg-white p-4">
        <h3 className="mb-1 flex-1 text-base font-black leading-tight text-[#1b0b04] sm:text-lg">
          {item.name}
        </h3>
        <p className="mb-4 line-clamp-2 text-xs leading-5 text-black/50 sm:text-sm">
          {item.description}
        </p>
        <div className="mt-auto flex items-center justify-between">
          <span className="text-sm font-black text-[#d95d20] sm:text-base">
            GHS {item.price.toFixed(2)}
          </span>
          <button
            type="button"
            onClick={onView}
            className="text-[11px] font-bold uppercase tracking-[0.12em] text-black/45 underline decoration-black/15 underline-offset-4"
          >
            {item.optionGroups?.length ? 'Choose options' : 'View details'}
          </button>
        </div>
      </div>
    </article>
  )
}
