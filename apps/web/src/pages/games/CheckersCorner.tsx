// Checkers Corner: a two-seat checkers board. The server owns the rules; this screen only
// shows the board, hints at legal moves for the piece you picked up, and animates landings.

import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { useParams } from 'react-router-dom'
import GameShell from '../../components/GameShell'
import Capy from '../../components/Capy'
import Confetti from '../../components/Confetti'
import { useActivity, useActivityRoom } from '../../games/room'

interface Piece { p: 0 | 1; k: boolean }
interface CheckersState {
  board: Array<Piece | null>
  seats: Record<string, 0 | 1>
  turn: 0 | 1
  winner: 0 | 1 | null
  last: { from: number; to: number; captured: number | null } | null
  counts: [number, number]
}

const SIZE = 8
const SEAT_NAME = ['Red', 'Blue']
const SEAT_COLOR = ['var(--duo-red, #ff4b4b)', 'var(--duo-blue, #1cb0f6)']

const dark = (i: number) => ((Math.floor(i / SIZE) + i) % 2 === 1)

/** Same move rule the server enforces, used only to draw the little target dots. */
function targets(board: Array<Piece | null>, seat: 0 | 1, from: number): number[] {
  const piece = board[from]
  if (!piece || piece.p !== seat) return []
  const row = Math.floor(from / SIZE)
  const col = from % SIZE
  const dirs = piece.k ? [1, -1] : [seat === 0 ? 1 : -1]
  const out: number[] = []
  for (const dr of dirs) {
    for (const dc of [-1, 1]) {
      const r1 = row + dr, c1 = col + dc
      if (r1 >= 0 && r1 < SIZE && c1 >= 0 && c1 < SIZE && !board[r1 * SIZE + c1]) out.push(r1 * SIZE + c1)
      const r2 = row + 2 * dr, c2 = col + 2 * dc
      if (r2 >= 0 && r2 < SIZE && c2 >= 0 && c2 < SIZE && !board[r2 * SIZE + c2]) {
        const mid = board[(row + dr) * SIZE + (col + dc)]
        if (mid && mid.p !== seat) out.push(r2 * SIZE + c2)
      }
    }
  }
  return out
}

