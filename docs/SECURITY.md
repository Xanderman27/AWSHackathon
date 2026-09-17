# Who the API believes

## The hole this replaced

Until 2026-09-17 the API worked out who you were by reading two headers off the request:

```
X-Role: teacher
X-User-Id: teacher-01
```

Both were chosen by the client. There was no step in which anything was proved. A request
with those two headers and no credentials of any kind returned a learner's complete support
plan — eligibility, present levels, accommodations, services, case manager, guardian names
and contact details — from the public internet:

```bash
curl -H 'X-Role: teacher' -H 'X-User-Id: teacher-01' \
  https://d1fai7rdy6j53g.cloudfront.net/api/support/students/student-01
```

Every record in the deployment is synthetic (see PRIVACY_POSTURE.md), so nothing real was
exposed. The design was still wrong, and the shape of the data it handed out — IEP documents
for children — is the shape where being wrong matters most.

`/auth/login` did exist and did check a password. It just had nothing to do with the rest of
the API: it returned a role, the browser stored it, and every later request re-asserted that
role for itself. Authentication and authorization were not connected to one another.

## What replaces it

Identity is now carried by a signed token and verified on every request.

`app/identity.py` verifies the token and returns a `Principal`. `app/auth.py` turns that
`Principal` into an `Actor` — the set of learners and classes this caller may touch. Routes
depend on the `Actor` exactly as they did before, so authorization still lives in the data
layer rather than in hidden buttons; what changed is that the `Actor` is now derived from
something the caller cannot write.

A caller cannot choose their role, cannot choose their user id, and cannot reach a record
outside the scope their own stored record gives them.

## Two issuers, one verification path

| | issuer | algorithm | when |
|---|---|---|---|
| Deployed | Amazon Cognito | RS256, verified against the pool's JWKS | a user pool is configured |
| Local | this process | HS256, per-process secret | no pool configured — a laptop, and the tests |

The local issuer is **not** a bypass. It mints and verifies real tokens, so an
unauthenticated request is refused in every mode, and the test suite exercises the same
verification code the deployment runs rather than a hole cut around it.

The two cannot be confused for one another. `_verify_cognito` accepts only RS256 and runs
only when a pool is configured; `_verify_local` accepts only HS256 and runs only when one is
not. A locally signed token presented to a Cognito-configured deployment is refused —
`test_local_and_cognito_tokens_cannot_be_swapped` is there because that particular confusion
is how a JWT layer gets downgraded back to forgeable.

## What the tests pin down

`services/api/tests/test_auth.py` asserts refusals, because refusals are the interesting
behaviour of an authorization layer:

- the exact old request, with the old headers, now gets 401
- no credentials at all gets 401
- a tampered signature, a token signed with another secret, and `alg: none` are all refused
- an expired token is refused
- a token whose groups are empty, or name a role the product does not have, is refused
- a learner with a valid token is refused another learner's plan (scope, not just role)
- a teacher id with no teacher record reaches nothing — that scope used to be the constant
  `class-4a`, which would have handed any teacher token the whole class
- the activity socket refuses an unauthenticated caller, and seats the token's holder rather
  than a `student_id` named in the query string

That last one was a second instance of the same bug: the WebSocket took the learner's id off
the query string, so a learner could sit down at an activity as one of their classmates.

## Cognito specifics

Provisioned by `scripts/provision_cognito.py`, which is safe to run repeatedly.

- **App client has no secret.** The API authorises its Cognito calls with the EC2 instance
  role, so there is no shared secret for anything to hold or leak.
- **`ALLOW_ADMIN_USER_PASSWORD_AUTH` only.** `USER_PASSWORD_AUTH` would let anyone on the
  internet attempt sign-ins against the pool directly, around our audit log. The admin flow
  requires AWS credentials, so it can only be driven by our server.
- **`custom:user_id`** carries the internal id (`student-01`) that the rest of the data is
  keyed by, because a Cognito `sub` is a fresh uuid nothing else in the product knows. It is
  immutable, and absent from the app client's `WriteAttributes`, so nobody can sign up and
  nominate themselves someone else's learner.
- **Role comes from group membership** (`cognito:groups`), set server-side at sign-up. Every
  family who signs up lands in `parent` and nothing else.
- **IAM is scoped to what the app does**: initiate auth, create a user, set a password, add
  to a group, read a user. Deliberately *not* `AdminDeleteUser` or
  `AdminUpdateUserAttributes` — this app creates and authenticates people, and nothing it
  does should be able to rewrite who someone already is.

## The password policy is deliberately loose

The pool requires 8 characters and nothing else. That is not an oversight.

The demo logins are printed on the landing page for judges to read — `sam` / `otter123`,
`rivera` / `teach123`. Their strength protects nothing, because they are published. What
protects the deployment is that the learners in it are synthetic, and what the change above
buys is that a caller must now hold *some* credential and can only reach that credential's
own scope.

**A real deployment must raise this**, and the accompanying change is the one that actually
matters: real accounts, no published credentials, and MFA for staff. The policy lives in
`ensure_pool` in `scripts/provision_cognito.py`.

## Known gaps

Honest list, so none of this reads as more finished than it is.

- **Anyone can read the synthetic data by using the published demo logins.** That is the
  intended demo behaviour, not a defect, but it does mean the deployment is not private.
- **No rate limiting on `/auth/login`.** Cognito applies its own throttling to
  `AdminInitiateAuth`, which is the only thing standing between the endpoint and a
  brute-force attempt. Our own limiter would be better.
- **Tokens live in `localStorage`**, so a cross-site scripting bug would expose them. The
  app renders no user-supplied HTML today, but that is a property worth keeping deliberately
  rather than by luck.
- **The local issuer's tokens do not survive a restart** unless `DORI_DEV_AUTH_SECRET` is
  set. That is fine for a laptop and for tests, and it is why it must never be the mode a
  deployment runs in: `auth_settings().configured` decides, and it is driven by Parameter
  Store rather than by a flag someone could set by accident.
- **No refresh on the local issuer.** Its tokens simply last twelve hours.
