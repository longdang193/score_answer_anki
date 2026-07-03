---
layer: change
artifact_type: plan
status: proposed
name: ai-analysis-ui-cleanup-implementation
parent_spec: docs/superpowers/specs/2026-07-03-16-35-ai-analysis-ui-cleanup-spec.md
targets:
  - __init__.py
  - README.md
  - Config.md
  - test_ai_analysis_ui_contract.py
---

# Goal

Implement bounded AI-analysis UI cleanup: clearer feedback-length wording, no visible question-context block, regenerate action instead of fake review suggestion, and no impact on real Anki scheduling buttons.

# Key Deliverables

- UI label changed from `Max tokens` to `Feedback length`
- Helper text clarifying lower values mean shorter, faster feedback
- No visible `Question Context` block in analysis panel
- No visible `Review Suggestion` block in analysis panel
- `Regenerate Analysis` control wired through one dedicated message/handler path
- Shared cache-key helper and shared invalidation helper
- Prompt/parser no longer require `review_suggestion`
- One tiny runnable proof artifact for cache/key/contract behavior
- Docs updated to match final UI

# Task Breakdown

## Task 1: Consolidate analysis identity and invalidation helpers

Files:
- `__init__.py`
- `test_ai_analysis_ui_contract.py`

Steps:
- Extract one shared helper for current analysis cache key
- Replace duplicated key construction in store/render paths with that helper
- Add one shared helper to invalidate analysis state for current key
- Ensure invalidation clears `ai_analysis_cache` and `analysis_results`
- Define safe handling for `is_analyzing` so regenerate cannot create duplicate concurrent request for same key

Verification:
- Store, render, and regenerate paths all use same key helper
- Invalidation clears state for exactly one key

## Task 2: Remove review-suggestion contract end to end

Files:
- `__init__.py`

Steps:
- Remove `review_suggestion` requirement from prompt template(s)
- Remove parser requirement that expects `review_suggestion`
- Keep score and tips behavior intact
- Remove review-suggestion display block from rendered analysis card

Verification:
- AI analysis still renders score and tips correctly
- No hidden UI dependency on `review_suggestion` remains

## Task 3: Clean up analysis panel UI

Files:
- `__init__.py`

Steps:
- Rename config label to `Feedback length`
- Add helper text explaining lower values produce shorter, faster feedback
- Remove visible `Question Context` block from rendered output
- Keep question extraction only if still needed by prompt/cache helper

Verification:
- Config dialog shows new wording
- Analysis panel no longer shows `Question Context`

## Task 4: Add regenerate action

Files:
- `__init__.py`

Steps:
- Add `Regenerate Analysis` control in analysis panel where review suggestion used to be
- Add one JS message name for regenerate, separate from refresh message
- Add one Python handler branch for regenerate
- Handler must invalidate current key, trigger fresh background analysis, and refresh panel
- During active analysis, either hide or disable regenerate control

Verification:
- Clicking regenerate reruns analysis for current answer pair
- Duplicate in-flight request for same key is prevented
- Real Anki `Again / Hard / Good / Easy` buttons remain untouched

## Task 5: Update docs and proof artifact

Files:
- `README.md`
- `Config.md`
- `test_ai_analysis_ui_contract.py`

Steps:
- Update docs to describe `Feedback length`
- Remove docs that imply review suggestion is a user-facing recommendation control
- Document regenerate behavior briefly
- Add one small assert-based proof script covering:
  - shared key helper stability
  - invalidation helper scope
  - prompt/parser no longer depend on `review_suggestion`

Verification:
- `python test_ai_analysis_ui_contract.py` exits cleanly
- Docs match actual UI wording and behavior

# Risks / Rollback

- Risk: removing `review_suggestion` breaks fallback parsing
  - rollback: keep parser tolerant during transition, but do not render suggestion
- Risk: regenerate triggers duplicate requests
  - rollback: disable button while `is_analyzing` is true for current key
- Risk: helper refactor changes cache behavior
  - rollback: keep helper logic minimal and prove with assert-based script

# Final Verification

- `python test_ai_analysis_ui_contract.py`
- `python -m py_compile __init__.py test_ai_analysis_ui_contract.py`
- Manual Anki check:
  - config dialog shows `Feedback length`
  - helper text explains lower = shorter/faster
  - analysis panel shows no `Question Context`
  - analysis panel shows no `Review Suggestion`
  - `Regenerate Analysis` appears and reruns analysis
  - clicking real Anki `Again / Hard / Good / Easy` still behaves normally

# Completion Criteria

- No misleading pseudo-scheduling control remains in analysis panel
- Regenerate uses one shared key helper and one shared invalidation helper
- Prompt/parser no longer require `review_suggestion`
- Real Anki scheduling controls remain untouched
- Proof script and syntax compile both pass

