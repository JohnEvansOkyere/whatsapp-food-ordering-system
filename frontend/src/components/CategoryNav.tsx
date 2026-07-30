import { CATEGORIES } from '../lib/menuData'
import clsx from 'clsx'

interface CategoryNavProps {
  active: string
  onSelect: (id: string) => void
}

export default function CategoryNav({ active, onSelect }: CategoryNavProps) {
  return (
    <div className="sticky top-[64px] z-30 border-b border-black/5 bg-[#fffaf4]/95 shadow-sm backdrop-blur-xl">
      <div className="category-nav mx-auto flex max-w-7xl gap-2 overflow-x-auto px-4 py-3 sm:px-6">
        {CATEGORIES.map(cat => (
          <button
            key={cat.id}
            onClick={() => onSelect(cat.id)}
            className={clsx(
              'flex-shrink-0 flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-bold transition-all duration-200',
              active === cat.id
                ? 'bg-[#1b0b04] text-white shadow-md'
                : 'border border-black/8 bg-white text-[#1b0b04] active:scale-95'
            )}
          >
            <span>{cat.emoji}</span>
            <span>{cat.name}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
