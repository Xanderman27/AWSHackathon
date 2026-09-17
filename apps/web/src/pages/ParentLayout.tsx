import { NavLink, Outlet } from 'react-router-dom'
import { getSession } from '../api'
import MessagesWidget from '../components/MessagesWidget'
import RoleGate from './RoleGate'

export default function ParentLayout() {
  const session = getSession()
  if (!session || session.role !== 'parent') return <RoleGate need="parent" />
  return (
    <div className="page">
      <div className="row between">
        <div>
          <span className="chip cream">Family view</span>
          <h1 style={{ margin: '10px 0 0' }}>Home for families</h1>
        </div>
        <nav className="tabs" aria-label="Family sections">
          <NavLink to="/parent" end>📈 My child's progress</NavLink>
          <NavLink to="/parent/updates">✉️ Updates from school</NavLink>
          <NavLink to="/parent/resources">📚 Resources</NavLink>
        </nav>
      </div>
      <Outlet />
      <MessagesWidget />
    </div>
  )
}
