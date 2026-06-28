# Example Scenario — Ambiguous

**Requirement:** *"Make the service more scalable."*

Ambiguous requirements are the most dangerous: they invite unbounded work and
building the wrong thing. The method is to **convert vagueness into measurable
tasks before writing any code.**

## 1. The prototype's response

Run it:

```powershell
python -m ai_eng "Make the service more scalable"
```

The analyzer classifies this as **ambiguous** (no concrete deliverable verb plus
the vague signal *more scalable*) and emits clarifying questions, each paired with
a documented default assumption so progress is not blocked:

| Clarifying question | Why it matters | Default assumption (to confirm) |
| --- | --- | --- |
| What scale target (RPS, total URLs, read/write ratio)? | Scalability is unbounded without a target | 1k RPS reads, 50 RPS writes, >95% reads |
| What's the baseline and desired delta? | "More" needs a baseline to be measurable | Current single instance; target horizontal scale to N |

The pipeline records these as **assumptions** and adds a **limitation**: *ambiguous
requirements proceed on documented assumptions that must be confirmed by a
stakeholder before shipping.* (See the `limitations` section of the generated
summary.)

## 2. From interpretation to structured tasks

Once the engineer fixes an interpretation — *"support horizontal scaling for a
read-heavy load without changing the API"* — it becomes a concrete plan:

| ID | Task | Depends on | AI assist | Validation focus |
| --- | --- | --- | --- | --- |
| S1 | Make the service stateless (externalize cache) | — | medium | No per-instance state on the hot path |
| S2 | Swap in-process LRU for Redis behind the same interface | S1 | high | `get/set/invalidate` parity; cache coherency across instances |
| S3 | Move click capture to an async queue | S1 | high | Redirect latency unaffected; no lost clicks |
| S4 | Add a load test proving the target RPS | S2,S3 | medium | Meets agreed RPS at target p99 |
| S5 | Document the deployment topology | S4 | low | Ops can reproduce |

This is exactly the kind of plan the decomposer would encode as a
`scalability_tasks()` template in `knowledge.py`.

## 3. AI-assisted execution (illustrative)

**Task S2 prompt:**

```
Implement a RedisCache that satisfies the existing cache interface
(get(key)->str|None, set(key,value), invalidate(key), clear, __len__) so it is a
drop-in replacement for LRUCache in ShortenerService. Connection settings come
from env vars; fail closed (treat Redis errors as a cache miss, never crash a
redirect). Provide tests using a fake/fakeredis client.
```

**Engineer review focus:**
- The redirect must still succeed if Redis is down (degrade to DB read).
- No secrets in code; connection string from the environment.
- Behaviour parity with `LRUCache` proven by reusing its test cases.

## 4. Validation

- Reuse the existing cache contract tests against the new implementation to prove
  parity (`get/set/invalidate`, eviction semantics where applicable).
- A load test asserts the **agreed** RPS/p99 numbers — the ambiguity is only
  "resolved" when there is a measurable pass/fail.
- Confirm the public API responses are unchanged (contract tests stay green).

## 5. Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Building the wrong thing from a vague ask | Clarify first; document assumptions; require stakeholder confirmation |
| Premature optimization with no target | No work accepted until a measurable target exists (Task S4 gates it) |
| New infra (Redis/queue) becomes a SPOF | Fail-closed cache, idempotent click capture, documented topology |
