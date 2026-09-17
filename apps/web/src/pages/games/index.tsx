// Route entry for every collaborative activity. The path carries the game id, so adding a
// game is one line here plus one module on the server.

import { useParams } from 'react-router-dom'
import BeatTogether from './BeatTogether'
import CheckersCorner from './CheckersCorner'
import FractionStrips from './FractionStrips'
import GlobeTrotters from './GlobeTrotters'
import MemoryMeadow from './MemoryMeadow'
import ShapeShift from './ShapeShift'
import SortItOut from './SortItOut'
import StoryDetectives from './StoryDetectives'

const SCREENS: Record<string, () => React.JSX.Element> = {
  'beat-together': BeatTogether,
  'fraction-strips': FractionStrips,
  'story-detectives': StoryDetectives,
  'memory-meadow': MemoryMeadow,
  'sort-it-out': SortItOut,
  'shape-shift': ShapeShift,
  'checkers': CheckersCorner,
  'globe-trotters': GlobeTrotters,
}

export default function GameRoute() {
  const { gameId = '' } = useParams()
  const Screen = SCREENS[gameId]
  if (!Screen) {
    return (
      <div className="card group-loading" role="alert">
        <span aria-hidden="true">💡</span>
        <div><h3>This activity cannot open</h3><p className="muted">That game is not available.</p></div>
      </div>
    )
  }
  return <Screen />
}
