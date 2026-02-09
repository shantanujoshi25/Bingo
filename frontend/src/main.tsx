import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// In dev mode, mock Alien launch params so useAlien() returns a dev token
if (import.meta.env.DEV) {
  import('@alien_org/bridge').then(({ mockLaunchParamsForDev }) => {
    mockLaunchParamsForDev({
      authToken: 'dev_token',
    })
  })
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
