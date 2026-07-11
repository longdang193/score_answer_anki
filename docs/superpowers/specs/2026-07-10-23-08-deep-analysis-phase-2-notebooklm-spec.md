---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: deep-analysis-phase-2-notebooklm
parent_workstream: none
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/Config.md
  - packages/score_answer_anki/README.md
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
related_features:
  - ai-analysis-ui
  - deep-analysis
  - notebooklm-mcp
  - prompt-profile
related_stages:
  - design
  - implementation
---

# Goal

Implement Phase 2 of `Deep Analysis`: add optional NotebookLM MCP context to deep-mode analysis, while preserving Phase 1 SSOT boundaries from `docs/superpowers/specs/2026-07-10-18-09-deep-analysis-phased-ssot-master-spec.md` and `docs/superpowers/specs/2026-07-10-18-15-deep-analysis-phase-1-core-spec.md`.

This phase is additive only.

Required outcome:

- deep mode keeps Phase 1 behavior when NotebookLM is off
- NotebookLM is available only inside deep mode
- NotebookLM is optional even when deep mode is on
- notebook selection persists by `notebook_id`
- notebook title is display metadata only
- deep analysis still returns one normalized result when NotebookLM is missing, unauthenticated, or fails
- provider settings stay owned by `Providers`
- request, result, panel, and cache ownership stay shared with Phase 1

# Key Deliverables

1. One `Deep`-tab NotebookLM section gated by `Use NotebookLM MCP`.
2. One manual NotebookLM session/auth action owned by deep settings, not by review panel.
3. One notebook selector persisted under canonical deep-mode config.
4. One optional context-retrieval step layered into shared deep analysis orchestration.
5. One fallback policy where NotebookLM problems downgrade to warning-backed deep analysis instead of hard failure.
6. One doc and test update set proving optionality, notebook persistence, and fallback behavior.

# Task/Wave Breakdown

## Wave 1: Extend canonical deep-mode config

Phase 2 adds only these persisted deep-mode fields:

```python
{
    "general": {...},
    "modes": {
        "standard": {...},
        "deep": {
            "enabled": True,
            "language": "english",
            "provider": "custom_openai",
            "model": "",
            "prompt_profile": "balanced",
            "max_tokens": 100,
            "temperature": 0.7,
            "show_anki_compare": True,
            "show_code_compare": True,
            "use_notebooklm": False,
            "notebook_id": "",
            "notebook_title": "",
        },
    },
    "providers": {...},
}
```

Rules:

- `use_notebooklm`, `notebook_id`, and `notebook_title` live only in `modes.deep`
- standard mode must not gain NotebookLM fields
- `notebook_id` is persisted SSOT
- `notebook_title` is display-only metadata persisted for convenience
- no NotebookLM state is stored in `general`
- no NotebookLM state is stored in `providers`

## Wave 2: Add deep-tab NotebookLM settings block

Phase 2 extends `Deep` tab only.

Concrete UI block:

- checkbox: `Use NotebookLM MCP`
- session status label
- button: `Refresh NotebookLM Session`
- button: `Refresh Notebook List`
- combo box: `Target Notebook`

Enable/disable rules:

- when `Use Deep Analysis` is off, entire deep-mode block stays grayed out, including NotebookLM controls
- when `Use Deep Analysis` is on and `Use NotebookLM MCP` is off, NotebookLM subcontrols stay grayed out
- when `Use NotebookLM MCP` is on, session and notebook controls ungray
- review panel does not own NotebookLM settings widgets
- `Providers` tab does not gain NotebookLM controls

Display rules:

- `Target Notebook` shows notebook title when available
- selector value persists by `notebook_id`
- if saved `notebook_id` is not present in refreshed list, keep saved config value and show a sentinel entry such as `Saved notebook not found (<title-or-id>)`
- notebook title changes must not break lookup if same `notebook_id` still exists

## Wave 3: Add manual session/auth flow

NotebookLM session control is explicit and user-triggered.

Concrete behavior:

1. User clicks `Refresh NotebookLM Session`.
2. Runtime calls NotebookLM MCP auth refresh path.
3. UI reports resulting state in deep settings.
4. User may then refresh notebook list.

Phase 2 session states:

- `Not checked`
- `Ready`
- `Auth required`
- `Error`

Rules:

- no automatic interactive auth popup during review-time `Deep Analysis`
- any browser/session side effect is allowed only after explicit user click on session button
- deep analysis runtime must not trust last-known UI session state as review-time authority
- review-time authority is direct NotebookLM query outcome only
- auth/session problems degrade to warnings in result envelope

