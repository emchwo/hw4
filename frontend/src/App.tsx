import { useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import NavBar from './components/NavBar'
import Footer from './components/Footer'
import ChatWidget from './components/ChatWidget'
import AuthModal from './components/AuthModal'
import Intro from './components/Intro'
import { useAuth, type AuthMode } from './auth'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductPage from './pages/ProductPage'
import About from './pages/About'
import NotFound from './pages/NotFound'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

// Old /login and /create-account URLs open the matching panel on the home page.
function OpenAuth({ mode }: { mode: AuthMode }) {
  const { openModal } = useAuth()
  useEffect(() => openModal(mode), [mode, openModal])
  return <Navigate to="/" replace />
}

export default function App() {
  return (
    <div className="app">
      <Intro />
      <ScrollToTop />
      <NavBar />
      <main className="main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductPage />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<OpenAuth mode="login" />} />
          <Route path="/create-account" element={<OpenAuth mode="register" />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
      <ChatWidget />
      <AuthModal />
    </div>
  )
}
