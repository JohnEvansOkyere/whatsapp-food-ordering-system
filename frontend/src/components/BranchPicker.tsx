import { ArrowRight } from 'lucide-react'
import HeroMedia from './HeroMedia'
import { Branch } from '@/lib/branches'
import { ENTRANCE_HERO_MEDIA } from '@/lib/branchHero'
import { RESTAURANT } from '@/lib/menuData'

interface BranchPickerProps {
  branches: Branch[]
  loading: boolean
  onSelect: (branch: Branch) => void
}

export default function BranchPicker({
  branches,
  loading,
  onSelect,
}: BranchPickerProps) {
  return (
    <div className="fixed inset-0 z-[70] isolate overflow-hidden bg-[#0d0502] text-white">
      <HeroMedia media={ENTRANCE_HERO_MEDIA} />

      {/* Light through the middle so the footage actually reads, weighted at the
          bottom where the buttons need contrast. */}
      <div
        className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/25 to-black/85"
        aria-hidden="true"
      />

      <div className="absolute inset-0 overflow-y-auto">
        <div className="mx-auto flex min-h-full w-full max-w-md flex-col justify-end px-5 pb-[calc(2.5rem+env(safe-area-inset-bottom))] pt-24">
          <p
            className="branch-entrance text-xs font-bold uppercase tracking-[0.34em] text-[#f6b51e]"
            style={{ animationDelay: '80ms' }}
          >
            {RESTAURANT.name}
          </p>
          <h1
            className="branch-entrance mt-2 text-5xl font-black leading-none tracking-[-0.03em] text-[#fffdf8]"
            style={{ animationDelay: '180ms', fontFamily: 'var(--font-display)' }}
          >
            Branches
          </h1>

          {/* Two up, side by side — one full-width row per branch left a lot of
              dead space and made each tile read as a banner rather than a
              choice. */}
          <div
            className="branch-entrance mt-7 grid grid-cols-2 gap-3"
            style={{ animationDelay: '300ms' }}
            role="group"
            aria-label="Choose a restaurant branch"
          >
            {loading
              ? [0, 1].map(index => (
                  <div
                    key={index}
                    className="h-[116px] animate-pulse rounded-2xl border border-white/10 bg-white/[0.08] backdrop-blur-xl"
                  />
                ))
              : branches.map(branch => (
                  <button
                    key={branch.id}
                    type="button"
                    disabled={!branch.accepting_orders}
                    onClick={() => onSelect(branch)}
                    aria-label={`Order from ${branch.name}`}
                    className="branch-card group flex min-h-[116px] flex-col justify-between gap-4 rounded-2xl border border-white/15 bg-black/35 p-4 text-left backdrop-blur-xl transition duration-300 hover:border-[#f6b51e]/60 hover:bg-black/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#f4ad18] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0d0502] disabled:cursor-not-allowed disabled:opacity-45"
                  >
                    <span className="text-base font-black leading-tight tracking-[-0.01em]">
                      {branch.name}
                    </span>
                    {branch.accepting_orders ? (
                      <ArrowRight
                        size={18}
                        className="self-end text-[#f6b51e] transition-transform duration-300 group-hover:translate-x-1"
                      />
                    ) : (
                      <span className="self-end text-[10px] font-bold uppercase tracking-[0.18em] text-white/60">
                        Closed
                      </span>
                    )}
                  </button>
                ))}
          </div>
        </div>
      </div>
    </div>
  )
}
