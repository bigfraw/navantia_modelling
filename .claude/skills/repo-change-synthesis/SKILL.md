---
name: repo-change-synthesis
description: Synthesise the relevant changes made to the navantia_modelling repo since the last synthesis, and distil them into updates for the standing documents (CLAUDE.md, the vibration→jitter interface note, the roadmap) so the code "workshop" and the derivation "brain" don't drift apart. Use this whenever the user asks to synthesise/digest/summarise repo changes, sync the docs, update CLAUDE.md or the interface note, catch up the derivation docs, or "what changed" — and proactively at the end of a working session in this repo or before the user switches back to derivation/spec work. Trigger even if the user doesn't say the word "skill": any request to reconcile code changes with the standing docs belongs here.
---

# Repo Change Synthesis

Keep the **workshop** and the **brain** in sync.

- **Workshop** = this repo (`navantia_modelling`). Code, runs, tests, commits.
- **Brain** = the standing documents that hold the physics reasoning, interface
  boundaries, and design-gate history.

Work happens in the workshop; the brain is where it gets *understood*. If the
code moves and the docs don't, the interface note starts asserting things the
code no longer does. This skill closes that gap: it reads what actually changed
in the repo, keeps only what matters, and turns it into doc updates.

## The standing documents

Two live in the repo (edit them directly here):

- `CLAUDE.md` — the operational summary Claude Code reads on entry. **§6** is the
  coupling-simulation architecture, still partly open and the most likely to move.

Two live in the user's **project workspace, not this repo** (you cannot edit them
from here — produce a *carry-back digest* instead):

- `vibration_jitter_interface_note.md` — the full derivation of the vibration→
  jitter chain, the tier ladder, interface ownership, decision-record box, `[AO]`
  fork tags.
- `claude_Optical_Terminal_Roadmap.md` — WBS/schedule standing context.

So synthesis flows two ways: **direct edits** to repo docs, and a **carry-back
digest** the user pastes into the project so the brain-side docs stay current.

## What counts as "relevant"

The whole value of this skill is separating signal from churn. Be strict.

**Synthesise (signal):**
- New or changed physics, model equations, or approximations.
- Anything that touches the **interface-ownership boundary** (see below) — most of
  all, a **mount input actually arriving** (a real loop shape or compensator `C`),
  which advances the tier ladder.
- **Config A/B fork** movement: a fork resolved, or new fork-tagged divergence.
  This is high priority — the fork propagates into nearly every spec item.
- A **placeholder becoming a committed value** (e.g. mass properties `m, d, I`
  firming up after the concept gate). This changes what every downstream number
  *means*, even if no equation changed.
- A new subsystem landing (e.g. the coupling simulation — thread 2).
- A change to a stated **invariant** (delay bookkeeping in the coupled loop, SI
  units, "bounds carry their direction") or a caveat a doc currently asserts.

