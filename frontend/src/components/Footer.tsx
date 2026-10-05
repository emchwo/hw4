import { Link } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Footer() {
  const { user, openModal } = useAuth()

  return (
    <footer className="footer">
      <div className="footer-inner">
        <Link to="/" className="brand">
          Campus Customs
        </Link>
        <nav className="footer-links">
          <Link to="/products">Shop</Link>
          <Link to="/about">About Us</Link>
          {!user && (
            <>
              <button className="text-link" onClick={() => openModal('login')}>
                Log In
              </button>
              <button className="text-link" onClick={() => openModal('register')}>
                Create Account
              </button>
            </>
          )}
        </nav>
      </div>
      <p className="footer-fine muted">© {new Date().getFullYear()} Campus Customs · New Haven, CT</p>
    </footer>
  )
}
