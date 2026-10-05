import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { useChatSearch } from '../chatSearch'
import { useCurrentPage } from '../pageContext'
import RichText from './RichText'
import {
  clearChatHistory,
  formatPrice,
  getChatHistory,
  sendChat,
  type ChatMessage,
  type ChatProductCard,
  type ChatReplyType,
  type ChatResponse,
  type HistoryMessage,
  type PriceInfo,
  type ProductMatch,
  type StockInfo,
} from '../api'

interface DisplayMessage extends ChatMessage {
  type?: ChatReplyType
  products?: ChatProductCard[]
  options?: string[]
  error?: boolean
  createdAt?: Date
  price?: PriceInfo | null
  stock?: StockInfo | null
  greeting?: boolean
  // Set on product_search replies so the results can be shown on the page again.
  search?: { label: string; matches: ProductMatch[]; total: number }
}

const guestGreeting = (): DisplayMessage => ({
  role: 'assistant',
  greeting: true,
  content: "Hi there! I'm the Campus Customs assistant. Ask me about sizes, stock, or finding the right piece.",
})

const memberGreeting = (firstName: string, returning: boolean): DisplayMessage => ({
  role: 'assistant',
  greeting: true,
  content: returning
    ? `Welcome back, ${firstName}! Your earlier chats are above. What can I help you find today?`
    : `Hi ${firstName}! I'm the Campus Customs assistant. Ask me about sizes, stock, or finding the right piece.`,
})

// SQLite stores UTC timestamps like "2026-09-19 11:40:23".
const parseDbDate = (s: string) => new Date(s.replace(' ', 'T') + 'Z')

