import { useEffect, useState } from 'react'
import { api, getSession, type AnswerOut, type NextItem, type Skill } from '../api'
import { usePrefs, useSpeech } from '../a11y'
import RoleGate from './RoleGate'

type Phase = 'pick' | 'question' | 'feedback' | 'done'
const LETTERS = ['A', 'B', 'C', 'D']

export default function StudentQuest() {
  const session = getSession()
  const { prefs } = usePrefs()
  const speech = useSpeech()
  const [skills, setSkills] = useState<Skill[]>([])
  const [phase, setPhase] = useState<Phase>('pick')
  const [next, setNext] = useState<NextItem | null>(null)
  const [picked, setPicked] = useState<string | null>(null)
  const [hintShown, setHintShown] = useState(false)
  const [result, setResult] = useState<AnswerOut | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { api<Skill[]>('/skills').then(setSkills).catch((e) => setError(String(e))) }, [])

  useEffect(() => {
    if (phase === 'question' && prefs.readAloud && next?.item) speech.speak(readable(next.item))
    if (phase === 'feedback' && prefs.readAloud && result) speech.speak(result.feedback)
    if (phase === 'done' && prefs.readAloud && next?.summary) speech.speak(`You did it. ${next.summary}`)
    return () => speech.stop()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, next, prefs.readAloud])

  if (!session || session.role !== 'student') return <RoleGate need="student" />
  if (error) return <p role="alert">Something went wrong. {error}</p>

  async function start(skillId: string) {
    const n = await api<NextItem>(`/attempts/start?skill_id=${skillId}`, { method: 'POST' })
    setNext(n); setPicked(null); setHintShown(false)
    setPhase(n.completed ? 'done' : 'question')
  }

  async function submit() {
    if (!next?.item || !picked) return
    const r = await api<AnswerOut>(`/attempts/${next.attempt_id}/answer`, { method: 'POST', body: JSON.stringify({ choice_id: picked, hint_used: hintShown }) })
    setResult(r); setPhase('feedback')
  }

  function goOn() {
    if (!result) return
    setNext(result.next); setPicked(null); setHintShown(false); setResult(null)
    setPhase(result.next.completed ? 'done' : 'question')
  }

  if (phase === 'pick') {
    return (
      <div className="page center">
        <div className="guide">
          <span className="face" aria-hidden="true">🦉</span>
          <div><h1 style={{ marginBottom: 4 }}>Hi Sam!</h1><p className="muted" style={{ margin: 0 }}>Pick a quest. Take your time.</p></div>
        </div>
        <div className="quest-pick">
          {skills.filter((s) => s.id !== 'fraction_parts').map((s, i) => (
            <button key={s.id} type="button" className={`quest-card ${i % 2 ? 'sky' : 'mint'}`} onClick={() => start(s.id)}>
              <span className="art" aria-hidden="true">{s.subject === 'math' ? '🔢' : '📖'}</span>
              <strong>{cap(s.child_name)}</strong>
              <span>6 questions · about 5 minutes</span>
            </button>
          ))}
        </div>
      </div>
    )
  }

  if (phase === 'done' && next) {
    return (
      <div className="page center"><div className="card celebrate">
        <div className="big" aria-hidden="true">🎉</div>
        <h1>You did it!</h1>
        <p style={{ fontSize: '1.2em' }}>{next.summary}</p>
        <button type="button" className="btn-primary btn-lg" onClick={() => setPhase('pick')}>Back to quests</button>
      </div></div>
    )
  }

  const item = next?.item
  if (!item) return null
  const pos = next!.position, total = next!.total

  return (
    <div className="page center"><div className="card">
      <div className="quest-head">
        <div className="progress" role="img" aria-label={`Question ${pos} of ${total}`}>
          {Array.from({ length: total }, (_, i) => <i key={i} className={i + 1 < pos ? 'done' : i + 1 === pos ? 'now' : ''} />)}
        </div>
        <span className="chip">Question {pos} of {total}</span>
      </div>

      {phase === 'question' && (
        <>
          <div className="guide" style={{ marginBottom: 10 }}>
            <span className="face" aria-hidden="true">🦉</span>
            <p className="prompt" id="prompt" style={{ margin: 0 }}>{item.prompt}</p>
          </div>
          {item.image_alt && <p className="muted" style={{ marginLeft: 88 }}><em>Picture: {item.image_alt}</em></p>}
          {prefs.readAloud && (
            <div className="row" role="group" aria-label="Read aloud controls" style={{ margin: '8px 0 14px 88px' }}>
              <button type="button" onClick={() => speech.speak(readable(item))}>▶ Play</button>
              <button type="button" onClick={speech.pause}>⏸ Pause</button>
              <button type="button" onClick={speech.stop}>⏹ Stop</button>
            </div>
          )}
          <div className="choices" role="group" aria-labelledby="prompt" style={{ marginTop: 14 }}>
            {item.choices.map((c, i) => (
              <button key={c.id} type="button" className="choice" aria-pressed={picked === c.id} onClick={() => setPicked(c.id)}>
                <span className="key" aria-hidden="true">{LETTERS[i]}</span>{c.text}
              </button>
            ))}
          </div>
          {hintShown && <p className="feedback hint" role="status" style={{ marginTop: 16 }}>💡 {item.hint}</p>}
          <div className="row" style={{ marginTop: 20 }}>
            <button type="button" className="btn-primary btn-lg" disabled={!picked} onClick={submit}>Check my answer</button>
            {!hintShown && <button type="button" className="btn-ghost" onClick={() => { setHintShown(true); if (prefs.readAloud) speech.speak(item.hint) }}>💡 I'd like a hint</button>}
          </div>
        </>
      )}

      {phase === 'feedback' && result && (
        <div className="stack">
          <p className={`feedback ${result.correct ? 'good' : 'try'}`} role="status">{result.correct ? '⭐ ' : '🌱 '}{result.feedback}</p>
          <div><button type="button" className="btn-primary btn-lg" onClick={goOn}>{result.next.completed ? 'Finish' : 'Next question'}</button></div>
        </div>
      )}
    </div></div>
  )
}

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
const readable = (it: { prompt: string; choices: { text: string }[] }) =>
  [it.prompt, ...it.choices.map((c, i) => `${LETTERS[i]}. ${c.text}`)].join('. ')