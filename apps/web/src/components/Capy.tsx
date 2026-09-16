// Capy the capybara — Dori's guide. Soft "almost 3D" rendering: gradient fills set as
// attributes (so the high-contrast CSS in styles.css can still override them), a sheen
// highlight, and a gentle grass-eating idle. Moods: happy (eats grass), cheer, think.
// 'wave' is accepted for compatibility with older callers and renders as happy.

type Mood = 'happy' | 'cheer' | 'wave' | 'think'

export default function Capy({ mood = 'happy', size = 72, float = false, className = '' }:
  { mood?: Mood; size?: number; float?: boolean; className?: string }) {
  const m: Exclude<Mood, 'wave'> = mood === 'wave' ? 'happy' : mood
  return (
    <svg
      className={`capy-svg ${float ? 'floaty' : ''} ${className}`}
      viewBox="0 0 220 210" width={size} height={Math.round(size * 0.955)}
      role="img" aria-label="Capy the capybara"
    >
      <defs>
        <linearGradient id="cpgBody" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#cd9a6b" /><stop offset="1" stopColor="#9b6d42" />
        </linearGradient>
        <linearGradient id="cpgHead" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#d8a97c" /><stop offset="1" stopColor="#aa794d" />
        </linearGradient>
        <linearGradient id="cpgMuzzle" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#eec9a2" /><stop offset="1" stopColor="#d0a273" />
        </linearGradient>
        <linearGradient id="cpgFoot" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#b0805a" /><stop offset="1" stopColor="#8a5f38" />
        </linearGradient>
        <linearGradient id="cpgLeaf" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#7ee49a" /><stop offset="1" stopColor="#3fae5f" />
        </linearGradient>
      </defs>

      <ellipse className="cp-shadow" cx="110" cy="196" rx="86" ry="12" fill="#e3f0da" />
      <ellipse className="cp-fur" cx="110" cy="152" rx="80" ry="48" fill="url(#cpgBody)" strokeWidth="5" />
      <ellipse className="cp-sheen" cx="86" cy="132" rx="34" ry="15" fill="#ffffff" opacity="0.16" />
      <rect className="cp-foot" x="76" y="184" width="26" height="16" rx="8" fill="url(#cpgFoot)" strokeWidth="4" />
      <rect className="cp-foot" x="118" y="184" width="26" height="16" rx="8" fill="url(#cpgFoot)" strokeWidth="4" />
      <g className="cp-ear">
        <circle className="cp-fur" cx="64" cy="26" r="15" fill="url(#cpgHead)" strokeWidth="5" />
        <circle className="cp-earin" cx="64" cy="27" r="6" fill="#7c5433" />
      </g>
      <g>
        <circle className="cp-fur" cx="156" cy="26" r="15" fill="url(#cpgHead)" strokeWidth="5" />
        <circle className="cp-earin" cx="156" cy="27" r="6" fill="#7c5433" />
      </g>
      <rect className="cp-head" x="46" y="18" width="128" height="110" rx="46" fill="url(#cpgHead)" strokeWidth="5" />
      <ellipse className="cp-sheen" cx="84" cy="42" rx="34" ry="15" fill="#ffffff" opacity="0.26" />
      <g className={m === 'happy' ? 'cp-mouthg' : ''}>
        <path className="cp-muzzle" d="M62 92 h96 a30 30 0 0 1 -30 34 h-36 a30 30 0 0 1 -30 -34 z" fill="url(#cpgMuzzle)" />
        <ellipse className="cp-nose" cx="100" cy="104" rx="4.6" ry="6" fill="#6d4a2a" />
        <ellipse className="cp-nose" cx="120" cy="104" rx="4.6" ry="6" fill="#6d4a2a" />
        {m === 'cheer'
          ? <path className="cp-mouthfill" d="M98 116 q12 14 24 0 z" fill="#6d4a2a" />
          : m === 'think'
            ? <path className="cp-stroke" d="M103 119 q8 3 15 0" strokeWidth="4" />
            : <path className="cp-stroke" d="M102 118 q8 7 16 0" strokeWidth="4" />}
      </g>

      {m === 'cheer' ? (
        <g>
          <path className="cp-eyearc" d="M76 66 q8 -9 16 0" strokeWidth="5" />
          <path className="cp-eyearc" d="M128 66 q8 -9 16 0" strokeWidth="5" />
        </g>
      ) : (
        <g className="cp-eyes">
          <circle className="cp-eye" cx="84" cy="66" r="8.5" fill="#33241a" />
          <circle className="cp-hi" cx="87" cy="63" r="2.8" fill="#ffffff" />
          <circle className="cp-eye" cx="136" cy="66" r="8.5" fill="#33241a" />
          <circle className="cp-hi" cx="139" cy="63" r="2.8" fill="#ffffff" />
        </g>
      )}

      <ellipse className="cp-blush" cx="66" cy="88" rx="9" ry="5.5" fill="#ef9f9f" />
      <ellipse className="cp-blush" cx="154" cy="88" rx="9" ry="5.5" fill="#ef9f9f" />

      {(m === 'happy' || m === 'think') && (
        <g className={m === 'happy' ? 'cp-grassg' : ''}>
          <path className="cp-grass" d="M110 121 q-4 16 -14 24" strokeWidth="5" />
          <path className="cp-grassleaf" d="M96 145 q-8 -2 -10 -9 q9 -2 12 4 z" fill="url(#cpgLeaf)" />
        </g>
      )}
    </svg>
  )
}

/** Just the face, cropped tight — for spots that want the mascot small. */
export function CapyMark({ size = 40, className = '' }: { size?: number; className?: string }) {
  return (
    <svg className={`capy-svg ${className}`} viewBox="42 10 136 124" width={size}
      height={Math.round(size * (124 / 136))} aria-hidden="true" style={{ display: 'block' }}>
      <circle className="cp-fur" cx="66" cy="30" r="14" fill="#c08b5c" strokeWidth="5" />
      <circle className="cp-fur" cx="154" cy="30" r="14" fill="#c08b5c" strokeWidth="5" />
      <rect className="cp-head" x="48" y="26" width="124" height="104" rx="44" fill="#c99a6b" strokeWidth="6" />
      <circle className="cp-eye" cx="86" cy="72" r="9" fill="#33241a" />
      <circle className="cp-eye" cx="134" cy="72" r="9" fill="#33241a" />
      <ellipse className="cp-nose" cx="98" cy="102" rx="5" ry="6.5" fill="#6d4a2a" />
      <ellipse className="cp-nose" cx="122" cy="102" rx="5" ry="6.5" fill="#6d4a2a" />
    </svg>
  )
}
