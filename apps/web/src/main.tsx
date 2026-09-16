import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Link, Route, Routes, useNavigate } from 'react-router-dom'
import { PrefsProvider } from './a11y'
import { getSession, setSession } from './api'
import Home from './pages/Home'
import StudentLayout from './pages/StudentLayout'
import StudentAssessments from './pages/StudentAssessments'
import StudentPath from './pages/StudentPath'
import StudentGames from './pages/StudentGames'
import BeatBuilder from './pages/BeatBuilder'
import StudentQuest from './pages/StudentQuest'
import TeacherDashboard from './pages/TeacherDashboard'
import ParentLayout from './pages/ParentLayout'
import ParentProgress from './pages/ParentProgress'
import { ResourceList } from './pages/Resources'
import './styles.css'

function Shell() {
  const nav = useNavigate()
  const session = getSession()
  return (
    <div className="shell">
      <a href="#main" className="visually-hidden">Skip to main content</a>
      <header className="topbar">
        <Link to="/" className="brand"><span className="dot" aria-hidden="true" />Dori</Link>
        {session && (
          <div className="row" style={{ gap: 10 }}>
            <span className="muted" style={{ fontWeight: 600, fontSize: '.92em' }}>{session.name ?? session.userId}</span>
            <button type="button" className="logout" onClick={() => { setSession(null); nav('/') }}>Log out</button>
          </div>
        )}
      </header>
      <main id="main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/student" element={<StudentLayout />}>
            <Route index element={<StudentPath />} />
            <Route path="quests" element={<StudentAssessments />} />
            <Route path="games" element={<StudentGames />} />
            <Route path="games/beat-together/:activityId" element={<BeatBuilder />} />
          </Route>
          <Route path="/student/quest/:skillId" element={<StudentQuest />} />
          <Route path="/teacher" element={<TeacherDashboard />} />
          <Route path="/parent" element={<ParentLayout />}>
            <Route index element={<ParentProgress />} />
            <Route path="resources" element={<ResourceList />} />
          </Route>
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
