// Thin API client. Role and user come from the synthetic session (PRD FR-01); Cognito later.

export type Role = 'student' | 'teacher' | 'parent'

export interface Session {
  role: Role
  userId: string
  name?: string
}

const KEY = 'alp.session'

export function getSession(): Session | null {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as Session) : null
  } catch {
    return null
  }
}

export function setSession(s: Session | null) {
  try {
    if (s) localStorage.setItem(KEY, JSON.stringify(s))
    else localStorage.removeItem(KEY)
  } catch {
    /* storage unavailable; session lives in memory only */
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const s = getSession()
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(init.headers as Record<string, string>) }
  if (s) {
    headers['X-Role'] = s.role
    headers['X-User-Id'] = s.userId
  }
  const res = await fetch(`/api${path}`, { ...init, headers })
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.json() as Promise<T>
}

export async function login(username: string, password: string): Promise<Session> {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) throw new Error(res.status === 401 ? 'bad-credentials' : `${res.status}`)
  const d = (await res.json()) as { role: Role; user_id: string; display_name: string }
  const s: Session = { role: d.role, userId: d.user_id, name: d.display_name }
  setSession(s)
  return s
}

export interface SignUpResult extends Session { class_name: string; needs_child: boolean }

/** Create a family account from a class code, and sign them straight in. */
export async function signUp(input: { name: string; email: string; password: string; classCode: string }): Promise<SignUpResult> {
  const res = await fetch('/api/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: input.name, email: input.email, password: input.password, class_code: input.classCode,
    }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => null)
    throw new Error(detail?.detail ?? 'We could not create that account. Please try again.')
  }
  const d = (await res.json()) as { role: Role; user_id: string; display_name: string; class_name: string; needs_child: boolean }
  const session: Session = { role: d.role, userId: d.user_id, name: d.display_name }
  setSession(session)
  return { ...session, class_name: d.class_name, needs_child: d.needs_child }
}

/** Fetch bytes rather than JSON, carrying the same role headers every other call does. */
export async function apiBlob(path: string): Promise<Blob> {
  const session = getSession()
  const headers: Record<string, string> = {}
  if (session) {
    headers['X-Role'] = session.role
    headers['X-User-Id'] = session.userId
  }
  const res = await fetch(`/api${path}`, { headers })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.blob()
}

export interface Choice { id: string; text: string }
export interface Item {
  id: string; prompt: string; image_alt?: string | null; choices: Choice[]; hint: string
  passage?: string | null; passage_read_aloud_allowed: boolean
}
export interface NextItem { attempt_id: string; position: number; total: number; item: Item | null; completed: boolean; summary?: string | null }
export interface AnswerOut { correct: boolean; feedback: string; next: NextItem }
export interface Skill { id: string; name: string; child_name: string; subject: string; standard_id: string }
