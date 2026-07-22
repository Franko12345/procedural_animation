# Domain docs — how agents consume them

Rules for engineering skills reading this repo's docs before touching code.

## Before exploring, read these

- [`CONTEXT.md`](../../CONTEXT.md) at the repo root — canonical
  vocabulary.
- [`docs/adr/`](../adr/README.md) — ADRs touching the area about to
  change.
- [`docs/concepts/`](../concepts/README.md) — one-file-per-concept
  descriptions; each concept links out to related concepts and ADRs.

`CONTEXT-MAP.md` does not exist — this is a **single-context repo**.
Everything lives at the root. If a `CONTEXT-MAP.md` ever appears, the
map takes precedence and points at per-context `CONTEXT.md`s.

If a file listed above doesn't exist yet, proceed silently. Don't flag
absence up-front; the domain-modeling skill creates files lazily when a
term or decision actually gets resolved.

## File structure

```
/
├── CONTEXT.md                       ← canonical vocabulary
├── CLAUDE.md                        ← working brief for Claude
├── docs/
│   ├── README.md
│   ├── adr/                         ← Architecture Decision Records
│   │   ├── README.md
│   │   └── NNNN-slug.md
│   ├── concepts/                    ← concept docs
│   │   ├── README.md
│   │   └── <slug>.md
│   └── agents/                      ← operational conventions
└── lagarto/                         ← code
```

## Use the glossary's vocabulary

When your output names a domain concept (issue title, refactor proposal,
hypothesis, test name), use the term defined in
[`CONTEXT.md`](../../CONTEXT.md). Don't drift to synonyms listed under
`_Avoid_`.

If the concept isn't in the glossary yet, that's a signal — either
you're inventing language the project doesn't use (reconsider) or
there's a real gap (add the term in the same commit as the code that
introduces it).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly
rather than silently overriding:

> _Contradicts [ADR-0007](../adr/0007-cosmetic-skeleton-for-tail.md) —
> but worth reopening because…_

Then either revise the output or open a new ADR that supersedes the old
one. Do not fork the truth in silence.
