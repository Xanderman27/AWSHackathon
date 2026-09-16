import { type CSSProperties } from 'react'
import { useParams } from 'react-router-dom'
import GameShell from '../../components/GameShell'
import Bear from '../../components/Bear'
import Confetti from '../../components/Confetti'
import { editorColor, editorName, useActivity, useActivityRoom } from '../../games/room'

interface MemoryState {
  cards: string[]
  matched: boolean[]
  matched_by: Array<string | null>
  flipped: number[]
  found: number
  pairs: number
}

export default function MemoryMeadow() {
  const { gameId = 'memory-meadow', activityId = '' } = useParams()
  const { meta, roomId, error: metaError } = useActivity(gameId, activityId)
  const { snapshot, connection, error, send, studentId } = useActivityRoom<MemoryState>(roomId)

  const board = snapshot?.state ?? null
  const people = snapshot?.participants ?? []
  const live = connection === 'live'
  const done = Boolean(board && board.found === board.pairs)

  return (
    <GameShell
      meta={meta} participants={people} connection={connection}
      error={metaError || error} ready={Boolean(meta && board)} studentId={studentId}
      tip="Say the spot out loud when you see a card. Remembering together is the whole game."
    >
      {board && (
        <>
          <Confetti burst={done ? board.pairs : 0} />
          <section className="card meadow-head">
            <Bear size={72} mood={done ? 'cheer' : 'happy'} />
            <div>
              <h3 style={{ margin: 0 }}>{done ? 'You found them all!' : 'Find the matching pairs'}</h3>
              <p className="muted" style={{ margin: 0 }}>
                {done ? 'Shuffle to play again.' : 'Anyone can flip a card. Two that match stay up.'}
              </p>
            </div>
            <div className="meadow-score" aria-live="polite">
              <strong>{board.found}</strong><span>of {board.pairs} pairs</span>
            </div>
            <button type="button" onClick={() => send({ type: 'shuffle' })} disabled={!live}>Shuffle and start again</button>
          </section>

          <section className="card" aria-labelledby="meadow-title">
            <h3 id="meadow-title" className="visually-hidden">Memory board</h3>
            <div className="meadow-grid">
              {board.cards.map((face, index) => {
                const matched = board.matched[index]
                const showing = matched || board.flipped.includes(index)
                const color = editorColor(people, board.matched_by[index])
                const name = editorName(people, board.matched_by[index])
                return (
                  <button type="button" key={index} disabled={!live || showing}
                    className={`meadow-card ${showing ? 'up' : ''} ${matched ? 'matched' : ''}`}
                    style={color ? { '--editor-color': color } as CSSProperties : undefined}
                    aria-label={showing
                      ? `Card ${index + 1}, showing, ${matched ? `matched${name ? ` by ${name}` : ''}` : 'turned over'}`
                      : `Card ${index + 1}, face down. Turn it over.`}
                    onClick={() => send({ type: 'flip', index })}>
                    <span aria-hidden="true">{showing ? face : '🌿'}</span>
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
