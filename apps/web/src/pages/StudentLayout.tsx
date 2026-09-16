import { NavLink, Outlet } from 'react-router-dom'
import { getSession } from '../api'
import Capy from '../components/Capy'
import RoleGate from './RoleGate'

export default function StudentLayout() {
  const session = getSession()
  if (!session || session.role !== 'student') return <RoleGate need="student" />
  return (
    <div className="page student-theme">
      <div className="student-head">
        <Capy size={90} mood="happy" float />
        <div>
          <h1 style={{ marginBottom: 2 }}>Hi Sam!</h1>
          <p className="muted" style={{ margin: 0 }}>What would you like to do today?</p>
        </div>
        <nav className="tabs big" aria-label="Student sections">
          <NavLink to="/student" end>🗺️ My path</NavLink>
          <NavLink to="/student/quests">🌟 Quests</NavLink>
          <NavLink to="/student/games">🎲 Games</NavLink>
        </nav>
      </div>
      <Outlet />
    </div>
  )
}
