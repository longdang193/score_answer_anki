---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: expected-answer-alternatives-display
targets:
  - __init__.py
  - test_ai_analysis_ui_contract.py
  - test_question_variants_contract.py
---

# Goal

Show acceptable alternative answers in `Expected` area with same semantics and nearly same visual pattern as question variants, while preserving one source of truth for answer acceptance.

This change must:

- keep `Back` as canonical displayed expected answer
- keep `Back_variants` as acceptable-answer extensions, not replacement display text
- reuse the accepted-answer pool already built from `Back` + `Back_variants`
- avoid copying answer-variant parsing or cleanup logic into UI code
- keep question-side and answer-side variant behavior structurally symmetric
- avoid mixing `sample_answers` from AI Analysis into `Expected` block

# Key Deliverables

- One canonical UI model for expected-answer display plus acceptable alternative answers, computed in `render_enhanced_comparison(...)` from accepted-answer-pool SSOT
- `Expected` column extended to show subordinate alternative-answer chips when alternatives exist
- One shared chip-list rendering path reused for question-side and answer-side variant lists where practical
- Focused tests for accepted-answer display behavior, omission rules, and SSOT alignment

# Task/Wave Breakdown

## Wave 1: Expected-answer display contract

Define `Expected` block semantics explicitly:

- primary displayed value remains canonical expected answer from `Back`
- subordinate alternatives come only from accepted-answer pool built from `Back_variants`
- displayed alternatives exclude primary canonical expected answer
- alternative-answer UI renders only when cleaned pool contains at least one non-canonical acceptable answer
- order of alternatives follows accepted-answer pool order after canonical answer

## Wave 2: Canonical display model

Add one small shared display-model builder for typed-answer comparison. Build it in `render_enhanced_comparison(...)` while `card` context is already available, then pass plain display data into compare renderer.

Canonical model shape:

```python
{
    "primary_expected": str,
    "alternative_expected_answers": list[str],
}
```

Rules:

- `primary_expected` is canonical answer already shown in `Expected`
- `alternative_expected_answers` is derived from `build_accepted_answer_pool(card)` inside `render_enhanced_comparison(...)`
- cleanup, trim, dedupe, and ordering remain owned by existing accepted-answer-pool helpers
- if no `card` or card is unsupported, build primary-only display model and keep current compare output semantics
- compare renderer receives display-ready values only and does not read `mw.reviewer.card` or parse `Back_variants` directly

## Wave 3: Shared variant-chip rendering

Add or reuse one shared helper for subordinate variant chips.

Rendering rules:

- render variants as small chips under primary value
- chips use same text-normalization path as primary expected display before escaping; if normalized text is blank, omit chip
- no extra chip section renders when list is empty
- question-side and answer-side chip lists should share classes or one parameterized helper unless that causes bigger diff than value returned

Symmetry rule:

- question side: active primary question + other eligible question chips
- expected side: primary canonical answer + other acceptable answer chips

## Wave 4: Comparison block composition

Keep ownership explicit: `render_enhanced_comparison(...)` builds expected-answer display data from `build_accepted_answer_pool(card)`, then `_code_compare_block(...)` or one nearby pure renderer renders that data into `Expected` column:

- label: existing localized `Expected`
- primary canonical expected answer
- subordinate acceptable-answer chips when present

Recommended HTML structure:

```html
<div class="ak-compare-col ak-compare-col-expected">
  <div class="ak-label">Expected</div>
  <pre class="ak-pre"><code>My name is Long</code></pre>
  <div class="ak-variant-list">
    <span class="ak-variant-chip">I'm Long</span>
    <span class="ak-variant-chip">Long is my name</span>
  </div>
</div>
```

Rules:

- keep current `Your answer` column unchanged
- keep current canonical expected answer visible even when alternatives exist
- do not add AI-only labels like `Sample Answers` inside comparison block
- do not render alternatives above primary expected answer

## Wave 5: Label policy

Keep labels bounded and source-owned.

Rules:

- `Expected` and `Your answer` remain in compare-label SSOT
- alternative-answer chips should render without inventing a second mandatory heading if current question-side pattern already omits one
- if a heading is needed for clarity, add one compare-label key such as `also_acceptable`, not hardcoded English in HTML

Default recommendation:

- no extra heading for V1
- chips only, under canonical expected answer

## Wave 6: Tests

Add focused tests covering:

- accepted-answer pool remains source of truth for displayed alternatives
- canonical answer is not repeated in alternative chip list
- empty or missing `Back_variants` keeps current display
- duplicate or blank `Back_variants` entries do not create duplicate or blank chips
- `sample_answers` never leak into `Expected` block
- question-side variant behavior remains unchanged

# Design Decisions

## Source of truth

`build_accepted_answer_pool(card)` remains authoritative for acceptable-answer semantics.

