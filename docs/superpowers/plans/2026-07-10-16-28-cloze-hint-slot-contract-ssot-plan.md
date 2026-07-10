---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: cloze-hint-slot-contract-ssot
parent_spec: docs/superpowers/specs/2026-07-10-16-20-cloze-hint-slot-contract-ssot-spec.md
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
  - packages/score_answer_anki/README.md
  - packages/score_answer_anki/Config.md
  - packages/score_answer_anki/docs/superpowers/specs/2026-07-05-11-23-hint-panel-ai-suggestions-spec.md
related_features:
  - front-hint-panel
  - cloze-answer-contract
  - ai-analysis-ui
related_stages:
  - design
---

# Cloze Hint Slot Contract SSOT Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement one shared active-slot field contract so cloze answer fields and manual hint fields resolve from same slot index, with no `Hint2+` fallback, explicit unresolved-slot behavior, and aligned docs/spec proofs.

**Architecture:** Keep slot ownership in one small helper near current cloze mapping helpers in `__init__.py`. Route answer contract and manual hint lookup through that helper. Preserve existing AI hint, scoring, and cloze parsing flows. Extend one focused test file to prove symmetry and unresolved-slot behavior. Patch the older hint-panel spec so doc-layer SSOT matches runtime SSOT.

**Tech Stack:** Python stdlib, existing add-on helper patterns, existing assert-based test files, existing docs/spec markdown files, existing sync script.

---

# Goal

Implement approved cloze hint slot contract update in the smallest safe way:

- one active-slot helper owns `Back`, `Back_variants`, and `Hint` family mapping
- slot `1` remains base-name exception
- slot `x > 1` uses suffixed names uniformly
- answer path keeps current invalid-contract behavior for unresolved or missing required fields
- hint path stays optional and returns empty string for unresolved slot or missing mapped hint field
- no runtime fallback from `Hint2+` to unsuffixed `Hint`
- old hint-panel spec no longer conflicts with new manual-hint contract

# Key Deliverables

- One shared slot-field resolver in `packages/score_answer_anki/__init__.py`
- One answer-contract update consuming shared slot-field resolver
- One manual-hint lookup update consuming shared slot-field resolver
- Focused regression proof for base slot, suffixed slots, missing mapped hint, and unresolved active slot
- Docs update for mapped manual hint behavior in `README.md` and `Config.md`
- One old-spec patch removing or superseding stale "field name is exactly `Hint`" wording

# Task Breakdown

### Task 1: Lock slot-contract behavior with failing tests

**Files:**
- Modify: `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

**Step 1: Extend dummy note fields for mapped hints**

Add explicit hint-family fields to dummy note fixtures used by cloze/front-hint tests:

- `Hint`
- `Hint2`
- `Hint3`
- `Hint4`

Populate distinct values so slot selection is observable.

**Step 2: Add shared-slot mapping assertions**

Add failing assertions proving slot mapping resolves:

- slot `1` to `Back`, `Back_variants`, `Hint`
- slot `2` to `Back2`, `Back2_variants`, `Hint2`
- slot `3` to `Back3`, `Back3_variants`, `Hint3`
- slot `4` to `Back4`, `Back4_variants`, `Hint4`

Prefer one helper-level assertion block if shared slot resolver is exposed, plus existing answer-mapping assertions if wrapper remains.

**Step 3: Add manual-hint slot assertions**

Add failing assertions showing:

- plain score card returns `Hint`
- cloze ord `0` returns `Hint`
- cloze ord `1` returns `Hint2`
- cloze ord `2` returns `Hint3`
- cloze ord `3` returns `Hint4`

Use `get_manual_hint_html(...)` or `build_front_hint_context(...)` as proof surface.

**Step 4: Add failure-mode assertions**

Add failing assertions proving:

- missing mapped hint field returns empty string and does not invalidate hint path
- missing mapped answer fields still invalidate answer contract
- unresolved active slot leaves answer contract invalid and returns empty manual hint
- no case falls back from `Hint2+` to unsuffixed `Hint`

**Step 5: Run tests red**

Run:

```powershell
py -3 test_ai_analysis_ui_contract.py
```

Expected:
- new slot/hint assertions fail before implementation

---

### Task 2: Add one shared slot-field resolver in runtime

**Files:**
- Modify: `packages/score_answer_anki/__init__.py`
- Modify: `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

