// Games are free play: no score sent to the teacher, no time limit, playable any time.
// The line-up is a placeholder until the team picks the real set.

const GAMES = [
  { id: 'pattern-path', name: 'Pattern Path', glyph: '🧩', tone: 'mint', blurb: 'Spot what comes next in a row of shapes and colours.', skill: 'Patterns' },
  { id: 'memory-meadow', name: 'Memory Meadow', glyph: '🌼', tone: 'sky', blurb: 'Flip the cards and remember where things are hiding.', skill: 'Working memory' },
  { id: 'sort-it-out', name: 'Sort It Out', glyph: '🧺', tone: 'cream', blurb: 'Put things into groups and say why they belong together.', skill: 'Sorting' },
  { id: 'shape-shift', name: 'Shape Shift', glyph: '🔷', tone: 'rose', blurb: 'Turn and flip shapes to see how they fit.', skill: 'Space and shape' },
]

export default function StudentGames() {
  return (
    <div className="stack">
      <h2 className="section-title">Play a game</h2>
      <p className="muted helper" style={{ marginTop: -6 }}>
        Games are just for fun and thinking practice. Play any time, as long as you like. Nothing here is graded.
      </p>
      <div className="game-grid">
        {GAMES.map((g, i) => (
          <div key={g.id} className={`game-card pop ${g.tone}`} style={{ animationDelay: `${i * 80}ms` }}>
            <span className="game-glyph floaty" aria-hidden="true" style={{ animationDelay: `${i * 0.25}s` }}>{g.glyph}</span>
            <strong>{g.name}</strong>
            <span className="game-blurb">{g.blurb}</span>
            <span className="row between" style={{ width: '100%', marginTop: 'auto' }}>
              <span className="chip">{g.skill}</span>
              <button type="button" disabled>Coming soon</button>
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
