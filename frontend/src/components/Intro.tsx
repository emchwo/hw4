import { useState } from 'react'

const SEEN_KEY = 'cc-intro-seen'

// Shows "Campus Customs" full-screen the first time the site is opened in a browser session.
export default function Intro() {
  const [show] = useState(() => {
    if (sessionStorage.getItem(SEEN_KEY)) return false
    sessionStorage.setItem(SEEN_KEY, '1')
    return true
  })
  if (!show) return null
  return (
    <div className="intro" aria-hidden="true">
      <span>Campus Customs</span>
    </div>
  )
}
