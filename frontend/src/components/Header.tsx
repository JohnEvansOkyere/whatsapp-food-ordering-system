import { ChevronDown, ShoppingBag, Utensils } from 'lucide-react'
import { RESTAURANT } from '../lib/menuData'
import { Branch } from '@/lib/branches'

interface HeaderProps {
  totalItems: number
  onCartOpen: () => void
  branch: Branch
  onBranchChange: () => void
}

export default function Header({
  totalItems,
  onCartOpen,
  branch,
  onBranchChange,
}: HeaderProps) {
  return (
    <header className="sticky top-0 z-40 border-b border-black/5 bg-[#fffaf4]/95 shadow-[0_8px_35px_rgba(31,14,5,0.08)] backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl bg-[#1b0b04] text-[#f7b32b]">
            <Utensils size={19} />
          </span>
          <div className="min-w-0">
            <p
              className="truncate text-lg font-black leading-none text-[#1b0b04]"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              {RESTAURANT.name}
            </p>
            <button
              type="button"
              onClick={onBranchChange}
              className="mt-1 flex max-w-full items-center gap-1 text-xs font-bold text-black/55 transition hover:text-[#d95d20]"
            >
              <span className="truncate">{branch.name}</span>
              <ChevronDown size={13} />
            </button>
          </div>
        </div>
        <button
          onClick={onCartOpen}
          className="relative flex items-center gap-2 rounded-full bg-[#1b0b04] px-4 py-2.5 text-sm font-bold text-white shadow-lg transition active:scale-95"
        >
          <ShoppingBag size={18} />
          <span>Cart</span>
          {totalItems > 0 && (
            <span className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-[#f7b32b] text-xs font-black text-[#1b0b04]">
              {totalItems}
            </span>
          )}
        </button>
      </div>
    </header>
  )
}