German_NewWords carryover lessons adopted here:

- session bootstrap is operational concern, not analysis-mode identity
- notebook lookup uses stable notebook identity, not title text
- auth problems must fail soft for optional context, not hard for whole review action

## Wave 4: Add notebook discovery and persistence

Notebook discovery is settings-owned.

Concrete behavior:

- `Refresh Notebook List` calls NotebookLM notebook listing path
- selector stores chosen notebook by `notebook_id`
- display text mirrors latest known title in `notebook_title`
- save writes both values back into `modes.deep`

Rules:

- no free-text notebook entry in Phase 2
- no multi-select notebook support
- no per-card notebook override
- no per-review chooser dialog
- no standard-mode access to notebook list
- review-time deep analysis must not call notebook-list APIs

If notebook list fetch fails:

- keep existing saved notebook values unchanged
- show settings-level error/status message
- do not clear `notebook_id` automatically

## Wave 5: Add optional NotebookLM context retrieval to deep analysis

Deep runtime stays single-family.

Phase 2 runtime branch rules:

### Case A: `use_notebooklm == false`

Behavior:

- run exact Phase 1 deep analysis path
- resolve `context_sources` as `[]`
- resolve `sources_used` as `[]`

### Case B: `use_notebooklm == true` and `notebook_id == ""`

Behavior:

- run deep analysis without NotebookLM context
- add warning: `NotebookLM enabled but no target notebook selected.`
- keep `context_sources` as `[]`
- keep `sources_used` as `[]`

Review-time lookup rule:

- when `use_notebooklm == true` and `notebook_id` is non-blank, runtime attempts one direct NotebookLM query by saved `notebook_id`
- review-time runtime must not refresh notebook list first

### Case C: `use_notebooklm == true` and notebook selected, but auth/session/query fails

Behavior:

- run deep analysis without NotebookLM context
- add warning describing skipped NotebookLM context
- keep `sources_used` as `[]`
- deep analysis stays available

### Case D: `use_notebooklm == true` and NotebookLM query succeeds

Behavior:

- retrieve notebook context first
- inject returned context into deep prompt assembly
- resolve `context_sources` as `["notebooklm"]`
- resolve `sources_used` as `["notebooklm"]`

Phase 2 does not change top-level resolved request shape from master spec.

NotebookLM context is transient orchestration input only.

It is not a new top-level request family.

## Wave 6: Define NotebookLM query contract

Phase 2 uses one fixed retrieval contract for NotebookLM.

Inputs to NotebookLM retrieval prompt:

- card question text
- canonical expected answer
- accepted-answer variants when present
- user answer
- current note language when available

Required retrieval intent:

- fetch concise source-grounded reference context that helps deep evaluation judge correctness, acceptable variants, and major omissions

Output handling contract:

- NotebookLM response is treated as plain context text
- Phase 2 does not require structured JSON from NotebookLM
- Phase 2 does not parse NotebookLM into a second scoring schema
- deep-model prompt receives NotebookLM context as an optional extra block
- adapter trims NotebookLM context to first `4000` characters after whitespace normalization before prompt injection
- if trimming occurs, result warnings include explicit NotebookLM truncation notice

Boundaries:

- NotebookLM is retrieval aid only
- configured deep LLM remains final scorer/renderer
- NotebookLM does not bypass existing deep prompt profile
- Phase 2 does not add separate NotebookLM prompt-profile settings

Operational limits:

- NotebookLM query must use strict timeout
- one failed NotebookLM query must not stall whole review flow indefinitely
- timeout or runtime failure downgrades to warning-backed deep analysis

## Wave 7: Cache policy for optional NotebookLM

Shared cache contract remains single-owner.

Request-identity additions for NotebookLM-enabled deep mode:

- `use_notebooklm`
- `notebook_id`

Non-keys:

- `notebook_title` is not cache identity
- session status is not cache identity

Write policy:

- deep result with NotebookLM disabled may cache normally
- deep result with NotebookLM enabled must not be written as reusable persistent cache entry in Phase 2, regardless of retrieval success or failure

Reason:

- avoids stale NotebookLM-backed results when notebook contents change outside addon control
- avoids stale fallback result from masking later successful enriched run under same notebook identity

## Wave 8: Docs and proofs

Phase 2 doc updates must cover:

- deep tab now has optional NotebookLM block
- NotebookLM is deep-only
- NotebookLM session/auth is manual
- notebook target persists by `notebook_id`
- deep review still works without NotebookLM

Phase 2 runnable proofs must cover:

- UI enable/disable symmetry
- notebook selection persistence
- fallback warnings
- successful source attribution
- cache behavior on retrieval failure vs success

# Design Decisions

## Decision 1: NotebookLM settings live in `Deep`, not `Providers`

NotebookLM is optional deep-mode context, not LLM provider transport.

Therefore:

- provider creds remain in `Providers`
- NotebookLM toggle/session/notebook controls live in `Deep`
- review panel stays action-only, not settings-owning

## Decision 2: NotebookLM control is explicit two-stage gating

Two gates exist:

1. `Use Deep Analysis`
2. `Use NotebookLM MCP`

Reason:

- preserves Phase 1 deep behavior when NotebookLM is irrelevant
- makes NotebookLM opt-in and visually subordinate to deep mode
- keeps grayout behavior symmetric and predictable

## Decision 3: Notebook identity SSOT is `notebook_id`

`notebook_title` is persisted only for display continuity.

Reason:

- stable identity
- title drift safe
- matches earlier NotebookLM project lessons

## Decision 4: Session/auth remains manual at settings time

Review-time deep analysis must not surprise user with login/bootstrap UI.

Reason:

- predictable UX
- no side-effectful auth during answer review
- optional context stays optional

## Decision 5: NotebookLM remains retrieval-only

NotebookLM provides context.

Configured deep LLM still performs final analysis.

Reason:

- preserves one scorer family
- avoids split-brain result synthesis
- keeps result contract unchanged

## Decision 6: Fallback deep result stays normalized

NotebookLM failures degrade to warnings, not to separate error mode.

Reason:

- one panel shell
- one result family
- one regenerate contract

## Decision 7: NotebookLM-enabled deep runs are non-cacheable in Phase 2

If NotebookLM was requested, result is displayable but not persistently reusable-cacheable in Phase 2.

Reason:

- notebook contents can change outside addon control without stable revision token
- avoids stale degraded cache poisoning
- keeps Phase 2 small until real freshness token exists

# Invariants

1. Phase 1 deep behavior remains exact when `use_notebooklm == false`.
2. NotebookLM is legal only for deep mode.
3. Standard mode must not read, render, or depend on NotebookLM config.
4. `modes.deep.notebook_id` is authoritative persisted notebook identity.
5. `modes.deep.notebook_title` is display-only metadata.
6. `Providers` tab remains sole owner of LLM provider credentials and provider-saved model extras.
7. `Deep` tab remains sole owner of NotebookLM toggle, session action, and notebook selector.
8. Review panel remains one shared `AI Analysis` shell.
9. Regenerate reruns current normalized request family; it does not open settings-time auth flows.
10. Successful NotebookLM context may enrich deep prompt assembly, but may not redefine top-level request/result ownership.
11. Deep fallback result from NotebookLM failure must still normalize into shared result envelope.
12. `sources_used` contains `"notebooklm"` only when NotebookLM context was actually retrieved and injected.
13. `context_sources` contains `"notebooklm"` only when runtime request resolves to actual NotebookLM usage.
14. Phase 2 does not add multi-notebook aggregation.
15. Phase 2 does not add NotebookLM support to standard analysis.
16. Review-time deep analysis queries NotebookLM directly by saved `notebook_id`; it does not refresh notebook list first.
17. NotebookLM context injection is capped to first `4000` characters after whitespace normalization.
18. Phase 2 does not write reusable persistent cache entries for NotebookLM-enabled deep runs.

# Acceptance Criteria

1. Deep settings show `Use NotebookLM MCP` only inside `Deep` tab.
2. NotebookLM subcontrols gray out unless both deep mode and NotebookLM mode are enabled.
3. `Providers` tab contains no NotebookLM controls.
4. Saved notebook choice persists by `notebook_id` and survives title changes.
5. If notebook list refresh fails, saved notebook config is preserved.
6. Deep analysis with `use_notebooklm == false` matches Phase 1 request/result behavior.
7. Deep analysis with NotebookLM enabled but no notebook selected still returns normalized deep result with warning.
8. Deep analysis with NotebookLM enabled and auth/query failure still returns normalized deep result with warning.
9. Deep analysis with NotebookLM success returns normalized deep result whose `sources_used` includes `"notebooklm"`.
10. Standard analysis remains fully independent of NotebookLM auth state and notebook settings.
11. Review-time deep analysis uses saved `notebook_id` directly and does not re-list notebooks first.
12. NotebookLM context injected into deep prompt is deterministically capped and warns when truncated.
13. Phase 2 writes no reusable persistent cache entry for NotebookLM-enabled deep runs.
14. Config docs and README explain manual session step and optional fallback semantics.

