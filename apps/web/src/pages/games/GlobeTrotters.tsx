// Globe Trotters: one clue, one big friendly world map. Tap the continent or ocean the
// clue describes. Continents bob gently, waves drift across the sea, wrong picks shake
// and fade, and the right one glows with confetti and a fun fact.

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

// Mirrors the server's answer list; ids must match exactly. Each region is a cartoon blob
// on the map below — recognisable shapes, not survey-grade geography.
interface Region {
  id: string; label: string[]; glyph: string; kind: 'continent' | 'ocean'
  fill: string; paths: string[]; at: [number, number]
}

const REGIONS: Region[] = [
  {
    id: 'north-america', label: ['North', 'America'], glyph: '🗽', kind: 'continent', fill: '#8fd694',
    at: [205, 152],
    paths: ['M95 190 C80 140 110 95 165 82 C225 68 292 76 316 108 C334 132 322 152 300 158 C318 174 308 200 282 208 C296 224 282 244 258 244 C240 258 214 252 202 238 C170 250 130 238 118 216 C100 210 92 200 95 190 Z'],
  },
  {
    id: 'south-america', label: ['South', 'America'], glyph: '🦜', kind: 'continent', fill: '#ffd166',
    at: [262, 336],
    paths: ['M242 262 C276 250 306 268 310 300 C314 336 300 380 276 410 C264 424 244 424 234 408 C216 380 208 336 214 300 C218 278 228 266 242 262 Z'],
  },
  {
    id: 'europe', label: ['Europe'], glyph: '🏰', kind: 'continent', fill: '#c9a6ff',
    at: [503, 118],
    paths: ['M455 148 C438 130 442 100 470 88 C500 74 540 74 556 92 C570 108 562 128 546 136 C552 150 540 162 520 162 C500 168 470 162 455 148 Z'],
  },
  {
    id: 'africa', label: ['Africa'], glyph: '🦁', kind: 'continent', fill: '#ffb377',
    at: [508, 272],
    paths: ['M448 190 C470 172 520 170 550 186 C578 200 582 232 568 258 C580 292 570 330 546 362 C532 382 508 388 492 372 C466 344 448 300 444 258 C440 232 440 206 448 190 Z'],
  },
  {
    id: 'asia', label: ['Asia'], glyph: '🐼', kind: 'continent', fill: '#f4989c',
    at: [735, 146],
    paths: ['M585 150 C570 110 600 80 650 74 C720 64 800 70 856 92 C888 106 892 136 868 152 C880 170 862 192 830 194 C838 214 816 230 786 224 C756 236 716 230 694 214 C660 224 620 210 608 188 C592 178 582 164 585 150 Z'],
  },
  {
    id: 'australia', label: ['Australia'], glyph: '🦘', kind: 'continent', fill: '#f9e076',
    at: [828, 330],
    paths: ['M775 330 C770 302 796 282 830 282 C864 282 884 302 880 330 C892 344 880 366 856 372 C830 384 796 380 782 362 C772 352 770 340 775 330 Z'],
  },
  {
    id: 'antarctica', label: ['Antarctica'], glyph: '🐧', kind: 'continent', fill: '#eef7ff',
    at: [500, 528],
    paths: ['M20 512 C120 494 300 502 500 500 C700 498 880 494 980 512 C982 528 980 540 970 544 L30 544 C20 540 18 528 20 512 Z'],
  },
  {
    id: 'arctic', label: ['Arctic Ocean'], glyph: '🐻‍❄️', kind: 'ocean', fill: '#bfe3ff',
    at: [500, 36],
    paths: ['M14 8 L986 8 C994 8 996 14 996 22 L996 56 L4 56 L4 22 C4 14 6 8 14 8 Z'],
  },
  {
    id: 'southern', label: ['Southern Ocean'], glyph: '🧊', kind: 'ocean', fill: '#9ed0f5',
    at: [500, 462],
    paths: ['M4 436 L996 436 L996 490 L4 490 Z'],
  },
  {
    id: 'atlantic', label: ['Atlantic', 'Ocean'], glyph: '⛵', kind: 'ocean', fill: '#7ec4f2',
    at: [381, 250],
    paths: ['M336 62 L426 62 L426 430 L336 430 Z'],
  },
  {
    id: 'indian', label: ['Indian', 'Ocean'], glyph: '🐠', kind: 'ocean', fill: '#8ecbf4',
    at: [668, 330],
    paths: ['M600 246 L742 246 L742 430 L600 430 Z'],
  },
  {
    id: 'pacific', label: ['Pacific', 'Ocean'], glyph: '🐋', kind: 'ocean', fill: '#6db9ee',
    at: [40, 250],
    paths: ['M4 62 L76 62 L76 430 L4 430 Z', 'M904 62 L996 62 L996 430 L904 430 Z'],
  },
]

const LABEL = Object.fromEntries(REGIONS.map((region) => [region.id, region.label.join(' ')]))

// Little drifting waves that make the sea feel alive. Decoration only.
const WAVES: [number, number][] = [
  [160, 300], [370, 120], [385, 360], [640, 300], [700, 400], [930, 150], [930, 350], [40, 130], [500, 460],
]

function WorldMap({ state, live, onPick }: {
  state: GlobeState; live: boolean; onPick: (id: string) => void
}) {
  const pickable = live && !state.solved && !state.done
  return (
    <svg className={`globe-map ${state.solved ? 'settled' : ''}`} viewBox="0 0 1000 552"
      role="group" aria-label="World map. Tap a continent or an ocean.">
      <rect className="gm-sea" x="2" y="2" width="996" height="548" rx="22" />
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
            {region.paths.map((d, pathIndex) => (
              <path key={pathIndex} className="gm-shape" d={d} fill={region.fill} />
            ))}
            <text className="gm-glyph" x={region.at[0]} y={region.at[1] - (region.label.length > 1 ? 14 : 16)}>
              {region.glyph}
            </text>
            {region.label.map((line, lineIndex) => (
              <text key={lineIndex} className="gm-label"
                x={region.at[0]} y={region.at[1] + 8 + lineIndex * 17}>
                {line}
              </text>
            ))}
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
