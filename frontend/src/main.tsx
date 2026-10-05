import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './auth'
import { ChatSearchProvider } from './chatSearch'
import { PageContextProvider } from './pageContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ChatSearchProvider>
          <PageContextProvider>
            <App />
          </PageContextProvider>
        </ChatSearchProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
