---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: question-variant-cache-root-cause
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/test_question_variants_contract.py
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
---

# Goal

Fix front-side question variant lifecycle in `score_answer_anki` so same card can show different eligible variants on later front-side exposures, while preserving one stable chosen variant across one review cycle for front render, hint generation, answer render, and AI analysis.

Exposure contract, SSOT:

- one exposure = one logical question-side showing of one review card before answer reveal
- repeated question-side rerenders inside same exposure must keep same chosen variant
- only transition into a new front-side exposure may choose a new variant for same card

# Key Deliverables

- One root-cause patch in `packages/score_answer_anki/__init__.py` that resets variant choice at new front-side exposure boundary only
- One regression test update in `packages/score_answer_anki/test_question_variants_contract.py` covering cross-exposure reshuffle with same-cycle stability
- One verification pass confirming hint and analysis cache behavior follows visible-question identity without extra cache redesign

# Task Breakdown

## Task 1: Add failing regression for exposure lifecycle

Files:
- `packages/score_answer_anki/test_question_variants_contract.py`

Steps:
- Add one test for same card across two front-side exposures.
- Add one test for repeated question-side render inside same exposure.
- Assert first front-side render chooses variant A.
- Assert repeated front-side render in same exposure still uses variant A.
- Assert same review cycle answer-side path keeps variant A.
- Assert only real new-exposure transition allows later front-side exposure to choose variant B.
- Keep existing helpers and RNG stubs; no new fixture layer.

Verification:
- Test fails before code patch because same card stays pinned to prior chosen variant.
- Test fails before code patch or candidate patch if repeated question-side render reshuffles variant inside same exposure.

## Task 2: Patch exposure boundary in render path

Files:
- `packages/score_answer_anki/__init__.py`

Steps:
- Trace current front-side entry through `_to_textarea_on_question(...)` and `apply_question_variant_to_rendered_question(...)`.
- Add one SSOT exposure-boundary rule in code so reset happens only on transition into a new front-side exposure, not on every `Question` render.
- Do not clear on answer-side render.
- Keep existing active-state structure unless test proves one extra exposure token is needed.
- Preserve same chosen variant for later reads in same cycle by leaving hint/answer accessors unchanged.

Verification:
- Same card can select different variant on later front-side exposure.
- Same exposure keeps one stable chosen variant for front, hint, and answer paths.

## Task 3: Recheck cache coupling after lifecycle fix

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Confirm analysis cache key still derives from visible question plus answer tuple.
- Confirm hint cache key still derives from visible question plus hint prompt identity.
- Add or adjust narrow assertions that changed visible question produces changed hint context/cache key and changed analysis cache key/context.
- Do not redesign cache policy unless stale behavior remains after Task 2.

Verification:
- New visible question creates new hint/analysis cache identity.
- Explicit regenerate still invalidates current key only.

## Task 4: Run focused proof

Files:
- `packages/score_answer_anki/test_question_variants_contract.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Run `python packages/score_answer_anki/test_question_variants_contract.py`.
- Run `python packages/score_answer_anki/test_ai_analysis_ui_contract.py`.
- Sync this worktree's `packages/score_answer_anki` into local Anki add-on location used for manual verification.
- If both tests pass and sync is complete, do one manual Anki check on repeated front-side exposures of same eligible `_score` card.

Verification:
- Front-side no longer stays stuck on one variant across exposures.
- Repeated question-side rerender in same exposure does not reshuffle variant.
- Answer-side still matches front-side chosen variant within same cycle.
- Hint and analysis behavior changes only when visible question changes or regenerate is clicked.

# Final Verification

- [x] `python packages/score_answer_anki/test_question_variants_contract.py`
- [x] `python packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- [x] Worktree add-on code synced into local Anki add-on path used for manual verification
- [ ] Manual Anki check with same eligible `_score` card across repeated front-side exposures verifies:
  - [ ] front-side variant changes across exposures
  - [ ] repeated question-side rerender in same exposure keeps same variant
  - [ ] answer-side keeps same variant chosen on front
  - [ ] `Suggest Hint` result tracks current visible question
  - [ ] AI analysis result tracks current visible question

# Completion Criteria

- Same card is not session-pinned to one variant when shown again on front side.
- One review cycle still has one stable visible question.
- Hint and analysis cache behavior follows visible-question identity, not stale session state.
