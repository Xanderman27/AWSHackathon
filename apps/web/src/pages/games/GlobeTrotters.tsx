// Globe Trotters: one clue, twelve tiles, everyone taps together. Wrong tiles dim, the
// right one pops with confetti, and a fun fact appears while the next clue loads.

import { useParams } from 'react-router-dom'
import GameShell from '../../components/GameShell'
import Capy from '../../components/Capy'
import Confetti from '../../components/Confetti'
import { editorName, useActivity, useActivityRoom } from '../../games/room'

interface GlobeState {
  index: number
  total: number
  score: number
  missed: string[]
  solved: boolean
  solved_by: string | null
  done: boolean
  round: { clue: string; answer?: string; fact?: string }
}

// Mirrors the server's tile list; ids must match exactly.
const TILES: { id: string; label: string; glyph: string; kind: 'continent' | 'ocean' }[] = [
  { id: 'africa', label: 'Africa', glyph: '🦁', kind: 'continent' },
  { id: 'antarctica', label: 'Antarctica', glyph: '🐧', kind: 'continent' },
  { id: 'asia', label: 'Asia', glyph: '🐼', kind: 'continent' },
  { id: 'australia', label: 'Australia', glyph: '🦘', kind: 'continent' },
  { id: 'europe', label: 'Europe', glyph: '🏰', kind: 'continent' },
  { id: 'north-america', label: 'North America', glyph: '🗽', kind: 'continent' },
  { id: 'south-america', label: 'South America', glyph: '🦜', kind: 'continent' },
  { id: 'arctic', label: 'Arctic Ocean', glyph: '🐻‍❄️', kind: 'ocean' },
  { id: 'atlantic', label: 'Atlantic Ocean', glyph: '⛵', kind: 'ocean' },
  { id: 'indian', label: 'Indian Ocean', glyph: '🐠', kind: 'ocean' },
  { id: 'pacific', label: 'Pacific Ocean', glyph: '🐋', kind: 'ocean' },
  { id: 'southern', label: 'Southern Ocean', glyph: '🧊', kind: 'ocean' },
]

export default function GlobeTrotters() {
  const { gameId = 'globe-trotters', activityId = '' } = useParams()
  const { meta, roomId, error: metaError } = useActivity(gameId, activityId)
  const { snapshot, connection, error, send, studentId } = useActivityRoom<GlobeState>(roomId)

  const state = snapshot?.state ?? null
  const people = snapshot?.participants ?? []
  const live = connection === 'live'

  const finderName = state?.solved_by
    ? (state.solved_by === studentId ? 'You' : editorName(people, state.solved_by) || 'A teammate')
    : ''

  return (
    <GameShell
      meta={meta} participants={people} connection={connection}
      error={metaError || error} ready={Boolean(meta && state)} studentId={studentId}
      tip="Read the clue out loud together before anyone taps."
    >
      {state && state.done && (
        <section className="card celebrate globe-done">
          <Confetti burst={4} />
          <Capy size={120} mood="cheer" float />
          <h2 style={{ marginTop: 10 }}>World travelers!</h2>
          <p style={{ fontSize: '1.15em' }}>
            You found {state.score} of {state.total} on the very first try. The whole planet, explored together!
          </p>
          <button type="button" className="btn-primary btn-lg" onClick={() => send({ type: 'restart' })} disabled={!live}>
            Travel again 🌏
          </button>
        </section>
      )}

      {state && !state.done && (
        <>
          <Confetti burst={state.solved ? state.index + 1 : 0} />

          <section className={`card globe-clue ${state.solved ? 'found' : ''}`}>
            <Capy size={84} mood={state.solved ? 'cheer' : 'think'} />
            <div aria-live="polite">
              <span className="chip">Clue {state.index + 1} of {state.total}</span>
              {state.solved ? (
                <>
                  <h3 className="globe-answer">
                    {finderName} found it: {TILES.find((tile) => tile.id === state.round.answer)?.label}! ⭐
                  </h3>
                  <p className="globe-fact">{state.round.fact}</p>
                </>
              ) : (
                <p className="globe-clue-text">{state.round.clue}</p>
              )}
            </div>
            <div className="globe-score" aria-label={`${state.score} first-try stars so far`}>
              <strong>{state.score}</strong><span>first-try ⭐</span>
            </div>
          </section>

          {(['continent', 'ocean'] as const).map((kind) => (
            <section key={kind} className="card globe-board">
              <h3 className="globe-kind">{kind === 'continent' ? '🗺️ Continents' : '🌊 Oceans'}</h3>
              <div className="globe-tiles">
                {TILES.filter((tile) => tile.kind === kind).map((tile) => {
                  const missed = state.missed.includes(tile.id)
                  const isAnswer = state.solved && state.round.answer === tile.id
                  return (
                    <button
                      type="button" key={tile.id}
                      className={`globe-tile ${kind} ${missed ? 'missed' : ''} ${isAnswer ? 'right' : ''}`}
                      disabled={!live || state.solved || missed}
                      aria-label={missed ? `${tile.label}. Not this one.` : tile.label}
                      onClick={() => send({ type: 'guess', tile: tile.id })}
                    >
                      <span className="globe-glyph" aria-hidden="true">{tile.glyph}</span>
                      {tile.label}
                    </button>
                  )
                })}
              </div>
            </section>
          ))}
        </>
      )}
    </GameShell>
  )
}
