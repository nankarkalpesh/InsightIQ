import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ThemeProvider } from './context/ThemeProvider'
import { DatasetProvider } from './store/datasetStore'
import { DashboardProvider } from './store/dashboardStore'
import { AuthProvider } from './store/authStore'
import { LLMProviderStore } from './store/llmStore'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <AuthProvider>
        <DatasetProvider>
          <DashboardProvider>
            <LLMProviderStore>
              <App />
            </LLMProviderStore>
          </DashboardProvider>
        </DatasetProvider>
      </AuthProvider>
    </ThemeProvider>
  </StrictMode>,
)
