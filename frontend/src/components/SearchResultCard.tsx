import { Link } from 'react-router-dom'
import { formatPrice, type ProductMatch } from '../api'
import Closeup from './Closeup'

export default function SearchResultCard({ match }: { match: ProductMatch }) {
  return (
    <Link to={match.product_url} className="product-card">
      <div className="product-card-image">
        <Closeup src={match.image_url} alt={match.name} />
        {!match.in_stock && <span className="badge badge-muted">Sold out</span>}
      </div>
      <div className="product-card-body">
        <h3>{match.name}</h3>
        <p className="product-card-desc">{match.short_description}</p>
        <span className="product-card-price">{formatPrice(match.price)}</span>
      </div>
    </Link>
  )
}
