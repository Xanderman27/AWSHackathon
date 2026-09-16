# What each role can see about other people's children

The PRD's default is strict: a parent sees their own child and nothing else, and activity
cohorts are "temporary, activity-specific, revisable, and hidden from parents and other
students" (§12, and principle 7, "No permanent tracks").

Two product decisions deliberately relax that. They are recorded here because they are
choices, not oversights, and because they are the first things a district privacy review
will ask about.

## 1. A parent sees their child's teammates, with names and faces

**What ships.** On the family dashboard, "Who Sam works with" lists each published team
activity with the first name and portrait of every teammate.

**Why.** A family that only sees the app between meetings has no idea who their child spends
the day with. Names and faces make the group real and give a parent something to ask their
child about.

**What is still withheld.** `_peer()` in `routers/parent.py` is deliberately narrower than
`_safe()`: a teammate is reduced to `id`, `display_name`, `photo`, `avatar`. No grade, no
class, no goal marker, and no progress of any kind. The teacher's *reason* for grouping those
learners never leaves the teacher — that is the part PRD §12 most cares about, and
`test_a_parent_sees_a_teammates_face_and_nothing_else_about_them` pins it.

**What a real district needs first.** Per-child photo and directory-information consent. In
the United States a child's name and likeness shown to another family is directory
information under FERPA, which families may opt out of. There is no opt-out in the product
yet. That is the gap to close before this is anything but a demo.

## 2. A teacher's classroom photo goes to every family in the class

**What ships.** A teacher uploads a photo and a sentence; every family in that class sees it
on their dashboard. Students never see it, and it is attached to no learner's record.

**Why.** It is the cheapest possible bridge between a teacher and twelve families, and the
alternative considered — tagging individual learners so only their parents see a photo — makes
the teacher do roster work before they can share anything.

**The consequence, plainly.** A photo containing one child is visible to every other family in
the class. That is how ClassDojo and Seesaw work too, and like them it depends on consent
collected outside the product.

**What the code does enforce.** Only a teacher may upload, and only to their own class. A
parent may only list photos for a class one of their linked children is in. The image bytes
are served through an authorised route (`GET /class-photos/{id}/file`), not a public static
folder, so a leaked or guessed filename is not a leaked photo; the same check gates the
listing and the bytes, and an unauthorised request gets `404`, not `403`, so it does not
confirm the photo exists. `tests/test_class_photos.py` covers each of these.

**Not yet built.** Per-child consent flags, an opt-out that removes a child from photos, a
parent-side report button, retention limits, and EXIF stripping (an uploaded photo may carry
GPS coordinates; the demo stores the file as received).

## Related

`apps/web/public/faces/CREDITS.md` covers the seeded learner portraits, which are stock
photographs of real children and carry their own licence limits.