# Non-Goals

- no NotebookLM support for standard analysis
- no NotebookLM controls in `Providers`
- no per-provider NotebookLM credentials surface
- no per-card or per-note notebook override
- no multi-notebook selection or aggregation
- no NotebookLM-only analysis mode
- no automatic interactive auth popup during review action
- no structured NotebookLM JSON parsing requirement in Phase 2
- no separate NotebookLM prompt profile in Phase 2
- no second result panel or second result schema

# Risks and Mitigations

## Risk: NotebookLM UI drifts into provider-owned settings

Mitigation:

- keep all NotebookLM controls in `Deep`
- keep `Providers` unchanged except existing LLM provider controls

## Risk: title-based persistence causes notebook drift bugs

Mitigation:

- persist and resolve by `notebook_id`
- treat title as display metadata only

## Risk: auth failures make deep analysis feel broken

Mitigation:

- manual session button in settings
- runtime fallback with explicit warning
- no hard failure for optional context path

## Risk: stale fallback cache hides later enriched run

Mitigation:

- do not write reusable persistent cache entries for NotebookLM-enabled deep runs in Phase 2

## Risk: NotebookLM becomes second scorer with divergent output style

Mitigation:

- keep NotebookLM retrieval-only
- keep configured deep model as sole final analyzer

## Risk: review action blocks too long on NotebookLM

Mitigation:

- strict timeout
- soft failure to warning-backed deep analysis

# Validation Plan

- proof target: deep-tab NotebookLM controls obey two-gate symmetry
  - method: UI-contract inspection test for deep off, deep on + notebook off, deep on + notebook on
  - evidence: controls gray/ungray exactly per spec; `Providers` tab stays NotebookLM-free

- proof target: notebook selection persists by stable identity
  - method: config round-trip test with notebook title change and same ID
  - evidence: saved `notebook_id` remains authority; display title updates without breaking selection

- proof target: deep without NotebookLM stays Phase 1-equivalent
  - method: request/result comparison test with `use_notebooklm == false`
  - evidence: resolved deep request uses empty notebook fields and no NotebookLM source metadata

- proof target: missing notebook degrades softly
  - method: runtime test with `use_notebooklm == true` and blank `notebook_id`
  - evidence: normalized result exists; warning present; `sources_used == []`

- proof target: auth/query failure degrades softly
  - method: runtime test with NotebookLM retrieval stub raising auth/runtime error
  - evidence: normalized result exists; warning present; no NotebookLM source attribution

- proof target: successful NotebookLM retrieval enriches source metadata
  - method: runtime test with NotebookLM retrieval stub returning context text
  - evidence: deep request path records `context_sources == ["notebooklm"]`; normalized result records `sources_used == ["notebooklm"]`

- proof target: review-time deep analysis never re-lists notebooks
  - method: runtime test with saved `notebook_id`, notebook-list stub, and NotebookLM query stub
  - evidence: direct query path is used; notebook-list stub is not called

- proof target: NotebookLM context cap is deterministic
  - method: runtime test with oversized NotebookLM response text
  - evidence: injected context is trimmed to first `4000` characters after whitespace normalization and warning is present

- proof target: NotebookLM-enabled deep runs are non-cacheable in Phase 2
  - method: cache behavior test with NotebookLM-enabled success and failure runs
  - evidence: no reusable persistent cache entry is written for either run

- proof target: standard mode ignores NotebookLM state completely
  - method: runtime and UI-contract tests with NotebookLM enabled in deep config
  - evidence: standard controls, requests, and results stay unchanged

Preferred runnable proof artifact targets:

- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- one narrow NotebookLM runtime-contract test file if current UI-contract file becomes too crowded

# Completion Criteria

- concrete Phase 2 behavior is specified without reopening master-spec SSOT boundaries
- implementation can proceed with one bounded plan
- Phase 1 and Phase 2 responsibilities stay non-overlapping
- NotebookLM remains optional, deep-only, and retrieval-only
- fallback, cache, notebook persistence, and docs obligations are explicit enough for implementation and review
