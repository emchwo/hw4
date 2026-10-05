import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getProducts, type Product } from '../api'
import ProductCard from '../components/ProductCard'
import SearchResultCard from '../components/SearchResultCard'
import { useChatSearch } from '../chatSearch'
import { usePublishPage } from '../pageContext'
import { CATEGORIES, categoryOf } from '../categories'

export default function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [params, setParams] = useSearchParams()
  const category = params.get('category')
  const { results, clearResults } = useChatSearch()

  // Picking a category (e.g. from the home page tiles) replaces any chat results.
  useEffect(() => {
    if (category) clearResults()
  }, [category])

  useEffect(() => {
    getProducts()
      .then(setProducts)
      .catch(() => setError('We couldn’t load products right now. Please make sure the server is running.'))
      .finally(() => setLoading(false))
  }, [])

  const visible = useMemo(
    () => (category ? products.filter((p) => categoryOf(p.garment_type) === category) : products),
    [products, category],
  )

  usePublishPage({
    category,
    search_label: results?.label ?? null,
    visible_product_ids: (results ? results.matches.map((m) => m.id) : visible.map((p) => p.product_id)).slice(0, 60),
  })

  const selectCategory = (c: string | null) => setParams(c ? { category: c } : {})

  return (
    <section className="section">
      <div className="container">
        <div className="page-head">
          <h1>Products</h1>
        </div>

        {results && (
          <section key={results.id} className="chat-results" aria-live="polite">
            <div className="chat-results-head">
              <div>
                <span className="eyebrow">From your chat</span>
                <h2>{results.label}</h2>
                <p className="muted">
                  {results.matches.length === 0
                    ? 'No products matched that search. Try asking the assistant another way.'
                    : results.total > results.matches.length
                      ? `Showing ${results.matches.length} of ${results.total} matches`
                      : `${results.total} ${results.total === 1 ? 'match' : 'matches'}`}
                </p>
              </div>
              <button className="btn btn-ghost btn-sm" onClick={clearResults}>
                Show all products
              </button>
            </div>
            {results.matches.length > 0 && (
              <div className="product-grid">
                {results.matches.map((m) => (
                  <SearchResultCard key={m.id} match={m} />
                ))}
              </div>
            )}
          </section>
        )}

        {!results && (
          <>
            <div className="chips" role="tablist" aria-label="Filter by category">
              <button className={`chip ${!category ? 'active' : ''}`} onClick={() => selectCategory(null)}>
                All
              </button>
              {CATEGORIES.map((c) => (
                <button key={c} className={`chip ${category === c ? 'active' : ''}`} onClick={() => selectCategory(c)}>
                  {c}
                </button>
              ))}
            </div>

            {loading && <p className="muted">Loading products…</p>}
            {error && <p className="notice notice-error">{error}</p>}

            {!loading && !error && (
              <>
                <p className="result-count muted">
                  {visible.length} {visible.length === 1 ? 'item' : 'items'}
                </p>
                <div className="product-grid">
                  {visible.map((p) => (
                    <ProductCard key={p.product_id} product={p} />
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </section>
  )
}
