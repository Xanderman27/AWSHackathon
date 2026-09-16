// Hand-drawn SVG badges for the practice path — real little illustrations, not emoji.
// All decorative: every icon is aria-hidden and sized by its parent.

interface P { size?: number; className?: string }
const S = ({ size = 48, className = '', children }: P & { children: React.ReactNode }) => (
  <svg viewBox="0 0 48 48" width={size} height={size} className={className} aria-hidden="true">{children}</svg>
)

export const BookIcon = (p: P) => (
  <S {...p}>
    <path d="M24 11 C18 6 10 6 5 8 V37 C10 35 18 36 24 41 Z" fill="#4aa8ff" stroke="#1d6fbe" strokeWidth="2" strokeLinejoin="round" />
    <path d="M24 11 C30 6 38 6 43 8 V37 C38 35 30 36 24 41 Z" fill="#8ccbff" stroke="#1d6fbe" strokeWidth="2" strokeLinejoin="round" />
    <path d="M10 14 c4-1 8 0 10 2 M10 20 c4-1 8 0 10 2 M10 26 c4-1 8 0 10 2" fill="none" stroke="#eaf5ff" strokeWidth="2" strokeLinecap="round" />
  </S>
)

export const PencilIcon = (p: P) => (
  <S {...p}>
    <g transform="rotate(45 24 24)">
      <rect x="19" y="4" width="10" height="7" rx="2" fill="#ff8fab" stroke="#d6336c" strokeWidth="2" />
      <rect x="19" y="11" width="10" height="22" fill="#ffd43b" stroke="#e8a500" strokeWidth="2" />
      <path d="M19 33 h10 l-5 10 z" fill="#f4e3b2" stroke="#c9a45c" strokeWidth="2" strokeLinejoin="round" />
      <path d="M22.5 37.5 L24 41 L25.5 37.5 Z" fill="#3f3222" />
    </g>
  </S>
)

export const FlaskIcon = (p: P) => (
  <S {...p}>
    <path d="M20 5 h8 v11 l10 19 a4.5 4.5 0 0 1 -4 6.5 H14 a4.5 4.5 0 0 1 -4 -6.5 l10 -19 Z" fill="#e6d9ff" stroke="#7048c9" strokeWidth="2.2" strokeLinejoin="round" />
    <path d="M15.5 27 h17 l5.5 8 a4.5 4.5 0 0 1 -4 6.5 H14 a4.5 4.5 0 0 1 -4 -6.5 Z" fill="#57cf78" stroke="#7048c9" strokeWidth="2.2" strokeLinejoin="round" />
    <circle cx="22" cy="33" r="2" fill="#bff2cc" />
    <circle cx="28" cy="37" r="1.5" fill="#bff2cc" />
    <rect x="18.5" y="3.5" width="11" height="3.5" rx="1.6" fill="#7048c9" />
  </S>
)

export const RocketIcon = (p: P) => (
  <S {...p}>
    <path d="M24 3 C30 9 32 17 32 24 L24 33 16 24 C16 17 18 9 24 3 Z" fill="#ff6b6b" stroke="#c92a2a" strokeWidth="2.2" strokeLinejoin="round" />
    <circle cx="24" cy="17" r="4.5" fill="#a5d8ff" stroke="#1971c2" strokeWidth="2" />
    <path d="M16 24 L9 32 L17 31 Z M32 24 L39 32 L31 31 Z" fill="#4aa8ff" stroke="#1971c2" strokeWidth="2" strokeLinejoin="round" />
    <path d="M21 34 C21 39 24 44 24 44 C24 44 27 39 27 34 Z" fill="#ffb020" stroke="#e8590c" strokeWidth="2" strokeLinejoin="round" />
  </S>
)

export const ShapesIcon = (p: P) => (
  <S {...p}>
    <rect x="6" y="22" width="17" height="17" rx="3" fill="#4aa8ff" stroke="#1971c2" strokeWidth="2.2" />
    <circle cx="33" cy="31" r="9.5" fill="#ff8fab" stroke="#d6336c" strokeWidth="2.2" />
    <path d="M24 4 L34 19 H14 Z" fill="#ffb020" stroke="#e8590c" strokeWidth="2.2" strokeLinejoin="round" />
  </S>
)

