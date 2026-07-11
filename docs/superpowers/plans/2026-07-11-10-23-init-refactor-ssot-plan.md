---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: init-refactor-ssot
parent_spec: packages/score_answer_anki/docs/superpowers/specs/2026-07-11-10-10-init-refactor-ssot-spec.md
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/locales.py
  - packages/score_answer_anki/config_model.py
  - packages/score_answer_anki/ai_runtime.py
  - packages/score_answer_anki/reviewer_ui.py
  - packages/score_answer_anki/configs/prompt_defaults.json
  - packages/score_answer_anki/scripts/sync_to_anki.ps1
  - packages/score_answer_anki/README.md
  - packages/score_answer_anki/Config.md
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
  - packages/score_answer_anki/test_question_variants_contract.py
  - packages/score_answer_anki/test_cloze_hint_slot_contract.py
  - packages/score_answer_anki/test_custom_openai_contract.py
  - packages/score_answer_anki/test_notebooklm_auth_contract.py
  - packages/score_answer_anki/test_refactor_contract.py
related_features:
  - ai-analysis-ui
  - front-hint-panel
  - prompt-profiles
  - notebooklm-deep-analysis
  - typed-answer-input
related_stages:
  - implementation
---

# Init Refactor SSOT Implementation Plan

**Goal:** Execute `init-refactor-ssot` with smallest safe refactor that preserves shipped behavior, establishes single ownership for language/config/runtime/UI concerns, and makes sync-to-Anki deployment explicit and testable.

**Architecture:** Choose the lazy safe Wave-0 path first: keep one embedded stylesheet owner in `packages/score_answer_anki/reviewer_ui.py` for this cycle, not `reviewer.css`, because current add-on sync and test contracts already assume embedded reviewer CSS and no authoritative Anki asset-export path exists yet. Extract pure SSOT modules first (`locales.py`, `config_model.py`), then runtime (`ai_runtime.py`), then UI (`reviewer_ui.py`), then reduce `__init__.py` to bootstrap-only. Keep native Qt config widgets; drive repeated provider/mode UI from data specs instead of repeated builder branches.

**Tech Stack:** Python stdlib, existing Anki add-on hooks and Qt widgets, existing assert-based contract tests, existing PowerShell sync script.

---

# Goal

Implement the approved refactor in bounded, executable slices:

- shipping contract is locked before module split
- mutable state ownership is singular and explicit
- language SSOT lives in `locales.py`
- config SSOT lives in `config_model.py`
- provider and NotebookLM runtime boundary lives in `ai_runtime.py`
- reviewer render/UI/state boundary lives in `reviewer_ui.py`
- one embedded stylesheet owner moves out of `__init__.py` into `reviewer_ui.py`
- `__init__.py` becomes bootstrap-only
- docs and sync workflow stay aligned with shipped add-on behavior

# Key Deliverables

- One new `packages/score_answer_anki/test_refactor_contract.py` covering:
  - import smoke for extracted module graph
  - config round-trip for legacy-flat and normalized inputs
  - shipped add-on surface after sync
- One updated `packages/score_answer_anki/scripts/sync_to_anki.ps1` that copies every runtime file required by module split
- One `packages/score_answer_anki/locales.py` owning all language/text registries and getters
- One `packages/score_answer_anki/config_model.py` owning config defaults, normalization, persistence, provider metadata, and prompt-default loading
- One `packages/score_answer_anki/ai_runtime.py` owning provider request execution and NotebookLM session/query helpers
- One `packages/score_answer_anki/reviewer_ui.py` owning reviewer render helpers, JS-message handlers, config-dialog builders, reviewer mutable state, and embedded stylesheet ownership
- One bootstrap-only `packages/score_answer_anki/__init__.py`
- Focused doc updates in `packages/score_answer_anki/README.md` and `packages/score_answer_anki/Config.md`

# Task Breakdown

## Task 1: Lock shipping and refactor proof before extraction

**Files:**
- `packages/score_answer_anki/test_refactor_contract.py`
- `packages/score_answer_anki/scripts/sync_to_anki.ps1`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

**Steps:**
- Create `test_refactor_contract.py` with failing proofs for:
  - extracted-module import smoke from add-on-like package layout
  - config round-trip from legacy-flat input and normalized input
  - synced add-on folder containing every required runtime file
- Patch `sync_to_anki.ps1` to copy:
  - `__init__.py`
  - extracted `*.py` runtime modules
  - `configs/prompt_defaults.json`
  - docs already copied today only if still intentionally shipped
