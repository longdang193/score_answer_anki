---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: answer-variant-pools
targets:
  - __init__.py
  - README.md
  - Config.md
  - test_question_variants_contract.py
  - test_ai_analysis_ui_contract.py
---

# Goal

Support one concept-safe field-based variant model for typed-answer cards:

- `Front` remains one canonical display question
- `Front_variants` becomes optional question-variant pool for alternate valid phrasings separated by `;;`
- `Back` remains one canonical display answer
- `Back_variants` becomes optional accepted-answer pool for alternate valid answers separated by `;;`
- AI analysis must evaluate user answers using question, canonical answer, accepted-answer pool, and user answer together
- obviously incompatible question variants must not be selected or scored

Requested behavior:

- if `Front_variants` is missing or empty, canonical `Front` question is used unchanged
- if `Front_variants` contains valid entries, exactly one question from `Front` + `Front_variants` pool is chosen per review exposure
- selection stays stable for that exposure across answer render and analysis regenerate
- `Back` remains source of truth for displayed expected answer
- `Back_variants` extends accepted-answer semantics, not display semantics
- question variants that fail deterministic V1 compatibility checks are excluded before display and before AI analysis

# Key Deliverables

- Shared parser for `Front_variants` and `Back_variants` using `;;`
- One canonical visible-question pool builder using `Front` + `Front_variants`
- One canonical accepted-answer pool builder using `Back` + `Back_variants`
- One deterministic V1 compatibility gate for `question ↔ accepted-answer-pool`
- Shared active-question state for current review exposure
- Shared AI analysis contract using question + canonical answer + accepted-answer pool + user answer
- Bounded mismatch behavior for incompatible card data
- Docs for `Front`, `Front_variants`, `Back`, and `Back_variants` roles and limits
- Runnable proof artifacts for pool parsing, validity gating, exposure state, mismatch handling, and AI-input contract

# Task/Wave Breakdown

## Wave 1: Field contracts and parsing

- Keep `Front` as canonical displayed question
- Add optional `Front_variants` field for alternate question phrasings using literal `;;`
- Keep `Back` as canonical displayed expected answer
- Add optional `Back_variants` field for alternate acceptable answers using literal `;;`
- Parse and normalize `Front` + `Front_variants` into one visible-question candidate pool
- Parse and normalize `Back` + `Back_variants` into one accepted-answer pool
- Deduplicate normalized question variants while preserving first display order
- Deduplicate normalized answer variants while preserving first display order

## Wave 2: Deterministic question-variant validity gate

- Add one deterministic pre-check that evaluates whether a question variant is obviously compatible with accepted-answer pool
- Use only variants marked `compatible` for random selection
- If canonical `Front` is marked `incompatible`, treat card as invalid configuration for add-on enhancement and suppress AI scoring with bounded mismatch output
- If canonical `Front` is compatible but all non-canonical variants are incompatible, use canonical `Front` only
- If gate cannot decide, mark result `unsupported` and do not auto-reject variant in V1

## Wave 3: Active question state and rendering

- Choose one eligible question variant per review exposure
- Persist chosen variant in shared state keyed by current card identity
- Render chosen question prominently and other eligible question variants as smaller secondary choices
- Reuse same chosen question on answer side and regenerate-analysis path

## Wave 4: AI analysis contract

- AI analysis must receive chosen visible question, canonical `Back`, accepted-answer pool, and user answer
- Add pre-analysis mismatch guard when chosen question is incompatible with accepted-answer pool
- If guard says mismatch, do not score user answer; show bounded mismatch message instead
- If guard says compatible or unsupported, score user answer against question and accepted-answer pool together

## Wave 5: Docs and proof

- Document `Front`, `Front_variants`, `Back`, and optional `Back_variants` roles in `README.md` and `Config.md`
- Document native-Anki-vs-add-on correctness boundary clearly
- Add targeted runnable tests for question-pool parsing, answer-pool parsing, deterministic compatibility filtering, active-question stability, and mismatch handling
- Add targeted runnable tests proving AI-input contract includes answer pool and mismatch path

