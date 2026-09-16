// Parent rights and resources library (PRD FR-22). Curated, static, every document cites an
// official source. Nothing here is model-generated and nothing here is legal advice.

import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'

interface ResourceCard {
  id: string; category: string; title: string; summary: string
  source_org: string; source_name: string; source_url: string; citation: string
  reading_minutes: number; key_points: string[]
}
interface Section { heading: string; paragraphs?: string[]; list?: string[] }
interface ResourceDoc extends ResourceCard { sections: Section[] }

const TONE = ['mint', 'sky', 'cream', 'rose']
const DISCLAIMER = 'This is general information from official sources, not legal advice. For help with your own situation, contact your state parent center.'

export function ResourceList() {
  const [items, setItems] = useState<ResourceCard[]>([])
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { api<ResourceCard[]>('/resources').then(setItems).catch((e) => setErr(String(e))) }, [])

  if (err) return <p role="alert">{err}</p>

  const categories = [...new Set(items.map((r) => r.category))]

  return (
    <div className="stack">
      <div>
        <h2 style={{ marginBottom: 2 }}>Know your rights</h2>
        <p className="muted" style={{ margin: 0, maxWidth: '70ch' }}>
          Plain-language guides to the federal rules that protect your child, each one linked to the
          official source so you can read the original.
        </p>
      </div>

      {categories.map((cat) => (
        <section key={cat}>
          <h3 style={{ marginBottom: 12 }}>{cat}</h3>
          <div className="res-grid">
            {items.filter((r) => r.category === cat).map((r, i) => (
              <Link key={r.id} to={`/parent/resources/${r.id}`} className="res-card card" style={{ textDecoration: 'none', color: 'inherit' }}>
                <span className={`chip ${TONE[i % TONE.length]}`}>{r.citation}</span>
                <h3>{r.title}</h3>
                <p className="muted" style={{ margin: 0 }}>{r.summary}</p>
                <span className="src">{r.source_org} · {r.reading_minutes} min read</span>
              </Link>
            ))}
          </div>
        </section>
      ))}

      <p className="note">{DISCLAIMER}</p>
    </div>
  )
}

export function ResourceDocument() {
  const { id } = useParams()
  const [doc, setDoc] = useState<ResourceDoc | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { api<ResourceDoc>(`/resources/${id}`).then(setDoc).catch((e) => setErr(String(e))) }, [id])

  if (err) return <p role="alert">{err}</p>
  if (!doc) return <p>Loading…</p>

  return (
    <div className="stack">
      <Link to="/parent/resources">← All resources</Link>
      <article className="card doc">
        <span className="chip">{doc.category}</span>
        <h1 style={{ marginTop: 12 }}>{doc.title}</h1>
        <p className="muted" style={{ fontSize: '1.1em' }}>{doc.summary}</p>

        <div className="card tinted-sky" style={{ margin: '20px 0' }}>
          <strong>The short version</strong>
          <ul style={{ marginBottom: 0 }}>{doc.key_points.map((k, i) => <li key={i}>{k}</li>)}</ul>
        </div>

        {doc.sections.map((s, i) => (
          <section key={i}>
            <h2>{s.heading}</h2>
            {s.paragraphs?.map((p, j) => <p key={j}>{p}</p>)}
            {s.list && <ul>{s.list.map((l, j) => <li key={j}>{l}</li>)}</ul>}
          </section>
        ))}

        <div className="source-card" style={{ marginTop: 28 }}>
          <strong>Official source</strong>
          <span>{doc.source_org}</span>
          <a href={doc.source_url} target="_blank" rel="noreferrer noopener">
            {doc.source_name} ({doc.citation}) ↗
          </a>
          <span className="muted" style={{ fontSize: '0.9em' }}>Opens the official government page in a new tab.</span>
        </div>

        <p className="note" style={{ marginTop: 20 }}>{DISCLAIMER}</p>
      </article>
    </div>
  )
}
