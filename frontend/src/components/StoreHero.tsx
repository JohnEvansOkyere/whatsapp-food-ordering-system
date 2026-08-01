import { useEffect, useRef, useState } from 'react'
import Image from 'next/image'
import { ChevronDown } from 'lucide-react'
import { Branch } from '@/lib/branches'
import { getBranchHeroMedia } from '@/lib/branchHero'

interface StoreHeroProps {
  branch: Branch
  onBrowse: () => void
}

export default function StoreHero({ branch, onBrowse }: StoreHeroProps) {
  const media = getBranchHeroMedia(branch.slug)
  const bgVideoRef = useRef<HTMLVideoElement>(null)
  const fgVideoRef = useRef<HTMLVideoElement>(null)
  const [ready, setReady] = useState(false)
  const [reducedMotion, setReducedMotion] = useState(false)

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    setReducedMotion(query.matches)
    const handleChange = (event: MediaQueryListEvent) => setReducedMotion(event.matches)
    query.addEventListener('change', handleChange)
    return () => query.removeEventListener('change', handleChange)
  }, [])

  useEffect(() => {
    if (reducedMotion) return
    ;[bgVideoRef.current, fgVideoRef.current].forEach(video => {
      if (!video) return
      video.muted = true
      video.playbackRate = 0.85
    })
  }, [reducedMotion, media.videoSrc])

  return (
    <section className="relative isolate h-[100svh] min-h-[560px] max-h-[880px] w-full overflow-hidden bg-[#160a05] text-white">
      {reducedMotion ? (
        <Image
          src={media.posterSrc}
          alt=""
          fill
          priority
          className="object-cover"
        />
      ) : (
        <>
          {/* Layer 1: blurred, scaled-up fill — masks empty space when the video's
              aspect ratio doesn't match the section's */}
          <video
            ref={bgVideoRef}
            className={`absolute inset-0 h-full w-full scale-[1.3] object-cover blur-[40px] brightness-[0.4] transition-opacity duration-1000 ${ready ? 'opacity-100' : 'opacity-0'}`}
            src={media.videoSrc}
            poster={media.posterSrc}
            autoPlay
            muted
            loop
            playsInline
            preload="auto"
            aria-hidden="true"
          />
          {/* Layer 2: the actual footage, framed rather than cropped */}
          <video
            ref={fgVideoRef}
            className={`absolute inset-0 h-full w-full object-contain saturate-[.9] contrast-[1.05] transition-opacity duration-1000 ${ready ? 'opacity-100' : 'opacity-0'}`}
            src={media.videoSrc}
            poster={media.posterSrc}
            autoPlay
            muted
            loop
            playsInline
            preload="auto"
            onCanPlay={() => setReady(true)}
            aria-hidden="true"
          />
        </>
      )}

      <div className="absolute inset-0 bg-gradient-to-b from-black/55 via-black/60 to-black/75" />
      <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-[#0c0503] to-transparent" />

      <div className="absolute inset-0 z-10 flex flex-col items-center justify-center px-6 text-center">
        <h1
          className="animate-hero-fade-up max-w-3xl text-4xl font-black leading-[0.98] sm:text-6xl lg:text-7xl"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          Where <span className="text-[#f7b32b]">Ghana</span> eats.
        </h1>
        <p
          className="animate-hero-fade-up mt-5 text-xs font-bold uppercase tracking-[0.3em] text-white/70"
          style={{ animationDelay: '200ms' }}
        >
          {branch.name}
        </p>
      </div>

      <button
        type="button"
        onClick={onBrowse}
        aria-label="Scroll to the menu"
        className="absolute bottom-7 left-1/2 z-10 flex -translate-x-1/2 animate-bounce flex-col items-center text-white/60 transition hover:text-white"
      >
        <ChevronDown size={26} strokeWidth={2.5} />
      </button>
    </section>
  )
}