# Design Decisions

## Field ownership model

Field semantics are symmetric by parser shape and distinct by responsibility.

Rules:

- `Front` owns canonical displayed question only
- `Front_variants` owns alternate question phrasings only
- `Back` owns canonical displayed answer only
- `Back_variants` owns alternate accepted answers only
- `Front` is always included in visible-question pool even when `Front_variants` is empty
- `Back` is always included in accepted-answer pool even when `Back_variants` is empty
- `Front_variants` never changes what is displayed as canonical question outside current exposure selection
- `Back_variants` never changes what is displayed as expected answer in core compare UI

Reason:

- keeps `Front` and `Back` as human-readable source-of-truth fields
- separates display answer from accepted-answer tolerance
- avoids overloading canonical fields with variant syntax

## `;;` parser symmetry

Use one delimiter model across variant-bearing fields.

Rules:

- `Front_variants` uses `;;` to split question variants
- `Back_variants` uses `;;` to split accepted-answer variants
- surrounding whitespace is ignored
- blank segments are ignored
- no escaping support in V1

Reason:

- parser symmetry without semantic confusion
- one authoring rule, two scoped uses

## Visible-question pool SSOT

One shared helper must build visible-question pool.

Rules:

- pool source is `Front` + parsed `Front_variants`
- canonical `Front` is always included first in candidate pool
- normalization for visible-question pool is minimal in V1:
  - trim outer whitespace
  - preserve case
  - preserve punctuation
  - preserve internal spacing except exact leading/trailing trim
- dedupe uses exact equality after minimal normalization
- all render, chooser, and compatibility paths use this one helper

Reason:

- keeps question semantics centralized
- prevents drift between visible question rendering and compatibility filtering

## Accepted-answer pool SSOT

One shared helper must build accepted-answer pool.

Rules:

- pool source is `Back` + parsed `Back_variants`
- canonical `Back` is always included first in accepted-answer pool
- normalization for accepted-answer pool is minimal in V1:
  - trim outer whitespace
  - preserve case
  - preserve punctuation
  - preserve internal spacing except exact leading/trailing trim
- dedupe uses exact equality after minimal normalization
- pool builder returns both canonical display answer and normalized accepted-answer list
- all matching, validity checks, and AI contract assembly use this one helper
- no ad hoc reconstruction of answer pool in render, compare, or AI paths

Reason:

- keeps answer semantics centralized
- prevents drift between acceptance logic and AI prompt construction
- avoids premature semantic normalization that could break code/math answers

## Deterministic V1 compatibility gate

One shared guard must decide whether a question variant is obviously compatible with current accepted-answer pool.

Rules:

- gate input is `question_variant + canonical_answer + accepted_answer_pool`
- gate output is one of:
  - `compatible`
  - `incompatible`
  - `unsupported`
- V1 gate is deterministic and local only; no LLM, no network, no probabilistic classifier
- V1 gate only rejects obvious contradictions it can prove locally
- for V1 arithmetic blank-style cards, if local deterministic reasoning proves expected value contradicts full accepted-answer pool, output `incompatible`
- if local deterministic reasoning proves compatibility, output `compatible`
- if card does not match bounded V1 gate patterns, output `unsupported`
- only `compatible` variants are auto-selected in normal path
- `incompatible` variants are excluded from display and analysis
- `unsupported` variants are not auto-rejected in V1 and may remain author-trusted candidates

Reason:

- prevents broken mixed-answer prompts like `221 = 13 * ?` with canonical answer `221`
- keeps gate reproducible and cheap
- avoids fake semantic certainty for hard domains like open-ended language cards

## Exposure state SSOT

One shared helper must own active visible question for current review exposure.

Rules:

- question-side render chooses active eligible question variant exactly once per exposure
- answer-side render reuses stored variant instead of reselecting
- regenerate-analysis path reuses stored variant instead of reselecting
- state stores at least `card_id`, `question_pool_hash`, `answer_pool_hash`, and `chosen_variant`
- state resets when card identity changes or either question-pool/answer-pool identity changes

