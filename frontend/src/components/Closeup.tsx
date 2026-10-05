import { useState, type CSSProperties, type SyntheticEvent } from 'react'

// Product photos come on white, black, or dark-gray backgrounds. To show every garment on a
// blank backdrop without editing the photo, sample its corner color and paint the frame to match.
const frameCache = new Map<string, string>()

function sampleFrame(img: HTMLImageElement): string | null {
  try {
    const canvas = document.createElement('canvas')
    canvas.width = canvas.height = 1
    const ctx = canvas.getContext('2d')
    if (!ctx) return null
    ctx.drawImage(img, 2, 2, 1, 1, 0, 0, 1, 1)
    const [r, g, b] = ctx.getImageData(0, 0, 1, 1).data
    return `rgb(${r}, ${g}, ${b})`
  } catch {
    return null
  }
}

interface CloseupProps {
  src: string
  alt?: string
  /** Scale > 1 crops in for a closeup of the fabric and graphic. */
  zoom?: number
  /** transform-origin for the zoom, e.g. "50% 40%". */
  focus?: string
  eager?: boolean
}

export default function Closeup({ src, alt = '', zoom = 1, focus, eager = false }: CloseupProps) {
  const [frame, setFrame] = useState<string | null>(() => frameCache.get(src) ?? null)

  function handleLoad(e: SyntheticEvent<HTMLImageElement>) {
    if (frameCache.has(src)) return
    const f = sampleFrame(e.currentTarget)
    if (f) {
      frameCache.set(src, f)
      setFrame(f)
    }
  }

  const style = {
    '--zoom': zoom,
    ...(focus ? { '--focus': focus } : {}),
    ...(frame ? { '--frame': frame } : {}),
  } as CSSProperties

  return (
    <div className="closeup" style={style}>
      <img src={src} alt={alt} loading={eager ? 'eager' : 'lazy'} onLoad={handleLoad} />
    </div>
  )
}
