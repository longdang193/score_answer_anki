---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: cloze-hint-slot-contract-ssot
parent_workstream: none
targets:
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\__init__.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_ai_analysis_ui_contract.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\README.md
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\Config.md
related_features:
  - front-hint-panel
  - cloze-answer-contract
  - ai-analysis-ui
related_stages:
  - design
---

# Goal

Replace split cloze answer and hint field mapping with one source-of-truth slot contract so every admissible card case resolves `Back`, `Back_variants`, and `Hint` from same active slot index.

Supersession note:

- this spec supersedes the manual-hint field-name contract from `docs/superpowers/specs/2026-07-05-11-23-hint-panel-ai-suggestions-spec.md`
- after approval, the authoritative manual-hint rule is slot-driven mapping from this spec, not "field name is exactly `Hint`"

Current root bug:

- answer mapping already follows cloze slot index through `resolve_answer_field_names(...)`
- manual hint mapping does not follow slot index and always reads `Hint`
- cloze cards with `c2`, `c3`, or `c4` therefore use mapped answer fields but unmapped hint field
- this breaks structural symmetry between answer-family and hint-family note fields
- this also forces future fixes to remember two naming systems for one slot concept

Admissible cases for this spec are exactly:

- non-cloze score cards
- cloze score cards that pass current `is_clozeanything_score_template(...)` gate and have a resolved active slot from `get_active_cloze_index(card)`
- cards with manual hint present
- cards with manual hint absent

Within those cases:

- slot `1` is base slot
- slot `x > 1` is admissible only when current runtime selects that active slot and note model contains matching mapped fields for required answer families

Uniform rule:

- slot `1` resolves to base names: `Back`, `Back_variants`, `Hint`
- slot `x > 1` resolves to suffixed names: `Back{x}`, `Back{x}_variants`, `Hint{x}`

No active-slot consumer may hardcode `Hint`, `Back`, or `Back_variants` based on card type after this change. Active-slot consumers must read field names from shared slot contract.

# Key Deliverables

1. One shared active-slot field contract in `__init__.py` that owns answer-field, answer-variants-field, and hint-field resolution.
2. One update to answer-contract construction so it consumes shared slot contract rather than separate answer-only resolver.
3. One update to manual-hint lookup so it consumes same shared slot contract and stops hardcoding `Hint`.
4. One explicit admissibility rule defining when missing mapped answer fields invalidate scoring and when missing mapped hint fields remain non-fatal.
5. Focused regression tests proving slot symmetry across `c1` through `c4` and plain score-card cases.
6. One docs update describing mapped manual hint behavior for cloze cards.

# Task/Wave Breakdown

## Wave 1: Define one slot contract

Required change:

- define one authoritative slot resolver for note-field families
- preferred contract shape:
  - `slot_index: int`
  - `source_kind: plain_back | cloze`
  - `answer_field: str`
  - `answer_variants_field: str`
  - `hint_field: str`

Required slot-index rules:

- non-cloze score cards use slot index `1`
- cloze score cards use `get_active_cloze_index(card)`
- slot resolution must not branch separately for answer family and hint family
- base-name exception for slot `1` must be encoded once inside slot resolver only
- if active slot cannot be resolved, answer path keeps current invalid-contract behavior and hint path resolves empty manual hint

Preferred helper ownership:

- one low-level suffix helper is allowed
- one exported slot-contract helper is preferred
- `resolve_answer_field_names(...)` may remain as thin wrapper over slot contract or be removed if no longer needed

## Wave 2: Route answer contract through slot contract

Required change:

- `build_answer_contract(...)` must consume slot contract for:
  - canonical answer field name
  - answer variants field name
- missing required mapped answer fields must keep current invalid-contract behavior
- invalid-contract messages must reference actual mapped field names from slot contract

Required admissible answer behavior:

1. plain score card resolves `Back` and `Back_variants`
2. active `c1` resolves `Back` and `Back_variants`
3. active `c2` resolves `Back2` and `Back2_variants`
4. active `c3` resolves `Back3` and `Back3_variants`
5. active `c4` resolves `Back4` and `Back4_variants`
6. any currently admissible slot `x > 1` resolves `Back{x}` and `Back{x}_variants` if current runtime selects that slot and note model includes those fields

