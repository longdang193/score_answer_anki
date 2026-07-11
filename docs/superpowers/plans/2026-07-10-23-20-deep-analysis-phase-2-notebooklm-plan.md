---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: deep-analysis-phase-2-notebooklm
parent_spec: packages/score_answer_anki/docs/superpowers/specs/2026-07-10-23-08-deep-analysis-phase-2-notebooklm-spec.md
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
  - packages/score_answer_anki/README.md
  - packages/score_answer_anki/Config.md
related_features:
  - ai-analysis-ui
  - deep-analysis
  - notebooklm-mcp
  - prompt-profile
related_stages:
  - implementation
---

# Deep Analysis Phase 2 NotebookLM Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Implement Phase 2 of `Deep Analysis` so `score_answer_anki` keeps Phase 1 SSOT architecture, adds optional deep-only NotebookLM MCP context, and preserves one shared request/result/panel flow with warning-backed fallback.

**Architecture:** Keep one analysis engine in `packages/score_answer_anki/__init__.py`. Keep `General`, `Standard`, `Deep`, and `Providers` ownership unchanged from Phase 1. Add NotebookLM fields only under `modes.deep`. Keep NotebookLM settings owned by `Deep`, not `Providers`. Review-time deep flow queries NotebookLM directly by saved `notebook_id`, never re-lists notebooks, trims context to fixed cap, and never writes reusable persistent cache for NotebookLM-enabled runs.

**Tech Stack:** Python stdlib, existing Anki add-on HTML-string UI, existing assert-based contract tests, NotebookLM MCP integration already available in environment, existing PowerShell sync script.

---

# Goal

Implement approved Phase 2 design in smallest safe slices:

- deep config gains optional NotebookLM fields under `modes.deep` only
- `Deep` tab gains bounded NotebookLM block behind `Use NotebookLM MCP`
- session/auth and notebook-list actions stay settings-owned
- review-time deep flow uses saved `notebook_id` directly
- NotebookLM context is retrieval-only, warning-backed, trimmed to deterministic cap, and injected into shared deep prompt path only
- standard mode remains NotebookLM-blind
- NotebookLM-enabled deep runs stay non-cacheable in Phase 2
- docs and focused runnable proofs match patched spec exactly

# Key Deliverables

- One canonical deep-mode config extension for:
  - `use_notebooklm`
  - `notebook_id`
  - `notebook_title`
- One `Deep`-tab NotebookLM UI block with:
  - `Use NotebookLM MCP`
  - session status label
  - `Refresh NotebookLM Session`
  - `Refresh Notebook List`
  - `Target Notebook`
- One direct-by-ID review-time NotebookLM query path with no notebook re-listing
- One deterministic NotebookLM context adapter:
  - whitespace-normalized
  - trimmed to first `4000` characters
  - warning emitted on truncation
- One explicit fallback contract where NotebookLM failures degrade to deep warnings, not hard failures
- One non-cacheable rule for all NotebookLM-enabled deep runs in Phase 2
- One focused contract-test expansion and doc update set

# Task Breakdown

## Task 1: Lock Phase 2 contracts with failing tests

Files:
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- `packages/score_answer_anki/__init__.py`

Steps:
- Add failing assertions for new canonical deep config keys:
  - `modes.deep.use_notebooklm`
  - `modes.deep.notebook_id`
  - `modes.deep.notebook_title`
- Add failing UI-contract assertions for deep-tab ownership:
  - NotebookLM controls exist only in `Deep`
  - controls gray out when deep disabled
  - controls gray out when NotebookLM disabled
  - `Providers` stays NotebookLM-free
- Add failing runtime-contract assertions for:
  - `use_notebooklm == false` keeps Phase 1-equivalent deep request/result behavior
  - blank `notebook_id` yields warning-backed deep result
  - direct review-time query path uses saved `notebook_id`
  - notebook-list API is not called during review-time deep run
  - oversized NotebookLM response trims to first `4000` chars and warns
  - NotebookLM-enabled deep runs do not write reusable persistent cache entries

