export interface BranchHeroMedia {
  /** Omitted when the surface leads with a still rather than motion. */
  videoSrc?: string
  posterSrc: string
}

/**
 * The entrance screen leads with motion — one clip of the room, shown before a
 * branch has been chosen, so it is deliberately not branch-specific.
 */
export const ENTRANCE_HERO_MEDIA: BranchHeroMedia = {
  videoSrc: '/video/branch-hero.mp4',
  posterSrc: '/video/branch-hero-poster.jpg',
}

/**
 * Branch pages lead with food instead. It gives the two screens something
 * different to say — the room, then the plate — and a still costs a fraction of
 * the clip on a phone, right where the menu is the next thing to load.
 *
 * Swap a branch back to motion by adding a `videoSrc` here.
 */
const HERO_MEDIA_BY_BRANCH: Record<string, BranchHeroMedia> = {
  'ashesi-university': { posterSrc: '/images/menu/entrance-jollof.webp' },
  abelemkpe: { posterSrc: '/images/menu/entrance-feast.webp' },
}

const FALLBACK_BRANCH_MEDIA: BranchHeroMedia = {
  posterSrc: '/images/menu/entrance-pizza.webp',
}

export function getBranchHeroMedia(branchSlug: string): BranchHeroMedia {
  return HERO_MEDIA_BY_BRANCH[branchSlug] || FALLBACK_BRANCH_MEDIA
}
