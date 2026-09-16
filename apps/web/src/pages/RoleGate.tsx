import { Link } from 'react-router-dom'

const LABEL: Record<string, string> = { student: 'a student', teacher: 'a teacher', parent: 'a parent' }

/** Shown when the signed-in demo role does not match the page. Keeps the page from ending in dead space. */
export default function RoleGate({ need }: { need: 'student' | 'teacher' | 'parent' }) {
  return (
    <div className="page center">
      <div className="card celebrate" style={{ maxWidth: 520, margin: '0 auto' }}>
        <div className="big" aria-hidden="true">🔑</div>
        <h1>Switch role to continue</h1>
        <p className="muted">This page is for {LABEL[need]}. Pick that role on the home page to see it.</p>
        <Link to="/" className="btn btn-primary btn-lg" style={{ textDecoration: 'none' }}>Go to the home page</Link>
      </div>
    </div>
  )
}
