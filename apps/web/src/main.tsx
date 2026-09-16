import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { AccessibilityBar, PrefsProvider } from './a11y'
import Home from './pages/Home'
import StudentQuest from './pages/StudentQuest'
import TeacherDashboard from './pages/TeacherDashboard'
import ParentView from './pages/ParentView'
import './styles.css'

function Shell() {
  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand"><span className="dot" aria-hidden="true" />Learning Quest</Link>
        <AccessibilityBar />
      </header>
      <main id="main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/student" element={<StudentQuest />} />
          <Route path="/teacher" element={<TeacherDashboard />} />
          <Route path="/parent" element={<ParentView />} />
        </Routes>
      </main>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <PrefsProvider>
      <BrowserRouter>
        <Shell />
      </BrowserRouter>
    </PrefsProvider>
  </StrictMode>,
)
