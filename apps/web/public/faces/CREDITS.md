# Student photos

Twelve portraits from [Pexels](https://www.pexels.com), used under the
[Pexels licence](https://www.pexels.com/license/) (free to use, no attribution required;
credited here anyway).

The files served from this folder are **built**, not downloaded. The originals live in
`data/faces-src/` and are never modified; `scripts/build_yearbook_photos.py` segments each
child out of their original background, places them on a shared mottled-grey studio backdrop
at a common head size, and applies one grade to all twelve, so the class list reads as a
single set of school photos rather than twelve unrelated stock pictures.

| Seeded learner | Pexels photo |
|---|---|
| student-01 (Sam)   | https://www.pexels.com/photo/8090247/  |
| student-02 (Ava)   | https://www.pexels.com/photo/38001098/ |
| student-03 (Leo)   | https://www.pexels.com/photo/7355313/  |
| student-04 (Mia)   | https://www.pexels.com/photo/8090248/  |
| student-05 (Noah)  | https://www.pexels.com/photo/6606240/  |
| student-06 (Zoe)   | https://www.pexels.com/photo/6182804/  |
| student-07 (Eli)   | https://www.pexels.com/photo/7114681/  |
| student-08 (Ivy)   | https://www.pexels.com/photo/12159295/ |
| student-09 (Kai)   | https://www.pexels.com/photo/8471800/  |
| student-10 (Ruby)  | https://www.pexels.com/photo/37544972/ |
| student-11 (Owen)  | https://www.pexels.com/photo/12270234/ |
| student-12 (Lily)  | https://www.pexels.com/photo/7114679/  |

## Before this ships anywhere real

These are photographs of real children, and the app places them beside mastery bands,
"needs more evidence", and goal markers — that is, it depicts identifiable children as
students receiving special-education services. The Pexels licence does not permit using
identifiable people in a way that is defamatory or implies a sensitive attribute, so this
set is suitable for an internal demo and not for a public launch, a screenshot in a deck,
or anything a family might see.

Compositing them onto a shared backdrop does not change this. If anything it makes them
look more like official school records, which is the impression to be most careful about.

Replace with commissioned illustration, consented photography, or the illustrated fallback
in `apps/web/src/components/Avatar.tsx` before any external use.
