import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

// Games are free play: no score sent to the teacher, no time limit, playable any time.

const GAMES = [
  { id: 'memory-meadow', name: 'Memory Meadow', glyph: '🌼', tone: 'sky', blurb: 'Flip the cards and remember where things are hiding.', skill: 'Working memory' },
  { id: 'sort-it-out', name: 'Sort It Out', glyph: '🧺', tone: 'cream', blurb: 'Put things into groups and say why they belong together.', skill: 'Sorting' },
  { id: 'shape-shift', name: 'Shape Shift', glyph: '🔷', tone: 'rose', blurb: 'Turn and flip shapes to see how they fit.', skill: 'Space and shape' },
]

interface GroupActivity {
  id: string
  game_id: string
  title: string
  group_name: string
  teammates: { id: string; display_name: string }[]
  member_count: number
  instructions: string
}

export default function StudentGames() {
  const [activities, setActivities] = useState<GroupActivity[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api<GroupActivity[]>('/student/group-activities').then(setActivities).catch(() => setError('Group activities could not load.'))
  }, [])

  return (
    <div className="stack">
      <div>
        <h2 className="section-title">Group activities</h2>
        <p className="muted helper">Activities your teacher picked for you and your teammates.</p>
      </div>
      {error && <div className="feedback try" role="alert">{error}</div>}
      {activities === null && !error && <div className="card"><p style={{ margin: 0 }}>Finding your activities…</p></div>}
      {activities?.length === 0 && (
        <div className="card group-empty">
          <span aria-hidden="true">🎒</span>
          <div><h3>No group activities right now</h3><p className="muted">Your teacher will add one here when it is ready.</p></div>
        </div>
      )}
      {activities && activities.length > 0 && (
        <div className="group-activity-grid">
          {activities.map((activity) => (
            <article className="card group-activity-card tinted-mint pop" key={activity.id}>
              <div className="group-activity-art" aria-hidden="true">🎵</div>
              <div>
                <span className="chip mint">Ready to join</span>
                <h3>{activity.title}</h3>
                <p>{activity.instructions}</p>
              </div>
              <div className="assigned-team">
                <strong>{activity.group_name}</strong>
                <span>With {activity.teammates.map((teammate) => teammate.display_name).join(' and ')}</span>
              </div>
              <Link className="btn btn-primary btn-lg group-join" to={`/student/games/beat-together/${activity.id}`}>
                Join activity <span aria-hidden="true">→</span>
              </Link>
            </article>
          ))}
        </div>
      )}

      <div style={{ marginTop: 12 }}>
        <h2 className="section-title">Play on your own</h2>
        <p className="muted helper">Just for fun and thinking practice. Nothing here is graded.</p>
      </div>
      <div className="game-grid">
        {GAMES.map((g, i) => (
          <div key={g.id} className={`game-card pop ${g.tone}`} style={{ animationDelay: `${i * 80}ms` }}>
            <span className="game-glyph floaty" aria-hidden="true" style={{ animationDelay: `${i * 0.25}s` }}>{g.glyph}</span>
            <strong>{g.name}</strong>
            <span className="game-blurb">{g.blurb}</span>
            <span className="row between" style={{ width: '100%', marginTop: 'auto' }}>
              <span className="chip">{g.skill}</span>
              <button type="button" disabled>Coming soon</button>
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
