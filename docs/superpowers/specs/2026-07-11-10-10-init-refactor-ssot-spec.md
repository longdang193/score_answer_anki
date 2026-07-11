---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: init-refactor-ssot
parent_workstream: none
targets:
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\__init__.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\locales.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\config_model.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\ai_runtime.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\reviewer_ui.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\reviewer.css
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\configs\prompt_defaults.json
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\README.md
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\Config.md
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\scripts\sync_to_anki.ps1
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_ai_analysis_ui_contract.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_refactor_contract.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_question_variants_contract.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_cloze_hint_slot_contract.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_custom_openai_contract.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_notebooklm_auth_contract.py
related_features:
  - ai-analysis-ui
  - front-hint-panel
  - prompt-profiles
  - notebooklm-deep-analysis
  - typed-answer-input
related_stages:
  - design
---

# Goal

Refactor `score_answer_anki` so `__init__.py` becomes bootstrap-only and each equivalent concern has one source of truth, one symmetric execution path, and one native-boundary integration point.

Current root problems:

- `__init__.py` owns unrelated concerns at once: language data, CSS/theme data, config schema, provider transport, NotebookLM transport, prompt resolution, reviewer DOM rendering, Qt config UI, hook registration, and runtime state.
- equivalent language concerns are split across multiple top-level tables instead of one language registry.
- config has two authoritative shapes at once:
  - legacy flat keys for storage and many call sites
  - nested `general / modes / providers` shape after normalization
- reviewer styling and theme behavior live as Python string blobs instead of one native CSS asset boundary.
- config UI is one long function, so mode/provider symmetry is hard to maintain.
- provider transport and reviewer rendering are coupled, so safe refactors require touching too much code at once.

This spec defines one bounded refactor that preserves current user-visible behavior while moving ownership into five explicit surfaces:

1. `__init__.py` as bootstrap only
2. `locales.py` as language/UI-text SSOT
3. `config_model.py` as config/provider/prompt-default SSOT
4. `ai_runtime.py` as provider + NotebookLM runtime boundary
5. `reviewer_ui.py` plus one Wave-0-selected stylesheet owner as reviewer render/style boundary

# Key Deliverables

1. `__init__.py` reduced to import wiring, hook registration, and add-on initialization only.
2. One authoritative language registry in `locales.py` replacing split top-level language dictionaries in `__init__.py`.
3. One authoritative config model in `config_model.py` owning defaults, legacy migration, normalized nested shape, and persisted output shape.
4. One authoritative provider/runtime module in `ai_runtime.py` owning API transport, prompt assembly entrypoints, and NotebookLM session helpers.
5. One authoritative reviewer UI module in `reviewer_ui.py` owning DOM/HTML/JS builders and hook callbacks.
6. One authoritative reviewer stylesheet owner, preferably `reviewer.css`, owning shared tokens, theme overrides, and reviewer-specific layout classes.
7. Focused regression tests proving SSOT boundaries hold and user-visible behavior stays stable.
8. Small documentation updates in `README.md` and `Config.md` describing stable architecture boundaries only where user behavior or setup wording changes.
9. One authoritative shipping contract in `scripts\sync_to_anki.ps1` that copies every runtime file required by module split.
10. One focused `test_refactor_contract.py` proof for import smoke, config round-trip, and shipped add-on surface.

# State Ownership Contract

Mutable state must be owned once:

- `reviewer_ui.py` owns review-session mutable state only:
  - `ai_analysis_cache`
  - `is_analyzing`
  - `analysis_results`
  - `hint_cache`
  - `is_generating_hint`
  - `current_analysis_context`
  - `current_hint_context`
  - `active_question_state`
  - `front_hint_panel_state`
- `ai_runtime.py` owns provider and NotebookLM runtime state only:
  - `notebooklm_runtime_state`
  - any subprocess/session/auth scratch state introduced during extraction
- `config_model.py` owns pure config transforms and file-backed default loading, but no long-lived runtime mutable state.
- `locales.py` owns immutable data + getters only.
- `__init__.py` is stateless after initialization except for one-time hook/menu registration.

State invariants:

- no mutable state family may be mirrored across modules
- no module may keep fallback shadow copies of another module's authoritative state
- any state crossing module boundaries must be passed through explicit function contracts, not imported and mutated opportunistically

# Task/Wave Breakdown

## Wave 0: Lock shipping and import contract first

Files:

- `scripts\sync_to_anki.ps1`
- `__init__.py`
- `reviewer_ui.py`
- `configs\prompt_defaults.json`
- `test_refactor_contract.py`
- `reviewer.css` if and only if stylesheet extraction lands in same change

Required change:

- define one exact shipping contract for live Anki sync before any module split lands
- update `scripts\sync_to_anki.ps1` to copy every runtime file introduced by this refactor:
  - `__init__.py`
  - extracted runtime modules
  - `configs\prompt_defaults.json`
  - `reviewer.css` only if stylesheet extraction lands
- add one import-smoke proof from add-on-like package layout so module split is validated as shipped, not only in worktree
- choose one exact stylesheet contract before implementation:
  - preferred native path: export one stylesheet asset through one authoritative Anki-compatible loader/export path and sync it with the add-on
  - lazy fallback: if that export path is not implemented in same change, keep one embedded CSS owner during this refactor and defer `reviewer.css` extraction
- no dual authority is allowed for reviewer styling after Wave 0 decision:
  - either one file-backed stylesheet owner
  - or one embedded stylesheet owner
  - never both as active authorities

Verification:

- proof target: synced add-on folder contains every runtime file required by module split
  - method: run + comparison
  - evidence: `test_refactor_contract.py` or equivalent proof enumerates required shipped files after `scripts\sync_to_anki.ps1` runs


## Wave 1: Extract language and label SSOT

Files:

- `__init__.py`
- `locales.py`
- `test_ai_analysis_ui_contract.py`

Required change:

- move all language-owned static data into `locales.py`:
  - `HINT_UI_TEXTS`
  - `AI_UI_TEXTS`
  - `LANG_TO_LABELS`
  - `LANGUAGES`
  - `LANGUAGE_INSTRUCTION_NAMES`
  - `LANGUAGE_REGISTRY`
- keep one getter family only in `locales.py`:
  - `_get_language_bundle(...)`
  - `get_compare_labels(...)`
  - `get_ui_texts(...)`
  - `get_hint_ui_texts(...)`
  - `get_ai_ui_texts(...)`
  - `get_supported_language_options(...)`
  - `get_language_name(...)`
  - `get_language_lock_instruction(...)`

Required SSOT rule:

- every user-facing language variant for equivalent semantics must be derivable from one `LANGUAGE_REGISTRY` tree.
- no second top-level language table may remain in `__init__.py` after extraction.
- any feature-specific text that truly differs may remain nested under registry entries, but not in parallel global tables.

Verification:

- proof target: language-owned UI strings are authoritative in one module only
  - method: code inspection + contract assertions
  - evidence: `test_ai_analysis_ui_contract.py` proves imported text helpers resolve equivalent labels from one registry path

## Wave 2: Extract config, provider, and prompt-default SSOT

Files:

- `__init__.py`
- `config_model.py`
- `configs\prompt_defaults.json`
- `test_custom_openai_contract.py`
- `test_notebooklm_auth_contract.py`
- `test_refactor_contract.py`

Required change:

- move config-owned data and helpers into `config_model.py`:
  - `DEFAULT_CONFIG`
  - prompt-profile constants and normalization helpers
  - provider catalog and provider keys
  - default builders for `general`, `modes`, and `providers`
  - `merge_config_with_defaults(...)`
  - `build_persisted_config(...)`
  - `get_config(...)`
  - `save_config(...)`
  - prompt-default loaders and resolvers rooted in `configs\prompt_defaults.json`
- preserve backward compatibility by keeping legacy flat-key read support only inside config normalization/persist boundaries.
- preserve one normalized runtime shape only:
  - `general`
  - `modes.standard`
  - `modes.deep`
  - `providers`

Required SSOT rule:

- nested normalized config is authoritative in memory.
- legacy flat keys exist only for:
  - reading old stored config
  - writing compatibility fields when persistence still needs them
- no feature logic outside `config_model.py` may hand-roll provider/model/config fallbacks.

Verification:

- proof target: config round-trip preserves current behavior while keeping one normalized in-memory shape
  - method: focused contract tests + inspection
  - evidence: tests prove old flat config still loads, normalized access still works, and persistence writes expected shape

## Wave 3: Move reviewer styling to one native CSS boundary

Files:

- `__init__.py`
- `reviewer_ui.py`
- `reviewer.css` when Wave 0 selects file-backed stylesheet ownership
- `test_ai_analysis_ui_contract.py`
- `test_refactor_contract.py`