- Keep stylesheet plan explicit in tests: this cycle expects one embedded stylesheet owner and therefore no shipped `reviewer.css` requirement.
- Add one narrow UI-contract assertion proving reviewer CSS ownership is no longer rooted in `__init__.py` once extraction lands.

**Verification:**
- `python test_refactor_contract.py` fails before extraction because shipped surface and import graph are incomplete
- `sync_to_anki.ps1` has one authoritative runtime file list, not ad hoc copy drift

## Task 2: Extract language SSOT into `locales.py`

**Files:**
- `packages/score_answer_anki/locales.py`
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

**Steps:**
- Move language-owned data out of `__init__.py`:
  - `HINT_UI_TEXTS`
  - `AI_UI_TEXTS`
  - `LANG_TO_LABELS`
  - `LANGUAGES`
  - `LANGUAGE_INSTRUCTION_NAMES`
  - `LANGUAGE_REGISTRY`
- Move getter family into `locales.py`:
  - `_get_language_bundle(...)`
  - `get_compare_labels(...)`
  - `get_ui_texts(...)`
  - `get_hint_ui_texts(...)`
  - `get_ai_ui_texts(...)`
  - `get_supported_language_options(...)`
  - `get_language_name(...)`
  - `get_language_lock_instruction(...)`
- Patch call sites to import from `locales.py` instead of touching global tables.
- Delete duplicate language ownership from `__init__.py` rather than keeping compatibility aliases.

**Verification:**
- existing UI-contract tests still pass on language labels
- `test_refactor_contract.py` proves no parallel language tables remain authoritative in `__init__.py`

## Task 3: Extract config and prompt-default SSOT into `config_model.py`

**Files:**
- `packages/score_answer_anki/config_model.py`
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/configs/prompt_defaults.json`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- `packages/score_answer_anki/test_custom_openai_contract.py`
- `packages/score_answer_anki/test_refactor_contract.py`

**Steps:**
- Move config-owned constants and helpers into `config_model.py`:
  - `DEFAULT_CONFIG`
  - prompt-profile constants and normalizers
  - provider metadata and provider keys
  - default builders for `general`, `modes`, and `providers`
  - `merge_config_with_defaults(...)`
  - `build_persisted_config(...)`
  - `get_config(...)`
  - `save_config(...)`
  - prompt-default load/resolve helpers
- Keep normalized nested config as sole in-memory authority.
- Keep legacy flat-key compatibility at load/save boundary only.
- Add/patch tests for:
  - `legacy-flat -> normalized -> persisted`
  - `normalized -> persisted`
  - custom OpenAI base URL ownership still stays under provider block
- Keep config model stateless except file-backed read helpers.

**Verification:**
- `python test_custom_openai_contract.py`
- `python test_refactor_contract.py`
- no non-config module hand-rolls provider/model/config fallback logic after this task

## Task 4: Extract runtime boundary into `ai_runtime.py`

**Files:**
- `packages/score_answer_anki/ai_runtime.py`
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_notebooklm_auth_contract.py`
- `packages/score_answer_anki/test_refactor_contract.py`

**Steps:**
- Move provider/runtime logic into `ai_runtime.py`:
  - request formatting
  - provider HTTP execution
  - NotebookLM subprocess/session helpers
  - NotebookLM status ownership
  - prompt rendering entrypoints and analysis/hint request entrypoints that are runtime-owned
- Keep runtime mutable state singular in `ai_runtime.py` only for NotebookLM/runtime session data.
- Preserve current public runtime function names where possible to minimize diff.
- Patch tests to import runtime helpers directly without reviewer DOM stubs where feasible.
- Keep `ai_runtime.py` free of reviewer HTML and Qt widget imports.

**Verification:**
- `python test_notebooklm_auth_contract.py`
- `python test_refactor_contract.py`
- import smoke proves `ai_runtime.py` does not require reviewer render module to import

## Task 5: Extract reviewer UI boundary into `reviewer_ui.py`

**Files:**
- `packages/score_answer_anki/reviewer_ui.py`
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- `packages/score_answer_anki/test_question_variants_contract.py`
- `packages/score_answer_anki/test_cloze_hint_slot_contract.py`

**Steps:**
- Move reviewer-owned functions into `reviewer_ui.py`:
  - question-side text/input shaping
  - answer-side comparison rendering
  - front-hint rendering and actions
  - JS-message dispatch
  - panel refresh/regenerate/deep actions
  - config menu builder entrypoint
- Move reviewer-session mutable state into `reviewer_ui.py` only:
  - analysis caches
  - hint caches
  - current analysis/hint context
  - active question state
  - front hint panel state
