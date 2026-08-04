export interface Branch {
  id: string
  name: string
  code: string
  slug: string
  phone?: string | null
  address?: string | null
  city?: string | null
  /** Used to bias address search towards the branch's service area. */
  latitude?: number | null
  longitude?: number | null
  is_default: boolean
  accepting_orders: boolean
  is_open_now?: boolean
  hours_label?: string | null
  service_area_label?: string | null
  delivery_fee: number
  minimum_order: number
  eta_min_minutes?: number | null
  eta_max_minutes?: number | null
}

export const FALLBACK_BRANCHES: Branch[] = [
  {
    id: 'a5010000-0000-4000-8000-000000000001',
    name: 'Ashesi University',
    code: 'ASHESI',
    slug: 'ashesi-university',
    address: 'Ashesi University campus',
    city: 'Berekuso',
    is_default: true,
    accepting_orders: true,
    hours_label: 'Daily 10:00–22:00 (provisional)',
    service_area_label: 'Ashesi campus and nearby Berekuso',
    delivery_fee: 5,
    minimum_order: 25,
    eta_min_minutes: 35,
    eta_max_minutes: 60,
  },
  {
    id: 'abe10000-0000-4000-8000-000000000002',
    name: 'Abelemkpe',
    code: 'ABELEMKPE',
    slug: 'abelemkpe',
    address: 'Abelemkpe, Accra',
    city: 'Accra',
    is_default: false,
    accepting_orders: true,
    hours_label: 'Daily 10:00–22:00 (provisional)',
    service_area_label: 'Abelemkpe and nearby Accra areas',
    delivery_fee: 8,
    minimum_order: 25,
    eta_min_minutes: 35,
    eta_max_minutes: 60,
  },
]

export function branchEta(branch: Branch): string {
  if (branch.eta_min_minutes && branch.eta_max_minutes) {
    return `${branch.eta_min_minutes}–${branch.eta_max_minutes} min`
  }
  return 'ETA confirmed after acceptance'
}
