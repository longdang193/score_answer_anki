---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: ai-ui-symmetry
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
---

# Goal

Fix UI inconsistency between `score_answer_anki` AI hint and AI analysis flows by moving equivalent AI-working and AI-regenerate behavior onto one shared render contract, while preserving their different data/content responsibilities.

SSOT scope:

- one shared contract for AI loading-state presentation
- one shared contract for AI action button presentation
- one shared text source for equivalent AI action labels and loading labels
- separate content render paths stay separate only where semantics differ:
  - hint text panel on front side
  - scored analysis panel on answer side

Target shared contract:

- loading state uses one shared spinner + title + body pattern in both flows
- regenerate action uses one shared visible affordance in both flows: same label/icon, same aria/title, same CSS class family
- allowed differences are only placement and feature-specific surrounding content:
  - hint stays inside front-side hint panel
  - analysis stays inside scored answer-side panel

# Key Deliverables

- One shared helper set in `packages/score_answer_anki/__init__.py` for AI status/action rendering used by both hint and analysis paths
- One SSOT text contract for equivalent AI labels now split across `HINT_UI_TEXTS` and `LANGUAGES`
- One focused contract-test update in `packages/score_answer_anki/test_ai_analysis_ui_contract.py` proving symmetry for loading and regenerate UI

# Task Breakdown

## Task 1: Define shared AI UI contract before edits

Files:
- `packages/score_answer_anki/__init__.py`

Steps:
- Identify equivalent semantics already implemented twice:
  - AI loading state
  - AI rerun action
- Keep data-specific panel content out of scope.
- Define one minimal shared contract for:
  - label text
  - button kind
  - disabled/loading state
  - optional spinner/loading body
- Lock exact target now:
  - one shared loading fragment with spinner, title, and body copy
  - one shared regenerate control with exact label/icon/aria/title contract
- Reuse existing panel shell classes where possible; do not invent new component layer unless current classes cannot cover both paths.

Verification:
- Contract makes it impossible for hint and analysis to drift on equivalent loading/regenerate semantics without changing one shared helper.

## Task 2: Centralize equivalent text and render helpers

Files:
- `packages/score_answer_anki/__init__.py`

Steps:
- Add one authoritative `AI_UI_TEXTS` source for equivalent AI UI copy currently split between `get_hint_ui_texts(...)` and `get_ui_texts(...)`.
- Keep feature-specific text in existing hint/analysis dictionaries only when semantics differ.
- Route both hint and analysis paths through shared helper(s) for:
  - loading label/body text where semantics match
  - regenerate button label/icon/aria/title where semantics match
- Keep distinct text only if semantics truly differ; if so, encode as explicit helper parameters, not duplicated markup.
- Reuse existing CSS tokens/classes first.
- Collapse equivalent AI action styling onto one shared class; parameterize placement only if needed.

Verification:
- Equivalent AI states in both flows are rendered from one helper path and one text source.
- No duplicated hard-coded regenerate labels remain in separate branches.
- No equivalent AI UI strings remain authoritative in more than one dictionary.

## Task 3: Patch hint and analysis render paths to consume shared contract

Files:
- `packages/score_answer_anki/__init__.py`

Steps:
- Update `build_front_hint_panel_html(...)` to use shared AI status/action helpers.
- Update `render_enhanced_comparison(...)` loading branch and regenerate control to use same shared helpers.
- Preserve answer-side score badge and analysis body behavior.
- Preserve front-side toggle behavior and manual-hint block behavior.
- Do not change cache/state ownership in this patch.

Verification:
- Hint loading UI and analysis loading UI now match on equivalent semantics.
- Hint rerun UI and analysis rerun UI now match on equivalent semantics.
- Different layout/content remains only where feature semantics differ.

## Task 4: Add focused symmetry proof

Files:
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Add assertions for shared loading-state copy/render markers across hint and analysis flows.
- Add assertions for shared regenerate button label/icon/aria/title/class contract across hint and analysis flows.
- Add structural proof that both hint and analysis paths call one shared loading helper and one shared action-button helper.
- Keep tests narrow: prove helper reuse and visible contract, not whole HTML snapshots.

Verification:
- Test fails before patch on current split UI contract.
- Test passes after shared helper patch.

## Task 5: Run focused proof and sync add-on

Files:
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- `packages/score_answer_anki/scripts/sync_to_anki.ps1`

Steps:
- Run `python packages/score_answer_anki/test_ai_analysis_ui_contract.py`.
- Sync this worktree's add-on with `powershell -ExecutionPolicy Bypass -File packages/score_answer_anki/scripts/sync_to_anki.ps1`.
- Use one deterministic loading-state proof path before manual review:
  - either contract-test stubbed slow `call_ai_api`
  - or one bounded local debug hook that forces visible loading state in both flows
- If test passes and sync succeeds, do one manual Anki check comparing:
  - hint loading vs analysis loading
  - hint regenerate vs analysis regenerate

Verification:
- Manual UI shows one consistent AI loading language/style family and one consistent regenerate control family.
- Loading-state verification is reproducible, not timing-lucky.

# Final Verification

- [x] `python packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- [x] Worktree add-on code synced into local Anki add-on path used for manual verification
- [ ] Manual Anki check verifies:
  - [ ] hint and analysis loading notifications use one shared wording pattern
  - [ ] hint and analysis regenerate controls use one shared style and affordance pattern
  - [ ] hint-specific and analysis-specific content still differ only where semantics differ
- [ ] Deterministic loading-state proof exists for both flows

# Completion Criteria

- Equivalent AI UI semantics are defined once and reused by both hint and analysis flows.
- UI copy, button affordance, and loading-state presentation no longer drift across the two AI features.
- Distinct feature behavior remains separate only for real semantic differences, not styling or wording drift.
