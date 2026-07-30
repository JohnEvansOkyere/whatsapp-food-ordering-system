import { useEffect, useState } from 'react'
import { ArrowRight, Clock3, MapPin, Store } from 'lucide-react'
import { Branch, branchEta } from '@/lib/branches'
import { RESTAURANT } from '@/lib/menuData'

interface BranchPickerProps {
  branches: Branch[]
  loading: boolean
  onSelect: (branch: Branch) => void
}

const BACKGROUND_SLIDES = [
  {
    src: '/images/menu/entrance-feast.webp',
    position: '68% center',
  },
  {
    src: '/images/menu/entrance-pizza.webp',
    position: '62% center',
  },
  {
    src: '/images/menu/entrance-jollof.webp',
    position: '70% center',
  },
]

export default function BranchPicker({
  branches,
  loading,
  onSelect,
}: BranchPickerProps) {
  const [activeSlide, setActiveSlide] = useState(0)

  useEffect(() => {
    BACKGROUND_SLIDES.forEach(slide => {
      const image = new window.Image()
      image.src = slide.src
    })

    const timer = window.setInterval(() => {
      setActiveSlide(current => (current + 1) % BACKGROUND_SLIDES.length)
    }, 9000)

    return () => window.clearInterval(timer)
  }, [])

  return (
    <div className="fixed inset-0 z-[70] overflow-y-auto bg-[#100704] text-white">
      <div className="relative isolate min-h-[100svh] overflow-hidden">
        <div className="absolute inset-0 -z-30 bg-[#100704]" aria-hidden="true">
          {BACKGROUND_SLIDES.map((slide, index) => (
            <div
              key={slide.src}
              className={`branch-background-slide ${
                activeSlide === index ? 'is-active' : ''
              }`}
              style={{
                backgroundImage: `url(${slide.src})`,
                backgroundPosition: slide.position,
              }}
            />
          ))}
        </div>

        <div
          className="absolute inset-0 -z-20 bg-[linear-gradient(90deg,rgba(13,5,2,0.98)_0%,rgba(13,5,2,0.91)_35%,rgba(13,5,2,0.48)_72%,rgba(13,5,2,0.3)_100%)] max-md:bg-[linear-gradient(180deg,rgba(13,5,2,0.76)_0%,rgba(13,5,2,0.86)_46%,rgba(13,5,2,0.98)_100%)]"
          aria-hidden="true"
        />
        <div
          className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_72%_33%,transparent_0%,rgba(13,5,2,0.08)_42%,rgba(13,5,2,0.76)_100%)]"
          aria-hidden="true"
        />
        <div
          className="branch-picker-grain pointer-events-none absolute inset-0 z-0"
          aria-hidden="true"
        />

        <main className="relative z-10 mx-auto flex min-h-[100svh] w-full max-w-[1400px] flex-col justify-center px-5 py-8 sm:px-8 sm:py-12 lg:px-14 xl:px-16">
          <div className="max-w-[780px]">
            <div
              className="branch-entrance inline-flex items-center gap-2.5 rounded-full border border-white/[0.11] bg-black/25 px-4 py-2.5 text-[11px] font-bold uppercase tracking-[0.24em] text-[#f5d9b5] backdrop-blur-xl sm:text-xs"
              style={{ animationDelay: '60ms' }}
            >
              <span className="h-2 w-2 rounded-full bg-[#f2aa16] shadow-[0_0_18px_rgba(242,170,22,0.9)]" />
              Freshly made in Ghana
            </div>

            <p
              className="branch-entrance mb-3 mt-8 text-xs font-bold uppercase tracking-[0.34em] text-[#f6b51e] sm:text-sm"
              style={{ animationDelay: '160ms' }}
            >
              {RESTAURANT.name}
            </p>
            <h1
              className="branch-entrance max-w-[760px] text-[clamp(3.4rem,7vw,6.25rem)] font-black leading-[0.92] tracking-[-0.04em] text-[#fffdf8]"
              style={{
                animationDelay: '270ms',
                fontFamily: 'var(--font-display)',
              }}
            >
              Hot food.
              <br />
              <span className="text-[#f6ad13]">Right branch.</span>
              <br />
              No guessing.
            </h1>
            <p
              className="branch-entrance mt-5 max-w-2xl text-sm leading-6 text-white/72 sm:text-lg sm:leading-7"
              style={{ animationDelay: '390ms' }}
            >
              Choose your kitchen and we will send every order update straight
              to WhatsApp.
            </p>
          </div>

          <section
            className="branch-entrance mt-8 grid min-w-0 w-full max-w-[1000px] gap-3 md:grid-cols-2"
            style={{ animationDelay: '520ms' }}
            aria-label="Choose a restaurant branch"
          >
            {loading
              ? [0, 1].map(index => (
                  <div
                    key={index}
                    className="h-[224px] animate-pulse rounded-[22px] border border-white/10 bg-white/[0.08] backdrop-blur-xl"
                  />
                ))
              : branches.map((branch, index) => (
                  <button
                    key={branch.id}
                    type="button"
                    disabled={!branch.accepting_orders}
                    onClick={() => onSelect(branch)}
                    aria-label={`Order from ${branch.name}`}
                    className="branch-card group min-h-[224px] min-w-0 w-full overflow-hidden rounded-[22px] border border-white/[0.11] bg-[#140a07]/55 p-5 text-left shadow-[0_20px_60px_rgba(0,0,0,0.22)] backdrop-blur-xl transition duration-300 ease-out hover:-translate-y-1 hover:border-[#f4ad18]/45 hover:shadow-[0_24px_70px_rgba(231,148,9,0.15)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#f4ad18] focus-visible:ring-offset-2 focus-visible:ring-offset-[#110704] disabled:cursor-not-allowed disabled:opacity-55 sm:p-6"
                    style={{ transitionDelay: `${index * 35}ms` }}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#d99400] text-white shadow-[0_14px_38px_rgba(225,150,0,0.25)] transition-transform duration-300 group-hover:scale-105">
                        <Store size={21} strokeWidth={2.2} />
                      </span>
                      <span
                        className={`inline-flex shrink-0 items-center gap-2 rounded-full px-3 py-1.5 text-[11px] font-bold ${
                          branch.accepting_orders
                            ? 'bg-emerald-400/15 text-emerald-200'
                            : 'bg-rose-400/15 text-rose-200'
                        }`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            branch.accepting_orders
                              ? 'branch-status-pulse bg-emerald-400'
                              : 'bg-rose-400'
                          }`}
                        />
                        {branch.accepting_orders
                          ? 'Taking orders'
                          : 'Unavailable'}
                      </span>
                    </div>

                    <h2 className="mt-6 text-xl font-black tracking-[-0.01em] sm:text-2xl">
                      {branch.name}
                    </h2>
                    <div className="mt-2.5 min-w-0 space-y-2 text-sm text-white/58">
                      <p className="flex items-start gap-2">
                        <MapPin
                          size={15}
                          className="mt-0.5 shrink-0 text-[#f6b51e]"
                        />
                        <span className="min-w-0 break-words">
                          {branch.service_area_label ||
                            branch.address ||
                            branch.city ||
                            'Location details pending'}
                        </span>
                      </p>
                      <p className="flex items-start gap-2">
                        <Clock3
                          size={15}
                          className="mt-0.5 shrink-0 text-[#f6b51e]"
                        />
                        <span className="min-w-0 break-words">
                          {branch.hours_label || 'Hours pending'} ·{' '}
                          {branchEta(branch)}
                        </span>
                      </p>
                    </div>

                    <span className="mt-5 inline-flex items-center gap-2 text-sm font-black text-[#f8b822] transition-colors group-hover:text-[#ffd36e]">
                      Order here
                      <ArrowRight
                        size={16}
                        className="transition-transform duration-300 group-hover:translate-x-1.5"
                      />
                    </span>
                  </button>
                ))}
          </section>
        </main>
      </div>
    </div>
  )
}
