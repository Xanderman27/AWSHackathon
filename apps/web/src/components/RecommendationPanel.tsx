// AI proposes, the teacher decides, the family sees the result. Every draft arrives with the
// approved sources it was built from and a badge saying whether a live model wrote it or it
// came from cache — a teacher should never have to guess which.

import { useEffect, useState } from 'react'
import { api } from '../api'

interface Citation {
  id: string; title: string; doc_type: string; tier: number
  source_org: string; source_url: string; citation: string; excerpt: string
}
export interface Recommendation {
  id: string; student_id: string; skill_id: string; status: string
  title: string; why: string; minutes: number; materials: string[]; steps: string[]
  citations: Citation[]; origin: string; pipeline_path: string[]; warning: string
  approved_by: string | null
}
interface AiStatus { offline: boolean; model_id: string | null; region: string | null; guardrail: boolean }

const TIER_LABEL: Record<number, string> = { 1: 'Standard', 2: 'Reviewed guidance', 3: 'Approved template' }

export default function RecommendationPanel({ studentId, skills }: {
  studentId: string
  skills: { skill_id: string; skill_name: string }[]
}) {
  const [status, setStatus] = useState<AiStatus | null>(null)
  const [rows, setRows] = useState<Recommendation[]>([])
  const [skillId, setSkillId] = useState(skills[0]?.skill_id ?? '')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [err, setErr] = useState('')

  useEffect(() => {
    api<AiStatus>('/teacher/ai/status').then(setStatus).catch(() => setStatus(null))
    api<Recommendation[]>(`/teacher/recommendations?student_id=${studentId}`)
      .then(setRows).catch(() => setErr('Recommendations could not load.'))
  }, [studentId])

  useEffect(() => { setSkillId((current) => current || skills[0]?.skill_id || '') }, [skills])

  async function draft() {
    if (!skillId) return
    setBusy(true); setErr(''); setNotice('')
    try {
      const row = await api<Recommendation>('/teacher/recommendations/draft', {
        method: 'POST', body: JSON.stringify({ student_id: studentId, skill_id: skillId }),
      })
      setRows((current) => [row, ...current])
    } catch (problem) {
      setErr(String(problem).includes('422')
        ? 'No approved source covers that skill yet, so nothing was drafted.'
        : 'A draft could not be generated.')
    } finally { setBusy(false) }
  }

  async function decide(id: string, decision: 'approve' | 'reject') {
    setErr(''); setNotice('')
    try {
      const row = await api<Recommendation>(`/teacher/recommendations/${id}/decision`, {
        method: 'POST', body: JSON.stringify({ decision }),
      })
      setRows((current) => current.map((r) => (r.id === id ? row : r)))
      setNotice(decision === 'approve'
        ? 'Approved. It is now on this family’s dashboard as a next step.'
        : 'Rejected. Nothing was sent to the family.')
    } catch {
      setErr('That decision could not be saved.')
    }
  }

  const proposed = rows.filter((r) => r.status === 'proposed')
  const decided = rows.filter((r) => r.status !== 'proposed')

  return (
    <section className="card rec-panel" aria-labelledby="rec-title">
      <div className="row between">
        <div>
          <span className="chip sky">Next steps for home</span>
          <h3 id="rec-title" style={{ margin: '8px 0 4px' }}>Suggest an activity</h3>
          <p className="muted" style={{ margin: 0, maxWidth: '62ch' }}>
            Built only from approved sources, and grounded in this learner's own evidence. Nothing
            reaches the family until you approve it.
          </p>
        </div>
        {status && (
          <span className={`origin-badge ${status.offline ? 'cached' : 'live'}`}>
            {status.offline
              ? 'Cached drafts · Bedrock not connected'
              : `Live · ${status.model_id}${status.guardrail ? ' · guardrail on' : ''}`}
          </span>
        )}
      </div>

      <div className="row rec-controls">
        <label className="msg-field" style={{ minWidth: 240 }}>
          <span>Skill</span>
          <select value={skillId} onChange={(e) => setSkillId(e.target.value)}>
            {skills.map((s) => <option key={s.skill_id} value={s.skill_id}>{s.skill_name}</option>)}
          </select>
        </label>
        <button type="button" className="btn-primary btn-lg" disabled={!skillId || busy} onClick={draft}>
          {busy ? 'Drafting…' : 'Draft an activity'}
        </button>
      </div>

      {notice && <div className="feedback good" role="status">✓ {notice}</div>}
      {err && <div className="feedback try" role="alert">{err}</div>}

      {proposed.map((rec) => (
        <article className="rec-draft" key={rec.id}>
          <div className="row between">
            <h4>{rec.title}</h4>
            <span className={`origin-badge ${rec.origin.startsWith('bedrock') ? 'live' : 'cached'}`}>
              {rec.origin.startsWith('bedrock') ? 'generated' : 'cached draft'}
            </span>
          </div>
          {rec.warning && <p className="feedback try rec-warning" role="alert">{rec.warning}</p>}
          <p className="rec-why">{rec.why}</p>
          <p className="muted"><strong>{rec.minutes} minutes</strong> · {rec.materials.join(', ')}</p>
          <ol className="rec-steps">{rec.steps.map((step, i) => <li key={i}>{step}</li>)}</ol>

          <details className="rec-sources">
            <summary>{rec.citations.length} approved source{rec.citations.length === 1 ? '' : 's'} behind this</summary>
            <ul>
              {rec.citations.map((c) => (
                <li key={c.id}>
                  <strong>{c.title}</strong>
                  <span className="chip">{TIER_LABEL[c.tier] ?? `Tier ${c.tier}`}</span>
                  <p className="muted">{c.excerpt}…</p>
                  <a href={c.source_url} target="_blank" rel="noreferrer noopener">{c.citation}</a>
                  <span className="muted"> · {c.source_org}</span>
                </li>
              ))}
            </ul>
            <p className="muted rec-path">Path: {rec.pipeline_path.join(' → ')}</p>
          </details>

          <div className="row rec-actions">
            <button type="button" className="btn-primary" onClick={() => decide(rec.id, 'approve')}>
              Approve and send to the family
            </button>
            <button type="button" onClick={() => decide(rec.id, 'reject')}>Reject</button>
          </div>
        </article>
      ))}

      {decided.length > 0 && (
        <div className="rec-decided">
          <h4>Already decided</h4>
          <ul className="plain-list">
            {decided.map((rec) => (
              <li key={rec.id}>
                <span className={`chip ${rec.status === 'approved' ? 'mint' : 'rose'}`}>{rec.status}</span>
                {' '}{rec.title}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
