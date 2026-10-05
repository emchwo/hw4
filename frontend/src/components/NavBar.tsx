import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../auth'
import { CATEGORIES } from '../categories'
import Closeup from './Closeup'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

// A thin menu bar. Hovering "Products" expands it into a frosted-glass shop panel
// (on mobile, the menu button opens the same panel with every link).
export default function NavBar() {
  const [expanded, setExpanded] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const { user, loading, openModal, logout } = useAuth()
  const { pathname } = useLocation()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Collapse after navigating.
  useEffect(() => setExpanded(false), [pathname])

  const close = () => setExpanded(false)
  const auth = (mode: 'login' | 'register') => {
    close()
    openModal(mode)
  }

  return (
    <header
      className={`nav ${expanded ? 'expanded' : ''} ${scrolled ? 'scrolled' : ''}`}
      onMouseLeave={close}
      onBlur={(e) => !e.currentTarget.contains(e.relatedTarget) && close()}
    >
      <div className="nav-bar">
        <nav className="nav-left" aria-label="Main">
          {links.map((l) => {
            const opensPanel = l.to === '/products'
            return (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                className="nav-item"
                onMouseEnter={opensPanel ? () => setExpanded(true) : close}
                onFocus={opensPanel ? () => setExpanded(true) : close}
              >
                {l.label}
              </NavLink>
            )
          })}
        </nav>

        <Link to="/" className="brand" aria-label="Campus Customs home" onMouseEnter={close}>
          Campus Customs
        </Link>

        <div className="nav-right" onMouseEnter={close}>
          {loading ? null : user ? (
            <>
              <span className="nav-greeting">Hi, {user.first_name ?? user.name}</span>
              <button className="nav-item" onClick={() => { close(); logout() }}>
                Log Out
              </button>
            </>
          ) : (
            <>
              <button className="nav-item" onClick={() => auth('login')}>
                Log In
              </button>
              <button className="nav-item" onClick={() => auth('register')}>
                Create Account
              </button>
            </>
          )}
        </div>

        <button
          className="nav-toggle"
          aria-label="Menu"
          aria-expanded={expanded}
          onClick={() => setExpanded((o) => !o)}
        >
          <span />
          <span />
        </button>
      </div>

      <div className="nav-panel" aria-hidden={!expanded}>
        <div className="nav-panel-inner">
          <div className="nav-panel-content">
            <div className="nav-col">
              <h3>Shop</h3>
              <Link to="/products" onClick={close}>All products</Link>
              {CATEGORIES.map((c) => (
                <Link key={c} to={`/products?category=${encodeURIComponent(c)}`} onClick={close}>
                  {c}
                </Link>
              ))}
            </div>
            {/* Phones hide the bar's links, so the panel repeats them there only. */}
            <div className="nav-col mobile-only">
              <h3>Campus Customs</h3>
              {links.map((l) => (
                <Link key={l.to} to={l.to} onClick={close}>
                  {l.label}
                </Link>
              ))}
            </div>
            <div className="nav-col mobile-only">
              <h3>Account</h3>
              {user ? (
                <button onClick={() => { close(); logout() }}>Log out</button>
              ) : (
                <>
                  <button onClick={() => auth('login')}>Log in</button>
                  <button onClick={() => auth('register')}>Create account</button>
                </>
              )}
            </div>
            <Link to="/products?category=Hoodies" className="nav-feature" onClick={close}>
              <Closeup src="/images/district-vit-hoodie-vintage-bulldog.jpg" zoom={1.6} focus="50% 38%" />
              <span>Hoodies →</span>
            </Link>
          </div>
        </div>
      </div>
    </header>
  )
}
