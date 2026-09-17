// The one tab on this dashboard aimed at families rather than at the teacher's own planning.
// Two ways to reach home live here, built in parallel and kept side by side on purpose:
// a short note to one learner's guardians, and the class blog, whose posts can go to every
// family or to just one. Consolidating them is a product decision, not a merge decision.

import FamilyUpdateComposer from '../components/FamilyUpdateComposer'
import ClassPhotoManager from '../components/ClassPhotoManager'

export default function TeacherUpdates() {
  return (
    <div className="stack">
      <FamilyUpdateComposer />
      <ClassPhotoManager />
    </div>
  )
}
