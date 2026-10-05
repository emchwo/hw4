export interface Product {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_file_path: string
  image_url: string
  price: number
  total_stock: number
}

export interface SizeStock {
  size: string
  quantity: number
}

export interface ProductDetail extends Product {
  inventory: SizeStock[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatProductCard {
  id: string
  name: string
  price: number
  currency: string
  image_url: string
  description: string
  in_stock: boolean
  product_url: string
}

export interface ProductMatch {
  id: string
  name: string
  price: number
  currency: string
  image_url: string
  short_description: string
  in_stock: boolean
  product_url: string
}

export type ChatReplyType =
  | 'text'
  | 'price'
  | 'stock'
  | 'product_search'
  | 'product_recommendation'
  | 'clarifying_question'

export interface PriceInfo {
  id: string
  name: string
  price: number
  currency: string
  product_url: string
}

export type StockStatus = 'in_stock' | 'low_stock' | 'out_of_stock'

export interface StockInfo {
  id: string
  name: string
  product_url: string
  requested_size: string | null
  requested_size_quantity: number | null
  requested_size_status: StockStatus | null
  sizes: { size: string; quantity: number; status: StockStatus }[]
  total_in_stock: number
  status: StockStatus
  summary: string
}

export interface ChatResponse {
  type: ChatReplyType
  reply: string
  price: PriceInfo | null
  stock: StockInfo | null
  products: ChatProductCard[]
  options: string[]
  search_label: string | null
  matches: ProductMatch[]
  total_matches: number
}

export interface User {
  id: number
  name: string
  first_name: string | null
  last_name: string | null
  email: string
}

export interface RegisterData {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    ...init,
  })
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') message = body.detail
    } catch {
      // Non-JSON error body; keep the status text.
    }
    throw new ApiError(res.status, message)
  }
  return res.json() as Promise<T>
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })

export const getCurrentUser = () => request<User>('/api/auth/me')

export const login = (email: string, password: string) => post<User>('/api/auth/login', { email, password })

export const register = (data: RegisterData) => post<User>('/api/auth/register', data)

export const logout = () => post<{ ok: boolean }>('/api/auth/logout')

export const getProducts = () => request<Product[]>('/api/products')

export const getProduct = (id: string) =>
  request<ProductDetail>(`/api/products/${encodeURIComponent(id)}`)

export interface PageContext {
  path: string
  product_id?: string | null
  selected_size?: string | null
  category?: string | null
  search_label?: string | null
  visible_product_ids?: string[]
}

export interface HistoryMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
  reply: ChatResponse | null
}

export const sendChat = (message: string, history: ChatMessage[], page: PageContext) =>
  post<ChatResponse>('/api/chat', { message, history, page })

export const getChatHistory = () => request<{ messages: HistoryMessage[] }>('/api/chat/history')

export const clearChatHistory = () => request<{ deleted: number }>('/api/chat/history', { method: 'DELETE' })

export const formatPrice = (price: number) =>
  price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