Required change:

- if Wave 0 selects file-backed stylesheet ownership, move reviewer-owned CSS out of Python string blobs into `reviewer.css`.
- if Wave 0 selects embedded stylesheet ownership for this refactor, move CSS ownership out of `__init__.py` into one bounded owner in `reviewer_ui.py` and defer `reviewer.css` extraction.
- whichever ownership path Wave 0 selects becomes authoritative for:
  - shared reviewer tokens
  - dark-mode overrides
  - compare surface styling
  - front-hint styling
  - typed-answer footer/layout styling
  - equivalent button/spinner/status class families
- `reviewer_ui.py` may still inject one loader snippet, but may not rebuild CSS token blocks in Python.

Required native-theme rule:

- theme adaptation must use native reviewer/theme signals only:
  - existing body classes such as `nightMode`, `night-mode`, or equivalent
  - CSS custom properties already exposed by host page when present
  - `prefers-color-scheme` fallback only in CSS
- no custom Python or JS theme detection branch may become authoritative when native CSS selectors already cover the same behavior.

Verification:

- proof target: reviewer style ownership lives behind one authoritative stylesheet contract
  - method: code inspection + HTML/CSS contract assertions
  - evidence: `test_ai_analysis_ui_contract.py` proves one stylesheet owner path only, and `__init__.py` no longer carries giant reviewer CSS constants

## Wave 4: Separate reviewer UI from AI runtime

Files:

- `__init__.py`
- `reviewer_ui.py`
- `ai_runtime.py`
- `test_ai_analysis_ui_contract.py`
- `test_question_variants_contract.py`
- `test_cloze_hint_slot_contract.py`
- `test_notebooklm_auth_contract.py`

Required change:

- move transport/runtime logic into `ai_runtime.py`:
  - provider request formatting
  - provider HTTP request execution
  - NotebookLM subprocess session helpers
  - prompt rendering entrypoints
  - answer-analysis request orchestration
- move reviewer render + interaction logic into `reviewer_ui.py`:
  - question-side input/hint markup shaping
  - answer-side compare panel rendering
  - JS message dispatch table
  - refresh/regenerate/deep-action UI handlers
  - render-time state updates that are UI-owned

Required symmetry rule:

- `reviewer_ui.py` may call `ai_runtime.py` through one bounded request surface.
- `ai_runtime.py` may not import reviewer rendering helpers.
- equivalent AI states with same semantics must use shared UI helpers in `reviewer_ui.py`, not repeated markup branches.

Required boundary shape:

- preferred runtime entrypoints:
  - `build_analysis_request(...)`
  - `analyze_answer_request(...)`
  - `build_hint_request(...)`
  - `query_notebooklm_context(...)`
- preferred UI entrypoints:
  - `render_front_hint_panel(...)`
  - `render_enhanced_comparison(...)`
  - `handle_js_message(...)`
  - `register_hooks(...)`

Verification:

- proof target: reviewer UI and AI transport are acyclic and separately testable
  - method: import inspection + focused contract tests
  - evidence: tests import runtime helpers without Anki reviewer HTML dependency and import UI helpers with stubbed runtime calls

## Wave 5: Reduce `__init__.py` to bootstrap-only

Files:

- `__init__.py`
- `reviewer_ui.py`
- `config_model.py`
- `scripts\sync_to_anki.ps1`
- `test_refactor_contract.py`

Required change:

- `__init__.py` keeps only:
  - top-level imports required by Anki add-on loading
  - one `init()` function
  - hook registration calls or one `register_hooks(...)` delegation
  - config menu registration delegation
- `__init__.py` must not remain authoritative for:
  - language data
  - provider catalog
  - CSS token blocks
  - NotebookLM helpers
  - prompt-default loading
  - long Qt config-builder internals

Preferred size target:

- soft target: `__init__.py` under 250 lines
- hard target: `__init__.py` under 400 lines
- shipping note: if `__init__.py` must temporarily host native asset-export registration for stylesheet loading, that registration is still bootstrap-owned and does not count as domain logic

Verification:

- proof target: bootstrap file no longer owns domain logic
  - method: file inspection
  - evidence: `__init__.py` contains wiring-only code and imports extracted modules for owned behavior

## Wave 6: Refactor config UI with native Qt components and data-at-boundary mapping

Files:

- `reviewer_ui.py`
- `config_model.py`
- `README.md`
- `Config.md`

Required change:

- split current `setup_config_menu(...)` monolith into bounded helpers inside `reviewer_ui.py`.
- keep native Qt widgets and tabs as rendering primitives.
- drive repeated provider/mode sections from data specs emitted by `config_model.py` instead of repeated hand-built branches.

Required native-component rule:

- use native Qt widgets and native tab/layout ownership for styling/theme behavior.
- adapt data at boundary:
  - provider metadata maps into widget labels/placeholders/options
  - mode metadata maps into standard/deep tab builders
- do not create custom widget frameworks, theme engines, or abstraction layers with one implementation.

Verification:

- proof target: provider and mode tabs are built symmetrically from data specs while preserving current fields and behavior
  - method: code inspection + focused UI contract assertions
  - evidence: tests and inspection show one provider-spec path and one mode-spec path instead of repeated hand-built blocks

# Design Decisions

1. Use module extraction, not class-framework rewrite.
   - Reason: plain modules fit current code shape and keep diff smaller than introducing service/container abstractions.
2. Keep legacy config migration inside `config_model.py` only.
   - Reason: one boundary is smaller and safer than leaving fallback logic spread across call sites.
3. Use one Wave-0-selected stylesheet owner as styling SSOT, preferably a CSS asset when shipped through one explicit Anki-compatible path.
   - Reason: styling/theme concerns belong in CSS; Python should pass state and markup only, but ownership must match one concrete shipping contract.
4. Keep native Qt config widgets.
   - Reason: user explicitly prefers native components; only data ownership should change.
5. Keep current user-visible behavior unless behavior is already implied by existing tests/docs.
   - Reason: this refactor is structural first, feature second.
6. Keep prompt defaults in `configs\prompt_defaults.json`.
   - Reason: file-backed defaults already exist and are a better SSOT than embedded Python strings.
7. Allow only one directional dependency flow:
   - `__init__.py` -> extracted modules
   - `reviewer_ui.py` -> `config_model.py`, `locales.py`, `ai_runtime.py`
   - `ai_runtime.py` -> `config_model.py`, `locales.py`
   - `config_model.py` and `locales.py` stay leaf-like
   - Reason: avoids circular import drift during future changes.

# Acceptance Criteria

1. `__init__.py` no longer contains language tables, provider catalogs, CSS token blocks, or long config UI builder internals.
2. All language-owned UI text for equivalent semantics resolves from `locales.py` only.
3. All config normalization and persistence ownership lives in `config_model.py` only.
4. Reviewer styling ownership lives behind one Wave-0-selected stylesheet owner; `__init__.py` no longer embeds large reviewer CSS constants.
5. Native theme adaptation uses CSS selectors and variables, not custom runtime theme logic.
6. Provider HTTP transport and NotebookLM helpers live in `ai_runtime.py` and do not import reviewer DOM builders.
7. Reviewer render helpers live in `reviewer_ui.py` and do not hand-roll provider/config fallback logic.
8. Config UI still exposes current user-visible settings:
   - general
   - standard
   - deep
   - providers
9. Current behavior covered by existing contract tests remains intact after refactor.
10. `README.md` and `Config.md` remain consistent with final architecture-relevant user behavior.
11. `__init__.py` finishes under hard target `400` lines.
12. No new dependency is added for styling, theming, transport, or config modeling.
13. `scripts\sync_to_anki.ps1` copies all runtime files required by final module split.
14. Mutable state families are owned exactly once and are not mirrored across modules.

# Non-Goals

- no scoring-policy change
- no prompt-semantics rewrite
- no NotebookLM feature expansion beyond current behavior
- no redesign of answer-side comparison UX
- no new configuration toggles for architecture choices
- no new dependency for CSS loading, state management, or HTTP client behavior
- no rewrite into classes, services, factories, or plugin registries
- no public-mirror workflow changes

# Invariants

1. One authoritative language registry.
2. One authoritative normalized config shape in memory.
3. One authoritative persisted-config builder.
4. One authoritative reviewer stylesheet owner selected in Wave 0.
5. One authoritative provider/runtime boundary.
6. One authoritative bootstrap file.
7. Equivalent UI semantics use shared helper/render paths unless behavior truly differs.
8. Native styling/theme behavior is adapted at boundary, not recreated in custom runtime logic.
9. Legacy compatibility is preserved only at explicit migration boundaries.
10. Extracted modules must not introduce circular imports.
11. One authoritative shipping contract must exist for worktree-to-Anki sync.
12. Mutable state ownership must remain singular per state family.

