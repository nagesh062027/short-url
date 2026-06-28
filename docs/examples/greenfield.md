# Example Scenario — Greenfield

**Requirement:** *"Add user authentication to the URL shortener so that links are
owned by accounts."*

A greenfield scenario adds a brand-new capability. This walkthrough shows how the
engineer drives the AI-assisted loop end to end.

## 1. Requirement understanding

Run the analyzer's lens over it:

- **Intent:** introduce accounts and tie created URLs to an owner.
- **Functional needs:** register/login, issue a credential, associate `urls.owner_id`,
  authorize analytics to the owner.
- **Non-functional:** credentials stored safely (hashing), auth must not slow the
  public redirect path.
- **Ambiguities (with assumptions):**
  - *Session vs token auth?* → assume stateless bearer tokens (JWT) for API use.
  - *Is redirect public or owner-only?* → assume redirects stay public; only
    management endpoints require auth.

## 2. Task breakdown (engineer-led)

| ID | Task | Depends on | AI assist | Validation focus |
| --- | --- | --- | --- | --- |
| A1 | `users` table + password hashing | — | medium | Hash never reversible; unique email |
| A2 | Register/login endpoints issuing a token | A1 | high | 201/200 happy path, 401 on bad creds |
| A3 | Auth dependency (verify bearer token) | A2 | medium | Rejects missing/expired tokens |
| A4 | Add `owner_id` to `urls`; scope create/list/analytics | A3 | high | Owner isolation, no cross-account leakage |
| A5 | Tests (unit + integration) | A4 | medium | Negative auth paths covered |
| A6 | Docs update | A5 | low | Auth flow documented |

This mirrors how the prototype's decomposer would extend `knowledge.py` with an
`auth_tasks()` template.

## 3. AI-assisted execution

**Task A1 prompt (engineer-authored):**

```
Task A1: Add a users table and password hashing.
Constraints: use a vetted KDF (bcrypt/argon2), never store plaintext, parameterize
all SQL, keep it behind the existing Repository pattern. Provide unit tests for
hash/verify and a uniqueness constraint on email.
```

**Engineer review of the AI draft (what to scrutinize):**
- Reject any draft that rolls its own crypto or uses fast hashes (`md5`/`sha1`).
- Confirm the work factor is configurable.
- Ensure timing-safe verification.

**Task A4 prompt:**

```
Task A4: Associate each created URL with the authenticated owner_id and scope
list/analytics to the owner. Keep the public redirect endpoint unauthenticated.
Add a migration that backfills existing rows with a NULL owner.
```

## 4. Output validation

Run the gate on the new artifacts:

```powershell
python -m ai_eng "Add user authentication to the URL shortener" --run-tests
pytest examples/url_shortener/tests -q
```

Acceptance criteria checked:

- `security_scan` confirms no hardcoded secrets and no risky constructs.
- New tests assert: `401` without a token, owner A cannot list owner B's URLs,
  passwords never appear in any response, redirect still works unauthenticated.
- Coverage includes the negative auth paths (the part most likely to be wrong).

## 5. Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| AI suggests insecure hashing | Engineer mandates argon2/bcrypt; gate flags weak patterns |
| Token handling bugs leak access | Dedicated tests for expiry/forgery; short token lifetime |
| Auth added to the redirect path slows it | Keep redirect public by design decision |