function dayLabel(d: Date) {
  const today = new Date()
  const yesterday = new Date()
  yesterday.setDate(today.getDate() - 1)
  if (d.toDateString() === today.toDateString()) return 'Today'
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday'
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function fromReply(res: ChatResponse, createdAt?: Date): DisplayMessage {
  return {
    role: 'assistant',
    content: res.reply,
    type: res.type,
    products: res.products,
    options: res.options,
    price: res.price,
    stock: res.stock,
    createdAt,
    search:
      res.type === 'product_search'
        ? { label: res.search_label ?? 'Search results', matches: res.matches, total: res.total_matches }
        : undefined,
  }
}

function fromHistory(m: HistoryMessage): DisplayMessage {
  const createdAt = parseDbDate(m.created_at)
  if (m.role === 'assistant' && m.reply) return fromReply(m.reply, createdAt)
  return { role: m.role, content: m.content, createdAt }
}

const GENERAL_STARTERS = ['Do you have any hoodies?', 'Gift ideas under $60', 'What’s in stock in size M?', 'Show me quarter-zips']
const PRODUCT_STARTERS = ['How much is this?', 'Which sizes are in stock?', 'Do you have this in another color?', 'Show me similar items']

const STATUS_LABEL = { in_stock: 'in stock', low_stock: 'low stock', out_of_stock: 'out of stock' } as const

function StockGrid({ stock }: { stock: StockInfo }) {
  return (
    <Link to={stock.product_url} className="chat-stock">
      <strong>{stock.name}</strong>
      <div className="chat-stock-grid">
        {stock.sizes.map((s) => (
          <div
            key={s.size}
            className={`chat-stock-cell ${s.status} ${s.size === stock.requested_size ? 'requested' : ''}`}
            title={`${s.size}: ${s.quantity} available`}
          >
            <span className="chat-stock-size">{s.size}</span>
            <span className="chat-stock-qty">{s.quantity === 0 ? 'Out' : s.quantity}</span>
          </div>
        ))}
      </div>
      <span className="chat-stock-legend">
        {stock.requested_size && stock.requested_size_status
          ? `Size ${stock.requested_size}: ${STATUS_LABEL[stock.requested_size_status]} · `
          : ''}
        {stock.total_in_stock} in stock total
      </span>
    </Link>
  )
}

function PriceCard({ price }: { price: PriceInfo }) {
  return (
    <Link to={price.product_url} className="chat-price">
      <span>{price.name}</span>
      <strong>{formatPrice(price.price)}</strong>
    </Link>
  )
}

function ChatProduct({ product }: { product: ChatProductCard }) {
  return (
    <Link to={product.product_url} className="chat-product">
      <img src={product.image_url} alt="" />
      <div className="chat-product-info">
        <strong>{product.name}</strong>
        <span className="chat-product-price">{formatPrice(product.price)}</span>
        <span className={`chat-product-stock ${product.in_stock ? '' : 'out'}`}>
          {product.in_stock ? 'In stock' : 'Sold out'}
        </span>
      </div>
    </Link>
  )
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<DisplayMessage[]>([guestGreeting()])
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const { user, loading: authLoading, openModal } = useAuth()
  const { showResults, openChatRequest } = useChatSearch()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const page = useCurrentPage()

  // Load saved history when a shopper logs in (or returns already logged in); reset for guests.
  useEffect(() => {
    if (authLoading) return
    if (!user) {
      setMessages([guestGreeting()])
      return
    }
    let cancelled = false
    const firstName = user.first_name ?? user.name
    getChatHistory()
      .then(({ messages: saved }) => {
        if (cancelled) return
        setMessages([...saved.map(fromHistory), memberGreeting(firstName, saved.length > 0)])
      })
      .catch(() => !cancelled && setMessages([memberGreeting(firstName, false)]))
    return () => {
      cancelled = true
    }
  }, [user, authLoading])

  // "Ask about this item" (or any page) can open the chat.
  useEffect(() => {
    if (openChatRequest > 0) setOpen(true)
  }, [openChatRequest])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking, open])

  function showOnPage(search: NonNullable<DisplayMessage['search']>, message: string) {
    showResults({ label: search.label, message, matches: search.matches, total: search.total })
    if (pathname !== '/products') navigate('/products')
  }

  async function send(text: string) {
    text = text.trim()
    if (!text || thinking) return

    // Guests send the conversation so far; logged-in history is loaded on the server.
    const history: ChatMessage[] = user
      ? []
      : messages.slice(1).filter((m) => !m.error).map(({ role, content }) => ({ role, content }))
    setMessages((m) => [...m, { role: 'user', content: text, createdAt: new Date() }])
    setInput('')
    setThinking(true)

    try {
      const res = await sendChat(text, history, page)
      const reply = fromReply(res, new Date())
      if (reply.search) showOnPage(reply.search, res.reply)
      setMessages((m) => [...m, reply])
    } catch (err) {
      const content =
        err instanceof Error && err.message && !/^\d{3} /.test(err.message)
          ? err.message
          : "Sorry, I couldn't reach the server. Please try again in a moment."
      setMessages((m) => [...m, { role: 'assistant', content, error: true }])
    } finally {
      setThinking(false)
    }
  }

  async function handleClear() {
    if (!user || !window.confirm('Delete your saved chat history? This can’t be undone.')) return
    try {
      await clearChatHistory()
      setMessages([memberGreeting(user.first_name ?? user.name, false)])
    } catch {
      setMessages((m) => [...m, { role: 'assistant', content: "Sorry, I couldn't clear your history.", error: true }])
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    send(input)
  }

  const last = messages[messages.length - 1]
  // One-tap starter questions while the latest message is a greeting; product-specific on a product page.
  const starters = last?.greeting && !thinking ? (page.product_id ? PRODUCT_STARTERS : GENERAL_STARTERS) : []

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" aria-label="Campus Customs chat">
          <header className="chat-header">
            <div className="chat-avatar" aria-hidden="true">CC</div>
            <div>
              <strong>Campus Customs</strong>
              <span className="chat-status">
                {user ? `Chatting as ${user.first_name ?? user.name} · history saved` : 'Shopping assistant'}
              </span>
            </div>
            {user && (
              <button className="chat-clear" onClick={handleClear} title="Delete saved chat history">
                Clear
              </button>
            )}
            <button className="chat-close" aria-label="Close chat" onClick={() => setOpen(false)}>
              ×
            </button>
          </header>

          <div className="chat-messages">
            {!user && !authLoading && (
              <div className="chat-guest-note">
                You're chatting as a guest.{' '}
                <button className="text-link" onClick={() => openModal('login')}>
                  Log in
                </button>{' '}
                to save your chat history.
              </div>
            )}

            {messages.map((m, i) => {
              const prev = messages.slice(0, i).reverse().find((p) => p.createdAt)
              const showDay = m.createdAt && (!prev?.createdAt || dayLabel(prev.createdAt) !== dayLabel(m.createdAt))
              return (
                <div key={i} className={`chat-row ${m.role}`}>
                  {showDay && <div className="chat-day">{dayLabel(m.createdAt!)}</div>}
                  <div className={`chat-bubble ${m.role} ${m.error ? 'error' : ''}`}>
                    {m.role === 'assistant' ? <RichText text={m.content} /> : m.content}
                  </div>
                  {m.price && <PriceCard price={m.price} />}
                  {m.stock && <StockGrid stock={m.stock} />}
                  {m.search && (
                    <button className="chat-page-note" onClick={() => showOnPage(m.search!, m.content)}>
                      ↖ {m.search.matches.length} {m.search.matches.length === 1 ? 'match' : 'matches'} · show on page
                    </button>
                  )}
                  {m.products && m.products.length > 0 && (
                    <div className="chat-products">
                      {m.products.map((p) => (
                        <ChatProduct key={p.id} product={p} />
                      ))}
                    </div>
                  )}
                  {m.options && m.options.length > 0 && m === last && !thinking && (
                    <div className="chat-options">
                      {m.options.map((o) => (
                        <button key={o} className="chat-option" onClick={() => send(o)}>
                          {o}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
            {starters.length > 0 && (
              <div className="chat-options chat-starters" aria-label="Suggested questions">
                {starters.map((q) => (
                  <button key={q} className="chat-option" onClick={() => send(q)}>
                    {q}
                  </button>
                ))}
              </div>
            )}
            {thinking && (
              <div className="chat-bubble assistant typing" aria-label="Assistant is typing">
                <span />
                <span />
                <span />
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form className="chat-input" onSubmit={handleSubmit}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about a product…"
              aria-label="Message"
              maxLength={2000}
              autoFocus
            />
            <button type="submit" disabled={!input.trim() || thinking}>
              Send
            </button>
          </form>
        </section>
      )}

      <button
        className={`chat-launcher ${open ? 'is-open' : ''}`}
        aria-label={open ? 'Close chat' : 'Open chat'}
        onClick={() => setOpen((o) => !o)}
      >
        {open ? '×' : (
          <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true">
            <path
              fill="currentColor"
              d="M12 3C6.5 3 2 6.9 2 11.7c0 2.6 1.3 4.9 3.4 6.5L4.6 22l4.2-2.3c1 .3 2.1.4 3.2.4 5.5 0 10-3.9 10-8.7S17.5 3 12 3Z"
            />
          </svg>
        )}
      </button>
    </div>
  )
}
