import { useEffect, useRef, useState } from 'react'
import Image from 'next/image'
import { BranchHeroMedia } from '@/lib/branchHero'

interface HeroMediaProps {
  media: BranchHeroMedia
}

/**
 * The cinematic background shared by the branch picker and the store hero, so
 * the two can't drift apart.
 *
 * Media without a `videoSrc` renders as a still — that is the branch pages,
 * which lead with food — and so does anything under `prefers-reduced-motion`.
 *
 * For video, phones get a single cover-cropped layer. Wide screens add the
 * blurred fill behind it, which masks the letterboxing when the footage is
 * narrower than the frame — on a portrait phone the crop already fills it, so
 * that second full-viewport video would be a doubled download and a second
 * filtered layer in the compositor for no visual gain.
 *
 * The host element must be `relative isolate overflow-hidden`.
 */
export default function HeroMedia({ media }: HeroMediaProps) {
  const bgVideoRef = useRef<HTMLVideoElement>(null)
  const fgVideoRef = useRef<HTMLVideoElement>(null)
  const [ready, setReady] = useState(false)
  const [reducedMotion, setReducedMotion] = useState(false)
  // Defaults to false so phones render the light treatment on first paint and
  // never fetch the desktop blur layer at all.
  const [wide, setWide] = useState(false)

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    setReducedMotion(query.matches)
    const handleChange = (event: MediaQueryListEvent) => setReducedMotion(event.matches)
    query.addEventListener('change', handleChange)
    return () => query.removeEventListener('change', handleChange)
  }, [])

  useEffect(() => {
    const query = window.matchMedia('(min-width: 640px)')
    setWide(query.matches)
    const handleChange = (event: MediaQueryListEvent) => setWide(event.matches)
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

  if (reducedMotion || !media.videoSrc) {
    return (
      <Image
        src={media.posterSrc}
        alt=""
        fill
        priority
        sizes="100vw"
        className="object-cover"
      />
    )
  }

  return (
    <>
      {wide && (
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
      )}
      <video
        ref={fgVideoRef}
        className={`absolute inset-0 h-full w-full saturate-[.9] contrast-[1.05] transition-opacity duration-1000 ${
          wide ? 'object-contain' : 'object-cover'
        } ${ready ? 'opacity-100' : 'opacity-0'}`}
        src={media.videoSrc}
        poster={media.posterSrc}
        autoPlay
        muted
        loop
        playsInline
        preload={wide ? 'auto' : 'metadata'}
        onCanPlay={() => setReady(true)}
        aria-hidden="true"
      />
    </>
  )
}
