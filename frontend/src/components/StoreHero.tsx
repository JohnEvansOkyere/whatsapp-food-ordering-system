import Image from 'next/image'
import { ArrowDown, Clock3, MapPin, MessageCircleMore } from 'lucide-react'
import { Branch, branchEta } from '@/lib/branches'

interface StoreHeroProps {
  branch: Branch
  onBrowse: () => void
}

export default function StoreHero({ branch, onBrowse }: StoreHeroProps) {
  return (
    <section className="relative isolate min-h-[500px] overflow-hidden bg-[#160a05] text-white sm:min-h-[580px]">
      <Image
        src="/images/menu/restaurant-feast-hero.png"
        alt="Fresh jollof rice, grilled chicken, pizza and fried rice"
        fill
        priority
        className="object-cover object-[65%_center]"
        sizes="100vw"
      />
      <div className="absolute inset-0 -z-0 bg-[linear-gradient(90deg,rgba(16,6,2,0.96)_0%,rgba(16,6,2,0.82)_40%,rgba(16,6,2,0.18)_78%,rgba(16,6,2,0.08)_100%)]" />
      <div className="absolute inset-x-0 bottom-0 h-40 -z-0 bg-gradient-to-t from-[#fffaf4] to-transparent" />

      <div className="relative z-10 mx-auto flex min-h-[500px] max-w-7xl items-center px-5 pb-24 pt-20 sm:min-h-[580px] sm:px-8">
        <div className="max-w-xl">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/15 bg-black/25 px-3 py-2 text-xs font-bold text-white/85 backdrop-blur-md">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Now serving from {branch.name}
          </div>
          <h1
            className="text-5xl font-black leading-[0.98] sm:text-6xl lg:text-7xl"
            style={{ fontFamily: 'var(--font-display)' }}
          >
            Big flavour.
            <br />
            <span className="text-[#f7b32b]">Made fresh.</span>
          </h1>
          <p className="mt-5 max-w-lg text-base leading-7 text-white/75 sm:text-lg">
            Ghanaian favourites, fire-grilled chicken and bubbling hot pizza
            prepared when you order—not before.
          </p>

          <div className="mt-6 flex flex-wrap gap-3 text-sm text-white/78">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-black/25 px-3 py-2 backdrop-blur">
              <MapPin size={15} className="text-[#f7b32b]" />
              {branch.name}
            </span>
            <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-black/25 px-3 py-2 backdrop-blur">
              <Clock3 size={15} className="text-[#f7b32b]" />
              {branchEta(branch)}
            </span>
            <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-black/25 px-3 py-2 backdrop-blur">
              <MessageCircleMore size={15} className="text-[#25d366]" />
              Live WhatsApp updates
            </span>
          </div>

          <button
            type="button"
            onClick={onBrowse}
            className="mt-8 inline-flex items-center gap-3 rounded-full bg-[#f7b32b] px-6 py-3.5 text-sm font-black text-[#1a0a00] shadow-[0_18px_55px_rgba(247,179,43,0.28)] transition hover:-translate-y-0.5 hover:bg-[#ffc852]"
          >
            Explore the menu
            <ArrowDown size={17} />
          </button>
        </div>
      </div>
    </section>
  )
}

