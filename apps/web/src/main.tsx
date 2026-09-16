import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { PrefsProvider } from './a11y'
import Home from './pages/Home'
import StudentLayout from './pages/StudentLayout'
import StudentAssessments from './pages/StudentAssessments'
import StudentGames from './pages/StudentGames'
import StudentQuest from './pages/StudentQuest'
import TeacherDashboard from './pages/TeacherDashboard'
import ParentLayout from './pages/ParentLayout'
import ParentProgress from './pages/ParentProgress'
import { ResourceList } from './pages/Resources'
import './styles.css'

function Shell() {
  return (
    <div className="shell">
      <a href="#main" className="visually-hidden">Skip to main content</a>
      <header className="topbar">
        <Link to="/" className="brand"><span className="dot" aria-hidden="true" />Dori</Link>
      </header>
      <main id="main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/student" element={<StudentLayout />}>
            <Route index element={<StudentAssessments />} />
            <Route path="games" element={<StudentGames />} />
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
