# ADR 001: Architecture Decision Records

- **Status:** Accepted
- **Date:** 2026-08-21
- **Deciders:** Engineering team

## Context

The BeautyRec recommendation system makes architectural choices that are
expensive to reverse: the hybrid algorithm design, technology stack, database
selection, and model serving strategy. These decisions must be recorded so
future contributors understand not just *what* was chosen but *why*, and what
alternatives were rejected.

## Decision

We adopt Architecture Decision Records (ADRs) as the canonical mechanism for
documenting significant architectural decisions. Each ADR:

1. Lives in `docs/adr/` with a sequential number and short kebab-case title.
2. Follows the template below.
3. Is immutable once accepted; superseding decisions create a new ADR that
   links back to the one it replaces.

### ADR Template

```markdown
# ADR NNN: Title

- **Status:** Proposed | Accepted | Superseded by ADR MMM
- **Date:** YYYY-MM-DD
- **Deciders:** names/roles

## Context

What forces are in play — technical, organizational, product. What problem
are we solving and what constraints apply?

## Decision

The choice we make, stated in active present tense ("We will use X").

## Alternatives Considered

For each alternative: a short description and why it was rejected.

## Consequences

Positive and negative outcomes, plus follow-up work this decision creates.
```

## Alternatives Considered

- **Wiki pages** — drift quickly, no review trail, hard to link from code.
- **Decision log in a spreadsheet** — no versioning, no code review process.
- **Comments in code only** — invisible to non-engineers, scattered.

## Consequences

- Every significant decision gets a durable, reviewable record in-repo.
- New joiners can reconstruct the reasoning behind the current architecture.
- Slight overhead per decision; mitigated by keeping ADRs short and focused.
