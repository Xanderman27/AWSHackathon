import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import Avatar from '../components/Avatar'
import type { GameSpec, GroupActivity } from '../games/room'

// Games are free play: no score is sent to the teacher, there is no timer, and a learner can
// stop whenever they like. The only thing a teacher controls is who is grouped with whom.

export default function StudentGames() {
  const [activities, setActivities] = useState<GroupActivity[] | null>(null)
  const [catalog, setCatalog] = useState<GameSpec[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api<GroupActivity[]>('/student/group-activities'),
      api<GameSpec[]>('/games'),
    ])
      .then(([assigned, games]) => { setActivities(assigned); setCatalog(games) })
      .catch(() => setError('Your activities could not load. Try again in a moment.'))
  }, [])

  // A game the teacher already assigned as a team activity stays out of the solo list,
  // so the same game never shows up in both sections.
  const teamGameIds = new Set((activities ?? []).map((activity) => activity.game_id))
  const solo = catalog.filter((game) => game.solo && !teamGameIds.has(game.id))

  return (
    <div className="stack">
      <div>
        <h2 className="section-title">Play together</h2>
        <p className="muted helper">
          Your teacher put you in a team. Everyone uses their own screen, and you all work on the
          same thing at the same time.
        </p>
      </div>
      {error && <div className="feedback try" role="alert">{error}</div>}
      {activities === null && !error && <div className="card"><p style={{ margin: 0 }}>Finding your activities…</p></div>}
      {activities?.length === 0 && (
        <div className="card group-empty">
          <span aria-hidden="true">🎒</span>
          <div><h3>No team activities right now</h3><p className="muted">Your teacher will put you in a team here when one is ready.</p></div>
        </div>
      )}
      {activities && activities.length > 0 && (
        <div className="group-activity-grid">
          {activities.map((activity) => (
            <article className={`card group-activity-card tinted-${activity.tone} pop`} key={activity.id}>
              <div className="group-activity-art" aria-hidden="true">{activity.glyph}</div>
              <div>
                <span className="chip team-chip">Team activity</span>
                <h3>{activity.title}</h3>
                <p>{activity.instructions}</p>
              </div>

              <div className="assigned-team">
                <strong>{activity.group_name}</strong>
                {/* Faces first: the point of the card is that other children are waiting. */}
                <ul className="team-strip">
                  {activity.members.map((member) => (
                    <li key={member.id} className={member.is_you ? 'you' : ''}>
                      <Avatar photo={member.photo} spec={member.avatar} size={46}
                        name={member.is_you ? `${member.display_name}, you` : member.display_name} />
                      <span>{member.is_you ? 'You' : member.display_name}</span>
                    </li>
                  ))}
                </ul>
                <span className="team-line">
                  You and {activity.teammates.length} classmate{activity.teammates.length === 1 ? '' : 's'}
                </span>
              </div>

              <Link className="btn btn-primary btn-lg group-join" to={`/student/games/${activity.game_id}/${activity.id}`}>
                Join your team <span aria-hidden="true">→</span>
              </Link>
            </article>
          ))}
        </div>
      )}

      {solo.length > 0 && (
        <>
          <div style={{ marginTop: 12 }}>
            <h2 className="section-title">Play on your own</h2>
            <p className="muted helper">Just for fun and thinking practice. Nothing here is graded.</p>
          </div>
          <div className="game-grid">
            {solo.map((game, index) => (
              <div key={game.id} className={`game-card pop ${game.tone}`} style={{ animationDelay: `${index * 80}ms` }}>
                <span className="game-glyph floaty" aria-hidden="true" style={{ animationDelay: `${index * 0.25}s` }}>{game.glyph}</span>
                <strong>{game.title}</strong>
                <span className="game-blurb">{game.blurb}</span>
                <span className="row between" style={{ width: '100%', marginTop: 'auto' }}>
                  <span className="chip">{game.skill_hint}</span>
                  <Link className="btn" to={`/student/games/${game.id}/solo`}>Play</Link>
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
