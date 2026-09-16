import { type CSSProperties, useState } from 'react'
import { useParams } from 'react-router-dom'
import GameShell from '../../components/GameShell'
import Bear from '../../components/Bear'
import Confetti from '../../components/Confetti'
import { editorName, useActivity, useActivityRoom } from '../../games/room'

type Cell = [number, number]

interface Piece {
  id: string
  name: string
  tone: string
  cells: Cell[]
  placed: { row: number; col: number } | null
  by: string | null
  held_by: string | null
}

interface ShapeState {
  round: number
  total_rounds: number
  puzzle: { title: string; rows: number; cols: number; silhouette: Cell[] }
  pieces: Piece[]
  solved: boolean
}

const key = (row: number, col: number) => `${row},${col}`

function bounds(cells: Cell[]) {
  return {
    rows: Math.max(...cells.map((cell) => cell[0])) + 1,
    cols: Math.max(...cells.map((cell) => cell[1])) + 1,
  }
}

export default function ShapeShift() {
  const { gameId = 'shape-shift', activityId = '' } = useParams()
  const { meta, roomId, error: metaError } = useActivity(gameId, activityId)
  const { snapshot, connection, error, send, studentId } = useActivityRoom<ShapeState>(roomId)
  const [hover, setHover] = useState<Cell | null>(null)

  const game = snapshot?.state ?? null
  const people = snapshot?.participants ?? []
  const live = connection === 'live'

  const mine = game?.pieces.find((piece) => piece.held_by === studentId && !piece.placed) ?? null
  const tray = game?.pieces.filter((piece) => !piece.placed) ?? []

  // Which board squares each placed piece covers, so the board can be drawn in one pass.
  // The number travels with the piece: in high contrast every piece is the same yellow, so
  // the marker is what tells one piece from its neighbour (two can even share a name).
  const filled = new Map<string, { piece: Piece; mark: number }>()
  game?.pieces.forEach((piece, order) => {
    if (!piece.placed) return
    piece.cells.forEach(([row, col]) =>
      filled.set(key(piece.placed!.row + row, piece.placed!.col + col), { piece, mark: order + 1 }))
  })

  const preview = new Set<string>()
  if (mine && hover) mine.cells.forEach(([row, col]) => preview.add(key(hover[0] + row, hover[1] + col)))

  const outline = new Set(game?.puzzle.silhouette.map(([row, col]) => key(row, col)) ?? [])
  const previewFits = [...preview].every((cell) => outline.has(cell) && !filled.has(cell))

  return (
    <GameShell
      meta={meta} participants={people} connection={connection}
      error={metaError || error} ready={Boolean(meta && game)} studentId={studentId}
      tip="If a piece will not fit, turn it a quarter turn and try the same spot again."
    >
      {game && (
        <>
          <Confetti burst={game.solved ? 3 : 0} />
          <section className="card shape-head">
            <Bear size={72} mood={game.solved ? 'cheer' : 'think'} />
            <div>
              <span className="chip rose">Puzzle {game.round + 1} of {game.total_rounds}</span>
              <h3 style={{ margin: '8px 0 2px' }}>{game.puzzle.title}</h3>
              <p className="muted" style={{ margin: 0 }} aria-live="polite">
                {game.solved
                  ? 'The outline is full. You fit every piece.'
                  : `${tray.length} piece${tray.length === 1 ? '' : 's'} still to place.`}
              </p>
            </div>
            <div className="row">
              <button type="button" onClick={() => send({ type: 'clear' })} disabled={!live}>Start over</button>
              {game.total_rounds > 1 && (
                <button type="button" disabled={!live}
                  onClick={() => send({ type: 'set_round', round: (game.round + 1) % game.total_rounds })}>
                  Next puzzle
                </button>
              )}
            </div>
          </section>

          <div className="shape-layout">
            <section className="card" aria-labelledby="board-title">
              <h3 id="board-title">The outline</h3>
              <p className="muted" style={{ marginTop: 0 }}>
                {mine
                  ? `Choose a square for the ${mine.name}.`
                  : tray.length === 0
                    ? 'Every piece is in. Tap one to take it back out.'
                    : 'Pick a piece from the tray first.'}
              </p>
              <div className="shape-board"
                style={{ '--cols': game.puzzle.cols, '--rows': game.puzzle.rows } as CSSProperties}
                onMouseLeave={() => setHover(null)}>
                {Array.from({ length: game.puzzle.rows }, (_, row) =>
                  Array.from({ length: game.puzzle.cols }, (_, col) => {
                    const id = key(row, col)
                    const inOutline = outline.has(id)
                    const held = filled.get(id)
                    if (!inOutline) return <span className="board-cell off" key={id} aria-hidden="true" />
                    if (held) {
                      const { piece, mark } = held
                      return (
                        <button type="button" key={id} disabled={!live}
                          className={`board-cell filled ${piece.tone}`}
                          aria-label={`Piece ${mark}, the ${piece.name}, covers row ${row + 1}, column ${col + 1}${piece.by ? `, placed by ${editorName(people, piece.by) || 'a classmate'}` : ''}. Take it back out.`}
                          onClick={() => send({ type: 'lift', piece: piece.id })}>
                          <span className="cell-mark" aria-hidden="true">{mark}</span>
                        </button>
                      )
                    }
                    const ghost = preview.has(id)
                    return (
                      <button type="button" key={id} disabled={!live || !mine}
                        className={`board-cell open ${ghost ? (previewFits ? 'ghost' : 'ghost-bad') : ''}`}
                        aria-label={mine
                          ? `Put the ${mine.name} at row ${row + 1}, column ${col + 1}`
                          : `Empty square at row ${row + 1}, column ${col + 1}`}
                        onMouseEnter={() => setHover([row, col])}
                        onFocus={() => setHover([row, col])}
                        onClick={() => { if (mine) send({ type: 'place', piece: mine.id, row, col }) }} />
                    )
                  }),
                )}
              </div>
              {mine && hover && !previewFits && (
                <p className="muted" role="status">That spot is too small for this piece. Try turning it.</p>
              )}
            </section>

            <section className="card" aria-labelledby="tray-title">
              <h3 id="tray-title">Pieces</h3>
              <p className="muted" style={{ marginTop: 0 }}>Tap a piece to pick it up, then turn or flip it.</p>
              <div className="piece-tray">
                {tray.map((piece) => {
                  const size = bounds(piece.cells)
                  const mark = game.pieces.findIndex((other) => other.id === piece.id) + 1
                  const holder = piece.held_by && piece.held_by !== studentId ? editorName(people, piece.held_by) : ''
                  return (
                    <div className={`tray-piece ${piece.held_by === studentId ? 'mine' : ''}`} key={piece.id}>
                      <button type="button" disabled={!live} aria-pressed={piece.held_by === studentId}
                        className="piece-pick" aria-label={`Pick up the ${piece.name}`}
                        onClick={() => send({ type: 'select', piece: piece.id })}>
                        <span className="piece-shape"
                          style={{ '--cols': size.cols, '--rows': size.rows } as CSSProperties} aria-hidden="true">
                          {Array.from({ length: size.rows }, (_, row) =>
                            Array.from({ length: size.cols }, (_, col) => (
                              <i key={key(row, col)}
                                className={piece.cells.some(([r, c]) => r === row && c === col) ? `on ${piece.tone}` : ''} />
                            )),
                          )}
                        </span>
                        <strong>{piece.name} <span className="cell-mark inline" aria-hidden="true">{mark}</span></strong>
                      </button>
                      {holder && <span className="piece-holder">{holder} has this</span>}
                      <div className="row piece-tools">
                        <button type="button" disabled={!live} onClick={() => send({ type: 'rotate', piece: piece.id })}
                          aria-label={`Turn the ${piece.name} a quarter turn`}>↻ Turn</button>
                        <button type="button" disabled={!live} onClick={() => send({ type: 'flip', piece: piece.id })}
                          aria-label={`Flip the ${piece.name} over`}>⇋ Flip</button>
                      </div>
                    </div>
                  )
                })}
                {tray.length === 0 && <p className="muted" style={{ margin: 0 }}>Every piece is on the board.</p>}
              </div>
            </section>
          </div>

          {game.solved && <div className="feedback good" role="status">You filled the whole outline together. Try the next puzzle.</div>}
        </>
      )}
    </GameShell>
  )
}
