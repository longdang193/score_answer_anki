---
layer: change
artifact_type: spec
status: proposed
name: ai-analysis-ui-cleanup
targets:
  - __init__.py
  - README.md
  - Config.md
---

# Goal

Clean up confusing AI-analysis UI text and controls without changing Anki scheduling behavior.

Requested changes:

- Rename `max_tokens` label to `Feedback length`
- Remove visible `Question Context`
- Replace `Review Suggestion` section with `Regenerate Analysis` button only
- Keep actual Anki `Again / Hard / Good / Easy` behavior untouched

# Key Deliverables

- Updated configuration label for response-length control
- AI analysis card without visible `Question Context` block
- AI analysis card with `Regenerate Analysis` button instead of static review suggestion badge
- No change to real Anki review buttons or scheduling logic
- Docs updated to match new UI wording

# Task/Wave Breakdown

## Wave 1: Configuration wording

- Change user-facing label from `Max tokens` to `Feedback length`
- Add short helper text clarifying lower values produce shorter, faster feedback
- Keep internal config key `max_tokens` unchanged
- Keep saved values and provider payload behavior unchanged

## Wave 2: Analysis card cleanup

- Remove visible `Question Context` section from rendered AI analysis panel
- Keep question extraction for internal prompt quality and cache identity only; do not display it in UI
- Remove static `Review Suggestion` display block
- Add `Regenerate Analysis` action in its place

## Wave 3: Docs and proof

- Update docs to reflect new wording and button behavior
- Verify regenerate action reruns analysis without altering Anki scheduling buttons

# Design Decisions

## `max_tokens` naming

User-facing label becomes `Feedback length`.

Rules:

- internal config key remains `max_tokens`
- provider request payload still uses `max_tokens`
- only UI wording changes
- helper text must clarify that lower values usually mean shorter, faster feedback

Reason:

- avoids config migration
- removes provider jargon from UI
- keeps implementation minimal

## `Question Context` visibility

Visible `Question Context` block is removed from rendered output.

Internal rule:

- question text may still be extracted for prompt construction and cache identity
- extracted question text must not be rendered in visible analysis UI

Reason:

- duplicates information already visible in question and answer sections
- currently exposes template noise such as `[[type:Back]]`
- reduces visual clutter

## `Review Suggestion` replacement

Static `Review Suggestion` section is removed entirely.

Replacement:

- one `Regenerate Analysis` button only

Reason:

- current suggestion display looks actionable but does not control real Anki scheduling
- misleading UI is worse than no UI
- regenerate is honest and useful

Scope rule:

- `review_suggestion` is removed from UI and from provider prompt/output contract in same change
- no unused hidden review-suggestion field should remain in rendered output or parser requirements

## Regenerate behavior contract

`Regenerate Analysis` must:

- clear cached AI result for current question/expected/provided tuple
- start a fresh background analysis request for current review state
- show loading state while request is in progress
- re-render analysis panel when fresh result arrives

Interface contract:

- frontend regenerate control must send one dedicated JS message, for example `regenerate_ai_analysis`
- backend must handle that message in one Python handler
- handler must use one shared helper to compute current analysis cache key
- handler must use one shared helper to invalidate all analysis state for that key

Invalidation scope for current key:

- remove entry from `ai_analysis_cache`
- remove entry from `analysis_results`
- clear in-flight flag in `is_analyzing` only when safe for regenerate path

`Regenerate Analysis` must not:

- trigger Anki `Again`, `Hard`, `Good`, or `Easy`
- change scheduler state
- change typed answer contents

## Running-state behavior

If analysis for current key is already in progress, regenerate action must not start duplicate concurrent requests for same key.

Simplest acceptable behavior:

- hide button during active analysis, or
- render disabled button state during active analysis

Spec does not require cancel support.

## Cache-key SSOT

One shared helper must define current analysis identity.

Rules:

- do not duplicate cache-key string construction across render, store, and regenerate paths
- regenerate, normal render, and background completion paths must all use same helper
- one shared invalidation helper must clear cached state for current key

# Invariants

- Real Anki review buttons remain source of truth for scheduling
- AI analysis panel remains advisory only
- Internal config key `max_tokens` remains stable
- Provider request contract changes only to remove unused `review_suggestion` requirement and support user-triggered regeneration reruns
- Cache identity for current answer pair remains stable across normal render and regenerate path

# Acceptance Criteria

- Config dialog shows `Feedback length` instead of `Max tokens`
- Config dialog shows helper text clarifying lower values produce shorter, faster feedback
- Saved configs using `max_tokens` continue to load and save without migration
- AI analysis panel no longer shows `Question Context`
- AI analysis panel no longer shows `Review Suggestion`
- AI analysis panel shows `Regenerate Analysis` control
- Clicking `Regenerate Analysis` starts fresh AI analysis for current answer pair
- During regeneration, duplicate concurrent request for same key is prevented
- Fresh result replaces previous cached analysis after regeneration completes
- Clicking `Regenerate Analysis` does not trigger or modify Anki `Again / Hard / Good / Easy`
- Provider prompt/parser no longer require or depend on `review_suggestion`

# Non-Goals

- No change to provider prompt format
- No change to scoring rubric
- No change to real Anki scheduling controls
- No streaming response support
- No cancel-analysis control
- No broader redesign of analysis card layout

# Risks and Mitigations

## Risk: regenerate button can spam provider calls

Mitigation:

- block duplicate in-flight request for same cache key
- reuse existing `is_analyzing` guard

## Risk: removing visible context reduces explanation clarity

Mitigation:

- expected and provided answer blocks remain visible
- keep hidden internal question text only if prompt quality still benefits

## Risk: wording change implies semantic behavior change

Mitigation:

- change label only
- keep internal config key and provider payload unchanged

## Risk: regenerate path drifts from normal analysis path

Mitigation:

- one shared cache-key helper
- one shared invalidation helper
- one dedicated regenerate message/handler pair

# Validation Plan

- proof target: label rename is UI-only
  - method: inspection and config save/reload check
  - evidence: label reads `Feedback length`, helper text explains lower = shorter/faster, and saved config key remains `max_tokens`

- proof target: question context is no longer visible
  - method: render inspection on reviewed card
  - evidence: analysis panel has no `Question Context` block

- proof target: regenerate replaces review suggestion
  - method: render inspection and click test
  - evidence: `Regenerate Analysis` control appears and static review-suggestion badge is absent

- proof target: regenerate reruns analysis safely
  - method: targeted runnable check plus manual click test with debug output
  - evidence: cache entry for current key is refreshed, duplicate in-flight request is prevented, and regenerate uses shared key/invalidation helpers

- proof target: provider contract no longer carries unused review suggestion
  - method: inspection plus targeted parser check
  - evidence: prompt/output contract and parser requirements no longer require `review_suggestion`

- proof target: cache identity is SSOT
  - method: targeted runnable check
  - evidence: store path, render path, and regenerate path use one shared key helper and one shared invalidation helper

- proof target: Anki scheduling remains untouched
  - method: manual review interaction check
  - evidence: only real Anki `Again / Hard / Good / Easy` buttons affect scheduling

# Completion Criteria

- Spec approved
- UI text and control changes are bounded to requested scope
- No misleading pseudo-scheduling control remains in AI panel
- Actual Anki review controls remain unchanged
