import { NavLink, Outlet } from 'react-router-dom'
import { getSession } from '../api'
import MessagesWidget from '../components/MessagesWidget'
import RoleGate from './RoleGate'

export default function TeacherLayout() {
  const session = getSession()
  if (!session || session.role !== 'teacher') return <RoleGate need="teacher" />
  return (
    <div className="page">
      <div className="row between">
        <div>
          <span className="chip sky">Class 4A</span>
          <h1 style={{ margin: '10px 0 0' }}>Your classroom</h1>
        </div>
        <nav className="tabs" aria-label="Teacher sections">
          <NavLink to="/teacher" end>🧑‍🎓 Learners</NavLink>
          <NavLink to="/teacher/activities">🎯 Activities</NavLink>
          <NavLink to="/teacher/updates">✉️ Family updates</NavLink>
          <NavLink to="/teacher/stats">📊 Class statistics</NavLink>
        </nav>
      </div>
      <Outlet />
      <MessagesWidget />
    </div>
  )
}