**Do not synthesise (noise) — note once, then move on:**
- Formatting, renames with no semantic change, comment/typo fixes.
- Dependency bumps, CI/config, `.gitignore`.
- Test scaffolding that doesn't change any asserted physics.
- Behaviour-preserving refactors (mention the refactor happened; don't rewrite docs).

## Interface-ownership discipline (do not let a change violate this)

The model is split along the real WBS interface. **We own** the drive
`tau=m·d·a(f)`, the mass properties `m,d,I`, and the plant `P=1/(I·s²)`. **The
mount owns** the sensitivity `S=1/(1+C·P)`, the loop bandwidth/rejection, and the
compensator `C`.

When classifying a change, watch for the failure mode where a commit **fabricates
a mount-owned block** to make a number appear — a hand-rolled compensator, an
invented bandwidth, a guessed sensitivity curve. If you see one, do **not** fold
it into the docs as fact. Flag it: "boundary event — is this a real mount input,
or a stub standing in for one?" Only a genuinely-arrived mount input advances the
tier ladder in the docs.

## Procedure

### 1. Establish the range

Read `docs/synthesis-log.md` (create it if absent). The last entry's `to` commit
is this run's `from`. If the log is empty, use the repo's first commit, or ask the
user for a starting point if the history is long.

```bash
git log --oneline <from>..HEAD
git diff --stat <from>..HEAD
```

### 2. Gather and read the diff

For each changed file that could carry signal (source modules, `CLAUDE.md`, new
scripts/notebooks), read the actual diff — not just the filename:

```bash
git diff <from>..HEAD -- <path>
```

Prefer the diff over commit messages; messages describe intent, diffs describe
what happened. Ignore files that are pure noise per the taxonomy above.

### 3. Classify

For each change, decide: signal or noise. For each signal change, name **what
changed** in one line and **which standing doc/section** it affects. Group by doc.
Apply the interface-ownership check to anything near the mount boundary.

### 4. Apply direct edits to repo docs

Edit `CLAUDE.md` in place for anything it currently asserts that the code has
outgrown — most often **§6** (coupling architecture) or the tier-ladder status
table. Match the doc's existing voice and conventions; don't restructure it.
State bounds with their direction (over/under-predicts, and in which band); keep
SI units. Do not invent mount inputs.

### 5. Produce the carry-back digest

Emit the digest below for the brain-side docs. Where a change maps to the
interface note's **decision-record box** or an `[AO]` fork tag, format it as such
so the user can drop it straight in. Where it's a new caveat or a changed
assumption, say which section of the interface note it lands in.

### 6. Log and close

Append an entry to `docs/synthesis-log.md` recording the range and a one-paragraph
summary, so the next run starts from `HEAD`. Commit the log and any `CLAUDE.md`
edits together with a message like `docs: synthesise <from>..<to>`.

## Output format

Always emit this exact structure:

```
## Synthesis <YYYY-MM-DD> — <from-hash>..<to-hash>

### Relevant changes
- [physics|interface|fork|placeholder|subsystem|invariant] <one line> → <doc>/<section>
  ...

### Direct edits applied (repo docs)
- CLAUDE.md §<n>: <what you changed and why>
  ...(or "none")

### Carry-back to the project workspace
Paste into the project so the interface note / roadmap / memory stay in sync:
> <self-contained block: what changed, which section of the interface note or
>  roadmap it updates, and — if applicable — a ready-to-drop decision-record
>  entry or [AO] fork tag>

### Decisions / gate movements
- <decision-record entry, if any — e.g. a Config A/B resolution> ...(or "none")

### Boundary flags
- <mount-input events, fabricated-mount-block warnings, placeholder→real
   transitions> ...(or "none")

### Noise (excluded, for the record)
- <formatting / deps / refactors> ...(or "none")
```

## Guardrails

- **Vibration spec ≠ jitter spec.** If a change blurs this — treating the standard
  as a jitter output, or as a random-vibration PSD rather than a swept sine —
  flag it loudly rather than propagating it into the docs.
- **Don't fabricate mount inputs.** Restated because it's the easiest error to make
  under pressure to produce a number.
- **Fork awareness.** Anything touching Config A/B is high priority; surface it in
  Decisions, not buried in the change list.
- **Placeholders.** A placeholder→real transition is a first-class synthesis event.
  A change that adds a *new* placeholder is fine but note it so it's tracked.
- **Bounds carry direction.** Never record a bound without its sense and band.
- **Two-way, but asymmetric.** You can edit repo docs; you can only *propose* edits
  to brain-side docs via the carry-back digest. Never claim to have updated a file
  you can't reach.

## Notes on testing this skill

Meaningful evaluation needs a repo with real commit history spanning a few
sessions — including at least one juicy change (a mount input arriving, or the
fork resolving). Until that history exists, run it against whatever range is
available and tune the relevance taxonomy from what it wrongly keeps or drops.
