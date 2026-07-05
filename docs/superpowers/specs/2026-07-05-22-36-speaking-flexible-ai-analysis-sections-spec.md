---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: speaking-flexible-ai-analysis-sections
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
---

# Goal

Extend `Speaking Flexible` AI Analysis so structured JSON fields `sample_answers` and `question_variants` render as first-class sections inside `AI Analysis`, while preserving SSOT and symmetry.

This change must:

- keep one canonical parsed analysis payload
- keep one shared rendering path for all `AI Analysis` sections
- avoid duplicating field-specific HTML logic across parser and UI
- reuse existing safe rich-text renderer, current UI text lookup, and current MathJax-friendly refresh flow
- preserve current unavailable and unscored behavior for non-success analysis payloads

# Key Deliverables

- Prompt contract update for `Speaking Flexible` analysis output
- Analysis payload normalization layer for optional structured fields
- Shared `AI Analysis` section model and shared HTML renderer
- `AI Analysis` block UI extended to render:
  - feedback
  - sample answers
  - alternative questions
- Focused tests for prompt contract, parser normalization, fallback-state behavior, and UI rendering symmetry

# Task/Wave Breakdown

## Wave 1: Prompt contract

Update `Speaking Flexible` analysis prompt so returned JSON includes:

- `score`
- `tips`
- `sample_answers`
- `question_variants`

Rules:

- `sample_answers`: 2–3 strings
- `question_variants`: 2–3 strings
- at least one sample answer must explicitly build from learner answer
- prompt contract applies only to successful `Speaking Flexible` AI Analysis responses

## Wave 2: Canonical payload normalization

Add one normalization step immediately after JSON parse succeeds for successful scored payloads.

Successful normalized payload shape:

```python
{
    "scored": True,
    "score": int,
    "tips": str,
    "sample_answers": list[str],
    "question_variants": list[str],
}
```

Unavailable or unscored payloads keep current fallback shape and behavior. They do not gain extra optional sections.

Normalization rules:

- `tips`
  - if string: keep
  - else: fallback to existing no-tips string or empty string
- `sample_answers`
  - if list: keep only string items with non-empty trimmed content
  - trim each item
  - if cleaned length is greater than `3`, keep first `3`
  - if cleaned length is `2` or `3`, keep list
  - if cleaned length is less than `2`, normalize to `[]`
  - if invalid or missing: `[]`
- `question_variants`
  - same rules as `sample_answers`
- unknown future keys
  - preserve if harmless, but renderer ignores them unless mapped into canonical sections

This normalization layer becomes single source of truth for `AI Analysis` data consumed by UI.

## Wave 3: Shared section model

Add one shared section builder for `AI Analysis`.

Canonical section model:

```python
[
    {"key": "tips", "title_key": None, "kind": "rich_text", "value": str},
    {"key": "sample_answers", "title_key": "ai_analysis_sample_answers", "kind": "string_list", "value": list[str]},
    {"key": "question_variants", "title_key": "ai_analysis_question_variants", "kind": "string_list", "value": list[str]},
]
```

Rules:

- section list is built from normalized payload only
- section titles come from existing AI UI text lookup SSOT, not hardcoded English literals in renderer
- `tips` is untitled inside panel body because panel header already owns `AI Analysis`
- empty list sections are omitted
- empty string sections are omitted except `tips`, which keeps current fallback behavior
- no direct template branching on raw JSON keys outside section builder

## Wave 4: Shared section rendering

Add one shared renderer for `AI Analysis` section bodies.

Rendering rules:

- `rich_text`
  - render with existing `render_ai_rich_text(...)`
- `string_list`
  - render as semantic `<ul>`
  - each `<li>` item rendered with existing `render_ai_rich_text(...)`
- no separate markdown or sanitizer logic for list items
- no special rendering path for formulas inside list items; existing rich renderer plus MathJax refresh handles all text fields uniformly

## Wave 5: Panel composition

Update `AI Analysis` panel template to render:

- header with title, regenerate button, score badge
- body containing one or more normalized sections for successful scored payloads only

Recommended order:

1. `tips`
2. `sample_answers`
3. `question_variants`

Section title behavior:

- panel header remains only owner of `AI Analysis` title
- `sample_answers` and `question_variants` render as subordinate titled sections inside same panel body
- unavailable or unscored states keep current single-body fallback behavior and do not render extra sections

## Wave 6: Tests

Extend UI contract tests to cover:

- prompt template contains required structured field names and 2–3 cardinality language for `Speaking Flexible`
- parser accepts extra fields without breaking existing `score` and `tips`
- invalid `sample_answers` type normalizes to `[]`
- invalid `question_variants` type normalizes to `[]`
- cleaned 1-item lists normalize to `[]` and do not render
- cleaned lists longer than `3` truncate to first `3`
- list items render through same rich renderer as `tips`
- formulas inside sample answers and question variants survive into rendered HTML and get same post-refresh MathJax path as existing rich text
- empty sections omitted from DOM
- unavailable or unscored payload does not render `sample_answers` or `question_variants`
- existing analysis-only payload still renders exactly as before

# Design Decisions

## 1. One normalized payload

