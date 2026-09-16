// Messages: a corner panel for parent-teacher conversations.
//
// The server decides who may talk to whom, so this component only ever renders the contacts
// the API hands back. A parent sees their child's teacher; a teacher sees their families.

import { useCallback, useEffect, useRef, useState } from 'react'
import { api, getSession } from '../api'

interface Contact {
  student_id: string; student_name: string
  contact_id: string; contact_name: string; contact_role: string; contact_subtitle: string
}
interface Thread {
  id: string; subject: string; with_name: string; with_role: string
  student_name: string; preview: string; last_at: string; unread: number
}
interface Message {
  id: string; sender_id: string; sender_role: string; sender_name: string; body: string; at: string
}

type View = { name: 'list' } | { name: 'new' } | { name: 'thread'; id: string }

const POLL_MS = 10000

function when(iso: string) {
  const d = new Date(iso)
  const today = new Date()
  const sameDay = d.toDateString() === today.toDateString()
  return sameDay
    ? d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
    : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export default function MessagesWidget() {
  const session = getSession()
  const [open, setOpen] = useState(false)
  const [view, setView] = useState<View>({ name: 'list' })
  const [threads, setThreads] = useState<Thread[]>([])
  const [unread, setUnread] = useState(0)
  const launcher = useRef<HTMLButtonElement>(null)
  const panel = useRef<HTMLDivElement>(null)

  const loadThreads = useCallback(async () => {
    try {
      const d = await api<{ threads: Thread[]; unread: number }>('/messages/threads')
      setThreads(d.threads); setUnread(d.unread)
    } catch { /* offline or not permitted; leave the badge as-is */ }
  }, [])

  useEffect(() => { loadThreads() }, [loadThreads])
  useEffect(() => {
    const t = setInterval(loadThreads, POLL_MS)
    return () => clearInterval(t)
  }, [loadThreads])

  // Escape closes the panel and hands focus back to the launcher.
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { setOpen(false); launcher.current?.focus() }
    }
    document.addEventListener('keydown', onKey)
    panel.current?.querySelector<HTMLElement>('h2')?.focus()
    return () => document.removeEventListener('keydown', onKey)
  }, [open, view])

  if (!session || (session.role !== 'parent' && session.role !== 'teacher')) return null

  return (
    <>
      <button ref={launcher} type="button" className="msg-launcher" aria-expanded={open}
        onClick={() => { setOpen((o) => !o); setView({ name: 'list' }); loadThreads() }}>
        <span aria-hidden="true">💬</span> Messages
        {unread > 0 && <span className="msg-badge" aria-hidden="true">{unread}</span>}
        {unread > 0 && <span className="visually-hidden">, {unread} unread</span>}
      </button>

      {open && (
        <div className="msg-panel" ref={panel} role="dialog" aria-label="Messages">
          {view.name === 'list' && (
            <ThreadList threads={threads} onOpen={(id) => setView({ name: 'thread', id })}
              onNew={() => setView({ name: 'new' })} onClose={() => setOpen(false)} />
          )}
          {view.name === 'new' && (
            <NewThread onCancel={() => setView({ name: 'list' })}
              onCreated={async (id) => { await loadThreads(); setView({ name: 'thread', id }) }} />
          )}
          {view.name === 'thread' && (
            <ThreadView id={view.id} onBack={() => { loadThreads(); setView({ name: 'list' }) }}
              onChanged={loadThreads} />
          )}
        </div>
      )}
    </>
  )
}

function PanelHead({ title, onBack, onClose }: { title: string; onBack?: () => void; onClose?: () => void }) {
  return (
    <header className="msg-head">
      {onBack && <button type="button" className="tool" aria-label="Back to all messages" onClick={onBack}>←</button>}
      <h2 tabIndex={-1}>{title}</h2>
      {onClose && <button type="button" className="tool" aria-label="Close messages" onClick={onClose}>✕</button>}
    </header>
  )
}

