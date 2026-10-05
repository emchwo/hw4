import type { ReactNode } from 'react'

// Minimal, safe Markdown for chat bubbles: **bold**, "- " / "1. " lists, and line breaks.
// Builds React elements (no innerHTML), so model text can't inject HTML.
function inline(text: string, keyBase: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') && part.length > 4 ? (
      <strong key={`${keyBase}-${i}`}>{part.slice(2, -2)}</strong>
    ) : (
      part
    ),
  )
}

export default function RichText({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  let list: { ordered: boolean; items: string[] } | null = null

  const flush = () => {
    if (!list) return
    const Tag = list.ordered ? 'ol' : 'ul'
    const key = `l${blocks.length}`
    const items = list.items
    blocks.push(
      <Tag key={key}>
        {items.map((item, i) => (
          <li key={i}>{inline(item, `${key}-${i}`)}</li>
        ))}
      </Tag>,
    )
    list = null
  }

  text.split('\n').forEach((line, i) => {
    const bullet = line.match(/^\s*[-*•]\s+(.*)$/)
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/)
    const item = bullet ?? numbered
    if (item) {
      const ordered = !bullet
      if (list && list.ordered !== ordered) flush()
      if (!list) list = { ordered, items: [] }
      list.items.push(item[1])
      return
    }
    flush()
    if (line.trim()) blocks.push(<p key={`p${i}`}>{inline(line, `p${i}`)}</p>)
  })
  flush()
  return <>{blocks}</>
}
