import { CATEGORIES } from '../lib/menuData'
import clsx from 'clsx'

interface CategoryNavProps {
  active: string
  onSelect: (id: string) => void
}

export default function CategoryNav({ active, onSelect }: CategoryNavProps) {
  return (
    <div className="sticky top-[88px] z-30 bg-brand-cream border-b border-orange-100 shadow-sm">
      <div className="category-nav flex gap-2 px-4 py-3 overflow-x-auto">
        {CATEGORIES.map(cat => (
          <button
            key={cat.id}
            onClick={() => onSelect(cat.id)}
            className={clsx(
              'flex-shrink-0 flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold transition-all duration-200',
              active === cat.id
                ? 'bg-brand-orange text-white shadow-md scale-105'
                : 'bg-white text-brand-dark border border-orange-100 active:scale-95'
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
