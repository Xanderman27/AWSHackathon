// Globe Trotters: one clue, one big friendly world map. Tap the continent or ocean the
// clue describes. Continents bob gently, waves drift across the sea, wrong picks shake
// and fade, and the right one glows with confetti and a fun fact.

import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import GameShell from '../../components/GameShell'
import { playHurray } from '../../components/sound'
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

import {
  CONTINENT_ANCHORS, CONTINENT_PATHS, MAP_H, MAP_W, OCEAN_ANCHORS, OCEAN_PATHS,
} from '../../games/worldPaths'

// Mirrors the server's answer list; ids must match exactly. Continent outlines are real
// Natural Earth geography (see games/worldPaths.ts); oceans are invisible tap areas on
// the open water, marked only by a floating label.
interface Region {
  id: string; label: string[]; glyph: string; kind: 'continent' | 'ocean'
  fill?: string; path: string; at: [number, number]
}

const CONTINENT_META: [string, string[], string, string][] = [
  ['north-america', ['North', 'America'], '🗽', '#8fd694'],
  ['south-america', ['South', 'America'], '🦜', '#ffd166'],
  ['europe', ['Europe'], '🏰', '#c9a6ff'],
  ['africa', ['Africa'], '🦁', '#ffb377'],
  ['asia', ['Asia'], '🐼', '#f4989c'],
  ['australia', ['Australia'], '🦘', '#f9e076'],
  ['antarctica', ['Antarctica'], '🐧', '#eef7ff'],
]
const OCEAN_META: [string, string[], string][] = [
  ['arctic', ['Arctic Ocean'], '🐻‍❄️'],
  ['atlantic', ['Atlantic', 'Ocean'], '⛵'],
  ['pacific', ['Pacific', 'Ocean'], '🐋'],
  ['indian', ['Indian', 'Ocean'], '🐠'],
  ['southern', ['Southern Ocean'], '🧊'],
]

const REGIONS: Region[] = [
  // Oceans first, so continents sit on top of the water and win overlapping taps.
  ...OCEAN_META.map(([id, label, glyph]): Region => (
    { id, label, glyph, kind: 'ocean', path: OCEAN_PATHS[id], at: OCEAN_ANCHORS[id] }
  )),
  ...CONTINENT_META.map(([id, label, glyph, fill]): Region => (
    { id, label, glyph, kind: 'continent', fill, path: CONTINENT_PATHS[id], at: CONTINENT_ANCHORS[id] }
  )),
]

const LABEL = Object.fromEntries(REGIONS.map((region) => [region.id, region.label.join(' ')]))

// Little drifting waves that make the sea feel alive. Decoration only.
const WAVES: [number, number][] = [
  [120, 240], [70, 380], [390, 130], [395, 330], [610, 320], [700, 420], [920, 130], [930, 320], [180, 460], [800, 470],
]

function WorldMap({ state, live, onPick }: {
  state: GlobeState; live: boolean; onPick: (id: string) => void
}) {
  const pickable = live && !state.solved && !state.done
  return (
    <svg className={`globe-map ${state.solved ? 'settled' : ''}`} viewBox={`0 0 ${MAP_W} ${MAP_H}`}
      role="group" aria-label="World map. Tap a continent, or tap the water for an ocean.">
      <rect className="gm-sea" x="2" y="2" width={MAP_W - 4} height={MAP_H - 4} rx="22" />
      {WAVES.map(([x, y], index) => (
        <path key={index} className="gm-wave" style={{ animationDelay: `${index * 0.7}s` }}
          d={`M${x} ${y} q 9 -7 18 0 q 9 7 18 0`} />
      ))}
      {REGIONS.map((region, index) => {
        const missed = state.missed.includes(region.id)
        const right = state.solved && state.round.answer === region.id
        const canPick = pickable && !missed
        return (
          <g
            key={region.id}
            className={`gm-region ${region.kind} ${missed ? 'missed' : ''} ${right ? 'right' : ''}`}
            style={{ animationDelay: `${(index % 5) * 0.55}s` }}
            role="button" tabIndex={canPick ? 0 : -1}
            aria-label={missed ? `${LABEL[region.id]}. Not this one.` : LABEL[region.id]}
            aria-disabled={!canPick}
            onClick={() => canPick && onPick(region.id)}
            onKeyDown={(event) => {
              if (canPick && (event.key === 'Enter' || event.key === ' ')) {
                event.preventDefault()
                onPick(region.id)
              }
            }}
          >
            <path className="gm-shape" d={region.path} fill={region.fill} />
            <g className="gm-tag">
              {region.at[1] < 64 ? (
                // A shallow band (the Arctic) has no room to stack glyph over text,
                // so the whole tag sits on one line.
                <text className="gm-label" x={region.at[0]} y={region.at[1] + 8}>
                  {region.glyph} {region.label.join(' ')}
                </text>
              ) : (
                <>
                  <text className="gm-glyph" x={region.at[0]} y={region.at[1] - (region.label.length > 1 ? 12 : 14)}>
                    {region.glyph}
                  </text>
                  {region.label.map((line, lineIndex) => (
                    <text key={lineIndex} className="gm-label"
                      x={region.at[0]} y={region.at[1] + 8 + lineIndex * 17}>
                      {line}
                    </text>
                  ))}
                </>
              )}
            </g>
          </g>
        )
      })}
    </svg>
  )
}

export default function GlobeTrotters() {
  const { gameId = 'globe-trotters', activityId = '' } = useParams()
  const { meta, roomId, error: metaError } = useActivity(gameId, activityId)
  const { snapshot, connection, error, send, studentId } = useActivityRoom<GlobeState>(roomId)

  const state = snapshot?.state ?? null
  const people = snapshot?.participants ?? []
  const live = connection === 'live'

  // The whole team hears the hurray the moment anyone finds the answer.
  useEffect(() => { if (state?.solved) playHurray() }, [state?.solved])

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
                    {finderName} found it: {LABEL[state.round.answer ?? '']}! ⭐
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

          <section className="card globe-map-card">
            <WorldMap state={state} live={live} onPick={(id) => send({ type: 'guess', tile: id })} />
          </section>
        </>
      )}
    </GameShell>
  )
}