function ThreadList({ threads, onOpen, onNew, onClose }:
  { threads: Thread[]; onOpen: (id: string) => void; onNew: () => void; onClose: () => void }) {
  return (
    <>
      <PanelHead title="Messages" onClose={onClose} />
      <div className="msg-body">
        {threads.length === 0 ? (
          <p className="muted" style={{ padding: '8px 4px' }}>No messages yet. Start a conversation below.</p>
        ) : (
          <ul className="msg-list">
            {threads.map((t) => (
              <li key={t.id}>
                <button type="button" className="msg-item" onClick={() => onOpen(t.id)}>
                  <span className="msg-item-top">
                    <strong>{t.with_name}</strong>
                    <span className="msg-when">{when(t.last_at)}</span>
                  </span>
                  <span className="msg-subject">{t.subject}</span>
                  <span className="msg-preview">{t.preview}</span>
                  {t.unread > 0 && <span className="msg-dot" aria-label={`${t.unread} unread`} />}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <footer className="msg-foot">
        <button type="button" className="btn-primary" onClick={onNew}>✏️ New message</button>
      </footer>
    </>
  )
}

function NewThread({ onCancel, onCreated }: { onCancel: () => void; onCreated: (id: string) => void }) {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [pick, setPick] = useState<string>('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api<Contact[]>('/messages/contacts')
      .then((c) => { setContacts(c); if (c.length === 1) setPick(c[0].student_id) })
      .catch((e) => setErr(String(e)))
  }, [])

  const only = contacts.length === 1 ? contacts[0] : null

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!pick || !subject.trim() || !body.trim() || busy) return
    setBusy(true); setErr(null)
    try {
      const t = await api<{ id: string }>('/messages/threads', {
        method: 'POST',
        body: JSON.stringify({ student_id: pick, subject, body }),
      })
      onCreated(t.id)
    } catch (e) {
      setErr('That message could not be sent.'); setBusy(false)
      void e
    }
  }

  return (
    <>
      <PanelHead title="New message" onBack={onCancel} />
      <form className="msg-body msg-form" onSubmit={submit}>
        {err && <p role="alert" className="feedback try" style={{ padding: 12, fontSize: '.95em' }}>{err}</p>}

        {only ? (
          <p className="msg-to">To <strong>{only.contact_name}</strong> <span className="muted">· {only.contact_subtitle}</span></p>
        ) : (
          <label className="msg-field">
            <span>To</span>
            <select value={pick} onChange={(e) => setPick(e.target.value)} required>
              <option value="">Choose a person…</option>
              {contacts.map((c) => (
                <option key={c.student_id} value={c.student_id}>
                  {c.contact_name} — {c.contact_subtitle}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="msg-field">
          <span>Subject</span>
          <input type="text" value={subject} maxLength={120} required
            onChange={(e) => setSubject(e.target.value)} placeholder="What is this about?" />
        </label>

        <label className="msg-field">
          <span>Message</span>
          <textarea value={body} maxLength={4000} required rows={5}
            onChange={(e) => setBody(e.target.value)} placeholder="Write your message…" />
        </label>

        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <button type="button" className="btn-ghost" onClick={onCancel}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={busy || !pick || !subject.trim() || !body.trim()}>
            {busy ? 'Sending…' : 'Send'}
          </button>
        </div>
      </form>
    </>
  )
}

function ThreadView({ id, onBack, onChanged }: { id: string; onBack: () => void; onChanged: () => void }) {
  const [thread, setThread] = useState<Thread | null>(null)
  const [msgs, setMsgs] = useState<Message[]>([])
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const me = getSession()?.userId
  const endRef = useRef<HTMLDivElement>(null)

  const load = useCallback(async () => {
    const d = await api<{ thread: Thread; messages: Message[] }>(`/messages/threads/${id}`)
    setThread(d.thread); setMsgs(d.messages)
  }, [id])

  useEffect(() => { load().then(onChanged) }, [load, onChanged])
  useEffect(() => { endRef.current?.scrollIntoView({ block: 'end' }) }, [msgs.length])
  useEffect(() => {
    const t = setInterval(() => { load().catch(() => {}) }, POLL_MS)
    return () => clearInterval(t)
  }, [load])

  async function send(e: React.FormEvent) {
    e.preventDefault()
    if (!body.trim() || busy) return
    setBusy(true)
    try {
      await api(`/messages/threads/${id}`, { method: 'POST', body: JSON.stringify({ body }) })
      setBody('')
      await load()
      onChanged()
    } finally { setBusy(false) }
  }

  return (
    <>
      <PanelHead title={thread?.with_name ?? 'Conversation'} onBack={onBack} />
      {thread && <p className="msg-thread-sub">{thread.subject}</p>}
      <div className="msg-body msg-thread">
        {msgs.map((m) => (
          <div key={m.id} className={`bubble ${m.sender_id === me ? 'mine' : 'theirs'}`}>
            {m.sender_id !== me && <span className="bubble-who">{m.sender_name}</span>}
            <p>{m.body}</p>
            <span className="bubble-when">{when(m.at)}</span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <form className="msg-foot msg-compose" onSubmit={send}>
        <label htmlFor="msg-reply" className="visually-hidden">Write a reply</label>
        <textarea id="msg-reply" rows={2} value={body} maxLength={4000} placeholder="Write a reply…"
          onChange={(e) => setBody(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(e) } }} />
        <button type="submit" className="btn-primary" disabled={busy || !body.trim()}>Send</button>
      </form>
    </>
  )
}
