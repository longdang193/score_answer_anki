---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: expected-answer-alternatives-display
parent_spec: packages/score_answer_anki/docs/superpowers/specs/2026-07-06-00-01-expected-answer-alternatives-display-spec.md
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
  - packages/score_answer_anki/test_question_variants_contract.py
---

# Expected Answer Alternatives Display Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show acceptable alternative answers under the `Expected` column using the existing accepted-answer-pool SSOT, while keeping `Back` as the primary expected value and keeping AI coaching examples out of the comparison block.

**Architecture:** Keep answer-acceptance ownership in `build_accepted_answer_pool(card)`. Build one tiny expected-display model inside `render_enhanced_comparison(...)` while card context is already present. Pass display-ready values into `_code_compare_block(...)` or one nearby pure renderer. Reuse existing escaping and current compare layout rather than introducing a new component layer.

**Tech Stack:** Python stdlib, existing add-on HTML string rendering, existing assert-based test files, existing sync script.

---

# Goal

Implement approved expected-answer alternative display in the smallest safe way:

- `Back` stays canonical displayed expected answer
- `Back_variants` stays acceptance-only input
- accepted-answer pool remains SSOT
- renderer gets plain display-ready values only
- alternative chips appear only when non-canonical acceptable answers exist
- question-side variant behavior and AI scoring behavior stay unchanged

# Key Deliverables

- One small expected-display-model helper built in `render_enhanced_comparison(...)`
- One compare-renderer update for subordinate acceptable-answer chips under `Expected`
- One normalization rule reusing the same text-cleaning path as primary expected display
- Focused regression coverage for SSOT, dedupe, omission, and fallback behavior

# Task Breakdown

### Task 1: Lock display contract with failing tests

**Files:**
- Modify: `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- Modify: `packages/score_answer_anki/test_question_variants_contract.py`

**Step 1: Add expected-column rendering assertions**

In `test_ai_analysis_ui_contract.py`, add failing assertions for rendered comparison HTML covering:

- canonical expected answer still appears
- acceptable alternative answers render under `Expected`
- canonical answer does not repeat in chip list
- `sample_answers` from cached AI analysis do not appear inside compare block

Use representative data like:

```python
card.note()["Back"] = "My name is Long"
card.note()["Back_variants"] = "I'm Long;;Long is my name"
```

Then assert rendered HTML contains:

- `My name is Long`
- `I'm Long`
- `Long is my name`

and does not duplicate canonical answer inside chip list.

**Step 2: Add accepted-answer-pool cleanup assertions**

In `test_question_variants_contract.py`, extend existing `build_accepted_answer_pool(card)` coverage with duplicates and blanks, for example:

```python
"Back_variants": "two hundred twenty-one;; ;;221.0;;two hundred twenty-one"
```

Assert cleaned pool remains ordered and unique.

**Step 3: Add fallback assertions**

Add one failing assertion proving missing-card or unsupported-card render path stays primary-only and does not emit alternative chip container.

**Step 4: Run tests red**

Run:

```powershell
py -3 packages\score_answer_anki\test_question_variants_contract.py
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- at least one new assertion fails in each touched test file or in the focused rendering test file

---

### Task 2: Build expected-display model from accepted-answer SSOT

**Files:**
- Modify: `packages/score_answer_anki/__init__.py`
- Modify: `packages/score_answer_anki/test_question_variants_contract.py`

**Step 1: Add one tiny display-model helper**

Near `build_accepted_answer_pool(card)`, add one helper with a plain return shape, for example:

```python
def build_expected_display_model(card, expected_text: str) -> dict:
    ...
```

Required behavior:

- if `card` is missing, return primary-only display model from `expected_text`
- otherwise call `build_accepted_answer_pool(card)` once
- set primary value from canonical answer when available, else fallback to `expected_text`
- build alternatives from non-canonical accepted answers only
- preserve accepted-answer-pool order
- do not parse `Back_variants` directly here; only consume helper output

**Step 2: Reuse primary text-normalization path**

Ensure alternatives use same text-cleaning path as primary expected display before escaping.

If current primary path is `extract_code_text(...)`, reuse it for each alternative value before chip rendering.

Drop alternatives that normalize to blank.

**Step 3: Keep helper side-effect free**

Do not read `mw.reviewer.card` inside this helper.
Do not touch caches.
Do not read AI analysis payload.

**Step 4: Run focused tests**

Run:

```powershell
py -3 packages\score_answer_anki\test_question_variants_contract.py
```

Expected:
- accepted-answer-pool cleanup still passes
- new display-model related assertions pass if added there

---

### Task 3: Render acceptable-answer chips in compare block

**Files:**
- Modify: `packages/score_answer_anki/__init__.py`
- Modify: `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

**Step 1: Keep ownership in caller**

