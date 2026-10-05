import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import type { PageContext } from './api'

// Lets pages tell the chat what the shopper is looking at (e.g. which product page they're on).
type PageDetails = Omit<PageContext, 'path'>

const PageContextCtx = createContext<{ details: PageDetails; setDetails: (d: PageDetails) => void } | null>(null)

export function PageContextProvider({ children }: { children: ReactNode }) {
  const [details, setDetails] = useState<PageDetails>({})
  return <PageContextCtx.Provider value={{ details, setDetails }}>{children}</PageContextCtx.Provider>
}

function useCtx() {
  const ctx = useContext(PageContextCtx)
  if (!ctx) throw new Error('Page context hooks must be used inside PageContextProvider')
  return ctx
}

/** Call from a page to publish what it shows; cleared when the page unmounts. */
export function usePublishPage(details: PageDetails) {
  const { setDetails } = useCtx()
  const key = JSON.stringify(details)
  useEffect(() => {
    setDetails(JSON.parse(key))
    return () => setDetails({})
  }, [key, setDetails])
}

/** The full page context sent with each chat message. */
export function useCurrentPage(): PageContext {
  const { details } = useCtx()
  const { pathname } = useLocation()
  return { path: pathname, ...details }
}