export const AbacusIcon = (p: P) => (
  <S {...p}>
    <rect x="7" y="7" width="34" height="34" rx="5" fill="#f4e3b2" stroke="#b3814f" strokeWidth="2.4" />
    <path d="M7 17 h34 M7 26 h34 M7 35 h34" stroke="#b3814f" strokeWidth="2" />
    <circle cx="15" cy="17" r="3.2" fill="#ff6b6b" /><circle cx="23" cy="17" r="3.2" fill="#ff6b6b" />
    <circle cx="30" cy="26" r="3.2" fill="#4aa8ff" /><circle cx="38" cy="26" r="3.2" fill="#4aa8ff" />
    <circle cx="13" cy="35" r="3.2" fill="#57cf78" /><circle cx="27" cy="35" r="3.2" fill="#57cf78" />
  </S>
)

export const PirateFlagIcon = (p: P) => (
  <S {...p}>
    <rect x="9" y="4" width="3.4" height="40" rx="1.6" fill="#8a5a2b" stroke="#5e3b17" strokeWidth="1.6" />
    <path d="M12.4 7 C21 3.5 29 10 40 6.5 V24 C29 27.5 21 21 12.4 24.5 Z" fill="#2b2f36" stroke="#14161a" strokeWidth="2" strokeLinejoin="round" />
    <circle cx="25" cy="13.5" r="4.2" fill="#fff" />
    <circle cx="23.4" cy="13" r="1" fill="#2b2f36" /><circle cx="26.6" cy="13" r="1" fill="#2b2f36" />
    <path d="M23.6 16 h2.8" stroke="#2b2f36" strokeWidth="1.2" strokeLinecap="round" />
    <path d="M19 20.5 l12 -1.5 M19 19 l12 1.5" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
  </S>
)

export const CastleIcon = (p: P) => (
  <S {...p}>
    <path d="M9 42 V16 h5 v-5 h5 v5 h5 v-5 h5 v5 h5 v-5 h5 v5 h0 v26 Z" fill="#cfc4b2" stroke="#8d7f66" strokeWidth="2.2" strokeLinejoin="round" />
    <path d="M20 42 v-10 a4 4 0 0 1 8 0 v10 Z" fill="#6b5a41" />
    <rect x="13" y="21" width="4" height="6" rx="1.6" fill="#6b5a41" />
    <rect x="31" y="21" width="4" height="6" rx="1.6" fill="#6b5a41" />
    <path d="M39 11 V4 l7 2.4 -7 2.4" fill="#ff6b6b" stroke="#c92a2a" strokeWidth="1.6" strokeLinejoin="round" />
  </S>
)

export const GlobeIcon = (p: P) => (
  <S {...p}>
    <circle cx="24" cy="24" r="19" fill="#4aa8ff" stroke="#1971c2" strokeWidth="2.4" />
    <path d="M14 12 c5 -2 9 1 8 5 c-1 4 -7 3 -8 7 c-1 3 2 6 6 6 c3 0 4 3 3 6" fill="none" stroke="#57cf78" strokeWidth="6" strokeLinecap="round" />
    <path d="M33 10 c3 3 3 7 0 9 c-2 1 -2 4 0 5" fill="none" stroke="#57cf78" strokeWidth="5" strokeLinecap="round" />
    <ellipse cx="24" cy="24" rx="19" ry="19" fill="none" stroke="#1971c2" strokeWidth="2.4" />
  </S>
)

export const TreasureMapIcon = (p: P) => (
  <S {...p}>
    <path d="M7 11 q8.5 -5 17 0 q8.5 5 17 0 v26 q-8.5 5 -17 0 q-8.5 -5 -17 0 Z" fill="#f4e3b2" stroke="#c9a45c" strokeWidth="2.2" strokeLinejoin="round" />
    <path d="M12 30 q6 -8 12 -4 q6 4 10 -6" fill="none" stroke="#b3814f" strokeWidth="2" strokeDasharray="3 3" strokeLinecap="round" />
    <path d="M31 15 l5 5 M36 15 l-5 5" stroke="#d6336c" strokeWidth="3" strokeLinecap="round" />
    <circle cx="14" cy="33" r="2" fill="#57cf78" stroke="#2b8a3e" strokeWidth="1.2" />
  </S>
)
