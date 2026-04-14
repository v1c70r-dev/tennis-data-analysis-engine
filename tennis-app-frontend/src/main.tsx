import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { TennisApp } from './TennisApp'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <TennisApp/>
  </StrictMode>,
)

