import { NavLink, Outlet } from 'react-router-dom'
import { getSession } from '../api'
import Bear from '../components/Bear'
import RoleGate from './RoleGate'

export default function StudentLayout() {
  const session = getSession()
  if (!session || session.role !== 'student') return <RoleGate need="student" />
  return (
    <div className="page">
      <div className="student-head">
        <Bear size={84} mood="wave" float />
        <div>
          <h1 style={{ marginBottom: 2 }}>Hi Sam!</h1>
          <p className="muted" style={{ margin: 0 }}>What would you like to do today?</p>
        </div>
        <nav className="tabs big" aria-label="Student sections">
          <NavLink to="/student" end>🌟 Quests</NavLink>
          <NavLink to="/student/games">🎲 Games</NavLink>
        </nav>
      </div>
      <Outlet />
    </div>
  )
}