Reason:

- preserves invariance across question render, answer render, and AI analysis
- prevents stale variant bleed after note edits

## Native Anki vs add-on correctness boundary

Correctness ownership must be explicit.

Rules:

- native Anki typed-answer compare remains source of truth for built-in compare display and scheduling behavior
- add-on AI analysis remains advisory only in V1
- add-on may classify a user answer as acceptable relative to accepted-answer pool even when native compare differs from canonical `Back`
- advisory acceptance must never silently override Anki scheduling or native compare output
- docs must state this boundary clearly

Reason:

- prevents hidden behavior changes in scheduling
- allows richer advisory logic without claiming native compare was replaced

## AI analysis contract

AI must evaluate four-part context, not only canonical answer and user answer.

Rules:

- prompt/input contract includes exactly:
  - chosen visible question
  - canonical display answer from `Back`
  - accepted-answer pool from `Back` + `Back_variants` as explicit ordered list
  - user answer
- prompt instructs model to first check whether chosen question is compatible with accepted-answer pool
- if chosen question is incompatible, return `variant_mismatch` and no score
- if chosen question is compatible or unsupported by local gate, evaluate whether user answer satisfies question in light of accepted-answer pool
- accepted-answer pool must be passed explicitly, not paraphrased vaguely

Reason:

- fixes false negatives where user answer is valid for chosen question but not string-equal to canonical answer
- prevents scoring on contradictory inputs
- makes prompt construction testable

## Variant-mismatch output contract

Scoring path needs one bounded mismatch status.

Rules:

- mismatch response shape must be:
  - `status: variant_mismatch`
  - `score: null`
  - `tips: <bounded warning>`
- mismatch path must not silently convert into low numeric score
- mismatch path must be visibly distinct from genuine user mistake

Reason:

- bad card data is not same thing as bad student answer

## Matching semantics

Accepted-answer pool represents semantic equivalents for one concept, not alternate question-answer mappings.

Rules:

- `Back_variants` is for synonyms, formatting variants, spelling variants, or equivalent surface forms of same answer
- `Front_variants` is for paraphrases or alternate surface forms of same question intent
- if a question requires a different correct answer, it belongs in a different Front/Back pair
- positional zipping between `Front_variants` and `Back_variants` is forbidden

Reason:

- preserves one-concept-per-card invariant
- avoids hidden mapping semantics and index drift

# Invariants

- One note/card pair represents one answer concept
- `Front` remains canonical display question
- `Back` remains canonical display answer
- `Front_variants` extends visible question options only
- `Back_variants` extends accepted answers only
- Question variants from `Front` + `Front_variants` must not be auto-selected when deterministically proven incompatible with accepted-answer pool
- Active visible question is single source of truth for render and AI analysis in one exposure
- AI analysis remains advisory only
- No scheduler action is triggered by variant filtering or AI mismatch detection

# Acceptance Criteria

- When `Front_variants` is missing or empty, canonical `Front` question is displayed unchanged
- When `Back_variants` is missing or empty, accepted-answer pool still contains canonical `Back`
- When `Front_variants` contains many variants, variants marked `compatible` are eligible for display
- Variants deterministically proven incompatible, such as `221 = 13 * ?` for canonical answer `221`, are not shown
- If canonical `Front` is deterministically proven incompatible with accepted-answer pool, add-on suppresses AI scoring and returns bounded mismatch result instead of fake score
- If canonical `Front` is compatible but all non-canonical variants are incompatible, canonical `Front` alone remains eligible
- Chosen visible question stays stable for one exposure across answer render and regenerate-analysis path
- AI prompt/input contract includes chosen question, canonical `Back`, explicit accepted-answer pool list, and user answer
- Variant mismatch returns bounded non-scored result, not fake low score
- `README.md` and `Config.md` document `Front`, `Front_variants`, `Back`, `Back_variants`, and native-vs-advisory correctness boundary clearly

