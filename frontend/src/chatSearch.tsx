import { createContext, useContext, useState, type ReactNode } from 'react'
import type { ProductMatch } from './api'

// Search results from the chat agent, shown on the Products page.
export interface ChatSearchResults {
  label: string
  message: string
  matches: ProductMatch[]
  total: number
  // Changes on every new search so the page can re-run its highlight animation.
  id: number
}

interface ChatSearchContextValue {
  results: ChatSearchResults | null
  showResults: (r: Omit<ChatSearchResults, 'id'>) => void
  clearResults: () => void
  // Lets any page open the chat (e.g. the "Ask about this item" button).
  openChatRequest: number
  openChat: () => void
}

const ChatSearchContext = createContext<ChatSearchContextValue | null>(null)

export function ChatSearchProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ChatSearchResults | null>(null)
  const [openChatRequest, setOpenChatRequest] = useState(0)

  return (
    <ChatSearchContext.Provider
      value={{
        results,
        showResults: (r) => setResults({ ...r, id: Date.now() }),
        clearResults: () => setResults(null),
        openChatRequest,
        openChat: () => setOpenChatRequest((n) => n + 1),
      }}
    >
      {children}
    </ChatSearchContext.Provider>
  )
}

export function useChatSearch() {
  const ctx = useContext(ChatSearchContext)
  if (!ctx) throw new Error('useChatSearch must be used inside ChatSearchProvider')
  return ctx
}
