import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, getSession, type AnswerOut, type NextItem, type Skill } from '../api'
import { QuestTools } from '../a11y'
import Capy from '../components/Capy'
import Confetti from '../components/Confetti'
import { buildScript, SpokenText, useNarrator } from '../components/speech'
import RoleGate from './RoleGate'

type Phase = 'question' | 'feedback' | 'done'
const LETTERS = ['A', 'B', 'C', 'D']

export default function StudentQuest() {
  const { skillId = '' } = useParams()
  const nav = useNavigate()
  const session = getSession()
  const narrator = useNarrator()

  const [phase, setPhase] = useState<Phase>('question')
  const [next, setNext] = useState<NextItem | null>(null)
  const [skill, setSkill] = useState<Skill | null>(null)
  const [picked, setPicked] = useState<string | null>(null)
  const [hintShown, setHintShown] = useState(false)
  const [result, setResult] = useState<AnswerOut | null>(null)
  const [burst, setBurst] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const startedFor = useRef<string | null>(null)

  const item = next?.item ?? null

  // One script covers the question and every choice, so highlighting follows the voice.
  const script = useMemo(() => {
    if (!item) return { full: '', tokens: [] }
    // The letter is spoken but drawn as a badge, so it gets a region that is never rendered.
    // A reading passage is only spoken when the item allows it: reading the text aloud would
    // change what a reading-comprehension item measures (PRD FR-07).
    return buildScript([
      ...(item.passage && item.passage_read_aloud_allowed ? [{ region: 'passage', text: item.passage }] : []),
      { region: 'prompt', text: item.prompt },
      ...item.choices.flatMap((c, i) => [
        { region: `key${i}`, text: LETTERS[i] },
        { region: `c${i}`, text: c.text },
      ]),
    ])
  }, [item])

  useEffect(() => { api<Skill[]>('/skills').then((all) => setSkill(all.find((s) => s.id === skillId) ?? null)) }, [skillId])

  useEffect(() => {
    if (!skillId || startedFor.current === skillId) return
    startedFor.current = skillId
    api<NextItem>(`/attempts/start?skill_id=${skillId}`, { method: 'POST' })
      .then((n) => { setNext(n); setPhase(n.completed ? 'done' : 'question') })
      .catch((e) => setError(String(e)))
  }, [skillId])

  // Nothing plays on its own. A new question just makes sure the last one has stopped.
  useEffect(() => { narrator.stop() /* eslint-disable-line react-hooks/exhaustive-deps */ }, [item?.id, phase])

  if (!session || session.role !== 'student') return <RoleGate need="student" />
  if (error) return <p role="alert">Something went wrong. {error}</p>

  async function submit() {
    if (!next?.item || !picked || sending) return
    setSending(true)
    narrator.stop()
    try {
      const r = await api<AnswerOut>(`/attempts/${next.attempt_id}/answer`, {
        method: 'POST', body: JSON.stringify({ choice_id: picked, hint_used: hintShown }),
      })
      setResult(r)
      setPhase('feedback')
      if (r.correct) setBurst((b) => b + 1)
    } catch (e) {
      // A finished attempt just means this quest is over; anything else is a real problem.
      if (String(e).includes('409')) setPhase('done')
      else setError(String(e))
    } finally {
      setSending(false)
    }
  }

  function goOn() {
    if (!result) return
    narrator.stop()
    setNext(result.next); setPicked(null); setHintShown(false); setResult(null)
    setPhase(result.next.completed ? 'done' : 'question')
  }

  function leave() { narrator.stop(); nav('/student') }

  if (phase === 'done' && next) {
    return (
      <div className="page center student-theme">
        <Confetti burst={burst} />
        <div className="card celebrate">
          <Capy size={126} mood="cheer" float />
          <h1 style={{ marginTop: 12 }}>You did it!</h1>
          <p style={{ fontSize: '1.2em' }}>{next.summary}</p>
          <button type="button" className="btn-primary btn-lg" onClick={leave}>Back to my path</button>
        </div>
      </div>
    )
  }

  if (!item || !next) return <p>Getting your quiz ready…</p>
  const { position: pos, total } = next
  const playing = narrator.state === 'playing'

  return (
    <div className="page center student-theme">
      <Confetti burst={burst} />
      <div className="card quest-card-main">
        <div className="quest-head">
          <button type="button" className="btn-ghost back" onClick={leave}>← Back</button>
          <div className="progress" role="img" aria-label={`Question ${pos} of ${total}`}>
            {Array.from({ length: total }, (_, i) => (
              <i key={i} className={i + 1 < pos ? 'done' : i + 1 === pos ? 'now' : ''} />
            ))}
          </div>
          <span className="chip">{pos} of {total}</span>
          <QuestTools />
        </div>

        {phase === 'question' && (
          <>
            {item.passage && (
              <div className="passage">
                <h2 className="passage-title">Read this first</h2>
                {item.passage_read_aloud_allowed
                  ? <SpokenText tokens={script.tokens} region="passage" charIndex={narrator.charIndex} playing={playing} />
                  : <p style={{ margin: 0 }}>{item.passage}</p>}
              </div>
            )}

            <div className="ask">
              <Capy size={78} mood="happy" />
              <p className="prompt" id="prompt">
                <SpokenText tokens={script.tokens} region="prompt" charIndex={narrator.charIndex} playing={playing} />
              </p>
            </div>

            {item.image_alt && <p className="muted picture-note"><em>Picture: {item.image_alt}</em></p>}

            {narrator.available && (
              <div className="listen-wrap">
              <button type="button" className={`listen ${playing ? 'on' : ''}`}
                aria-pressed={playing} onClick={() => narrator.toggle(script.full)}>
                <span className="listen-ico" aria-hidden="true">{playing ? '⏸' : '▶'}</span>
                {playing ? 'Pause' : 'Play'}
                <span className="visually-hidden"> the question and answers out loud</span>
                {playing && <span className="eq" aria-hidden="true"><i /><i /><i /></span>}
              </button>
              </div>
            )}
            {narrator.available && item.passage && !item.passage_read_aloud_allowed && (
              <p className="muted read-note" style={{ textAlign: 'center' }}>
                This one is a reading quiz, so the story stays for your eyes. Capy will read the
                question and the answers.
              </p>
            )}

            <div className="choices" role="group" aria-labelledby="prompt">
              {item.choices.map((c, i) => (
                <button key={c.id} type="button" className="choice" aria-pressed={picked === c.id}
                  onClick={() => setPicked(c.id)}>
                  <span className="key" aria-hidden="true">{LETTERS[i]}</span>
                  <SpokenText tokens={script.tokens} region={`c${i}`} charIndex={narrator.charIndex} playing={playing} />
                </button>
              ))}
            </div>

            {hintShown && (
              <div className="hint-row" role="status">
                <Capy size={72} mood="think" />
                <div className="hint-bubble"><strong>Capy says:</strong> {item.hint}</div>
              </div>
            )}

            <div className="row actions">
              <button type="button" className="btn-primary btn-lg" disabled={!picked || sending} onClick={submit}>
                Check my answer
              </button>
              {!hintShown && (
                <button type="button" className="btn-ghost" onClick={() => setHintShown(true)}>
                  <Capy size={26} mood="think" /> Ask Capy for a hint
                </button>
              )}
            </div>
          </>
        )}

        {phase === 'feedback' && result && (
          <div className="stack">
            <div className={`feedback ${result.correct ? 'good' : 'try'}`} role="status">
              <Capy size={68} mood={result.correct ? 'cheer' : 'happy'} />
              <span>{result.feedback}</span>
            </div>
            <div>
              <button type="button" className="btn-primary btn-lg" onClick={goOn}>
                {result.next.completed ? 'Finish' : 'Next question'}
              </button>
            </div>
          </div>
        )}
      </div>
      {skill && <p className="muted quest-foot">{skill.child_name}</p>}
    </div>
  )
}
