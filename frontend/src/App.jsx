import { useState } from 'react'
import Dashboard from './pages/Dashboard'
import Detect from './pages/Detect'
import History from './pages/History'

const NAV = [
  { id: 'dashboard', label: 'Обзор', icon: '🌿' },
  { id: 'detect', label: 'Детекция', icon: '🔍' },
  { id: 'history', label: 'История', icon: '🗂️' },
]

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const handleDetectionSuccess = () => setRefreshTrigger((prev) => prev + 1)

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-gradient-to-b from-sky-50 via-forest-50 to-forest-100">
      {/* Animated nature background blobs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-32 -left-24 h-96 w-96 rounded-full bg-forest-300/40 blur-3xl animate-blob" />
        <div className="absolute top-1/3 -right-32 h-[28rem] w-[28rem] rounded-full bg-sky-300/40 blur-3xl animate-blob [animation-delay:6s]" />
        <div className="absolute bottom-0 left-1/4 h-80 w-80 rounded-full bg-lime-300/30 blur-3xl animate-blob [animation-delay:3s]" />
      </div>

      {/* Header / Nav */}
      <header className="sticky top-0 z-30">
        <div className="glass-strong border-b border-white/40">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4">
            <button
              onClick={() => setCurrentPage('dashboard')}
              className="flex items-center gap-3 group"
            >
              <span className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-forest-500 to-forest-700 text-2xl shadow-glow transition-transform group-hover:scale-105">
                🐦
              </span>
              <div className="text-left leading-tight">
                <p className="font-display text-xl font-extrabold tracking-tight text-forest-800">
                  SparrowVision
                </p>
                <p className="text-xs font-medium text-forest-600/70">
                  AI-детектор воробьёв
                </p>
              </div>
            </button>

            <nav className="flex items-center gap-1 rounded-2xl bg-forest-900/5 p-1.5">
              {NAV.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setCurrentPage(item.id)}
                  className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-all ${
                    currentPage === item.id
                      ? 'bg-white text-forest-700 shadow-soft'
                      : 'text-forest-700/60 hover:text-forest-700 hover:bg-white/50'
                  }`}
                >
                  <span className="text-base">{item.icon}</span>
                  <span className="hidden sm:inline">{item.label}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="relative z-10 mx-auto max-w-7xl px-5 py-10">
        <div key={currentPage} className="animate-fade-up">
          {currentPage === 'dashboard' && <Dashboard refreshTrigger={refreshTrigger} onNavigate={setCurrentPage} />}
          {currentPage === 'detect' && <Detect onSuccess={handleDetectionSuccess} />}
          {currentPage === 'history' && <History refreshTrigger={refreshTrigger} />}
        </div>
      </main>

      <footer className="relative z-10 pb-8 pt-4 text-center text-sm text-forest-700/50">
        🌳 SparrowVision · детекция на YOLO11x
      </footer>
    </div>
  )
}

export default App
