import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <section className="section">
      <div className="container narrow">
        <h1>Page not found</h1>
        <p className="muted">That page wandered off campus.</p>
        <Link to="/" className="btn btn-primary">
          Back home
        </Link>
      </div>
    </section>
  )
}
