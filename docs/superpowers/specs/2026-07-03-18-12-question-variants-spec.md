---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: question-variants
targets:
  - __init__.py
  - README.md
  - Config.md
  - test_question_variants_contract.py
---

# Goal

Support author-authored question variants in `{{Front}}` using `;;` separators, with one variant chosen at random per card exposure.

Requested behavior:

- If `Front` contains one question, current behavior stays unchanged
- If `Front` contains multiple variants separated by `;;`, one variant is chosen at random when card question is shown
- Selection stays stable for that review exposure and answer-side analysis
- Next time card opens, selection may change again
- No note mutation, no scheduler impact, no answer-analysis drift

# Key Deliverables

- Shared parser for `Front` question variants using `;;`
- Shared active-question state for current review exposure
- Question-side rendering contract that shows one chosen variant only
- Answer-analysis flow keyed to chosen visible variant
- Docs for variant syntax and boundaries
- Targeted runnable contract test for variant parsing/selection state

# Task/Wave Breakdown

## Wave 1: Variant source and parsing

- Define `;;` as reserved question-variant separator inside raw `Front` field text
- Parse raw `Front` into ordered variant list
- Trim whitespace around each candidate
- Drop empty candidates
- Support only plain-text `Front` content in V1
- If parsing yields no valid candidates, fall back to existing single-question flow

## Wave 2: Active question selection lifecycle

- Choose one variant when question side is rendered
- Persist chosen variant in shared current-review context keyed by current `card.id`
- Reuse same chosen variant on answer side and AI-regenerate path
- Clear active variant when `card.id` changes or raw `Front` content changes for same card

## Wave 3: Analysis/cache alignment

- Use chosen visible question as source of truth for analysis context
- Ensure analysis cache key includes chosen visible question text
- Prevent re-randomization during answer render, loading refresh, or analysis regeneration

## Wave 4: Docs and proof

- Document `;;` syntax in `README.md` and `Config.md`
- Add targeted runnable test for parsing and stable per-exposure selection behavior
- Add targeted runnable test for render-state reuse and deterministic variant selection

# Design Decisions

## Variant source of truth

V1 source of truth is raw note field `Front` when that field is plain text.

Rules:

- read from current card note field named exactly `Front`
- split raw field text on literal `;;`
- do not parse arbitrary card-template HTML for variants when raw `Front` is available
- if raw `Front` contains HTML tags or media markup, fall back to existing single-question behavior in V1
- if `Front` field is missing, empty, or resolves to one valid candidate, preserve current behavior

Reason:

- matches explicit user authoring model
- avoids fragile HTML parsing
- keeps implementation bounded and predictable

## Question render contract

V1 must define one concrete question-render path.

Rules:

- parse candidates from raw `Front` field text before choosing active variant
- chosen active variant becomes only visible `Front` question text for current exposure
- rendered front-side question must not show literal `;;` separators to user
- answer-side analysis must use same chosen active variant text, not independently cleaned HTML from a different source
- if implementation cannot safely replace rendered `Front` with chosen variant for current card template, fall back to existing single-question behavior

Reason:

- makes visible-question behavior implementable in one way
- prevents drift between raw field parsing and actual rendered prompt
- prevents partial implementations that only affect analysis key

## `;;` syntax contract

`;;` is reserved syntax for question variants in V1.

Examples:

- `2*3*4 = ?;;2*12 = ?`
- `Capital of France?;;Which city is capital of France?`

Rules:

- surrounding whitespace is ignored
- blank segments are ignored
- ordering in field is preserved for candidate list
- no escaping support in V1

Reason:

- tiny authoring surface
- easy to explain
- no extra config needed

## Active visible question SSOT

One shared helper must own active visible question for current review exposure.

Rules:

- question-side render chooses active variant exactly once per exposure
- answer-side render reuses stored active variant instead of reselecting
- regenerate-analysis path reuses stored active variant instead of reselecting
- all question-dependent logic uses same helper or shared context slot
- shared state object stores at least `card_id`, `raw_front_hash`, and `chosen_variant`

Reason:

- prevents question drift between front and back
- prevents cache-key mismatch
- prevents confusing rerenders

## Exposure lifecycle

Selection lifetime is one review exposure.

Definition:

- starts when question side for current card is shown
- ends when reviewer moves away from current card exposure

Rules:

- active variant stays fixed through typing, answer reveal, loading refresh, and analysis regeneration
- next fresh exposure may choose different variant from same candidate list
- spec does not require deterministic seed persistence across app restart
- exposure state must be reset when `mw.reviewer.card.id` changes
- exposure state must be reset when same `card.id` presents different raw `Front` content hash

Reason:

- user sees stable prompt during one attempt
- randomness still works across repetitions

## Random selection behavior

Variant choice is uniform across valid candidates.

Rules:

