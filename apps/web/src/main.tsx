import { StrictMode, useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Link, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { PrefsProvider, QuestTools } from './a11y'
import { api, getSession, setSession } from './api'
import { DoriLogo } from './components/Logo'
import Home from './pages/Home'
import StudentLayout from './pages/StudentLayout'
import StudentAssessments from './pages/StudentAssessments'
import StudentPath from './pages/StudentPath'
import StudentGames from './pages/StudentGames'
import GameRoute from './pages/games'
import StudentQuest from './pages/StudentQuest'
import TeacherLayout from './pages/TeacherLayout'
import TeacherDashboard from './pages/TeacherDashboard'
import TeacherLearner from './pages/TeacherLearner'
import TeacherActivities from './pages/TeacherActivities'
import TeacherUpdates from './pages/TeacherUpdates'
import TeacherStats from './pages/TeacherStats'
import ParentLayout from './pages/ParentLayout'
import ParentProgress from './pages/ParentProgress'
import { ResourceList } from './pages/Resources'
import './styles.css'

function Shell() {
  const nav = useNavigate()
  const location = useLocation()
  const session = getSession()
  const confirmRef = useRef<HTMLDialogElement>(null)
  const [stars, setStars] = useState<number | null>(null)

  // The star count lives beside the student's name and refreshes as they move around,
  // so finishing a quiz shows up without a reload.
  useEffect(() => {
    if (session?.role === 'student') {
      api<{ stars: number }>('/student/path').then((d) => setStars(d.stars)).catch(() => {})
    } else {
      setStars(null)
    }
  }, [session?.userId, session?.role, location.pathname])

  return (
    <div className="shell">
      <a href="#main" className="visually-hidden">Skip to main content</a>
      <header className="topbar">
        <Link to="/" className="brand"><DoriLogo size={34} />Dori</Link>
        {session && (
          <div className="row" style={{ gap: 10 }}>
            {session.role === 'student' && <span className="topbar-tools"><QuestTools /></span>}
            {session.role === 'student' && stars !== null && (
              <span className="stars-chip stars-mini" aria-label={`${stars} stars earned`}>⭐ {stars}</span>
            )}
            {session.role !== 'student' && (
              <span className="muted" style={{ fontWeight: 600, fontSize: '.92em' }}>{session.name ?? session.userId}</span>
            )}
            <button type="button" className="logout" onClick={() => confirmRef.current?.showModal()}>Log out</button>
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
            <Route path="games/:gameId/:activityId" element={<GameRoute />} />
          </Route>
          <Route path="/student/quest/:skillId" element={<StudentQuest />} />
          <Route path="/teacher" element={<TeacherLayout />}>
            <Route index element={<TeacherDashboard />} />
            <Route path="learners/:studentId" element={<TeacherLearner />} />
            <Route path="activities" element={<TeacherActivities />} />
            <Route path="updates" element={<TeacherUpdates />} />
            <Route path="stats" element={<TeacherStats />} />
            <Route path="resources" element={<ResourceList />} />
          </Route>
          <Route path="/parent" element={<ParentLayout />}>
            <Route index element={<ParentProgress />} />
            <Route path="resources" element={<ResourceList />} />
          </Route>
        </Routes>
      </main>
      <dialog ref={confirmRef} className="confirm-dialog" aria-labelledby="logout-q">
        <h2 id="logout-q" style={{ fontSize: '1.15em' }}>Are you sure you want to log out?</h2>
        <div className="row" style={{ justifyContent: 'center', marginTop: 14 }}>
          <button type="button" onClick={() => confirmRef.current?.close()}>Stay logged in</button>
          <button type="button" className="btn-primary"
            onClick={() => { confirmRef.current?.close(); setSession(null); nav('/') }}>Log out</button>
        </div>
      </dialog>
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