# Non-Goals

- No positional mapping between question variants and answer variants
- No support for one card holding multiple different answer concepts
- No automatic generation of new variants in this change
- No arbitrary custom separator config
- No escaping syntax for literal `;;` in V1
- No rich HTML/media variant parsing in `Front_variants` or `Back_variants` in V1 unless already proven safe
- No replacement of Anki scheduler semantics
- No generic semantic proof of question-answer compatibility across all domains in V1

# Risks and Mitigations

## Risk: compatibility gate becomes overly magical

Mitigation:

- keep gate outputs explicit: `compatible | incompatible | unsupported`
- keep V1 gate deterministic and local only
- do not pretend to prove semantic equivalence in hard domains without explicit signal

## Risk: visible-question pool drifts across code paths

Mitigation:

- one question-pool builder helper only
- all render, chooser, and compatibility paths consume same returned structure

## Risk: accepted-answer pool drifts across code paths

Mitigation:

- one answer-pool builder helper only
- all compare and AI paths consume same returned structure

## Risk: linguistic cards still false-negative on canonical-only compare

Mitigation:

- AI contract must use full accepted-answer pool, not only canonical `Back`
- native-vs-advisory boundary is documented explicitly
- tests include linguistic-equivalent examples in advisory path

## Risk: users misuse variant fields for different concepts

Mitigation:

- docs explicitly state one concept per card pair
- deterministic gate rejects obvious contradictions

## Risk: no eligible variants remain

Mitigation:

- if canonical `Front` is compatible, canonical `Front` remains only eligible question
- if canonical `Front` is incompatible, add-on suppresses AI scoring and surfaces bounded mismatch warning

# Validation Plan

- proof target: visible-question pool is built from `Front` + `Front_variants`
  - method: targeted runnable test for pool parsing, trim, empty-drop, and dedupe
  - evidence: contract test asserts canonical question and question-variant list for representative note inputs

- proof target: accepted-answer pool is built from `Back` + `Back_variants`
  - method: targeted runnable test for pool parsing, trim, empty-drop, and dedupe
  - evidence: contract test asserts canonical answer and accepted-answer list for representative note inputs

- proof target: deterministic compatibility gate rejects obvious contradictions
  - method: targeted runnable test with compatible and incompatible arithmetic examples
  - evidence: incompatible variant `221 = 13 * ?` is excluded while `13 * 17 = ?` and `17 * 13 = ?` remain eligible

- proof target: unsupported domains are not falsely rejected
  - method: targeted runnable test with non-arithmetic language-style examples
  - evidence: gate returns `unsupported` rather than `incompatible` for cases outside bounded V1 rules

- proof target: active visible question stays stable for one exposure
  - method: targeted runnable test with deterministic chooser and simulated answer render
  - evidence: same chosen variant is reused without reselection during same exposure

- proof target: AI-input contract includes accepted-answer pool
  - method: targeted runnable test for prompt/input builder
  - evidence: chosen question, canonical answer, full accepted-answer pool list, and user answer all appear in built contract payload/text

- proof target: mismatch path is non-scored
  - method: targeted runnable test for mismatch result handling
  - evidence: `variant_mismatch` response yields `score: null` and bounded warning text

- proof target: docs match field-role contract and correctness boundary
  - method: doc inspection
  - evidence: `README.md` and `Config.md` describe `Front`, `Front_variants`, `Back`, `Back_variants`, one-concept-per-card rule, and native-vs-advisory boundary

# Completion Criteria

- Spec approved
- Field ownership for `Front`, `Front_variants`, `Back`, and `Back_variants` is unambiguous
- Visible-question pool SSOT is explicitly defined
- Accepted-answer pool SSOT is explicitly defined
- Deterministic V1 compatibility gate is explicitly defined
- Native Anki vs add-on correctness boundary is explicitly defined
- AI analysis contract is explicitly question-aware and answer-pool-aware
- Validation plan names concrete proof targets and evidence paths
