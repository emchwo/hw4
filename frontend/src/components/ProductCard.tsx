import { Link } from 'react-router-dom'
import { formatPrice, type Product } from '../api'
import Closeup from './Closeup'

export default function ProductCard({ product }: { product: Product }) {
  const soldOut = product.total_stock === 0

  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <div className="product-card-image">
        <Closeup src={product.image_url} alt={product.name} />
        {soldOut && <span className="badge badge-muted">Sold out</span>}
      </div>
      <div className="product-card-body">
        <span className="product-card-type">{product.garment_type}</span>
        <h3>{product.name}</h3>
        <span className="product-card-price">{formatPrice(product.price)}</span>
      </div>
    </Link>
  )
}
