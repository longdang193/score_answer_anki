---
layer: change
artifact_type: plan
status: proposed
name: question-variants
source_spec: docs/superpowers/specs/2026-07-03-18-12-question-variants-spec.md
targets:
  - __init__.py
  - README.md
  - Config.md
  - test_question_variants_contract.py
---

# Goal

Implement bounded question variants for plain-text `Front` values using `;;` separators, with one chosen variant shown per card exposure and reused across answer rendering and AI-analysis paths.

# Key Deliverables

- One shared helper that parses raw plain-text `Front` into valid question candidates
- One shared helper that chooses active variant through injectable RNG
- One shared active-question state object keyed by `card.id`
- One concrete render path that shows chosen variant only and never leaks literal `;;`
- Shared analysis integration that reuses chosen visible question for cache identity and regenerate path
- Safe fallback to current behavior for missing `Front`, single-candidate `Front`, or rich HTML/media `Front`
- One small runnable proof artifact for parser, chooser, state reuse, and cache-key behavior
- Docs updated for `;;` syntax, exact `Front` requirement, and plain-text V1 limitation

# Task Breakdown

## Task 1: Add variant parsing and chooser helpers

Files:
- `__init__.py`
- `test_question_variants_contract.py`

Steps:
- Add one helper to read raw `Front` field from current card note
- Add one helper to detect whether V1 variant mode is allowed for that raw `Front`
- Treat HTML tags or media-like markup as out of scope and return fallback mode
- Add one parser helper that splits on literal `;;`, trims segments, and drops empties
- Add one chooser helper such as `choose_question_variant(candidates, rng)`
- Keep chooser interface injectable so tests can provide deterministic RNG

Verification:
- Parser returns ordered candidate list for plain-text inputs
- Parser falls back for HTML/media-like inputs
- Chooser returns deterministic value with stub RNG

## Task 2: Add active-question exposure state

Files:
- `__init__.py`
- `test_question_variants_contract.py`

Steps:
- Add one shared active-question state object storing at least `card_id`, `raw_front_hash`, and `chosen_variant`
- Add one helper that returns current active variant for exposure, reusing stored value when state still matches
- Reset exposure state when `card.id` changes
- Reset exposure state when same `card.id` produces different raw `Front` hash
- Keep this state as single source of truth for all question-dependent logic

Verification:
- Same exposure reuses same chosen variant
- New exposure reruns chooser
- State reset happens on card/content identity change

## Task 3: Patch question render path

Files:
- `__init__.py`
- `test_question_variants_contract.py`

Steps:
- Identify narrowest hook/helper path that can replace visible `Front` question text without changing scheduler behavior
- Use raw `Front` candidates to choose one active variant before final question display
- Ensure visible question text for active variant contains no literal `;;`
- If current card/template shape cannot be patched safely, fall back to current single-question behavior
- Keep implementation localized; avoid duplicate render branches for variant vs non-variant mode

Verification:
- Plain-text multi-variant `Front` shows one candidate only
- Single-question or unsupported `Front` shows current behavior unchanged
- Rendered active variant text never contains `;;`

## Task 4: Align answer analysis and regenerate path

Files:
- `__init__.py`
- `test_question_variants_contract.py`

Steps:
- Replace ad hoc current-question lookup for analysis identity with shared active visible question helper when variant mode is active
- Keep existing non-variant analysis path unchanged for fallback mode
- Ensure store/render/regenerate paths all reuse same active visible question source
- Ensure analysis cache key changes when chosen visible question changes across exposures
- Ensure regenerate path never reshuffles active question inside same exposure

Verification:
- Store, render, and regenerate paths use same visible question for one exposure
- Different chosen variants produce different analysis keys for same expected/user answers
- Regenerate does not trigger reselection

## Task 5: Add docs and proof artifact

Files:
- `README.md`
- `Config.md`
- `test_question_variants_contract.py`

Steps:
- Document `;;` variant authoring syntax with one or two concrete examples
- Document exact `Front` requirement
- Document plain-text-only V1 limitation and fallback behavior for rich content
- Add one assert-based proof script covering:
  - parser split/trim/empty-drop behavior
  - unsupported rich-content fallback
  - deterministic chooser behavior with stub RNG
  - stable active variant reuse during one exposure
  - cache-key change across different chosen variants

Verification:
- `python test_question_variants_contract.py` exits cleanly
- Docs match final implementation boundaries

# Risks / Rollback

- Risk: render hook cannot safely swap visible question text for all card shapes
  - rollback: keep variant mode disabled unless helper confirms plain-text `Front` and safe patch path
- Risk: global active state leaks across cards
  - rollback: scope state by `card.id` and raw `Front` hash only; clear on identity mismatch
- Risk: variant feature breaks analysis cache reuse
  - rollback: keep one shared visible-question helper and prove key behavior in assert-based test
- Risk: deterministic test seam gets bypassed in production path
  - rollback: make chooser helper the only selection path and test helper directly

# Final Verification

- `python test_question_variants_contract.py`
- `python -m py_compile __init__.py test_question_variants_contract.py`
- Manual Anki check with plain-text `Front` examples:
  - `2*3*4 = ?;;2*12 = ?`
  - `Capital of France?;;Which city is capital of France?`
- Manual Anki check confirms:
  - only one variant is shown on question side
  - same variant remains visible/active through answer reveal
  - `Regenerate Analysis` does not reshuffle variant
  - unsupported rich-content `Front` falls back to normal single-question behavior

# Completion Criteria

- Plain-text `Front` variant syntax works end to end
- Active visible question has one SSOT across render and analysis paths
- Unsupported `Front` content falls back safely
- Proof script and syntax compile both pass
- Docs match actual V1 boundaries
