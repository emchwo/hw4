import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { formatPrice, getProduct, type ProductDetail } from '../api'
import { usePublishPage } from '../pageContext'
import { useChatSearch } from '../chatSearch'
import Closeup from '../components/Closeup'

const LOW_STOCK = 5

function stockLabel(qty: number) {
  if (qty === 0) return 'Out of stock'
  if (qty <= LOW_STOCK) return `Only ${qty} left`
  return `${qty} in stock`
}

export default function ProductPage() {
  const { productId } = useParams()
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [error, setError] = useState('')
  const [selectedSize, setSelectedSize] = useState<string | null>(null)
  // Tell the chat which product (and size) the shopper is looking at.
  usePublishPage({ product_id: product?.product_id ?? null, selected_size: selectedSize })
  const { openChat } = useChatSearch()

  useEffect(() => {
    if (!productId) return
    setProduct(null)
    setError('')
    setSelectedSize(null)
    getProduct(productId)
      .then(setProduct)
      .catch(() => setError('We couldn’t find that product.'))
  }, [productId])

  if (error) {
    return (
      <section className="section">
        <div className="container">
          <p className="notice notice-error">{error}</p>
          <Link to="/products" className="link-arrow">
            ← Back to products
          </Link>
        </div>
      </section>
    )
  }

  if (!product) {
    return (
      <section className="section">
        <div className="container">
          <p className="muted">Loading…</p>
        </div>
      </section>
    )
  }

  const selected = product.inventory.find((s) => s.size === selectedSize)

  return (
    <section className="section">
      <div className="container">
        <Link to="/products" className="link-arrow back-link">
          ← Back to products
        </Link>

        <div className="product-detail">
          <div className="product-detail-image">
            <Closeup src={product.image_url} alt={product.name} eager />
          </div>

          <div className="product-detail-info">
            <span className="eyebrow">{product.garment_type}</span>
            <h1>{product.name}</h1>
            <p className="product-detail-price">{formatPrice(product.price)}</p>
            <button className="btn btn-ghost btn-sm ask-item-btn" onClick={openChat}>
              Ask about this item
            </button>

            <p className="product-detail-desc">{product.description}</p>

            <div className="detail-block">
              <h2>Colors</h2>
              <div className="color-list">
                {product.colors.map((c) => (
                  <span key={c} className="color-tag">
                    {c}
                  </span>
                ))}
              </div>
            </div>

            <div className="detail-block">
              <div className="detail-block-head">
                <h2>Sizes</h2>
                <span className="muted">{product.total_stock} total in stock</span>
              </div>
              <div className="size-grid">
                {product.inventory.map((s) => (
                  <button
                    key={s.size}
                    className={`size-option ${selectedSize === s.size ? 'selected' : ''}`}
                    disabled={s.quantity === 0}
                    onClick={() => setSelectedSize(s.size)}
                  >
                    <span className="size-name">{s.size}</span>
                    <span className={`size-stock ${s.quantity === 0 ? 'out' : s.quantity <= LOW_STOCK ? 'low' : ''}`}>
                      {stockLabel(s.quantity)}
                    </span>
                  </button>
                ))}
              </div>
              {selected && (
                <p className="muted selected-note">
                  Size {selected.size}: {stockLabel(selected.quantity).toLowerCase()}.
                </p>
              )}
            </div>

            <div className="detail-block">
              <h2>Tags</h2>
              <div className="tag-list">
                {product.search_tags.map((t) => (
                  <span key={t} className="tag">
                    #{t}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