Verification:
- tests express all new SSOT boundaries before implementation
- NotebookLM ownership is pinned to `Deep` tab and `modes.deep`
- cache and fallback behavior are explicit in tests

## Task 2: Extend config load/save and settings state

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Patch `DEFAULT_CONFIG`, merge helpers, and save helpers to include:
  - `modes.deep.use_notebooklm`
  - `modes.deep.notebook_id`
  - `modes.deep.notebook_title`
- Keep load path tolerant of pre-Phase-2 configs with missing NotebookLM keys.
- Save canonical nested shape with new deep keys only under `modes.deep`.
- Add any minimal in-memory settings state needed for session status and notebook list display without creating new top-level config owners.

Verification:
- pre-Phase-2 configs still load cleanly
- save path persists NotebookLM fields only under `modes.deep`
- no NotebookLM keys leak into `general` or `providers`

## Task 3: Patch `Deep` tab NotebookLM controls

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Extend existing `Deep` mode tab builder instead of creating parallel UI.
- Add:
  - `Use NotebookLM MCP`
  - session status label
  - `Refresh NotebookLM Session`
  - `Refresh Notebook List`
  - `Target Notebook` combo box
- Wire grayout rules to existing deep enablement plus NotebookLM checkbox.
- Keep saved notebook sentinel display when saved `notebook_id` is absent from refreshed list.
- Keep all NotebookLM controls out of `Providers` and review panel.

Verification:
- `Deep` tab remains single owner of NotebookLM settings widgets
- gating is symmetric and exact
- notebook display preserves saved identity and latest known title cleanly

## Task 4: Add settings-owned NotebookLM actions

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Patch settings action handler for `Refresh NotebookLM Session` using available NotebookLM auth-refresh path.
- Patch settings action handler for `Refresh Notebook List` using available notebook-list path.
- Keep side-effectful auth/session work user-triggered only.
- Record only bounded UI-facing session states:
  - `Not checked`
  - `Ready`
  - `Auth required`
  - `Error`
- Keep notebook-list failures local to settings status; do not clear saved `notebook_id` automatically.

Verification:
- review-time deep flow does not trigger interactive auth/setup actions
- settings actions update visible state predictably
- saved notebook config survives list failures

## Task 5: Wire direct NotebookLM retrieval into shared deep runtime

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Patch shared deep request/runtime path, not panel shell.
- When `use_notebooklm == false`, keep exact Phase 1 deep behavior.
- When `use_notebooklm == true` and `notebook_id` blank, emit warning and continue deep run without NotebookLM.
- When `use_notebooklm == true` and `notebook_id` present:
  - attempt one direct NotebookLM query by saved `notebook_id`
  - do not refresh notebook list first
  - do not trust stale UI session state as authority
- On auth/query failure, emit warning and continue deep run without NotebookLM context.
- On success:
  - normalize whitespace
  - trim to first `4000` characters
  - add truncation warning if needed
  - inject context into shared deep prompt assembly only
  - set `context_sources` / `sources_used` to `['notebooklm']`

Verification:
- one deep runtime family handles all NotebookLM cases
- NotebookLM stays retrieval-only
- standard mode stays unchanged

## Task 6: Patch cache/write behavior for NotebookLM-enabled deep runs

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Keep request identity aware of:
  - `use_notebooklm`
  - `notebook_id`
- Keep `notebook_title` and session status out of identity.
- Allow normal cache behavior for standard mode and deep-without-NotebookLM.
- Skip reusable persistent cache writes for any NotebookLM-enabled deep run, regardless of retrieval success or failure.
- Keep immediate display/regenerate behavior working without introducing second cache subsystem.

Verification:
- no stale NotebookLM-backed result becomes reusable persistent cache
- non-NotebookLM flows preserve Phase 1 cache behavior
- regenerate still reruns current mode cleanly

## Task 7: Update docs and run focused verification

Files:
- `packages/score_answer_anki/README.md`
- `packages/score_answer_anki/Config.md`
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- `packages/score_answer_anki/scripts/sync_to_anki.ps1`

