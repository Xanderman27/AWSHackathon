import { useNavigate } from 'react-router-dom'
import { setSession, type Role } from '../api'

const ROLES: { role: Role; userId: string; label: string; blurb: string; emoji: string; tone: string }[] = [
  { role: 'student', userId: 'student-01', label: 'I am a student', blurb: 'Start a quest. Sam, Grade 4.', emoji: '🧒', tone: 'mint' },
  { role: 'teacher', userId: 'teacher-01', label: 'I am a teacher', blurb: 'See the class and each learner.', emoji: '🧑‍🏫', tone: 'sky' },
  { role: 'parent', userId: 'parent-01', label: 'I am a parent', blurb: "See your child's progress.", emoji: '👪', tone: 'cream' },
]

export default function Home() {
  const nav = useNavigate()
  return (
    <div className="page center">
      <section className="hero">
        <div>
          <h1>Learning that <span className="underline">listens</span> to every kid.</h1>
          <p className="muted" style={{ fontSize: '1.15em', maxWidth: 520 }}>
            Short, friendly check-ins for students. Clear next steps for teachers. Plain-language progress for families.
          </p>
          <div className="role-list" role="group" aria-label="Choose who you are">
            {ROLES.map((r) => (
              <button key={r.role} type="button" className="role" onClick={() => { setSession({ role: r.role, userId: r.userId }); nav(`/${r.role}`) }}>
                <span className={`ico ${r.tone}`} aria-hidden="true">{r.emoji}</span>
                <span><strong>{r.label}</strong><span className="sub">{r.blurb}</span></span>
              </button>
            ))}
          </div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="tile tall" style={{ background: 'var(--brand)' }}>🦉</div>
          <div className="tile" style={{ background: 'var(--mint)' }}>🔢</div>
          <div className="tile" style={{ background: 'var(--cream)' }}>📖</div>
        </div>
      </section>
    </div>
  )
}
