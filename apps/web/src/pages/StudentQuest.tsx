import { useEffect, useState } from 'react'
import { api, getSession, type AnswerOut, type NextItem, type Skill } from '../api'
import { usePrefs, useSpeech } from '../a11y'

type Phase = 'pick' | 'question' | 'feedback' | 'done'

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
    if (phase === 'question' && prefs.readAloud && next?.item) {
      const t = next.item
      speech.speak([t.prompt, ...t.choices.map((c, i) => `Choice ${i + 1}. ${c.text}`)].join('. '))
    }
    if (phase === 'feedback' && prefs.readAloud && result) speech.speak(result.feedback)
    if (phase === 'done' && prefs.readAloud && next?.summary) speech.speak(`You did it. ${next.summary}`)
    return () => speech.stop()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, next, prefs.readAloud])

  if (!session || session.role !== 'student') return <p>Please pick "I am a student" on the home page.</p>
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
      <div className="card">
        <div className="guide"><span className="face" aria-hidden="true">🦉</span><h1>Hi Sam! Pick a quest.</h1></div>
        <div className="stack">
          {skills.filter((s) => s.id !== 'fraction_parts').map((s) => (
            <button key={s.id} type="button" className="choice" onClick={() => start(s.id)}>
              {s.subject === 'math' ? '🔢' : '📖'} {cap(s.child_name)}
            </button>
          ))}
        </div>
      </div>
    )
  }

  if (phase === 'done' && next) {
    return (
      <div className="card celebrate">
        <div aria-hidden="true" style={{ fontSize: '4em' }}>🎉</div>
        <h1>You did it!</h1>
        <p>{next.summary}</p>
        <button type="button" className="btn-primary" onClick={() => setPhase('pick')}>Back to quests</button>
      </div>
    )
  }

  const item = next?.item
  if (!item) return null

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <span className="quest-progress" aria-live="polite">Question {next!.position} of {next!.total}</span>
        {prefs.readAloud && (
          <div className="row" role="group" aria-label="Read aloud controls">
            <button type="button" onClick={() => speech.speak([item.prompt, ...item.choices.map((c, i) => `Choice ${i + 1}. ${c.text}`)].join('. '))}>▶ Play</button>
            <button type="button" onClick={speech.pause}>⏸ Pause</button>
            <button type="button" onClick={speech.stop}>⏹ Stop</button>
          </div>
        )}
      </div>

      {phase === 'question' && (
        <>
          <p className="prompt" id="prompt">{item.prompt}</p>
          {item.image_alt && <p className="muted"><em>Picture: {item.image_alt}</em></p>}
          <div className="choices" role="group" aria-labelledby="prompt">
            {item.choices.map((c) => (
              <button key={c.id} type="button" className="choice" aria-pressed={picked === c.id} onClick={() => setPicked(c.id)}>
                {c.text}
              </button>
            ))}
          </div>
          <div className="row" style={{ marginTop: 16 }}>
            <button type="button" className="btn-primary" disabled={!picked} onClick={submit}>Check my answer</button>
            {!hintShown && <button type="button" onClick={() => { setHintShown(true); if (prefs.readAloud) speech.speak(item.hint) }}>💡 I'd like a hint</button>}
          </div>
          {hintShown && <p className="feedback" role="status">💡 {item.hint}</p>}
        </>
      )}

      {phase === 'feedback' && result && (
        <div className="stack">
          <p className="feedback" role="status">{result.correct ? '⭐ ' : '🌱 '}{result.feedback}</p>
          <button type="button" className="btn-primary" onClick={goOn}>{result.next.completed ? 'Finish' : 'Next question'}</button>
        </div>
      )}
    </div>
  )
}

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
