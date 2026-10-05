// garment_type in the catalogue is free text (22 variants), so group it into shop categories.
export const CATEGORIES = ['Hoodies', 'Crewnecks', 'Quarter-Zips', 'T-Shirts', 'Jackets', 'Long Sleeve'] as const

export type Category = (typeof CATEGORIES)[number]

export function categoryOf(garmentType: string): Category {
  const t = garmentType.toLowerCase()
  if (t.includes('t-shirt')) return 'T-Shirts'
  if (t.includes('hood')) return 'Hoodies'
  if (t.includes('quarter-zip')) return 'Quarter-Zips'
  if (t.includes('jacket')) return 'Jackets'
  if (t.includes('long-sleeve')) return 'Long Sleeve'
  return 'Crewnecks'
}
