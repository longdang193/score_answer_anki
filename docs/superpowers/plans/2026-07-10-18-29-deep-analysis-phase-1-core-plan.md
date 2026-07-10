---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: deep-analysis-phase-1-core
parent_spec: packages/score_answer_anki/docs/superpowers/specs/2026-07-10-18-15-deep-analysis-phase-1-core-spec.md
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
  - packages/score_answer_anki/README.md
  - packages/score_answer_anki/Config.md
related_features:
  - ai-analysis-ui
  - deep-analysis
  - prompt-profile
related_stages:
  - implementation
---

# Deep Analysis Phase 1 Core Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Implement Phase 1 of `Deep Analysis` so `score_answer_anki` keeps automatic standard analysis, adds manual deep analysis, and adopts one symmetry-driven SSOT across shared settings, mode settings, and provider settings with no NotebookLM MCP dependency.

**Architecture:** Keep one analysis engine in `packages/score_answer_anki/__init__.py`. Replace flat deep-mode special casing with one canonical config topology: `general`, `modes`, `providers`. Keep `Standard` and `Deep` structurally symmetric. Keep provider credentials owned only by `Providers`. Route review actions, request resolution, cache identity, and render state through one shared mode-aware contract. Delete brain icon; keep text-only actions.

**Tech Stack:** Python stdlib, existing Anki add-on HTML-string UI, existing assert-based contract tests, existing PowerShell sync script.

---

# Goal

Implement approved Phase 1 deep-analysis design in smallest safe slices:

- config adopts canonical `general` / `modes` / `providers` shape
- `General`, `Standard`, `Deep`, `Providers` tabs replace mixed settings layout
- `Use Deep Analysis` is sole deep enablement flag
- provider credentials live only under `Providers`
- standard and deep requests resolve from mode blocks plus provider blocks
- cache/state contract distinguishes standard vs deep by resolved mode-owned values
- panel shell stays shared and gets bounded mode-aware text-only actions
- NotebookLM remains fully absent in this phase except fixed neutral request/result values

# Key Deliverables

- One canonical nested config merge/save contract for `general`, `modes`, and `providers`
- One flat-to-nested migration path from legacy keys into canonical storage
- One shared request/runtime resolver consuming `mode + provider` ownership cleanly
- One exact cache-key extension including resolved mode-owned values: `analysis_mode`, `provider`, `model`, `prompt_profile`, `max_tokens`, `temperature`, and prompt contract
- One settings dialog refactor to four tabs:
  - `General`
  - `Standard`
  - `Deep`
  - `Providers`
- One shared panel shell with:
  - text-only `Deep Analysis` action on standard result when allowed
  - text-only `Show standard` action on deep result when sibling cached standard result exists
  - explicit mode badge for standard vs deep
- One focused contract-test expansion in `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- One docs update in `packages/score_answer_anki/README.md` and `packages/score_answer_anki/Config.md`

# Task Breakdown

## Task 1: Lock canonical config contract with failing tests

Files:
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- `packages/score_answer_anki/__init__.py`

Steps:
- Add failing assertions for canonical ownership:
  - `general.language`
  - `general.show_anki_compare`
  - `general.show_code_compare`
  - `modes.standard.enabled|provider|model|prompt_profile|max_tokens|temperature`
  - `modes.deep.enabled|provider|model|prompt_profile|max_tokens|temperature`
  - `providers.<provider_key>.api_key`
  - `providers.custom_openai.base_url`
- Add failing migration assertions from current flat keys:
  - `provider`
  - provider model keys
  - `standard_prompt_profile`
  - `deep_prompt_profile`
  - `deep_analysis_model`
  - `max_tokens`
  - `temperature`
  - provider credentials
- Add assertions that save path emits canonical nested shape and does not keep global `deep_analysis_model` as runtime authority.

Verification:
- merged config resolves deterministic nested structure
- save path persists canonical nested structure only
- provider credentials are not duplicated under mode blocks

## Task 2: Implement config migration and persistence

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Patch `DEFAULT_CONFIG`, merge helpers, and save helpers to own canonical shape:
  - `general`
  - `modes`
  - `providers`
- Migrate legacy flat keys into canonical nested structure on load.
- Keep legacy flat keys readable during migration only.
- Save canonical nested structure after first write.
- Keep shared custom prompt fields single-owner.

Verification:
- old configs still load
- new saves normalize to canonical nested shape
- no runtime path depends on global `deep_analysis_model`

## Task 3: Add one shared mode/provider runtime resolver

Files:
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- `packages/score_answer_anki/__init__.py`

Steps:
- Add failing request-resolution tests for same card/user answer under `standard` and `deep`.
- Extract or patch one helper boundary that resolves, for requested mode:
  - `provider`
  - `model`
  - `prompt_profile`
  - `max_tokens`
  - `temperature`
  - provider connection data from provider-owned block
  - fixed Phase 1 NotebookLM-neutral fields
- Keep one normalized request shape for both modes.
- Add explicit unavailability rules:
  - deep disabled => unavailable with exact reason
  - deep enabled + blank model => unavailable with exact reason
  - no silent fallback to standard model

Verification:
- same card/answer payload stays same across modes
- only intended mode-owned fields differ
- provider credentials resolve from provider block only

## Task 4: Extend cache and current-request ownership

Files:
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- `packages/score_answer_anki/__init__.py`

Steps:
- Add failing cache-key assertions for same card/input under `standard` and `deep`.
- Extend cache identity with resolved mode-owned values:
  - `analysis_mode`
  - `provider`
  - `model`
  - `prompt_profile`
  - `max_tokens`
  - `temperature`
  - prompt contract
- Keep one cache family, not separate standard/deep stores.
- Keep `current_analysis_context` mode-aware and able to return to sibling standard result.

Verification:
- standard and deep cache entries do not collide
- regenerate can rerun active mode without heuristics
- deep context can return to cached standard result safely

## Task 5: Refactor settings dialog to four tabs

Files:
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- `packages/score_answer_anki/__init__.py`

Steps:
- Add failing UI/source assertions for four tabs:
  - `General`
  - `Standard`
  - `Deep`
  - `Providers`
- Move shared review/UI settings into `General` only:
  - `language`
  - `show_anki_compare`
  - `show_code_compare`
- Make `Standard` and `Deep` tabs structurally symmetric:
  - `Use Standard Analysis` / `Use Deep Analysis`
  - `Provider`
  - `Model`
  - `Prompt profile`
  - `Max tokens`
  - `Temperature`
  - mode-scoped test button or equivalent bounded test path
- Make `Providers` sole owner of:
  - provider API keys
  - provider base URL where applicable
  - provider custom model registry
  - provider help text
- Disable all deep-tab controls except checkbox when `Use Deep Analysis` is unchecked.
- Keep shared custom prompt block one-owner and visible iff either selected mode profile resolves to `custom`.

Verification:
- settings tabs match spec topology
- `Standard` and `Deep` stay schema-identical
- deep controls gray out correctly when deep disabled
- provider credentials are editable in one place only

## Task 6: Patch panel actions and remove brain icon

Files:
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- `packages/score_answer_anki/__init__.py`

Steps:
- Add failing panel-render assertions for:
  - text-only `Deep Analysis`
  - text-only `Show standard`
  - no brain icon
- Keep current shared panel shell and score badge.
- Keep explicit mode badge.
- Show `Deep Analysis` only when:
  - current panel mode is `standard`
  - deep mode enabled
  - deep model configured
  - resolved deep runtime available
- Keep `Show standard` only when sibling standard cache exists.

Verification:
- panel stays one shell
- action labels are text-only
- deep trigger visibility follows exact gate
- deep panel return path stays explicit and cache-backed

## Task 7: Update API test flow and docs, then verify

Files:
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/README.md`
- `packages/score_answer_anki/Config.md`
- `packages/score_answer_anki/scripts/sync_to_anki.ps1`