UI must consume that helper output rather than re-reading `Back` / `Back_variants`.

## Semantics split

Three answer-like concepts remain distinct:

- canonical expected answer: `Back`
- accepted alternative answers: `Back_variants` via accepted-answer pool
- AI coaching examples: `sample_answers`

These must not be merged.

## Symmetry policy

Question and expected blocks should follow same high-level pattern:

- one primary displayed value
- optional subordinate alternatives
- alternatives omitted when absent

Exact CSS classes may differ only when required by existing layout constraints.

## Minimal-scope policy

V1 changes comparison block only.

This spec does not require:

- changing AI Analysis payload shape
- changing prompt contracts
- changing front-side question variant selection logic
- changing acceptance logic used for AI scoring

# Invariants

1. `Back` stays canonical displayed expected answer.
2. `Back_variants` stays acceptance-only source and is never parsed separately in renderer.
3. `sample_answers` are not shown in `Expected` block.
4. Alternative answers preserve accepted-answer-pool order after canonical answer.
5. Canonical answer is never duplicated in alternative-answer chips.
6. Empty, blank, or duplicate variants do not create UI artifacts.
7. If accepted-answer pool has only canonical answer, `Expected` block remains visually equivalent to current behavior.
8. Question-side variant behavior and AI analysis scoring semantics remain unchanged.

# Acceptance Criteria

1. For a card with `Back = "My name is Long"` and `Back_variants = "I'm Long;;Long is my name"`, `Expected` block shows:
   - primary expected answer `My name is Long`
   - subordinate chips for `I'm Long` and `Long is my name`
2. For a card with no `Back_variants`, `Expected` block shows current primary-only layout.
3. For `Back_variants` containing duplicates or blanks, chips render once per cleaned unique value.
4. Canonical `Back` value never appears again in alternative-answer chip list.
5. Alternative-answer chips come from accepted-answer pool SSOT, not from AI Analysis `sample_answers`.
6. Question-side variant chips still render as before.
7. `Your answer` column remains unchanged.
8. Current AI analysis prompt payload and scoring behavior remain unchanged.

# Non-Goals

- using AI-generated `sample_answers` as expected-answer alternatives
- changing scoring thresholds or acceptance logic
- adding per-profile compare-block behavior
- adding collapsible variant sections
- adding rich Markdown or Math rendering inside expected-answer chips in V1
- redesigning full comparison layout
- storing alternative-answer UI state separately from card data

# Risks and Mitigations

## Risk: UI shows coaching examples as if they were accepted answers

Mitigation:

- source `Expected` alternatives only from `build_accepted_answer_pool(card)`
- keep `sample_answers` confined to AI Analysis block

## Risk: duplicated parsing logic drifts from answer-acceptance logic

Mitigation:

- one display-model builder consumes accepted-answer-pool helper
- no direct `Back_variants` parsing in compare renderer

## Risk: visual clutter in narrow compare column

Mitigation:

- omit heading in V1
- show chips only when alternatives exist
- keep primary expected answer unchanged and visually dominant

## Risk: symmetry attempt causes oversized refactor

Mitigation:

- prefer one small parameterized chip helper only if local reuse is cheap
- otherwise keep question behavior untouched and add answer-side helper with same semantics

# Validation Plan

- proof target: accepted-answer pool is SSOT for displayed alternatives
  - method: focused test
  - evidence: `test_ai_analysis_ui_contract.py` or `test_question_variants_contract.py` asserts `Expected` chips reflect `build_accepted_answer_pool(card)` output

- proof target: canonical expected answer is not duplicated
  - method: focused test
  - evidence: rendered HTML contains canonical expected answer once in primary block and not in chip list

- proof target: blank and duplicate variants are suppressed
  - method: focused test
  - evidence: rendered HTML contains one chip per cleaned unique non-canonical value

- proof target: no alternatives means no visual regression
  - method: focused test
  - evidence: rendered HTML for card without `Back_variants` omits chip container or remains equivalent to current output

- proof target: AI coaching examples do not leak into expected block
  - method: focused test
  - evidence: rendered comparison HTML ignores `sample_answers` even when AI analysis cache contains them

- proof target: unsupported or missing-card path keeps current fallback behavior
  - method: focused test
  - evidence: rendered HTML for missing-card or unsupported-card path stays primary-only and omits alternative-answer chip container

- proof target: question-side behavior stays stable
  - method: regression test
  - evidence: current question-variant markup assertions remain green

# Completion Criteria

- spec approved
- expected-answer alternative-display contract is unambiguous
- accepted-answer pool is explicitly named as SSOT for expected alternatives
- comparison block renders subordinate acceptable-answer chips when available
- canonical expected answer remains primary
- `sample_answers` and accepted-answer alternatives remain separate concepts
- focused tests prove omission, ordering, dedupe, and non-leakage behavior