- Move reviewer CSS ownership out of `__init__.py` into one bounded embedded stylesheet owner in `reviewer_ui.py`.
- Keep CSS semantics native:
  - body theme classes
  - CSS custom properties
  - `prefers-color-scheme` fallback in CSS only
- Keep `reviewer_ui.py` consuming runtime/config/locale helpers through imports, not duplicated local fallbacks.

**Verification:**
- `python test_ai_analysis_ui_contract.py`
- `python test_question_variants_contract.py`
- `python test_cloze_hint_slot_contract.py`
- no reviewer-owned mutable globals remain in `__init__.py`

## Task 6: Refactor native Qt config dialog to data-driven symmetric builders

**Files:**
- `packages/score_answer_anki/reviewer_ui.py`
- `packages/score_answer_anki/config_model.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

**Steps:**
- Split `setup_config_menu(...)` monolith into bounded helpers inside `reviewer_ui.py`.
- Keep native Qt widgets and tabs as sole widget primitives.
- Drive repeated `Standard` / `Deep` control construction from one mode-spec path.
- Drive repeated provider-tab construction from one provider-spec path.
- Keep shared custom prompt fields one-owner and shown by resolved profile state, not duplicated per tab.
- Preserve current field names and behavior while deleting repeated hand-built branches.

**Verification:**
- `test_ai_analysis_ui_contract.py` proves one mode-spec path and one provider-spec path
- dialog still exposes same user-facing settings without duplicate ownership

## Task 7: Reduce `__init__.py` to bootstrap-only and patch sync surface

**Files:**
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/scripts/sync_to_anki.ps1`
- `packages/score_answer_anki/test_refactor_contract.py`

**Steps:**
- Reduce `__init__.py` to:
  - imports needed by add-on load
  - one `init()`
  - hook registration delegation
  - config-menu registration delegation
- Remove domain logic, mutable state, and CSS ownership from `__init__.py`.
- Keep any temporary bootstrap-owned loader/export registration only if required by add-on load mechanics.
- Finalize sync script to copy exact runtime module set and `configs/prompt_defaults.json`.
- Add shipped-surface assertions for final file list in `test_refactor_contract.py`.

**Verification:**
- `__init__.py` stays under hard target `400` lines
- `python test_refactor_contract.py` proves shipped file list and import smoke

## Task 8: Update docs and run focused end-to-end verification

**Files:**
- `packages/score_answer_anki/README.md`
- `packages/score_answer_anki/Config.md`
- `packages/score_answer_anki/scripts/sync_to_anki.ps1`
- all touched tests/files as needed

**Steps:**
- Update docs to reflect:
  - architecture ownership only where useful to operators/contributors
  - same user-visible settings topology
  - sync expectations if contributor workflow changed
- Run focused checks:

```powershell
python test_refactor_contract.py
python test_ai_analysis_ui_contract.py
python test_question_variants_contract.py
python test_cloze_hint_slot_contract.py
python test_custom_openai_contract.py
python test_notebooklm_auth_contract.py
python -m py_compile __init__.py locales.py config_model.py ai_runtime.py reviewer_ui.py
powershell -ExecutionPolicy Bypass -File scripts\sync_to_anki.ps1
```

- Manual Anki smoke on one eligible `_score` card:
  - front-side typed question still renders correctly
  - front hint still works
  - answer-side AI analysis still renders
  - deep analysis action still works when configured
  - config dialog opens without runtime/import errors

**Verification:**
- docs no longer mention dead architecture details
- shipped add-on works after sync, not only in worktree tests

# Verification

- `python test_refactor_contract.py`
- `python test_ai_analysis_ui_contract.py`
- `python test_question_variants_contract.py`
- `python test_cloze_hint_slot_contract.py`
- `python test_custom_openai_contract.py`
- `python test_notebooklm_auth_contract.py`
- `python -m py_compile __init__.py locales.py config_model.py ai_runtime.py reviewer_ui.py`
- `powershell -ExecutionPolicy Bypass -File scripts\sync_to_anki.ps1`
- Manual Anki smoke for typed-answer, hint, analysis, deep action, and config dialog

# Completion Criteria

- shipping contract is explicit and executable before module split risk lands
- language/config/runtime/UI concerns each have one authoritative owner
- mutable state families are singular and not mirrored across modules
- `__init__.py` is bootstrap-only under hard target `400` lines
- reviewer styling is owned once in `reviewer_ui.py` for this cycle and no longer in `__init__.py`
- all focused tests pass
- synced add-on folder contains final runtime surface and imports cleanly
- docs and sync workflow match shipped behavior
