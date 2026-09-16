// Parent rights and resources library (PRD FR-22). Compact tiles; each opens a condensed popup.
// Curated, static, every document cites an official source. Nothing here is legal advice.

import { useEffect, useRef, useState } from 'react'
import { api } from '../api'

interface ResourceCard {
  id: string; category: string; title: string; summary: string
  source_org: string; source_name: string; source_url: string; citation: string
  reading_minutes: number; key_points: string[]
}
interface Section { heading: string; paragraphs?: string[]; list?: string[] }
interface ResourceDoc extends ResourceCard { sections: Section[] }

const ICON: Record<string, string> = {
  'Special education': '🎓', 'Progress and goals': '📈', 'Privacy and records': '🔒',
  Discipline: '🛡️', 'Your rights': '⚖️',
}
const DISCLAIMER = 'General information from official sources, not legal advice. For your own situation, contact your state parent center.'

export function ResourceList() {
  const [items, setItems] = useState<ResourceCard[]>([])
  const [openId, setOpenId] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { api<ResourceCard[]>('/resources').then(setItems).catch((e) => setErr(String(e))) }, [])

  if (err) return <p role="alert">{err}</p>
  const categories = [...new Set(items.map((r) => r.category))]

  return (
    <div className="stack">
      <div>
        <h2 style={{ marginBottom: 2 }}>Know your rights</h2>
        <p className="muted" style={{ margin: 0 }}>Short guides to the rules that protect your child. Tap one to read it.</p>
      </div>

      {categories.map((cat) => (
        <section key={cat} className="res-section">
          <h3 className="res-cat"><span aria-hidden="true">{ICON[cat] ?? '📄'}</span> {cat}</h3>
          <div className="res-tiles">
            {items.filter((r) => r.category === cat).map((r) => (
              <button key={r.id} type="button" className="res-tile" onClick={() => setOpenId(r.id)}>
                <span className="res-tile-title">{r.title}</span>
                <span className="res-tile-meta">{r.reading_minutes} min</span>
              </button>
            ))}
          </div>
        </section>
      ))}

      <p className="note" style={{ fontSize: '.9em' }}>{DISCLAIMER}</p>

      {openId && <ResourceDialog id={openId} onClose={() => setOpenId(null)} />}
    </div>
  )
}

function ResourceDialog({ id, onClose }: { id: string; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const [doc, setDoc] = useState<ResourceDoc | null>(null)

  useEffect(() => { api<ResourceDoc>(`/resources/${id}`).then(setDoc).catch(() => onClose()) }, [id, onClose])

  // Native <dialog> gives us focus trapping, Escape, and a backdrop for free. onClose is kept
  // in a ref so a new arrow function from the parent never re-runs the open/close wiring.
  const onCloseRef = useRef(onClose)
  useEffect(() => { onCloseRef.current = onClose }, [onClose])
  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (!d.open) d.showModal()
    const handleClose = () => onCloseRef.current()
    d.addEventListener('close', handleClose)
    return () => d.removeEventListener('close', handleClose)
  }, [])

  return (
    <dialog ref={ref} className="res-dialog" aria-labelledby="res-title"
      onClick={(e) => { if (e.target === ref.current) ref.current?.close() }}>
      <div className="res-dialog-body">
        {!doc ? <p>Loading…</p> : (
          <>
            <div className="res-dialog-head">
              <div style={{ flex: 1, minWidth: 0 }}>
                <span className="chip">{doc.category}</span>
                <h2 id="res-title" style={{ margin: '10px 0 4px' }}>{doc.title}</h2>
                <p className="muted" style={{ margin: 0 }}>{doc.summary}</p>
              </div>
              <button type="button" className="tool" aria-label="Close" onClick={() => ref.current?.close()}>✕</button>
            </div>

            <div className="card tinted-sky" style={{ margin: '16px 0', padding: '16px 20px' }}>
              <strong>The short version</strong>
              <ul style={{ margin: '6px 0 0', paddingLeft: '1.2em' }}>
                {doc.key_points.map((k, i) => <li key={i}>{k}</li>)}
              </ul>
            </div>

            <div className="res-more">
              {doc.sections.map((s, i) => (
                <details key={i}>
                  <summary>{s.heading}</summary>
                  <div className="res-more-body">
                    {s.paragraphs?.map((p, j) => <p key={j}>{p}</p>)}
                    {s.list && <ul>{s.list.map((l, j) => <li key={j}>{l}</li>)}</ul>}
                  </div>
                </details>
              ))}
            </div>

            <div className="source-card" style={{ marginTop: 16 }}>
              <strong>Official source</strong>
              <a href={doc.source_url} target="_blank" rel="noreferrer noopener">
                {doc.source_name} ({doc.citation}) ↗
              </a>
              <span className="muted" style={{ fontSize: '.85em' }}>{doc.source_org}</span>
            </div>
            <p className="note" style={{ marginTop: 14, fontSize: '.85em' }}>{DISCLAIMER}</p>
          </>
        )}
      </div>
    </dialog>
  )
}