## Wave 3: Route manual hint through same slot contract

Required change:

- `get_manual_hint_html(...)` must consume slot contract for mapped hint field name
- hardcoded `Hint` lookup must be removed from manual hint path
- manual hint remains optional in every slot
- missing mapped hint field must resolve to empty string, not error
- blank mapped hint value must resolve to empty string, not fallback to another slot

Required admissible hint behavior:

1. plain score card reads `Hint`
2. active `c1` reads `Hint`
3. active `c2` reads `Hint2`
4. active `c3` reads `Hint3`
5. active `c4` reads `Hint4`
6. any currently admissible slot `x > 1` reads `Hint{x}` if current runtime selects that slot and note model includes that field
7. if active slot cannot be resolved, manual hint resolves to empty string

Explicit non-behavior:

- no compatibility fallback from `Hint2+` back to unsuffixed `Hint`
- no merging of hint values across slots
- no inference from `Back` field names at individual call sites

## Wave 4: Keep hint-panel and AI context behavior stable

Required change:

- `build_front_hint_context(...)` continues to read `manual_hint` through `get_manual_hint_html(...)`
- front-hint render order, AI hint behavior, cache-key shape, and panel refresh flow stay unchanged except mapped manual hint value may differ for cloze cards

Required boundary:

- this change is field-resolution only
- this change must not alter:
  - AI provider calls
  - prompt profiles
  - cache invalidation semantics beyond manual hint value changing when slot changes
  - answer comparison semantics
  - cloze target parsing semantics

# Design Decisions

## Decision 1: Slot index is canonical source of truth

`slot_index` is canonical identity for all note-field families participating in active answer/hint resolution.

Reason:

- answer family and hint family describe same active recall slot
- index already exists as answer-contract input for cloze cards
- one shared slot identity eliminates drift between answer lookup and hint lookup

## Decision 2: Slot `1` base-name exception is allowed once

Base-name exception for slot `1` is real model behavior and remains supported.

Allowed special case:

- slot `1` maps to unsuffixed base names

Disallowed special cases:

- separate hardcoded `Hint` logic outside slot resolver
- separate hardcoded `Back` logic outside slot resolver for active-slot consumers

## Decision 3: Required and optional families have different failure semantics

Answer families are required for valid scoring contracts. Hint family is optional.

Rules:

- missing mapped `Back*` or `Back*_variants` fields on active slot invalidates answer contract
- missing mapped `Hint*` field on active slot yields empty manual hint only
- optional hint absence must never block review flow or scoring flow

## Decision 4: No compatibility fallback for `Hint2+`

This update is symmetry-driven and SSOT-driven, not migration-driven.

Reason:

- fallback would preserve two truths for one slot concept
- fallback would hide malformed notes and keep behavior case-dependent
- user requested one uniform rule for all admissible cases

## Decision 5: Shared contract owns future indexed slots automatically

If current runtime later expands admissible slot range, shared slot contract should scale by same naming rule without new hint-specific logic.

# Invariants

1. Active slot index determines answer field, answer variants field, and hint field together.
2. Slot `1` always maps to `Back`, `Back_variants`, and `Hint`.
3. Slot `x > 1` always maps to `Back{x}`, `Back{x}_variants`, and `Hint{x}`.
4. No active-slot consumer hardcodes `Hint` outside shared slot contract.
5. No active-slot consumer hardcodes `Back{x}` naming outside shared slot contract.
6. Missing mapped hint field never invalidates answer contract.
7. Missing mapped answer fields continue to invalidate answer contract.
8. Changing active cloze card ordinal changes both mapped answer family and mapped hint family together.
9. Front-hint UI semantics remain unchanged except for mapped manual hint source.
10. If active slot cannot be resolved, answer path stays invalid and hint path returns empty manual hint.

# Acceptance Criteria

