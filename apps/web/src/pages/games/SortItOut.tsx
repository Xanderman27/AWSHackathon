import { type CSSProperties, useState } from 'react'
import { useParams } from 'react-router-dom'
import GameShell from '../../components/GameShell'
import { editorColor, editorName, useActivity, useActivityRoom } from '../../games/room'

interface Item { id: string; label: string; glyph: string }
interface Bin { id: string; name: string; created_by: string | null }

interface SortState {
  round: number
  total_rounds: number
  set: { title: string; prompt: string; items: Item[] }
  bins: Bin[]
  placements: Record<string, { bin: string; by: string }>
  next_bin: number
}

const MAX_BINS = 4

export default function SortItOut() {
  const { gameId = 'sort-it-out', activityId = '' } = useParams()
  const { meta, roomId, error: metaError } = useActivity(gameId, activityId)
  const { snapshot, connection, error, send, studentId } = useActivityRoom<SortState>(roomId)
  const [held, setHeld] = useState<string | null>(null)
  const [newBin, setNewBin] = useState('')

  const game = snapshot?.state ?? null
  const people = snapshot?.participants ?? []
  const live = connection === 'live'
  const pile = game ? game.set.items.filter((item) => !game.placements[item.id]) : []

  function addBin() {
    const name = newBin.trim()
    if (!name) return
    send({ type: 'add_bin', name })
    setNewBin('')
  }

  return (
    <GameShell
      meta={meta} participants={people} connection={connection}
      cursors={snapshot?.cursors} onCursor={(x, y) => send({ type: 'cursor', x, y })}
      error={metaError || error} ready={Boolean(meta && game)} studentId={studentId}
      tip="There is no right answer here. If you can say why a card belongs, it belongs."
    >
      {game && (
        <>
          <section className="card sort-head">
            <div>
              <span className="chip cream">Set {game.round + 1} of {game.total_rounds}</span>
              <h3 style={{ margin: '8px 0 2px' }}>{game.set.title}</h3>
              <p className="muted" style={{ margin: 0 }}>{game.set.prompt}</p>
            </div>
            <div className="row">
              <button type="button" onClick={() => { setHeld(null); send({ type: 'clear' }) }} disabled={!live}>Start over</button>
              {game.total_rounds > 1 && (
                <button type="button" disabled={!live}
                  onClick={() => { setHeld(null); send({ type: 'set_round', round: (game.round + 1) % game.total_rounds }) }}>
                  Next set
                </button>
              )}
            </div>
          </section>

          <section className="card" aria-labelledby="sort-pile-title">
            <h3 id="sort-pile-title">Cards to sort</h3>
            <p className="muted" style={{ marginTop: 0 }}>
              {held ? 'Now pick a group for it.' : 'Pick up a card, then pick a group.'}
            </p>
            <div className="sort-pile">
              {pile.map((item) => (
                <button type="button" key={item.id} disabled={!live} aria-pressed={held === item.id}
                  className={`sort-card ${held === item.id ? 'held' : ''}`}
                  onClick={() => setHeld(held === item.id ? null : item.id)}>
                  <span className="sort-glyph" aria-hidden="true">{item.glyph}</span>
                  {item.label}
                </button>
              ))}
              {pile.length === 0 && <p className="muted" style={{ margin: 0 }}>Every card has a group. Can you explain each one?</p>}
            </div>
          </section>

          <div className="bin-grid">
            {game.bins.map((bin) => {
              const inside = game.set.items.filter((item) => game.placements[item.id]?.bin === bin.id)
              return (
                <section className="card bin-card" key={bin.id}>
                  <label className="bin-name">
                    <span className="visually-hidden">Name for this group</span>
                    <input value={bin.name} maxLength={24} disabled={!live}
                      onChange={(event) => send({ type: 'rename_bin', bin: bin.id, name: event.target.value })} />
                  </label>
                  {bin.created_by && (
                    <span className="bin-author" style={{ '--editor-color': editorColor(people, bin.created_by) ?? 'var(--brand)' } as CSSProperties}>
                      made by {editorName(people, bin.created_by) || 'a classmate'}
                    </span>
                  )}
                  <button type="button" className="drop-here" disabled={!live || !held}
                    onClick={() => { send({ type: 'place', item: held, bin: bin.id }); setHeld(null) }}>
                    {held ? 'Put the card here' : 'Pick up a card first'}
                  </button>
                  <div className="bin-items">
                    {inside.map((item) => (
                      <button type="button" key={item.id} className="sort-card placed" disabled={!live}
                        style={{ '--editor-color': editorColor(people, game.placements[item.id].by) ?? 'var(--brand)' } as CSSProperties}
                        aria-label={`Take ${item.label} back out of ${bin.name}`}
                        onClick={() => send({ type: 'place', item: item.id, bin: null })}>
                        <span className="sort-glyph" aria-hidden="true">{item.glyph}</span>
                        {item.label}
                      </button>
                    ))}
                    {inside.length === 0 && <span className="muted">Empty for now.</span>}
                  </div>
                  {game.bins.length > 1 && (
                    <button type="button" className="table-btn" disabled={!live}
                      onClick={() => send({ type: 'remove_bin', bin: bin.id })}>
                      Remove this group
                    </button>
                  )}
                </section>
              )
            })}

            {game.bins.length < MAX_BINS && (
              <section className="card bin-card new-bin">
                <h3 style={{ margin: 0 }}>Make a new group</h3>
                <p className="muted" style={{ margin: 0 }}>What do these cards have in common? Give it a name.</p>
                <label>
                  <span className="visually-hidden">Name for the new group</span>
                  <input value={newBin} maxLength={24} placeholder="Things that go fast" disabled={!live}
                    onChange={(event) => setNewBin(event.target.value)}
                    onKeyDown={(event) => { if (event.key === 'Enter') addBin() }} />
                </label>
                <button type="button" className="btn-primary" disabled={!live || !newBin.trim()} onClick={addBin}>
                  Add the group
                </button>
              </section>
            )}
          </div>
        </>
      )}
    </GameShell>
  )
}