# Risks and Mitigations

1. Risk: circular imports appear during extraction.
   - Mitigation: keep dependency flow one-directional and move shared constants/helpers into leaf modules first.
2. Risk: CSS asset loading behaves differently from embedded CSS in Anki reviewer webview.
   - Mitigation: implement stylesheet loading in one bounded loader path and keep a focused UI contract test around expected loader marker.
3. Risk: legacy config migration misses rarely used provider/model fields.
   - Mitigation: keep old-flat-config read coverage in focused contract tests before deleting call-site fallbacks.
4. Risk: `setup_config_menu(...)` split accidentally drops fields or signal wiring.
   - Mitigation: refactor by native-tab section with one field inventory checklist and focused review after each section move.
5. Risk: NotebookLM runtime extraction breaks auth/status flow because subprocess helpers currently share nearby globals.
   - Mitigation: move runtime state ownership with helper extraction and preserve existing public entrypoints first.
6. Risk: spec assumes canonical operating-system templates that are missing in this repo slice.
   - Mitigation: follow existing local `docs\superpowers\specs\*.md` artifact shape and keep this spec bounded to package-local execution.
7. Risk: module split passes worktree tests but fails after sync because shipped add-on folder misses new files.
   - Mitigation: make `scripts\sync_to_anki.ps1` an in-scope target and require executable shipped-surface proof.
8. Risk: state dictionaries get duplicated across UI and runtime modules during extraction.
   - Mitigation: use explicit state-ownership table and reject mirrored mutable globals in review and tests.

# Validation Plan

Proof targets:

- proof target: `__init__.py` is bootstrap-only after refactor
  - method: inspection
  - evidence: `__init__.py` file diff shows only wiring/import/init/hook code remains

- proof target: language SSOT is consolidated
  - method: inspection + contract assertions
  - evidence: no parallel language tables remain in `__init__.py`; tests import and use `locales.py`

- proof target: config SSOT is consolidated
  - method: focused contract tests + inspection
  - evidence: legacy flat config fixtures still normalize correctly; persistence path emits expected shape from one builder

- proof target: config round-trip is executable for both legacy-flat and normalized inputs
  - method: test
  - evidence: `python test_refactor_contract.py` proves `legacy-flat -> normalized -> persisted` and `normalized -> persisted` preserve required fields and ownership

- proof target: reviewer styling follows one Wave-0-selected stylesheet contract
  - method: inspection + HTML/CSS contract assertions
  - evidence: reviewer HTML uses one stylesheet owner path only, and Python CSS constants are removed from `__init__.py`

- proof target: runtime/UI separation is acyclic
  - method: inspection + test
  - evidence: `ai_runtime.py` imports no reviewer render helpers; `reviewer_ui.py` consumes runtime through bounded functions only; `python test_refactor_contract.py` performs import smoke against extracted module graph

- proof target: user-visible contract remains stable
  - method: existing focused tests
  - evidence:
    - `python test_ai_analysis_ui_contract.py`
    - `python test_question_variants_contract.py`
    - `python test_cloze_hint_slot_contract.py`
    - `python test_custom_openai_contract.py`
    - `python test_notebooklm_auth_contract.py`
    - `python test_refactor_contract.py`

- proof target: docs stay aligned with shipped behavior
  - method: inspection
  - evidence: `README.md` and `Config.md` mention no removed field or outdated architecture claim

- proof target: packaged add-on still works in live reviewer flows after module split
  - method: run + comparison + manual smoke check in Anki
  - evidence: `scripts\sync_to_anki.ps1` copies final runtime surface; `python test_refactor_contract.py` verifies shipped file list; typed-answer review still shows question-side input, front hint, answer-side AI analysis, deep analysis action, and config dialog opens without import/runtime errors

# Completion Criteria

- all six waves complete without adding new dependency weight
- `__init__.py` meets bootstrap-only hard target
- current focused contract tests pass
- no duplicate authoritative language/config/style surfaces remain
- reviewer theme behavior is owned by one Wave-0-selected stylesheet owner + native selectors
- config UI still works through native Qt widgets with symmetric data-driven section builders
- implementation can proceed from this spec without needing another architecture decision round for file ownership or SSOT boundaries