**Step 1: Add one shared slot helper**

Near current cloze mapping helpers, add one SSOT helper with plain return shape, for example:

```python
def resolve_slot_field_names(slot_index: int) -> dict[str, str]:
    ...
```

Return exactly:

- `answer_field`
- `answer_variants_field`
- `hint_field`

Keep slot `1` base-name exception encoded only here.

**Step 2: Keep answer-only wrapper thin or delete it**

If `resolve_answer_field_names(...)` remains for compatibility with tests or nearby callers, make it a thin wrapper over shared slot helper only.

No second naming path.

**Step 3: Keep helper pure**

Helper must:

- not inspect reviewer globals
- not read note contents
- not perform validation
- only map slot index to field names

**Step 4: Run focused tests**

Run:

```powershell
py -3 test_ai_analysis_ui_contract.py
```

Expected:
- slot-field mapping assertions pass
- unrelated front-hint behavior may still fail until later tasks land

---

### Task 3: Route answer contract through shared slot helper

**Files:**
- Modify: `packages/score_answer_anki/__init__.py`
- Modify: `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

**Step 1: Keep plain-card behavior unchanged**

For non-cloze score cards, preserve current base-field behavior:

- `Back`
- `Back_variants`

No new branching beyond using base slot semantics if reuse is cheap.

**Step 2: Replace bespoke cloze answer mapping**

Inside `build_answer_contract(...)`:

- resolve active slot
- if unresolved, keep current invalid-contract behavior
- otherwise fetch mapped answer field names from shared slot helper
- use mapped names for field-presence checks and data reads

**Step 3: Preserve existing invalidity semantics**

Keep current behavior for:

- unresolved active slot
- missing mapped answer field
- missing mapped answer-variants field
- missing active cloze group in `Front`
- invalid multi-segment canonical back contract

Only naming ownership changes here.

**Step 4: Keep invalid messages truthful**

Invalid reason text must name actual mapped fields from shared helper.

**Step 5: Run focused tests**

Run:

```powershell
py -3 test_ai_analysis_ui_contract.py
```

Expected:
- existing cloze answer-contract assertions still pass
- missing mapped answer-field assertions still pass

---

### Task 4: Route manual hint lookup through shared slot helper

**Files:**
- Modify: `packages/score_answer_anki/__init__.py`
- Modify: `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

**Step 1: Remove hardcoded `Hint` lookup from active-slot path**

Update `get_manual_hint_html(...)` so active-slot behavior comes from shared slot helper, not hardcoded field name.

Preferred behavior:

- non-cloze score card uses base slot `Hint`
- cloze card with resolved slot uses mapped `Hint{x}`
- unresolved active slot returns empty string
- missing mapped hint field returns empty string
- blank mapped hint stays blank

**Step 2: Preserve current front-hint UI ownership**

Do not change:

- `build_front_hint_context(...)` shape
- hint cache key builder shape
- AI hint transport
- render ordering

Only `manual_hint` source changes.

**Step 3: Keep no-fallback rule explicit**

Do not add:

- fallback from `Hint2+` to `Hint`
- cross-slot merge logic
- per-call-site inference from answer field names

**Step 4: Run focused tests**

Run:

```powershell
py -3 test_ai_analysis_ui_contract.py
```

Expected:
- manual hint slot assertions pass
- unresolved-slot returns empty string
- no-fallback assertions pass

---

### Task 5: Align docs and old spec with runtime SSOT

**Files:**
- Modify: `packages/score_answer_anki/README.md`
- Modify: `packages/score_answer_anki/Config.md`
- Modify: `packages/score_answer_anki/docs/superpowers/specs/2026-07-05-11-23-hint-panel-ai-suggestions-spec.md`

**Step 1: Update user-facing docs**

Change manual-hint wording so docs say:

