import { type CSSProperties, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import GameShell from '../../components/GameShell'
import { editorColor, editorName, useActivity, useActivityRoom } from '../../games/room'

type TrackId = 'drums' | 'claps' | 'bass' | 'bells'

interface BeatState {
  grid: Record<TrackId, boolean[]>
  updated_by: Record<TrackId, Array<string | null>>
  tempo: number
  playing: boolean
  started_at: number | null
}

const TRACKS: Array<{ id: TrackId; name: string; icon: string; hint: string }> = [
  { id: 'drums', name: 'Drums', icon: '🥁', hint: 'Boom' },
  { id: 'claps', name: 'Claps', icon: '👏', hint: 'Clap' },
  { id: 'bass', name: 'Bass', icon: '🎸', hint: 'Bum' },
  { id: 'bells', name: 'Bells', icon: '🔔', hint: 'Ding' },
]

const BASS_NOTES = [110, 110, 130.81, 146.83, 110, 164.81, 146.83, 130.81]
const BELL_NOTES = [523.25, 659.25, 783.99, 659.25, 523.25, 698.46, 783.99, 659.25]

function audioContext() {
  const AudioContextClass = window.AudioContext || (window as typeof window & { webkitAudioContext: typeof AudioContext }).webkitAudioContext
  return new AudioContextClass()
}

function playHit(ctx: AudioContext, track: TrackId, step: number) {
  const now = ctx.currentTime
  const output = ctx.createGain()
  output.connect(ctx.destination)

  if (track === 'drums') {
    const osc = ctx.createOscillator()
    osc.type = 'sine'
    osc.frequency.setValueAtTime(135, now)
    osc.frequency.exponentialRampToValueAtTime(48, now + 0.13)
    output.gain.setValueAtTime(0.7, now)
    output.gain.exponentialRampToValueAtTime(0.001, now + 0.2)
    osc.connect(output)
    osc.start(now)
    osc.stop(now + 0.21)
    return
  }

  if (track === 'claps') {
    const buffer = ctx.createBuffer(1, Math.floor(ctx.sampleRate * 0.12), ctx.sampleRate)
    const data = buffer.getChannelData(0)
    for (let i = 0; i < data.length; i += 1) data[i] = Math.random() * 2 - 1
    const noise = ctx.createBufferSource()
    const filter = ctx.createBiquadFilter()
    filter.type = 'bandpass'
    filter.frequency.value = 1400
    filter.Q.value = 0.7
    output.gain.setValueAtTime(0.28, now)
    output.gain.exponentialRampToValueAtTime(0.001, now + 0.12)
    noise.buffer = buffer
    noise.connect(filter).connect(output)
    noise.start(now)
    return
  }

  const osc = ctx.createOscillator()
  osc.type = track === 'bass' ? 'triangle' : 'sine'
  osc.frequency.value = track === 'bass' ? BASS_NOTES[step] : BELL_NOTES[step]
  output.gain.setValueAtTime(track === 'bass' ? 0.32 : 0.22, now)
  output.gain.exponentialRampToValueAtTime(0.001, now + (track === 'bass' ? 0.3 : 0.45))
  osc.connect(output)
  osc.start(now)
  osc.stop(now + 0.46)
}

export default function BeatTogether() {
  const { gameId = 'beat-together', activityId = '' } = useParams()
  const { meta, roomId, error: metaError } = useActivity(gameId, activityId)
  const { snapshot, connection, error, send, studentId } = useActivityRoom<BeatState>(roomId)

  const audio = useRef<AudioContext | null>(null)
  const latest = useRef<BeatState | null>(null)
  const [currentStep, setCurrentStep] = useState(-1)

  const beat = snapshot?.state ?? null
  useEffect(() => { latest.current = beat }, [beat])
  useEffect(() => () => { void audio.current?.close() }, [])

  // The server hands out one start time, so every browser lands on the same count.
  useEffect(() => {
    if (!beat?.playing || !beat.started_at) { setCurrentStep(-1); return }
    let lastStep = -1
    const tick = () => {
      const state = latest.current
      if (!state?.playing || !state.started_at) return
      const elapsed = Date.now() - state.started_at
      if (elapsed < 0) { setCurrentStep(-1); return }
      const step = Math.floor(elapsed / (60_000 / state.tempo / 2)) % 8
      if (step === lastStep) return
      lastStep = step
      setCurrentStep(step)
      const ctx = audio.current
      if (ctx?.state === 'running') {
        TRACKS.forEach(({ id }) => { if (state.grid[id][step]) playHit(ctx, id, step) })
      }
    }
    tick()
    const timer = window.setInterval(tick, 24)
    return () => window.clearInterval(timer)
  }, [beat?.playing, beat?.started_at, beat?.tempo])

  function wakeAudio() {
    if (!audio.current) audio.current = audioContext()
    if (audio.current.state === 'suspended') void audio.current.resume()
    return audio.current
  }

  const live = connection === 'live'
  const visibleStep = beat?.playing ? currentStep : -1

  return (
    <GameShell
      meta={meta} participants={snapshot?.participants ?? []} connection={connection}
      error={metaError || error} ready={Boolean(meta && beat)} studentId={studentId}
      tip="Try this: one person makes the drums while another adds bass and bells."
    >
      {beat && (
        <>
          <section className="card beat-controls" aria-label="Song controls">
            <button className={`transport ${beat.playing ? 'stop' : 'play'}`} type="button" disabled={!live}
              onClick={() => { wakeAudio(); send({ type: 'transport', playing: !beat.playing }) }}>
              <span aria-hidden="true">{beat.playing ? '■' : '▶'}</span>
              {beat.playing ? 'Stop for everyone' : 'Play for everyone'}
            </button>
            <label className="tempo-control">
              <span>Speed <strong>{beat.tempo} BPM</strong></span>
              <input type="range" min="60" max="140" step="4" value={beat.tempo} disabled={!live}
                onChange={(event) => send({ type: 'tempo', tempo: Number(event.target.value) })} />
              <span className="tempo-words" aria-hidden="true"><i>Chill</i><i>Fast</i></span>
            </label>
            <button type="button" onClick={() => send({ type: 'clear' })} disabled={!live}>Clear the beat</button>
          </section>

          <section className="card sequencer-card" aria-labelledby="sequencer-title">
            <div className="row between">
              <div><h3 id="sequencer-title">Your 8-count loop</h3><p className="muted">Tap squares to add sounds. The song repeats after count 8.</p></div>
              <div className={`mini-eq ${beat.playing ? 'on' : ''}`} aria-hidden="true"><i /><i /><i /><i /></div>
            </div>
            <div className="sequencer-scroll" tabIndex={0} aria-label="Scrollable instrument grid">
              <div className="sequencer">
                <div className="step-numbers" aria-hidden="true">
                  <span />
                  {Array.from({ length: 8 }, (_, step) => <i className={visibleStep === step ? 'now' : ''} key={step}>{step + 1}</i>)}
                </div>
                {TRACKS.map((track) => (
                  <div className="track-row" key={track.id}>
                    <div className="track-name"><span aria-hidden="true">{track.icon}</span><strong>{track.name}</strong><small>{track.hint}</small></div>
                    {beat.grid[track.id].map((active, step) => {
                      const who = beat.updated_by[track.id][step]
                      const color = editorColor(snapshot?.participants ?? [], who)
                      const name = editorName(snapshot?.participants ?? [], who)
                      return (
                        <button type="button" key={step} disabled={!live} aria-pressed={active}
                          className={`beat-step ${active ? 'active' : ''} ${visibleStep === step ? 'now' : ''}`}
                          style={color ? { '--editor-color': color } as CSSProperties : undefined}
                          aria-label={`${active ? 'Remove' : 'Add'} ${track.name} on count ${step + 1}${name ? `, last changed by ${name}` : ''}`}
                          onClick={() => {
                            const ctx = wakeAudio()
                            if (!active) playHit(ctx, track.id, step)
                            send({ type: 'set_step', track: track.id, step, active: !active })
                          }}>
                          <span aria-hidden="true">{active ? track.icon : ''}</span>
                        </button>
                      )
                    })}
                  </div>
                ))}
              </div>
            </div>
          </section>
        </>
      )}
    </GameShell>
  )
}
