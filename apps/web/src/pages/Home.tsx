import { useNavigate } from 'react-router-dom'
import { setSession, type Role } from '../api'

const ROLES: { role: Role; userId: string; label: string; blurb: string; emoji: string }[] = [
  { role: 'student', userId: 'student-01', label: 'I am a student', blurb: 'Start a quest. Sam, Grade 4.', emoji: '🧒' },
  { role: 'teacher', userId: 'teacher-01', label: 'I am a teacher', blurb: 'See the class and each learner.', emoji: '🧑‍🏫' },
  { role: 'parent', userId: 'parent-01', label: 'I am a parent', blurb: "See your child's progress.", emoji: '👪' },
]

export default function Home() {
  const nav = useNavigate()
  return (
    <div className="stack">
      <div className="card">
        <h1>Welcome</h1>
        <p className="muted">Synthetic demo accounts. Pick who you are.</p>
        <div className="stack">
          {ROLES.map((r) => (
            <button key={r.role} type="button" className="choice" onClick={() => { setSession({ role: r.role, userId: r.userId }); nav(`/${r.role}`) }}>
              <span aria-hidden="true">{r.emoji} </span>{r.label}
              <span className="muted"> — {r.blurb}</span>
            </button>
          ))}
        </div>
      </div>
      <p className="muted">This tool supports learning. It does not make eligibility, placement, or IEP decisions.</p>
    </div>
  )
}