- manual hint comes from mapped active-slot hint field
- base slot uses `Hint`
- cloze slot `x > 1` uses `Hint{x}`
- missing mapped hint field behaves as empty manual hint

Keep AI hint language and render semantics unchanged.

**Step 2: Remove stale exact-name claim from old spec**

Update old hint-panel spec so it no longer claims:

- note field name is exactly `Hint`

Replace with slot-driven manual-hint wording or explicit supersession reference to new slot-contract spec.

**Step 3: Keep docs aligned with no-fallback rule**

Do not describe migration fallback or hybrid lookup.

**Step 4: Review docs diff**

Confirm old spec, `README.md`, and `Config.md` all describe same manual-hint contract.

---

### Task 6: Final verification and sync

**Files:**
- Modify: `packages/score_answer_anki/__init__.py`
- Modify: `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- Modify: `packages/score_answer_anki/README.md`
- Modify: `packages/score_answer_anki/Config.md`
- Modify: `packages/score_answer_anki/docs/superpowers/specs/2026-07-05-11-23-hint-panel-ai-suggestions-spec.md`
- Run: `packages/score_answer_anki/scripts/sync_to_anki.ps1`

**Step 1: Run focused test proof**

Run:

```powershell
py -3 test_ai_analysis_ui_contract.py
```

Expected:
- all slot-contract, hint, and existing cloze assertions pass

**Step 2: Run syntax proof**

Run:

```powershell
py -3 -m py_compile __init__.py test_ai_analysis_ui_contract.py
```

Expected:
- no output
- exit code `0`

**Step 3: Sync add-on into Anki**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\sync_to_anki.ps1
```

Expected:
- sync success message with target add-on path

**Step 4: Manual Anki check**

Open representative cards and confirm:

- plain `_score` typed-answer card shows existing manual `Hint`
- cloze `c1` card shows `Hint`
- cloze `c2` card shows `Hint2`
- cloze `c3` card shows `Hint3`
- cloze `c4` card shows `Hint4`
- missing mapped `Hint{x}` shows no manual hint and does not break panel
- unresolved cloze slot does not leak unsuffixed `Hint`
- answer comparison and AI hint behavior remain unchanged

---

# Risks / Rollback

- Risk: shared helper duplicates existing answer-only mapping instead of replacing it
  - rollback: make `resolve_answer_field_names(...)` a thin wrapper over one shared slot helper only
- Risk: unresolved cloze cards start showing stale base `Hint`
  - rollback: keep unresolved-slot hint behavior as explicit empty string and test it directly
- Risk: doc-layer SSOT remains split after runtime fix
  - rollback: patch old hint-panel spec in same change set, not later
- Risk: broader front-hint behavior changes accidentally piggyback on mapping refactor
  - rollback: limit runtime diff to field-resolution call sites and their focused tests/docs only

# Verification

- [ ] `py -3 test_ai_analysis_ui_contract.py`
- [ ] `py -3 -m py_compile __init__.py test_ai_analysis_ui_contract.py`
- [ ] `powershell -ExecutionPolicy Bypass -File scripts\sync_to_anki.ps1`
- [ ] Manual Anki check verifies:
  - [ ] plain `_score` card still uses `Hint`
  - [ ] cloze `c1` uses `Hint`
  - [ ] cloze `c2` uses `Hint2`
  - [ ] cloze `c3` uses `Hint3`
  - [ ] cloze `c4` uses `Hint4`
  - [ ] missing mapped hint field behaves as empty manual hint
  - [ ] unresolved active slot returns empty manual hint
  - [ ] no fallback from `Hint2+` to `Hint`
  - [ ] answer comparison behavior is unchanged
  - [ ] AI hint behavior is unchanged

# Completion Criteria

- one shared slot-field helper owns active-slot answer-family and hint-family mapping
- answer contract consumes shared helper for cloze slot field names
- `get_manual_hint_html(...)` no longer hardcodes active-slot `Hint`
- focused tests prove base slot, suffixed slots, missing mapped hint, and unresolved active slot behavior
- `README.md`, `Config.md`, and old hint-panel spec all describe same slot-driven manual-hint contract
- no compatibility fallback remains in runtime for `Hint2+`
