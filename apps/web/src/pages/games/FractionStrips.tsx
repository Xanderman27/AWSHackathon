import { type CSSProperties } from 'react'
import { useParams } from 'react-router-dom'
import GameShell from '../../components/GameShell'
import Bear from '../../components/Bear'
import { editorColor, editorName, useActivity, useActivityRoom } from '../../games/room'

interface Target { num: number; den: number; label: string; words: string }

interface FractionState {
  round: number
  total_rounds: number
  target: Target
  rows: Record<string, boolean[]>
  updated_by: Record<string, Array<string | null>>
  matched: string[]
}

// Row order and names are fixed on the server; the labels here are what a child reads.
const ROWS: Array<{ id: string; name: string }> = [
  { id: 'halves', name: 'Halves' },
  { id: 'thirds', name: 'Thirds' },
  { id: 'fourths', name: 'Fourths' },
  { id: 'sixths', name: 'Sixths' },
  { id: 'eighths', name: 'Eighths' },
  { id: 'twelfths', name: 'Twelfths' },
]

/** Numerator over a bar over a denominator. Decorative: callers supply the spoken text. */
function Fraction({ num, den, size }: { num: number; den: number; size: 'lg' | 'sm' }) {
  return (
    <span className={`frac ${size}`} aria-hidden="true">
      <span>{num}</span>
      <i className="frac-bar" />
      <span>{den}</span>
    </span>
  )
}

export default function FractionStrips() {
  const { gameId = 'fraction-strips', activityId = '' } = useParams()
  const { meta, roomId, error: metaError } = useActivity(gameId, activityId)
  const { snapshot, connection, error, send, studentId } = useActivityRoom<FractionState>(roomId)

  const wall = snapshot?.state ?? null
  const people = snapshot?.participants ?? []
  const live = connection === 'live'

  return (
    <GameShell
      meta={meta} participants={people} connection={connection}
      cursors={snapshot?.cursors} onCursor={(x, y) => send({ type: 'cursor', x, y })}
      error={metaError || error} ready={Boolean(meta && wall)} studentId={studentId}
      tip="Two rows that cover the same amount are equivalent fractions, even when the pieces look different."
    >
      {wall && (
        <>
          <section className="card target-card" aria-live="polite">
            <Bear size={72} mood={wall.matched.length > 1 ? 'cheer' : 'happy'} />
            <div className="target-main">
              <span className="chip sky">Target</span>
              <div className="target-line">
                <Fraction num={wall.target.num} den={wall.target.den} size="lg" />
                <div>
                  <h3 className="target-name">Cover {wall.target.label}</h3>
                  <p className="muted" style={{ margin: 0 }}>
                    That is {wall.target.words}. Shade other rows until they cover the very same amount.
                  </p>
                </div>
              </div>
            </div>
            <div className="target-found">
              <strong>{wall.matched.length}</strong>
              <span>row{wall.matched.length === 1 ? '' : 's'} match so far</span>
            </div>
          </section>

          <section className="card wall-card" aria-labelledby="wall-title">
            <div className="row between">
              <div>
                <h3 id="wall-title">The fraction wall</h3>
                <p className="muted" style={{ margin: 0 }}>Every row is one whole, cut into a different number of equal pieces.</p>
              </div>
              <button type="button" onClick={() => send({ type: 'clear' })} disabled={!live}>Clear the wall</button>
            </div>

            <div className="fraction-wall">
              {ROWS.map((row) => {
                const pieces = wall.rows[row.id] ?? []
                const shaded = pieces.filter(Boolean).length
                const matched = wall.matched.includes(row.id)
                return (
                  <div className={`wall-row ${matched ? 'matched' : ''}`} key={row.id}>
                    <div className="wall-label">
                      <strong>{row.name}</strong>
                      {/* The strip below is a group labelled "<row>, N of M shaded", so the
                          notation here is decorative and saying it twice would be noise. */}
                      <Fraction num={shaded} den={pieces.length} size="sm" />
                    </div>
                    <div className="wall-strip" role="group" aria-label={`${row.name}, ${shaded} of ${pieces.length} shaded`}>
                      {pieces.map((on, index) => {
                        const who = wall.updated_by[row.id]?.[index]
                        const color = editorColor(people, who)
                        const name = editorName(people, who)
                        return (
                          <button type="button" key={index} disabled={!live} aria-pressed={on}
                            className={`wall-piece ${on ? 'on' : ''}`}
                            style={color ? { '--editor-color': color } as CSSProperties : undefined}
                            aria-label={`${on ? 'Unshade' : 'Shade'} piece ${index + 1} of ${pieces.length} in ${row.name}${name ? `, shaded by ${name}` : ''}`}
                            onClick={() => send({ type: 'set_cell', row: row.id, index, active: !on })} />
                        )
                      })}
                    </div>
                    <span className="wall-mark" aria-hidden="true">{matched ? '✓' : ''}</span>
                    <span className="visually-hidden">{matched ? `${row.name} covers the same amount as ${wall.target.label}.` : ''}</span>
                  </div>
                )
              })}
            </div>

            {wall.matched.length > 1 && (
              <div className="feedback good" role="status">
                Nice. {wall.matched.length} rows cover {wall.target.label} with different sized pieces.
              </div>
            )}
          </section>

          <section className="card round-picker" aria-label="Choose a target">
            <strong>Pick a target for everyone</strong>
            <div className="row">
              {Array.from({ length: wall.total_rounds }, (_, index) => (
                <button type="button" key={index} disabled={!live} aria-pressed={wall.round === index}
                  onClick={() => send({ type: 'set_round', round: index })}>
                  Target {index + 1}
                </button>
              ))}
            </div>
            <p className="muted" style={{ margin: 0 }}>Changing the target clears the wall for the whole group.</p>
          </section>
        </>
      )}
    </GameShell>
  )
}