Inside `render_enhanced_comparison(...)`:

- keep existing `card` lookup
- build expected display model there
- pass plain display values into compare renderer

Do not make `_code_compare_block(...)` read global reviewer state.

**Step 2: Extend compare renderer minimally**

Update `_code_compare_block(...)` or one nearby pure helper so `Expected` column can render:

- existing localized label
- primary canonical expected value
- optional variant-chip container under primary value

Keep `Your answer` column unchanged.

**Step 3: Reuse or add one small chip renderer**

Prefer one parameterized helper if reuse is cheap.
If not, add one answer-side local helper with same semantics as question chips:

- escape text
- omit empty container
- preserve order

Do not broaden question-side selection logic.
Do not add new headings in V1.

**Step 4: Run focused rendering test**

Run:

```powershell
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- expected column shows primary plus acceptable alternatives
- canonical answer not duplicated in chips
- `Your answer` column remains unchanged

---

### Task 4: Preserve fallback and non-leakage behavior

**Files:**
- Modify: `packages/score_answer_anki/__init__.py`
- Modify: `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

**Step 1: Guard missing-card and unsupported paths**

Ensure compare rendering keeps current primary-only behavior when:

- `card` is missing
- card is unsupported for typed-answer enhancement
- accepted-answer pool has no non-canonical alternatives

No empty chip wrapper should render.

**Step 2: Preserve AI separation**

Ensure comparison block does not consume `sample_answers` or any other AI Analysis structured fields.

The compare block must stay sourced from:

- caller-provided expected text
- caller-provided provided text
- accepted-answer pool derived from card

Nothing else.

**Step 3: Run fallback tests**

Run:

```powershell
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- missing-card or unsupported-card assertions pass
- compare block remains free of `sample_answers`

---

### Task 5: Final verification and sync

**Files:**
- Modify: `packages/score_answer_anki/__init__.py`
- Modify: `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- Modify: `packages/score_answer_anki/test_question_variants_contract.py`
- Run: `packages/score_answer_anki/scripts/sync_to_anki.ps1`

**Step 1: Run full focused test set**

Run:

```powershell
py -3 packages\score_answer_anki\test_question_variants_contract.py
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- all assertions pass

**Step 2: Run syntax proof**

Run:

```powershell
py -3 -m py_compile packages\score_answer_anki\__init__.py packages\score_answer_anki\test_question_variants_contract.py packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- no output
- exit code `0`

**Step 3: Sync add-on into Anki**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File packages\score_answer_anki\scripts\sync_to_anki.ps1
```

Expected:
- sync success message with target add-on path

**Step 4: Manual Anki check**

Open one `_score` card with answer variants and confirm:

- `Expected` still shows primary canonical answer
- alternative acceptable answers appear as subordinate chips below it
- no extra heading appears in V1
- `Your answer` column looks unchanged
- cards without `Back_variants` look unchanged
- question-side variant chips still behave as before
- AI Analysis `Sample Answers` stay inside AI panel and never appear in compare block

---

# Risks / Rollback

- Risk: compare renderer starts reading card-global state
  - rollback: keep card lookup and display-model construction in `render_enhanced_comparison(...)` only
- Risk: alternative chips show raw markup-like text while primary expected text is cleaned
  - rollback: route alternatives through same text-normalization path as primary expected display
- Risk: accepted-answer semantics drift from UI semantics
  - rollback: keep `build_accepted_answer_pool(card)` as sole source for alternatives
- Risk: empty chip container clutters unchanged cards
  - rollback: render chip container only when non-canonical cleaned alternatives exist

# Verification

- [ ] `py -3 packages\score_answer_anki\test_question_variants_contract.py`
- [ ] `py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py`
- [ ] `py -3 -m py_compile packages\score_answer_anki\__init__.py packages\score_answer_anki\test_question_variants_contract.py packages\score_answer_anki\test_ai_analysis_ui_contract.py`
- [ ] `powershell -ExecutionPolicy Bypass -File packages\score_answer_anki\scripts\sync_to_anki.ps1`
- [ ] Manual Anki check verifies:
  - [ ] canonical expected answer remains primary
  - [ ] acceptable alternatives render only when present
  - [ ] canonical answer is not duplicated in chips
  - [ ] missing/unsupported-card path stays primary-only
  - [ ] `sample_answers` do not leak into compare block
  - [ ] question-side variant behavior remains unchanged

# Completion Criteria

- expected-answer display model is built in `render_enhanced_comparison(...)` from accepted-answer-pool SSOT
- compare renderer consumes display-ready values only
- alternative-answer chips render under `Expected` when non-canonical acceptable answers exist
- primary expected answer remains canonical and visually dominant
- missing-card, unsupported-card, and no-variant paths keep current behavior
- focused tests and syntax proof pass