- if candidate count is `n`, each candidate gets `1/n` chance
- if `n == 1`, show that candidate
- if `n == 0`, fall back to existing front rendering
- one shared helper such as `choose_question_variant(candidates, rng)` must own selection
- production path may use standard RNG; tests must inject deterministic stub RNG

Simplification:

- no weighted variants in V1
- no "avoid immediate repeat" memory in V1

## Analysis cache-key contract

Chosen visible question must participate in AI analysis identity.

Rules:

- analysis cache key includes active visible question text, expected answer, and user answer
- changing visible question variant for future exposure may produce different analysis key even when expected and user answers match
- no duplicate ad hoc cache-key construction across render/store/regenerate paths

Reason:

- same answer under different prompt wording may need separate advisory analysis context
- prevents wrong cached panel reuse

# Invariants

- Real Anki scheduling remains source of truth
- Typed answer contents remain untouched by variant logic
- Visible question on answer side matches question shown on front for same exposure
- AI analysis remains advisory only
- `Front` authoring with no `;;` remains backward compatible
- Active visible question is single source of truth for render and analysis context

# Acceptance Criteria

- When `Front` has no `;;`, card displays current question behavior unchanged
- When raw `Front` contains HTML tags or media markup, card displays current single-question behavior unchanged in V1
- When `Front` contains `A;;B`, exactly one of `A` or `B` is shown on question side for that exposure
- Whitespace-only segments such as `A;; ;;B` are ignored
- Literal `;;` separators are never shown in visible question text when variant mode is active
- Active question does not change between question side and answer side for same exposure
- Clicking `Regenerate Analysis` does not cause question variant reshuffle
- Analysis cache key uses chosen visible question text
- Moving to next exposure allows variant to be reselected
- No scheduler action is triggered by question variant selection
- `README.md` and `Config.md` document `;;` syntax, exact `Front` requirement, and plain-text V1 limitation

# Non-Goals

- No automatic LLM generation of stored review variants
- No question-side LLM suggestion action in V1
- No arbitrary custom separator config
- No escaping syntax for literal `;;` in V1
- No weighted randomness or spaced-rotation strategy
- No per-note management UI for variant lists
- No support for arbitrary field names beyond exact `Front` in V1
- No support for rich HTML/media `Front` variant parsing in V1

# Risks and Mitigations

## Risk: variant reshuffles during one attempt

Mitigation:

- shared active-question state for current exposure
- no reselection on answer render or regenerate path

## Risk: analysis cache shows result for wrong variant

Mitigation:

- include chosen visible question in cache key
- use one shared helper for active question identity

## Risk: `;;` appears in natural content

Mitigation:

- document reserved syntax clearly
- no escaping support in V1 is explicit, not accidental

## Risk: missing `Front` field on non-standard notes

Mitigation:

- bounded V1 fallback to current behavior
- document exact `Front` requirement

## Risk: render path cannot safely replace visible question text

Mitigation:

- keep one explicit render contract
- if current card template cannot be patched safely, fall back to current single-question behavior

## Risk: tests become flaky because randomness is implicit

Mitigation:

- one shared chooser helper accepts injected RNG
- tests use deterministic stub RNG instead of probabilistic assertions

# Validation Plan

- proof target: `;;` parsing yields bounded valid candidate list
  - method: targeted runnable test for split, trim, empty-drop behavior
  - evidence: `test_question_variants_contract.py` asserts candidate lists for representative inputs

- proof target: rich HTML/media `Front` falls back safely
  - method: targeted runnable test for tagged or media-like raw `Front` values
  - evidence: helper returns existing single-question path instead of variant mode

- proof target: active question stays stable for one exposure
  - method: targeted runnable test with simulated front render then answer render
  - evidence: same chosen question is reused without reselection during same simulated exposure

- proof target: next exposure may reselect variant
  - method: targeted runnable test that clears exposure state, injects deterministic RNG, and reruns selection
  - evidence: selection helper is called again for fresh exposure and chosen result follows injected RNG

- proof target: render path never shows literal separators in active variant mode
  - method: targeted runnable test or render helper inspection
  - evidence: visible rendered question contains chosen candidate text without `;;`

- proof target: analysis identity follows visible question
  - method: targeted runnable test for cache-key inputs
  - evidence: different chosen question variants produce different keys when expected/user answers stay same

- proof target: regenerate analysis does not reshuffle question
  - method: targeted runnable test around regenerate path state
  - evidence: active question before and after regenerate remains identical for same exposure

- proof target: user docs match behavior
  - method: doc inspection
  - evidence: `README.md` and `Config.md` include `;;` authoring syntax, exact `Front` requirement, and plain-text V1 limitation

# Completion Criteria

- Spec approved
- Variant syntax, render contract, and selection lifecycle are unambiguous
- Active-question SSOT and analysis-cache alignment are explicitly defined
- Out-of-scope rich-content and authoring behaviors are explicitly rejected for V1
- Validation plan names concrete proof targets and evidence paths
