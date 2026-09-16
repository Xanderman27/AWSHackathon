// Thin API client. Role and user come from the synthetic session (PRD FR-01); Cognito later.

export type Role = 'student' | 'teacher' | 'parent'

export interface Session {
  role: Role
  userId: string
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

export interface Choice { id: string; text: string }
export interface Item {
  id: string; prompt: string; image_alt?: string | null; choices: Choice[]; hint: string
  passage?: string | null; passage_read_aloud_allowed: boolean
}
export interface NextItem { attempt_id: string; position: number; total: number; item: Item | null; completed: boolean; summary?: string | null }
export interface AnswerOut { correct: boolean; feedback: string; next: NextItem }
export interface Skill { id: string; name: string; child_name: string; subject: string; standard_id: string }
