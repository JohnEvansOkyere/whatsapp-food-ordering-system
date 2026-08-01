export interface BranchHeroMedia {
  videoSrc: string
  posterSrc: string
}

const DEFAULT_HERO_MEDIA: BranchHeroMedia = {
  videoSrc: '/video/branch-hero.mp4',
  posterSrc: '/video/branch-hero-poster.jpg',
}

// Keyed by branch slug — override per branch here once branch-specific footage exists.
const HERO_MEDIA_BY_BRANCH: Record<string, BranchHeroMedia> = {
  'ashesi-university': DEFAULT_HERO_MEDIA,
  abelemkpe: DEFAULT_HERO_MEDIA,
}

export function getBranchHeroMedia(branchSlug: string): BranchHeroMedia {
  return HERO_MEDIA_BY_BRANCH[branchSlug] || DEFAULT_HERO_MEDIA
}
