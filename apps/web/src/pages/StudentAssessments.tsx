// Quizzes tab: only what the teacher has assigned (PRD FR-02). Free practice lives on My path.

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

interface Assigned { assignment_id: string; skill_id: string; title: string; subject: string; at: string }

const ART: Record<string, { glyph: string; tone: string }> = {
  math: { glyph: '🔢', tone: 'mint' },
  english: { glyph: '📖', tone: 'sky' },
  science: { glyph: '🧪', tone: 'mint' },
  history: { glyph: '🏴‍☠️', tone: 'cream' },
  geography: { glyph: '🗺️', tone: 'sky' },
}

export default function StudentAssessments() {
  const nav = useNavigate()
  const [quests, setQuests] = useState<Assigned[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { api<Assigned[]>('/student/assignments').then(setQuests).catch((e) => setErr(String(e))) }, [])

  if (err) return <p role="alert">Something went wrong. {err}</p>
  if (quests === null) return <p>Finding your quizzes…</p>

  return (
    <div className="stack">
      <h2 className="section-title">Quizzes from your teacher</h2>
      {quests.length === 0 ? (
        <div className="card celebrate" style={{ padding: 32 }}>
          <div className="big" aria-hidden="true">🌟</div>
          <h2>No quizzes right now</h2>
          <p className="muted" style={{ margin: 0 }}>Your teacher will send one when it is ready. You can practice on your path any time!</p>
        </div>
      ) : (
        <div className="quest-pick">
          {quests.map((q, i) => {
            const art = ART[q.subject] ?? { glyph: '⭐', tone: 'cream' }
            return (
              <button key={q.assignment_id} type="button" className={`quest-card pop ${art.tone}`}
                style={{ animationDelay: `${i * 90}ms` }}
                onClick={() => nav(`/student/quest/${q.skill_id}`)}>
                <span className="art floaty" aria-hidden="true" style={{ animationDelay: `${i * 0.3}s` }}>{art.glyph}</span>
                <strong>{cap(q.title)}</strong>
                <span className="quest-meta">6 questions · about 5 minutes</span>
                <span className="quest-go" aria-hidden="true">Let's go →</span>
              </button>
            )
          })}
        </div>
      )}
      <p className="muted helper">Take your time. You can ask Capy for a hint on any question.</p>
    </div>
  )
}

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
