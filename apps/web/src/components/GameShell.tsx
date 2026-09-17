// The frame every collaborative activity sits in: who is in your group, who is here right
// now, and one way back out. Each game only has to draw its own board.
//
// The roster shows every seat in the group, not only the people currently connected, so a
// child can see they are working with Kai and Leo and Zoe before any of them have arrived.

import { useRef, type CSSProperties, type PointerEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import Avatar from './Avatar'
import type { ActivityMeta, Connection, Participant } from '../games/room'

interface Props {
  meta: ActivityMeta | null
  participants: Participant[]
  connection: Connection
  error: string
  ready: boolean
  studentId: string
  tip?: string
  /** Teammates' live pointers (normalized 0..1) from the room snapshot. */
  cursors?: Record<string, [number, number]>
  /** Called (throttled) with this player's own normalized pointer position. */
  onCursor?: (x: number, y: number) => void
  children: ReactNode
}

/** Wraps the play area: reports your pointer, draws everyone else's. */
function CursorField({ cursors, onCursor, participants, studentId, children }: {
  cursors?: Record<string, [number, number]>
  onCursor?: (x: number, y: number) => void
  participants: Participant[]
  studentId: string
  children: ReactNode
}) {
  const field = useRef<HTMLDivElement>(null)
  const lastSent = useRef(0)

  function report(event: PointerEvent<HTMLDivElement>) {
    if (!onCursor || !field.current) return
    const at = performance.now()
    if (at - lastSent.current < 66) return // ~15 updates a second is plenty
    lastSent.current = at
    const box = field.current.getBoundingClientRect()
    if (box.width < 1 || box.height < 1) return
    onCursor((event.clientX - box.left) / box.width, (event.clientY - box.top) / box.height)
  }

  const others = Object.entries(cursors ?? {}).filter(([id]) => id !== studentId)
  return (
    <div className="cursor-field" ref={field} onPointerMove={report}>
      {children}
      {others.map(([id, [x, y]]) => {
        const who = participants.find((person) => person.id === id)
        if (!who) return null
        return (
          <div key={id} className="peer-cursor"
            style={{ left: `${x * 100}%`, top: `${y * 100}%`, '--player-color': who.color } as CSSProperties}
            aria-hidden="true">
            <svg viewBox="0 0 24 24" width="20" height="20">
              <path d="M4 2 L20 11 L12.5 12.8 L9.5 20 Z" fill="var(--player-color)" stroke="#fff" strokeWidth="1.6" />
            </svg>
            <span className="peer-cursor-name">{who.name}</span>
          </div>
        )
      })}
    </div>
  )
}

function names(list: { display_name: string }[]) {
  const all = list.map((person) => person.display_name)
  if (all.length <= 1) return all.join('')
  return `${all.slice(0, -1).join(', ')} and ${all[all.length - 1]}`
}

export default function GameShell({ meta, participants, connection, error, ready, studentId, tip, cursors, onCursor, children }: Props) {
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

  const here = new Set(participants.map((person) => person.id))
  const colorOf = (id: string) => participants.find((person) => person.id === id)?.color
  const presentCount = meta.members.filter((member) => here.has(member.id)).length

  return (
    <div className="beat-page stack">
      <div className="beat-studio-head">
        <div>
          <span className="eyebrow">{meta.glyph} {meta.groupName ?? 'On your own'}</span>
          <h2>{meta.title}</h2>
          <p className="muted">
            {meta.solo ? 'Playing on your own. Nothing here is graded.' : `You are working with your classmates ${names(meta.teammates)}.`}
          </p>
        </div>
        <Link className="btn" to="/student/games">← Back to activities</Link>
      </div>

      {!meta.solo && (
        <section className="card team-bar" aria-labelledby="team-title">
          <div className="team-head">
            <h3 id="team-title">Your team</h3>
            <span className={`live-status ${connection}`} role="status">
              <i aria-hidden="true" />
              {connection === 'live'
                ? `${presentCount} of ${meta.members.length} here · changes are live`
                : connection === 'connecting' ? 'Connecting' : 'Connection lost'}
            </span>
          </div>
          <ul className="team-faces">
            {meta.members.map((member) => {
              const present = here.has(member.id)
              return (
                <li key={member.id} className={`teammate ${present ? 'here' : 'away'}`}
                  style={{ '--player-color': colorOf(member.id) ?? 'var(--line)' } as CSSProperties}>
                  <span className="teammate-face">
                    <Avatar photo={member.photo} spec={member.avatar} size={56} />
                    <i className="teammate-dot" aria-hidden="true" />
                  </span>
                  <strong>{member.display_name}{member.id === studentId ? ' (you)' : ''}</strong>
                  <small>{present ? 'here now' : 'not here yet'}</small>
                </li>
              )
            })}
          </ul>
        </section>
      )}

      <p className="card game-instructions">{meta.instructions}</p>

      {connection === 'lost' && (
        <div className="feedback try" role="alert">The activity lost its connection. Go back and join again.</div>
      )}
      {error && <div className="feedback try" role="alert">{error}</div>}

      <CursorField cursors={cursors} onCursor={onCursor} participants={participants} studentId={studentId}>
        {children}
      </CursorField>

      <div className="beat-footer row between">
        <p className="muted">{tip ?? 'Take your time. Nothing here is graded.'}</p>
        <Link className="btn" to="/student/games">Leave activity</Link>
      </div>
    </div>
  )
}
