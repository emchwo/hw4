import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { getProducts, type Product } from '../api'
import ProductCard from '../components/ProductCard'
import Closeup from '../components/Closeup'
import Seal from '../components/Seal'

const FEATURED_IDS = [
  'champion-reverse-weave-crewneck',
  'basic-hoodie-big-yale',
  '2025-yale-vs-harvard-t-shirt',
  'brooks-brothers-bomber-jacket-yale',
]

// How far the hero video advances per pixel of mouse movement (~2,500px of movement = the full 9s loop).
const SECONDS_PER_PIXEL = 0.0036

// One closeup per category: cropped in on the fabric and graphic.
const COLLECTIONS = [
  { category: 'Hoodies', image: 'district-vit-hoodie-vintage-sailor-bulldog', zoom: 1.7, focus: '50% 40%' },
  { category: 'Crewnecks', image: 'champion-reverse-weave-crewneck', zoom: 1.6, focus: '50% 38%' },
  { category: 'Quarter-Zips', image: 'benjamin-franklin-1-4-zip', zoom: 1.6, focus: '50% 30%' },
  { category: 'T-Shirts', image: 'yale-bowl-t-shirt', zoom: 1.6, focus: '50% 42%' },
  { category: 'Jackets', image: 'brooks-brothers-bomber-jacket-yale', zoom: 1.5, focus: '55% 35%' },
  { category: 'Long Sleeve', image: 'ua-mens-tech-l-s-2-0', zoom: 1.6, focus: '50% 35%' },
]

export default function Home() {
  const [featured, setFeatured] = useState<Product[]>([])
  const videoRef = useRef<HTMLVideoElement>(null)

  // The video never plays on its own: moving the mouse scrubs it forward, looping at the end.
  // (hero.mp4 is encoded with a keyframe on every frame so seeking is smooth.
  // "Reduce motion" users keep the still frame.)
  useEffect(() => {
    const video = videoRef.current
    if (!video || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    let pending = 0
    let frame = 0

    const step = () => {
      frame = 0
      if (!video.duration) return
      // Wait for the previous seek to land so frames don't pile up.
      if (video.seeking) {
        frame = requestAnimationFrame(step)
        return
      }
      video.currentTime = (video.currentTime + pending * SECONDS_PER_PIXEL) % video.duration
      pending = 0
    }

    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== 'mouse') return
      pending += Math.hypot(e.movementX, e.movementY)
      if (!frame) frame = requestAnimationFrame(step)
    }

    window.addEventListener('pointermove', onMove, { passive: true })
    return () => {
      window.removeEventListener('pointermove', onMove)
      cancelAnimationFrame(frame)
    }
  }, [])

  useEffect(() => {
    getProducts()
      .then((all) =>
        setFeatured(FEATURED_IDS.map((id) => all.find((p) => p.product_id === id)).filter((p): p is Product => !!p)),
      )
      .catch(() => setFeatured([]))
  }, [])

  return (
    <>
      <section className="hero">
        {/* The Campus Customs ad (HW 3/data/videos/ad_humble.mp4), re-encoded to H.264 with no audio. */}
        <video
          ref={videoRef}
          className="hero-video"
          src="/hero.mp4"
          poster="/hero.jpg"
          preload="auto"
          muted
          playsInline
          aria-hidden="true"
        />
        <div className="hero-center">
          <h1 className="sr-only">Campus Customs</h1>
          <Seal className="hero-seal" />
          <Link to="/products" className="btn btn-primary">
            Shop the collection
          </Link>
        </div>
      </section>

      <section className="collection-grid sepia-hover" aria-label="Shop by category">
        {COLLECTIONS.map((c) => (
          <Link key={c.category} to={`/products?category=${encodeURIComponent(c.category)}`} className="collection-tile">
            <Closeup src={`/images/${c.image}.jpg`} zoom={c.zoom} focus={c.focus} />
            <span className="collection-label">
              <span>{c.category}</span>
              <span>→</span>
            </span>
          </Link>
        ))}
      </section>

      <div className="statement">
        <span className="wood" aria-hidden="true" />
        <p>Heavyweight fleece, washed cotton, and Bulldog blue — for the people who make Yale home.</p>
      </div>

      {featured.length > 0 && (
        <section className="section">
          <div className="container">
            <div className="section-head">
              <h2>Essentials</h2>
              <Link to="/products" className="link-arrow">
                View all →
              </Link>
            </div>
            <div className="product-grid">
              {featured.map((p) => (
                <ProductCard key={p.product_id} product={p} />
              ))}
            </div>
          </div>
        </section>
      )}
    </>
  )
}
