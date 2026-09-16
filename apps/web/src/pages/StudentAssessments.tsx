import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type Skill } from '../api'

const ART: Record<string, { glyph: string; tone: string }> = {
  math: { glyph: '🔢', tone: 'mint' },
  reading: { glyph: '📖', tone: 'sky' },
}

export default function StudentAssessments() {
  const nav = useNavigate()
  const [skills, setSkills] = useState<Skill[]>([])
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { api<Skill[]>('/skills').then(setSkills).catch((e) => setErr(String(e))) }, [])

  if (err) return <p role="alert">Something went wrong. {err}</p>

  return (
    <div className="stack">
      <h2 className="section-title">Pick a quest</h2>
      <div className="quest-pick">
        {skills.filter((s) => s.id !== 'fraction_parts').map((s, i) => {
          const art = ART[s.subject] ?? { glyph: '⭐', tone: 'cream' }
          return (
            <button key={s.id} type="button" className={`quest-card pop ${art.tone}`}
              style={{ animationDelay: `${i * 90}ms` }}
              onClick={() => nav(`/student/quest/${s.id}`)}>
              <span className="art floaty" aria-hidden="true" style={{ animationDelay: `${i * 0.3}s` }}>{art.glyph}</span>
              <strong>{cap(s.child_name)}</strong>
              <span className="quest-meta">6 questions · about 5 minutes</span>
              <span className="quest-go" aria-hidden="true">Let's go →</span>
            </button>
          )
        })}
      </div>
      <p className="muted helper">Take your time. You can ask Dori for a hint on any question.</p>
    </div>
  )
}

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
