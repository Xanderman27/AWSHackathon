import { type CSSProperties, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, getSession } from '../api'

type TrackId = 'drums' | 'claps' | 'bass' | 'bells'

interface Participant {
  id: string
  name: string
  color: string
}

interface GroupActivity {
  id: string
  game_id: string
  title: string
  group_name: string
  teammates: { id: string; display_name: string }[]
  member_count: number
  instructions: string
}

interface BeatState {
  type: 'state'
  activity_id: string
  grid: Record<TrackId, boolean[]>
  updated_by: Record<TrackId, Array<string | null>>
  tempo: number
  playing: boolean
  started_at: number | null
  revision: number
  participants: Participant[]
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
  const frequency = track === 'bass' ? BASS_NOTES[step] : BELL_NOTES[step]
  osc.type = track === 'bass' ? 'triangle' : 'sine'
  osc.frequency.value = frequency
  output.gain.setValueAtTime(track === 'bass' ? 0.32 : 0.22, now)
  output.gain.exponentialRampToValueAtTime(0.001, now + (track === 'bass' ? 0.3 : 0.45))
  osc.connect(output)
  osc.start(now)
  osc.stop(now + 0.46)
}

export default function BeatBuilder() {
  const { activityId } = useParams()
  const session = getSession()
  const studentId = session?.role === 'student' ? session.userId : ''
  const socket = useRef<WebSocket | null>(null)
  const currentState = useRef<BeatState | null>(null)
  const audio = useRef<AudioContext | null>(null)
  const [activity, setActivity] = useState<GroupActivity | null>(null)
  const [beat, setBeat] = useState<BeatState | null>(null)
  const [connection, setConnection] = useState<'connecting' | 'live' | 'lost'>('connecting')
  const [error, setError] = useState('')
  const [currentStep, setCurrentStep] = useState(-1)

  useEffect(() => {
    currentState.current = beat
  }, [beat])

  useEffect(() => () => {
    audio.current?.close()
  }, [])

  useEffect(() => {
    let active = true
    let ws: WebSocket | null = null
    if (!activityId || !studentId) return

    api<GroupActivity[]>('/student/group-activities')
      .then((activities) => {
        if (!active) return
        const assigned = activities.find((item) => item.id === activityId)
        if (!assigned) {
          setError('This activity is not assigned to your group.')
          return
        }
        setActivity(assigned)
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const params = new URLSearchParams({ student_id: studentId })
        ws = new WebSocket(`${protocol}//${window.location.host}/api/games/beat/ws/activity/${activityId}?${params}`)
        socket.current = ws

        ws.onmessage = (event) => {
          if (!active) return
          const message = JSON.parse(event.data) as BeatState | { type: 'error'; message: string }
          if (message.type === 'error') {
            setError(message.message)
            return
          }
          setBeat(message)
          setConnection('live')
        }
        ws.onerror = () => {
          if (active) setError('The activity could not connect. Try opening it again.')
        }
        ws.onclose = (event) => {
          if (active && event.code !== 1000 && currentState.current) setConnection('lost')
        }
      })
      .catch(() => {
        if (active) setError('The activity could not load. Try again.')
      })

    return () => {
      active = false
      ws?.close(1000)
      if (socket.current === ws) socket.current = null
    }
  }, [activityId, studentId])

  useEffect(() => {
    if (!beat?.playing || !beat.started_at) return

    let lastStep = -1
    const tick = () => {
      const state = currentState.current
      if (!state?.playing || !state.started_at) return
      const elapsed = Date.now() - state.started_at
      if (elapsed < 0) {
        setCurrentStep(-1)
        return
      }
      const stepLength = 60_000 / state.tempo / 2
      const step = Math.floor(elapsed / stepLength) % 8
      if (step === lastStep) return
      lastStep = step
      setCurrentStep(step)
      const ctx = audio.current
      if (ctx?.state === 'running') {
        TRACKS.forEach(({ id }) => {
          if (state.grid[id][step]) playHit(ctx, id, step)
        })
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

  function send(message: Record<string, unknown>) {
    if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify(message))
  }

  function setStep(track: TrackId, step: number, active: boolean) {
    const ctx = wakeAudio()
    if (active) playHit(ctx, track, step)
    send({ type: 'set_step', track, step, active })
  }

  function toggleTransport() {
    wakeAudio()
    send({ type: 'transport', playing: !beat?.playing })
  }

  const pageError = (!activityId || !studentId) ? 'This activity is not available for this student.' : error

  if (!activity || !beat) {
    return (
      <div className="beat-page stack">
        <div className="row between">
          <div><span className="eyebrow">🎵 Group activity</span><h2>Beat Together</h2></div>
          <Link className="btn" to="/student/games">← Back to games</Link>
        </div>
        <div className="card group-loading" role={pageError ? 'alert' : 'status'}>
          <span aria-hidden="true">{pageError ? '💡' : '🎧'}</span>
          <div>
            <h3>{pageError ? 'This activity cannot open' : 'Joining your teammates…'}</h3>
            <p className="muted">{pageError || 'Getting the shared music ready.'}</p>
          </div>
        </div>
      </div>
    )
  }

  const visibleStep = beat.playing ? currentStep : -1

  return (
    <div className="beat-page stack">
      <div className="beat-studio-head">
        <div>
          <span className="eyebrow">🎵 {activity.group_name}</span>
          <h2>{activity.title}</h2>
          <p className="muted">With {activity.teammates.map((teammate) => teammate.display_name).join(' and ')}</p>
        </div>
        <Link className="btn" to="/student/games">← Back to activities</Link>
      </div>

      <div className="collaborator-bar">
        <div className="row" aria-label="Teammates in this activity">
          {beat.participants.map((person) => (
            <span className="collaborator" key={person.id} style={{ '--player-color': person.color } as CSSProperties}>
              <i aria-hidden="true" />{person.name}{person.id === studentId ? ' (you)' : ''}
            </span>
          ))}
          <span className="muted">{beat.participants.length} of {activity.member_count} here</span>
        </div>
        <span className={`live-status ${connection}`} role="status">
          <i aria-hidden="true" />{connection === 'live' ? 'Changes are live' : connection === 'connecting' ? 'Connecting' : 'Connection lost'}
        </span>
      </div>

      {connection === 'lost' && <div className="feedback try" role="alert">The activity lost its connection. Go back and join again.</div>}

      <section className="card beat-controls" aria-label="Song controls">
        <button className={`transport ${beat.playing ? 'stop' : 'play'}`} type="button" onClick={toggleTransport} disabled={connection !== 'live'}>
          <span aria-hidden="true">{beat.playing ? '■' : '▶'}</span>
          {beat.playing ? 'Stop for everyone' : 'Play for everyone'}
        </button>
        <label className="tempo-control">
          <span>Speed <strong>{beat.tempo} BPM</strong></span>
          <input type="range" min="60" max="140" step="4" value={beat.tempo} disabled={connection !== 'live'}
            onChange={(event) => send({ type: 'tempo', tempo: Number(event.target.value) })} />
          <span className="tempo-words" aria-hidden="true"><i>Chill</i><i>Fast</i></span>
        </label>
        <button type="button" onClick={() => send({ type: 'clear' })} disabled={connection !== 'live'}>Clear the beat</button>
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
                  const editor = beat.participants.find((person) => person.id === beat.updated_by[track.id][step])
                  return (
                    <button type="button" className={`beat-step ${active ? 'active' : ''} ${visibleStep === step ? 'now' : ''}`}
                      style={editor ? { '--editor-color': editor.color } as CSSProperties : undefined}
                      aria-label={`${active ? 'Remove' : 'Add'} ${track.name} on count ${step + 1}${editor ? `, last changed by ${editor.name}` : ''}`}
                      aria-pressed={active} disabled={connection !== 'live'} key={step}
                      onClick={() => setStep(track.id, step, !active)}>
                      <span aria-hidden="true">{active ? track.icon : ''}</span>
                    </button>
                  )
                })}
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="beat-footer row between">
        <p className="muted">Try this: one person makes the drums while another adds bass and bells.</p>
        <Link className="btn" to="/student/games">Leave activity</Link>
      </div>
    </div>
  )
}