export default function CheckersCorner() {
  const { gameId = 'checkers', activityId = '' } = useParams()
  const { meta, roomId, error: metaError } = useActivity(gameId, activityId)
  const { snapshot, connection, error, send, studentId } = useActivityRoom<CheckersState>(roomId)
  const [picked, setPicked] = useState<number | null>(null)
  // A just-captured checker briefly lingers as a ghost that spins away.
  const [poof, setPoof] = useState<{ index: number; seat: 0 | 1; key: number } | null>(null)

  const state = snapshot?.state ?? null
  const people = snapshot?.participants ?? []
  const live = connection === 'live'
  const mySeat = state?.seats[studentId]
  const seated = mySeat !== undefined

  // Sit down automatically the moment the room is live and a chair is free.
  useEffect(() => {
    if (live && state && !seated && Object.keys(state.seats).length < 2) send({ type: 'sit' })
  }, [live, state, seated]) // eslint-disable-line react-hooks/exhaustive-deps

  // Dropping the piece when the board changes under you avoids stale highlights.
  useEffect(() => { setPicked(null) }, [snapshot?.revision && state?.turn]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const captured = state?.last?.captured
    const landedPiece = state?.last ? state.board[state.last.to] : null
    if (captured == null || !landedPiece) return
    setPoof({ index: captured, seat: (1 - landedPiece.p) as 0 | 1, key: snapshot?.revision ?? 0 })
    const timer = setTimeout(() => setPoof(null), 550)
    return () => clearTimeout(timer)
  }, [state?.last?.from, state?.last?.to, state?.last?.captured]) // eslint-disable-line react-hooks/exhaustive-deps

  const hints = useMemo(() => (
    state && picked !== null && mySeat !== undefined ? targets(state.board, mySeat, picked) : []
  ), [state, picked, mySeat])

  const nameOfSeat = (seat: 0 | 1) => {
    const id = state ? Object.keys(state.seats).find((pid) => state.seats[pid] === seat) : undefined
    if (!id) return `${SEAT_NAME[seat]} (empty chair)`
    const who = people.find((person) => person.id === id)?.name
      ?? meta?.members.find((member) => member.id === id)?.display_name ?? SEAT_NAME[seat]
    return id === studentId ? `${who} (you)` : who
  }

  const myTurn = seated && state?.turn === mySeat && state.winner === null

  function tap(index: number) {
    if (!state || !live || !seated || state.winner !== null || state.turn !== mySeat) return
    const piece = state.board[index]
    if (piece && piece.p === mySeat) { setPicked(picked === index ? null : index); return }
    if (picked !== null && hints.includes(index)) {
      send({ type: 'move', from: picked, to: index })
      setPicked(null)
    }
  }

  return (
    <GameShell
      meta={meta} participants={people} connection={connection}
      cursors={snapshot?.cursors} onCursor={(x, y) => send({ type: 'cursor', x, y })}
      error={metaError || error} ready={Boolean(meta && state)} studentId={studentId}
      tip="Talk about your moves! Saying a plan out loud is half the fun."
    >
      {state && (
        <>
          <Confetti burst={state.winner !== null ? 8 : 0} />

          <section className="card checkers-head">
            <Capy size={70} mood={state.winner !== null ? 'cheer' : 'happy'} />
            <div aria-live="polite">
              {state.winner !== null ? (
                <>
                  <h3 style={{ margin: 0 }}>{nameOfSeat(state.winner)} wins! 🎉</h3>
                  <p className="muted" style={{ margin: 0 }}>Great game, both of you. Reset the board for a rematch.</p>
                </>
              ) : (
                <>
                  <h3 style={{ margin: 0 }}>
                    {myTurn ? 'Your move!' : `${nameOfSeat(state.turn)} is thinking…`}
                  </h3>
                  <p className="muted" style={{ margin: 0 }}>
                    {seated
                      ? `You are ${SEAT_NAME[mySeat!]}. Tap one of your checkers, then tap a glowing square.`
                      : 'Both chairs are taken, so you are watching this game.'}
                  </p>
                </>
              )}
            </div>
            <div className="checkers-score" aria-label="Checkers left on the board">
              {[0, 1].map((seat) => (
                <span key={seat} className={`checkers-count ${state.turn === seat && state.winner === null ? 'up' : ''}`}
                  style={{ '--seat-color': SEAT_COLOR[seat] } as CSSProperties}>
                  <i aria-hidden="true" />{nameOfSeat(seat as 0 | 1)} · {state.counts[seat]}
                </span>
              ))}
            </div>
            <button type="button" onClick={() => send({ type: 'reset' })} disabled={!live || !seated}>
              Reset the board
            </button>
          </section>

          <section className="card checkers-wrap" aria-label="Checkers board">
            {/* Your own checkers belong at the bottom of your screen, moving up it. Seat 0
                starts on rows 0-2 and moves down the board, so seat 0 is the one that needs
                turning round; seat 1 already starts at the bottom. Flipping seat 1 instead
                put both players' pieces at the top, moving away from them. */}
            <div className={`checkers-board ${mySeat === 0 ? 'flipped' : ''}`} role="grid" aria-label="8 by 8 checkers board">
              {state.board.map((piece, index) => {
                const isDark = dark(index)
                const hinted = hints.includes(index)
                const last = state.last
                const landed = last?.to === index
                // The landing piece slides in from its old square (offsets are in piece widths;
                // one square is 100/0.76 because the checker fills 76% of its cell).
                const slide = landed && last
                  ? {
                      '--sdx': `${((last.from % SIZE) - (last.to % SIZE)) * (100 / 0.76)}%`,
                      '--sdy': `${(Math.floor(last.from / SIZE) - Math.floor(last.to / SIZE)) * (100 / 0.76)}%`,
                    } as CSSProperties
                  : undefined
                const label = piece
                  ? `${SEAT_NAME[piece.p]}${piece.k ? ' king' : ''} checker`
                  : hinted ? 'You can move here' : 'Empty square'
                return (
                  <button
                    type="button" key={index} role="gridcell"
                    className={`checkers-cell ${isDark ? 'dark' : 'light'} ${hinted ? 'hint' : ''}`}
                    aria-label={`Row ${Math.floor(index / SIZE) + 1}, column ${(index % SIZE) + 1}. ${label}`}
                    disabled={!isDark || !live}
                    onClick={() => tap(index)}
                  >
                    {piece && (
                      <span
                        key={landed && last ? `m${last.from}-${last.to}` : 'still'}
                        className={`checker seat-${piece.p} ${picked === index ? 'picked' : ''} ${landed ? 'landed' : ''} ${myTurn && piece.p === mySeat ? 'mine' : ''}`}
                        style={{ '--seat-color': SEAT_COLOR[piece.p], ...slide } as CSSProperties}
                        aria-hidden="true"
                      >
                        {piece.k && <em className="crown">👑</em>}
                      </span>
                    )}
                    {poof?.index === index && !piece && (
                      <span key={`poof-${poof.key}`} className="checker ghost"
                        style={{ '--seat-color': SEAT_COLOR[poof.seat] } as CSSProperties} aria-hidden="true" />
                    )}
                    {hinted && !piece && <span className="hint-dot" aria-hidden="true" />}
                  </button>
                )
              })}
            </div>
          </section>
        </>
      )}
    </GameShell>
  )
}