Steps:
- Align `Test API Connection` behavior with canonical ownership:
  - resolve from current mode selection(s) and provider-owned credentials
  - skip blank model targets
- Update docs to explain:
  - four-tab settings topology
  - shared vs mode-owned vs provider-owned settings
  - `Use Deep Analysis`
  - no brain icon / text-only deep action
  - no NotebookLM in Phase 1
- Run focused checks:

```powershell
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
py -3 -m py_compile packages\score_answer_anki\__init__.py packages\score_answer_anki\test_ai_analysis_ui_contract.py
powershell -ExecutionPolicy Bypass -File packages\score_answer_anki\scripts\sync_to_anki.ps1
```

- Manual Anki check on one eligible `_score` card:
  - standard result appears automatically when standard enabled
  - deep action appears only when deep enabled and deep model configured
  - deep result loads in same panel shell
  - `Show standard` returns to cached standard result
  - regenerate reruns currently displayed mode
  - structured sections still render when payload contains them

Verification:
- focused test file passes
- patched add-on syncs cleanly
- manual review behavior matches Phase 1 spec and excludes NotebookLM

# Risks / Rollback

- Risk: migration leaves mixed flat and nested truths
  - rollback: centralize one canonical normalization helper and make save path always rewrite canonical nested shape
- Risk: mode tabs accidentally duplicate provider credentials
  - rollback: move all provider credential widgets behind one `Providers` owner and wire mode tabs to provider references only
- Risk: cache-key extension omits one mode-owned runtime field
  - rollback: keep one ordered cache-key builder and assert exact entropy fields in tests
- Risk: deep-disable gate diverges between settings UI and review UI
  - rollback: centralize one `is_deep_enabled(...)` helper and reuse it across settings, runtime, and panel rendering
- Risk: panel-shell patch regresses current structured section rendering
  - rollback: preserve current `build_ai_analysis_sections(...)` and `render_ai_analysis_section(...)` ownership, patch action/badge logic only

# Final Verification

- [ ] `py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py`
- [ ] `py -3 -m py_compile packages\score_answer_anki\__init__.py packages\score_answer_anki\test_ai_analysis_ui_contract.py`
- [ ] `powershell -ExecutionPolicy Bypass -File packages\score_answer_anki\scripts\sync_to_anki.ps1`
- [ ] Manual Anki check verifies:
  - [ ] standard analysis still auto-runs on answer reveal when standard enabled
  - [ ] deep-tab controls gray out when `Use Deep Analysis` is off
  - [ ] deep trigger is hidden when deep disabled
  - [ ] deep trigger is hidden when deep enabled but deep model blank
  - [ ] deep trigger appears when deep enabled and deep model configured
  - [ ] deep result renders in same `AI Analysis` shell with deep badge
  - [ ] `Show standard` returns to cached standard result without recomputation
  - [ ] `Regenerate` reruns active mode only
  - [ ] review actions are text-only and no brain icon appears
  - [ ] structured sections still render in scored results
  - [ ] no NotebookLM-specific UI or runtime behavior appears

# Completion Criteria

- canonical nested config is authoritative and persisted
- one shared request/runtime resolver serves both modes
- one provider-owned settings surface serves all provider credentials
- `Standard` and `Deep` tabs are symmetric and bounded
- deep mode uses explicit deep enablement and deep model with no silent fallback
- panel shell stays unified and exposes bounded mode-aware text-only actions only
- current structured-section rendering remains intact
- docs and focused verification match Phase 1 behavior exactly