1. For non-cloze score cards, answer contract and manual hint path use base fields: `Back`, `Back_variants`, `Hint`.
2. For cloze card with active `c1`, answer contract and manual hint path use same base slot fields.
3. For cloze card with active `c2`, answer contract uses `Back2` and `Back2_variants`, and manual hint path uses `Hint2`.
4. For cloze card with active `c3`, answer contract uses `Back3` and `Back3_variants`, and manual hint path uses `Hint3`.
5. For cloze card with active `c4`, answer contract uses `Back4` and `Back4_variants`, and manual hint path uses `Hint4`.
6. If mapped hint field for active slot is absent, front-hint context returns empty manual hint and panel still functions.
7. If mapped answer field for active slot is absent, answer contract is invalid and invalid reason names mapped field(s).
8. Switching cloze ordinal from slot `1` to slot `2` changes both canonical answer source and manual hint source in lockstep.
9. No test or code path depends on fallback from `Hint2+` to unsuffixed `Hint`.
10. If active cloze slot cannot be resolved, answer contract remains invalid and manual hint path returns empty string.

# Non-Goals

- changing note-model schema
- auto-migrating existing note data from `Hint` to `Hint2+`
- adding UI warnings for notes with unmigrated hint content
- changing AI hint generation prompts or output format
- changing answer comparison, scoring, or accepted-answer normalization semantics
- changing cloze parsing rules or template detection rules

# Risks and Mitigations

## Risk 1: Existing decks may store second-slot hints in unsuffixed `Hint`

Impact:

- those hints stop appearing for `c2+` after symmetry fix

Mitigation:

- document new mapped-field contract explicitly in docs
- keep scope honest: no fallback hidden inside runtime
- if migration support is later required, handle it as separate explicit migration feature, not hidden field-resolution logic

## Risk 2: Tests cover answer symmetry but miss hint symmetry

Impact:

- future regressions could reintroduce hardcoded `Hint`

Mitigation:

- add explicit slot-by-slot manual hint tests beside existing answer mapping proofs
- assert mapped hint values for ordinals `0..3`

## Risk 3: Contract duplication remains through legacy wrappers

Impact:

- future edits may update wrapper but not SSOT helper

Mitigation:

- keep one clearly named shared slot helper
- if legacy answer-only resolver remains, make it thin wrapper over slot contract only

# Validation Plan

- proof target: active-slot contract resolves symmetric field families for base and suffixed slots
  - method: test
  - evidence: assertions for slot `1..4` field mapping in `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_ai_analysis_ui_contract.py`

- proof target: answer contract still invalidates on missing mapped answer fields
  - method: test
  - evidence: existing invalid-contract assertions continue to pass with mapped-field names from shared slot contract

- proof target: manual hint path follows active slot index instead of hardcoded `Hint`
  - method: test
  - evidence: `build_front_hint_context(...)` or `get_manual_hint_html(...)` returns `Hint`, `Hint2`, `Hint3`, `Hint4` values for ordinals `0..3`

- proof target: missing mapped hint field is non-fatal
  - method: test
  - evidence: context build returns empty `manual_hint` and front-hint path remains available

- proof target: unresolved active cloze slot has symmetric failure behavior
  - method: test
  - evidence: answer contract remains invalid while manual hint path returns empty string without fallback to unsuffixed `Hint`

- proof target: docs describe mapped manual hint contract for cloze cards
  - method: inspection
  - evidence: updated wording in `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\README.md` and `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\Config.md`

- proof target: legacy hint-panel spec no longer conflicts on manual-hint field contract
  - method: inspection
  - evidence: `docs/superpowers/specs/2026-07-05-11-23-hint-panel-ai-suggestions-spec.md` is updated or explicitly superseded by this spec for manual-hint field naming

# Completion Criteria

- one shared slot contract exists and owns answer-family plus hint-family resolution
- `get_manual_hint_html(...)` no longer hardcodes unsuffixed `Hint`
- answer contract uses shared slot contract instead of separate bespoke mapping logic
- focused tests prove slot symmetry for `c1` through `c4` and non-cloze base case
- focused tests prove unresolved active-slot behavior for both answer and hint paths
- docs state manual hint uses active-slot field mapping for cloze cards
- prior hint-panel spec no longer claims exact field name is always `Hint`
- no compatibility fallback remains in runtime for `Hint2+`
