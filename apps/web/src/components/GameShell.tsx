// The frame every collaborative activity sits in: who is here, whether changes are live,
// and one way back out. Each game only has to draw its own board.

import { type CSSProperties, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { ActivityMeta, Connection, Participant } from '../games/room'

interface Props {
  meta: ActivityMeta | null
  participants: Participant[]
  connection: Connection
  error: string
  ready: boolean
  studentId: string
  tip?: string
  children: ReactNode
}

export default function GameShell({ meta, participants, connection, error, ready, studentId, tip, children }: Props) {
  if (!ready || !meta) {
    return (
      <div className="beat-page stack">
        <div className="row between">
          <div><span className="eyebrow">🎲 Group activity</span><h2>{meta?.title ?? 'Activity'}</h2></div>
          <Link className="btn" to="/student/games">← Back to games</Link>
        </div>
        <div className="card group-loading" role={error ? 'alert' : 'status'}>
          <span aria-hidden="true">{error ? '💡' : '🎧'}</span>
          <div>
            <h3>{error ? 'This activity cannot open' : 'Getting things ready…'}</h3>
            <p className="muted">{error || 'Finding your teammates.'}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="beat-page stack">
      <div className="beat-studio-head">
        <div>
          <span className="eyebrow">{meta.glyph} {meta.groupName ?? 'On your own'}</span>
          <h2>{meta.title}</h2>
          <p className="muted">
            {meta.solo
              ? 'Playing on your own. Nothing here is graded.'
              : `With ${meta.teammates.join(' and ')}`}
          </p>
        </div>
        <Link className="btn" to="/student/games">← Back to activities</Link>
      </div>

      <p className="card game-instructions">{meta.instructions}</p>

      {!meta.solo && (
        <div className="collaborator-bar">
          <div className="row" aria-label="Teammates in this activity">
            {participants.map((person) => (
              <span className="collaborator" key={person.id} style={{ '--player-color': person.color } as CSSProperties}>
                <i aria-hidden="true" />{person.name}{person.id === studentId ? ' (you)' : ''}
              </span>
            ))}
            <span className="muted">{participants.length} of {meta.memberCount} here</span>
          </div>
          <span className={`live-status ${connection}`} role="status">
            <i aria-hidden="true" />
            {connection === 'live' ? 'Changes are live' : connection === 'connecting' ? 'Connecting' : 'Connection lost'}
          </span>
        </div>
      )}

      {connection === 'lost' && (
        <div className="feedback try" role="alert">The activity lost its connection. Go back and join again.</div>
      )}
      {error && <div className="feedback try" role="alert">{error}</div>}

      {children}

      <div className="beat-footer row between">
        <p className="muted">{tip ?? 'Take your time. Nothing here is graded.'}</p>
        <Link className="btn" to="/student/games">Leave activity</Link>
      </div>
    </div>
  )
}
