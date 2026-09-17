import { type CSSProperties, useState } from 'react'
import { useParams } from 'react-router-dom'
import GameShell from '../../components/GameShell'
import Bear from '../../components/Bear'
import { editorColor, editorName, useActivity, useActivityRoom } from '../../games/room'

interface Card { id: string; text: string; answer: string }
interface Column { id: string; name: string; help: string }

interface DetectiveState {
  round: number
  total_rounds: number
  story: { title: string; passage: string; cards: Card[] }
  columns: Column[]
  placements: Record<string, { column: string; by: string }>
  revealed: boolean
}

export default function StoryDetectives() {
  const { gameId = 'story-detectives', activityId = '' } = useParams()
  const { meta, roomId, error: metaError } = useActivity(gameId, activityId)
  const { snapshot, connection, error, send, studentId } = useActivityRoom<DetectiveState>(roomId)
  // Which card this child is holding. Picking up is local: two teammates can each hold one.
  const [held, setHeld] = useState<string | null>(null)

  const game = snapshot?.state ?? null
  const people = snapshot?.participants ?? []
  const live = connection === 'live'

  function place(column: string | null) {
    if (!held) return
    send({ type: 'place', card: held, column })
    setHeld(null)
  }

  const pile = game ? game.story.cards.filter((card) => !game.placements[card.id]) : []
  const allPlaced = pile.length === 0

  return (
    <GameShell
      meta={meta} participants={people} connection={connection}
      cursors={snapshot?.cursors} onCursor={(x, y) => send({ type: 'cursor', x, y })}
      error={metaError || error} ready={Boolean(meta && game)} studentId={studentId}
      tip="The big idea is what the whole story is about. A detail is one true piece that backs it up."
    >
      {game && (
        <>
          <section className="card passage-card">
            <span className="chip cream">Story {game.round + 1} of {game.total_rounds}</span>
            <h3 className="passage-title">{game.story.title}</h3>
            <p className="story-text">{game.story.passage}</p>
          </section>

          <section className="card" aria-labelledby="pile-title">
            <div className="row between">
              <div>
                <h3 id="pile-title">Clue cards</h3>
                <p className="muted" style={{ margin: 0 }}>
                  {held ? 'Now choose where it goes.' : 'Pick up a card, then choose a column.'}
                </p>
              </div>
              <button type="button" onClick={() => { setHeld(null); send({ type: 'clear' }) }} disabled={!live}>
                Start over
              </button>
            </div>
            <div className="clue-pile">
              {pile.map((card) => (
                <button type="button" key={card.id} disabled={!live} aria-pressed={held === card.id}
                  className={`clue-card ${held === card.id ? 'held' : ''}`}
                  onClick={() => setHeld(held === card.id ? null : card.id)}>
                  {card.text}
                </button>
              ))}
              {allPlaced && <p className="muted" style={{ margin: 0 }}>Every card is sorted. Well done.</p>}
            </div>
          </section>

          <div className="detective-columns">
            {game.columns.map((column) => {
              const cards = game.story.cards.filter((card) => game.placements[card.id]?.column === column.id)
              return (
                <section className="card column-card" key={column.id} aria-labelledby={`col-${column.id}`}>
                  <h3 id={`col-${column.id}`}>{column.name}</h3>
                  <p className="muted column-help">{column.help}</p>
                  <button type="button" className="drop-here" disabled={!live || !held} onClick={() => place(column.id)}>
                    {held ? `Put the card in “${column.name}”` : 'Pick up a card first'}
                  </button>
                  <ul className="placed-list">
                    {cards.map((card) => {
                      const who = game.placements[card.id].by
                      const right = card.answer === column.id
                      return (
                        <li key={card.id}
                          className={`placed ${game.revealed ? (right ? 'right' : 'rethink') : ''}`}
                          style={{ '--editor-color': editorColor(people, who) ?? 'var(--brand)' } as CSSProperties}>
                          <span className="placed-text">{card.text}</span>
                          <span className="placed-by">
                            {editorName(people, who) || 'You'}
                            {game.revealed && <strong>{right ? ' ✓' : ' try again'}</strong>}
                          </span>
                          <button type="button" className="table-btn" disabled={!live}
                            onClick={() => send({ type: 'place', card: card.id, column: null })}>
                            Take back
                          </button>
                        </li>
                      )
                    })}
                    {cards.length === 0 && <li className="muted empty">Nothing here yet.</li>}
                  </ul>
                </section>
              )
            })}
          </div>

          <section className="card check-card">
            <Bear size={64} mood={game.revealed ? 'cheer' : 'think'} />
            <div>
              <strong>Ready to check together?</strong>
              <p className="muted" style={{ margin: 0 }}>
                Nothing is scored or sent to your teacher. Look, talk about it, and move any card you like.
              </p>
            </div>
            <div className="row">
              <button type="button" className="btn-primary" disabled={!live}
                onClick={() => send({ type: 'reveal', revealed: !game.revealed })}>
                {game.revealed ? 'Hide the answers' : 'Check together'}
              </button>
              {game.total_rounds > 1 && (
                <button type="button" disabled={!live}
                  onClick={() => { setHeld(null); send({ type: 'set_round', round: (game.round + 1) % game.total_rounds }) }}>
                  Next story
                </button>
              )}
            </div>
          </section>
        </>
      )}
    </GameShell>
  )
}