Steps:
- Update docs to explain:
  - NotebookLM is deep-only and optional
  - NotebookLM controls live in `Deep`
  - session/auth is manual
  - notebook target persists by `notebook_id`
  - review-time deep query uses saved notebook directly
  - NotebookLM context is trimmed and warning-backed
  - NotebookLM-enabled deep runs are non-cacheable in Phase 2
- Run focused checks:

```powershell
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
py -3 -m py_compile packages\score_answer_anki\__init__.py packages\score_answer_anki\test_ai_analysis_ui_contract.py
powershell -ExecutionPolicy Bypass -File packages\score_answer_anki\scripts\sync_to_anki.ps1
```

- Manual Anki check on one eligible `_score` card:
  - standard result still appears automatically when standard enabled
  - deep result still appears in same panel shell
  - NotebookLM controls appear only in `Deep`
  - NotebookLM controls gray out correctly
  - deep with NotebookLM off matches Phase 1 behavior
  - deep with NotebookLM on and no notebook selected warns and continues
  - deep with NotebookLM on and query failure warns and continues
  - deep with NotebookLM on and success shows expected source attribution

Verification:
- focused test file passes
- patched add-on syncs cleanly
- manual review behavior matches Phase 2 spec and preserves Phase 1 shell/ownership

# Risks / Rollback

- Risk: NotebookLM keys leak outside `modes.deep`
  - rollback: centralize load/save normalization and assert exact ownership in tests
- Risk: settings and review flows both own notebook discovery
  - rollback: keep notebook listing settings-only and direct query review-only
- Risk: oversized NotebookLM text destabilizes provider requests
  - rollback: centralize one adapter cap and assert exact trimmed length in tests
- Risk: NotebookLM-enabled results become stale through persistent cache reuse
  - rollback: skip all persistent cache writes for NotebookLM-enabled deep runs in Phase 2
- Risk: NotebookLM patch regresses Phase 1 deep behavior
  - rollback: keep `use_notebooklm == false` path byte-for-byte aligned with existing deep flow where possible

# Final Verification

- [ ] `py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py`
- [ ] `py -3 -m py_compile packages\score_answer_anki\__init__.py packages\score_answer_anki\test_ai_analysis_ui_contract.py`
- [ ] `powershell -ExecutionPolicy Bypass -File packages\score_answer_anki\scripts\sync_to_anki.ps1`
- [ ] Manual Anki check verifies:
  - [ ] standard analysis still auto-runs on answer reveal when standard enabled
  - [ ] `Deep` tab owns all NotebookLM controls
  - [ ] NotebookLM controls gray out when `Use Deep Analysis` is off
  - [ ] NotebookLM controls gray out when `Use NotebookLM MCP` is off
  - [ ] `Providers` tab contains no NotebookLM controls
  - [ ] review-time deep run with NotebookLM uses saved `notebook_id` directly
  - [ ] review-time deep run does not refresh notebook list first
  - [ ] blank notebook selection yields warning-backed deep result
  - [ ] NotebookLM query failure yields warning-backed deep result
  - [ ] oversized NotebookLM response yields truncation warning
  - [ ] successful NotebookLM retrieval sets `sources_used` to `notebooklm`
  - [ ] NotebookLM-enabled deep runs do not become reusable persistent cache entries
  - [ ] deep result still renders in same `AI Analysis` shell
  - [ ] standard mode remains NotebookLM-blind

# Completion Criteria

- Phase 2 NotebookLM fields are canonical under `modes.deep` only
- one `Deep`-tab NotebookLM settings block is authoritative
- review-time deep flow uses one direct NotebookLM query path by saved identity
- NotebookLM context is retrieval-only, deterministic, and bounded
- NotebookLM failures degrade to normalized warnings, not hard failures
- Phase 2 writes no reusable persistent cache entries for NotebookLM-enabled deep runs
- standard mode, provider ownership, and shared panel shell remain intact
- docs and focused verification match patched Phase 2 spec exactly