Reason:

- SSOT for parsed AI analysis
- prevents template code from reinterpreting raw AI JSON
- future fields added in one place

## 2. One shared section renderer

Reason:

- symmetry across `tips`, `sample_answers`, `question_variants`
- no drift where bold, lists, or math work in one field but not another

## 3. Reuse existing rich renderer

Reason:

- existing `render_ai_rich_text(...)` already owns safe markdown subset handling
- existing post-refresh MathJax hook already exists
- shortest safe path

## 4. Reuse existing UI text SSOT

Reason:

- avoids duplicate ownership for section labels
- keeps localization path consistent with current AI panel strings
- prevents duplicate `AI Analysis` heading in panel body

## 5. Optional fields only for successful scored payloads

Reason:

- `Speaking Flexible` needs structured extras now
- other profiles may continue returning only `score` and `tips`
- unavailable and unscored states keep current semantics
- parser remains backward-compatible

# Invariants

1. `AI Analysis` UI reads structured data only from normalized analysis payload.
2. All text-like `AI Analysis` content uses same safe rich-text rendering path.
3. List-based AI content uses same sanitizer and MathJax lifecycle as paragraph content.
4. Optional list sections render only when cleaned list length is `2` or `3`.
5. Empty optional fields do not create empty UI shells.
6. Existing profiles without new fields keep working.
7. Unavailable or unscored payloads never render extra optional sections.
8. No logic duplicates question or sample rendering in multiple template branches.
9. Prompt contract and UI contract stay aligned:
   - prompt names fields
   - parser normalizes fields
   - renderer maps fields to sections

# Acceptance Criteria

1. `Speaking Flexible` prompt explicitly requests:
   - 2–3 `sample_answers`
   - 2–3 `question_variants`
   - at least one sample answer built from learner answer
2. JSON with valid `sample_answers` and `question_variants` displays them in `AI Analysis` block.
3. After cleanup, `sample_answers` and `question_variants` render only when cleaned length is `2` or `3`; values longer than `3` truncate to first `3`; values shorter than `2` are omitted.
4. Section labels for new fields come from existing AI UI text lookup, not hardcoded body literals.
5. Bold, italic, inline code, lists, fenced code blocks, and math delimiters render consistently inside:
   - `tips`
   - each sample answer
   - each question variant
6. Existing `AI Analysis` output containing only `score` and `tips` remains supported with no visual regression.
7. Unavailable or unscored payloads preserve current fallback behavior and do not show extra sections.
8. No raw JSON keys appear in rendered panel.
9. Rendering order is deterministic and section titles are stable.

# Non-Goals

- changing `AI Hint` payload shape
- adding collapsible sections
- adding per-profile custom section titles
- persisting sample answers or question variants outside current analysis payload
- adding new storage schema or cache layer
- supporting arbitrary nested JSON structures in `AI Analysis`
- adding brand-new markdown or HTML capabilities beyond current safe renderer policy

# Risks and Mitigations

## Risk: prompt returns malformed list values

Mitigation:

- normalize aggressively
- drop non-string items
- enforce cleaned cardinality rule in one normalizer
- omit bad sections instead of failing full analysis block

## Risk: formulas render in `tips` but not list items

Mitigation:

- force all item rendering through same `render_ai_rich_text(...)` path

## Risk: renderer drift from parser contract

Mitigation:

- one section builder owns field mapping
- tests assert structured fields appear through shared renderer path

## Risk: duplicate or untranslated body titles

Mitigation:

- derive section labels from existing UI text lookup
- keep `tips` untitled inside panel body

## Risk: UI clutter

Mitigation:

- fixed section order
- omit empty sections
- no extra chrome beyond simple titles and lists

# Validation Plan

- proof target: `Speaking Flexible` prompt requests structured extras
  - method: focused test
  - evidence: `packages/score_answer_anki/test_ai_analysis_ui_contract.py` asserts prompt template contains `sample_answers`, `question_variants`, and `2–3` cardinality language

- proof target: normalized payload is canonical SSOT
  - method: focused test plus inspection
  - evidence: one normalization helper used before `AI Analysis` panel render and tests cover invalid, short, and overlong list cases

- proof target: list sections render in `AI Analysis` block
  - method: focused test
  - evidence: `packages/score_answer_anki/test_ai_analysis_ui_contract.py` asserts section labels and items appear in rendered HTML

- proof target: formulas survive inside list items
  - method: focused test
  - evidence: rendered HTML contains canonical math delimiters from sample answer or question variant content and existing refresh typeset hook remains active

- proof target: backward compatibility
  - method: regression test
  - evidence: existing analysis payload with only `score` and `tips` still passes prior UI contract assertions

- proof target: unavailable or unscored semantics stay stable
  - method: focused test
  - evidence: unavailable or unscored payload renders current fallback body and omits optional sections

# Completion Criteria

- prompt updated
- parser normalization added
- shared section builder added
- new section labels sourced from existing AI UI text lookup
- `AI Analysis` panel renders `tips`, `sample_answers`, `question_variants` for successful scored payloads
- unavailable or unscored behavior unchanged
- focused tests green
- no regression in existing analysis-only rendering
