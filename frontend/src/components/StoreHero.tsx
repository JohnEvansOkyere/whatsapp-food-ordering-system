import { ChevronDown } from 'lucide-react'
import HeroMedia from './HeroMedia'
import { Branch } from '@/lib/branches'
import { getBranchHeroMedia } from '@/lib/branchHero'
import { RESTAURANT } from '@/lib/menuData'

interface StoreHeroProps {
  branch: Branch
  onBrowse: () => void
}

export default function StoreHero({ branch, onBrowse }: StoreHeroProps) {
  const media = getBranchHeroMedia(branch.slug)

  return (
    // Short of full height on phones on purpose: the top of the menu header
    // stays visible, so the menu reads as reachable without the chevron.
    <section className="relative isolate h-[86svh] min-h-[460px] max-h-[880px] w-full overflow-hidden bg-[#160a05] text-white sm:h-[100svh] sm:min-h-[560px]">
      <HeroMedia media={media} />

      {/* Kept light through the middle so the food stays the subject. */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/55 via-black/30 to-black/80" />

      {/* The shadow is inherited by both lines. A food still is far brighter
          than the video this replaced, and it is bright in unpredictable
          places, so the type carries its own contrast rather than the whole
          photo being dimmed to suit it. */}
      <div
        className="absolute inset-0 z-10 flex flex-col items-center justify-center px-6 text-center"
        style={{ textShadow: '0 2px 20px rgba(0,0,0,0.8), 0 1px 4px rgba(0,0,0,0.5)' }}
      >
        <p
          className="animate-hero-fade-up text-xs font-bold uppercase tracking-[0.34em] text-[#f6b51e]"
        >
          {RESTAURANT.name}
        </p>
        <h1
          className="animate-hero-fade-up mt-3 max-w-3xl text-5xl font-black leading-[0.95] tracking-[-0.03em] sm:text-7xl"
          style={{ animationDelay: '160ms', fontFamily: 'var(--font-display)' }}
        >
          {branch.name}
        </h1>
      </div>

      <button
        type="button"
        onClick={onBrowse}
        aria-label="Scroll to the menu"
        className="absolute bottom-3 left-1/2 z-10 flex h-12 w-12 -translate-x-1/2 animate-bounce items-center justify-center text-white/60 transition hover:text-white"
      >
        <ChevronDown size={26} strokeWidth={2.5} />
      </button>
    </section>
  )
}
