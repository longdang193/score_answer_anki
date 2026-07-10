---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: deep-analysis-phased-ssot-master
parent_workstream: none
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/Config.md
  - packages/score_answer_anki/README.md
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
related_features:
  - ai-analysis-ui
  - deep-analysis
  - prompt-profile
  - notebooklm-mcp
related_stages:
  - design
  - implementation
---

# Goal

Introduce `Deep Analysis` in two implementation phases while preserving one SSOT-driven analysis architecture across all admissible score-card cases.

This master spec defines shared contracts and phase boundaries only. It is the parent design artifact for two later detailed specs:

- Phase 1: `Deep Analysis` without NotebookLM MCP
- Phase 2: `Deep Analysis` with optional NotebookLM MCP context

Requested behavior:

- keep current `AI Analysis` fast path available
- add `Deep Analysis` as a second analysis mode, not a second subsystem
- give deep mode its own prompt profile
- let deep mode use a stronger configured model than standard mode
- make NotebookLM MCP optional, not mandatory
- keep one uniform request, cache, state, render, and regenerate flow across all admissible cases

Admissible cases for this master spec are exactly:

- score-eligible cards that already pass current scoring gate
- `standard` analysis mode
- `deep` analysis mode without NotebookLM MCP
- `deep` analysis mode with NotebookLM MCP disabled by config
- `deep` analysis mode with NotebookLM MCP enabled and notebook selected
- `deep` analysis mode with NotebookLM MCP enabled but unavailable due auth, notebook selection, or runtime failure

Uniform rule:

- all admissible cases must route through one shared analysis request contract, one shared runtime resolver, one shared result contract, one shared panel shell, and one shared cache policy

# Key Deliverables

1. One master SSOT contract for analysis request resolution, result normalization, cache identity, and panel ownership.
2. One phase boundary for `Deep Analysis` core behavior with no NotebookLM dependency.
3. One phase boundary for optional NotebookLM-backed deep context, layered on top of Phase 1 contracts.
4. One config contract that separates shared settings, mode-owned settings, and provider-owned settings without duplicated truths.
5. One NotebookLM target contract that stores notebook identity by `notebook_id`, with notebook title as display-only metadata.
6. One symmetry policy preventing duplicated standard-vs-deep subsystems or duplicated provider-credential edit surfaces.
7. One four-tab settings topology: `General`, `Standard`, `Deep`, `Providers`.
8. One validation contract that future phase-specific specs must inherit without redefining SSOT boundaries.

# Task/Wave Breakdown

## Wave 1: Establish master analysis contracts

Define one canonical analysis runtime request shape.

Canonical resolved request shape:

```python
{
    "analysis_mode": "standard" | "deep",
    "question_text": str,
    "canonical_answer": str,
    "accepted_answers": list[str],
    "user_answer": str,
    "language": str,
    "provider": str,
    "model": str,
    "prompt_profile": str,
    "max_tokens": int,
    "temperature": float,
    "use_notebooklm": bool,
    "notebook_id": str,
    "notebook_title": str,
    "context_sources": list[str],
}
```

Rules:

- this is resolved runtime data, not raw UI widget state
- `analysis_mode` is always explicit
- `provider`, `model`, and `prompt_profile` are already resolved before request leaves runtime-resolution boundary
- `notebook_title` is display-only metadata and must never be used as lookup SSOT
- `context_sources` is empty in Phase 1 and may include `"notebooklm"` in Phase 2
- request builder must not branch into separate standard and deep payload formats

Define one canonical normalized result shape.

Canonical normalized result shape:

```python
{
    "status": "loading" | "ready" | "unavailable",
    "analysis_mode": "standard" | "deep",
    "scored": bool,
    "score": int | None,
    "tips": str,
    "sections": list[dict],
    "warnings": list[str],
    "sources_used": list[str],
}
```

Rules:

- panel renderer consumes normalized result only
- renderer must not infer mode from button origin or config widgets
- `sources_used` is empty in Phase 1 and may include `"notebooklm"` in Phase 2
- warnings such as auth failure or skipped context stay inside result envelope, not side channels only

## Wave 2: Phase 1 boundary — Deep Analysis core

Phase 1 introduces deep mode without NotebookLM MCP.

Phase 1 owns:

- one deep-analysis trigger in UI
- one deep-mode runtime resolution path
- one mode/provider-separated settings contract
- one mode-owned model selection contract
- one mode-owned prompt-profile contract
- one mode-owned `max_tokens` / `temperature` contract
- one cache-key extension for mode-aware requests
- one shared panel shell that can show standard or deep result state uniformly
- one regenerate flow that reruns whichever normalized request is current

Phase 1 required settings topology:

- `General` tab owns shared review/UI settings only
- `Standard` tab owns standard-mode runtime settings only
- `Deep` tab owns deep-mode runtime settings only
- `Providers` tab owns shared provider connection settings only

Phase 1 ownership rules:

- shared settings: `language`, `show_anki_compare`, `show_code_compare`
- mode-owned settings for both `standard` and `deep`: `enabled`, `provider`, `model`, `prompt_profile`, `max_tokens`, `temperature`
- provider-owned settings: `base_url`, `api_key`, provider-scoped custom model registry, provider help text
- provider credentials and base URLs must be editable in one place only
- mode tabs may reference provider identities but must not duplicate provider credential inputs

Phase 1 runtime rules:

- standard mode resolves prompt profile from standard-mode settings
- deep mode resolves prompt profile from deep-mode settings
- standard and deep each resolve provider and model from their own mode block
- provider connection data always resolves from shared provider settings
- resolved request must include explicit `max_tokens` and `temperature` from current mode block
- if deep mode is disabled, normal review UI must not expose deep trigger
- if deep mode is enabled but deep model is blank, deep request is legal but resolves unavailable explicitly
- if migration state lacks explicit mode blocks or provider blocks, migration behavior must be defined in detailed Phase 1 spec, but runtime must still stay on one shared request shape

Phase 1 explicit non-scope:

- no NotebookLM checkbox behavior
- no NotebookLM auth flow
- no notebook selector
- no NotebookLM query or context merge
- no duplicated provider connection editors inside `Standard` and `Deep` tabs

## Wave 3: Phase 2 boundary — Optional NotebookLM context

Phase 2 layers optional NotebookLM MCP behavior on top of Phase 1 contracts.

Phase 2 owns:

- NotebookLM enable checkbox for deep mode settings
- NotebookLM auth / refresh-session control
- notebook selector UI
- notebook identity persistence by `notebook_id`
- optional context retrieval before deep-model call or as part of deep-analysis orchestration
- fallback behavior when NotebookLM is unavailable

Phase 2 required config additions:

- `deep_analysis_use_notebooklm`
- `deep_analysis_notebook_id`
- `deep_analysis_notebook_title`

Phase 2 runtime rules:

- NotebookLM integration is legal only for `deep` mode
- if `use_notebooklm` is false, deep mode must behave exactly like Phase 1 deep mode
- if `use_notebooklm` is true and `notebook_id` is missing, deep mode still runs and records warning
- if `use_notebooklm` is true and NotebookLM auth or runtime fails, deep mode still runs and records warning
- NotebookLM failure must never downgrade request shape or panel ownership into a special subsystem
- NotebookLM target lookup SSOT is `notebook_id`, not exact-title string matching at runtime call sites

Phase 2 explicit non-scope:

- no NotebookLM usage for standard mode
- no multi-notebook aggregation in V1
- no per-review modal notebook chooser
- no second deep-analysis panel variant

## Wave 4: Child detailed-spec authoring contract

This master spec requires two child detailed specs.

Phase 1 detailed spec must define exactly:

- four-tab settings topology and ownership boundaries
- mode and provider config migration from legacy flat keys
- exact fallback rules for disabled deep mode and blank deep model
- exact request builder and cache-key field list
- exact panel badge / action-label policy for deep results
- exact runnable proofs for standard-vs-deep symmetry and provider-setting SSOT

Phase 2 detailed spec must define exactly:

- NotebookLM enablement UI behavior
- auth/session status ownership
- notebook-list loading path
- notebook persistence and refresh rules
- context merge policy into deep analysis prompt/runtime
- exact runnable proofs for NotebookLM optionality and fallback behavior

Child specs must not redefine:

- normalized request shape
- normalized result shape
- notebook identity SSOT
- shared panel ownership
- shared regenerate ownership

# Design Decisions

## Decision 1: One analysis engine, not parallel standard/deep subsystems

`standard` and `deep` are runtime modes of one analysis system.

Reason:

- shortest path to SSOT
- avoids duplicated caches, spinners, renderers, and button handlers
- keeps future features mode-agnostic where possible

## Decision 2: Deep owns its own prompt profile explicitly

Deep mode must not mutate prompt behavior indirectly by only changing model.

Required ownership:

- standard mode has its own prompt-profile selector
- deep mode has its own prompt-profile selector

Reason:

- deep prompt can ask for richer reasoning, evidence, and uncertainty handling
- explicit config keeps prompt behavior inspectable and testable
- avoids hidden mode-based prompt rewriting scattered across code

## Decision 3: Mode settings and provider settings stay separate

Standard and deep are mode tabs. Provider credentials are provider tabs.

Reason:

- preserves one truth for provider connection data
- preserves symmetry between `standard` and `deep` mode contracts
- allows standard and deep to use same provider or different providers without copying credentials

Required outcome:

- no global `deep_analysis_model` authority in target design
- no duplicated `base_url` / `api_key` inputs inside mode tabs
- target settings layout is `General`, `Standard`, `Deep`, `Providers`

## Decision 4: NotebookLM is an optional context source, not a mode-defining subsystem

NotebookLM modifies deep context availability only.

It does not own:

- panel title
- panel shell
- cache namespace root
- regenerate button semantics
- scoring payload semantics outside context enrichment

Reason:

- keeps Phase 2 additive
- keeps deep mode usable when NotebookLM is unavailable
- prevents MCP failures from fragmenting core analysis behavior

## Decision 5: Notebook identity persists by `notebook_id`

Notebook title may change and may duplicate.

Required ownership:

- `deep_analysis_notebook_id` is authoritative persisted identity
- `deep_analysis_notebook_title` is UI display only

Reason:

- stable lookup contract
- matches earlier NotebookLM lessons from other project patterns
- prevents title-drift bugs

## Decision 6: Shared request and result envelopes are phase-stable

Phase 2 may add populated context metadata, but may not invent new top-level runtime families for deep-with-NotebookLM.

Reason:

- detailed specs stay layered instead of conflicting
- tests can assert stable API-like internal contracts
- render path stays uniform across all admissible cases

# Invariants

1. Current score-card gate remains single owner of whether any AI analysis path runs.
2. `standard` and `deep` share one analysis request builder family.
3. `standard` and `deep` share one analysis result normalization family.
4. Shared settings, mode settings, and provider settings each have one owner only.
5. Deep mode owns its own prompt profile and must not borrow standard prompt profile implicitly once resolved config exists.
5. NotebookLM is legal only for deep mode.
6. NotebookLM is optional even inside deep mode.
7. Notebook identity SSOT is `notebook_id`; title is display-only metadata.
8. Panel shell ownership remains one `AI Analysis` surface with mode-aware metadata, not split panels.
9. Regenerate action reruns current normalized request, regardless of mode or context-source availability.
11. Cache identity must distinguish at least: question/answer payload, `analysis_mode`, resolved provider, resolved model, resolved prompt profile, resolved `max_tokens`, resolved `temperature`, NotebookLM enablement, and notebook identity.
12. Standard-mode analysis must never depend on NotebookLM config or auth state.
13. Phase 2 may extend context collection, but may not redefine Phase 1 request/result ownership boundaries.

# Acceptance Criteria

1. Master spec clearly separates shared contracts from phase-specific behavior.
2. Master spec defines one normalized request shape used by both phases.
3. Master spec defines one normalized result shape used by both phases.
4. Master spec assigns prompt-profile ownership separately to standard and deep modes.
5. Master spec assigns NotebookLM identity ownership to `notebook_id`.
6. Master spec keeps NotebookLM optional for deep mode and disallowed for standard mode.
7. Master spec states child detailed specs may extend behavior but may not fork shared panel, cache, or result ownership.
8. Master spec provides enough contract detail that Phase 1 and Phase 2 detailed specs can be written without re-litigating SSOT boundaries.

# Non-Goals

- no implementation code in this master spec
- no final Phase 1 fallback-model UX decision beyond requiring one shared contract
- no duplicated provider credential storage or duplicate provider edit surfaces in V1
- no per-review notebook chooser popup
- no multi-notebook fan-in behavior
- no NotebookLM support for standard analysis mode
- no redesign of current score gating, answer comparison, or non-score-card behavior

# Risks and Mitigations

## Risk: deep mode forks panel and cache behavior

Mitigation:

- require one request envelope, one result envelope, one panel shell, one regenerate flow
- child specs must not introduce separate deep panel state stores without explicit superseding design

## Risk: cache collisions between standard and deep runs

Mitigation:

- make `analysis_mode`, resolved model, resolved prompt profile, NotebookLM usage, and notebook identity part of cache identity contract

## Risk: mode/provider ownership drifts back into duplicated fields

Mitigation:

- keep one provider settings surface under `Providers` only
- keep `Standard` and `Deep` tabs structurally identical
- keep mode resolver consuming one mode block plus one provider block

## Risk: deep prompt profile drifts into hidden special cases

Mitigation:

- deep prompt profile is explicit persisted config
- prompt resolution remains centralized and testable

## Risk: NotebookLM failure blocks deep analysis entirely

Mitigation:

- require fallback-to-deep-only behavior with warnings in normalized result
- keep NotebookLM as optional context source only

## Risk: notebook selection by title causes drift or ambiguity

Mitigation:

- persist and query by `notebook_id`
- keep title as display-only convenience

## Risk: phase specs overlap and contradict each other

Mitigation:

- this master spec freezes shared contracts first
- child specs own only their bounded phase surfaces

# Validation Plan

- proof target: shared request contract stays phase-stable
  - method: detailed-spec review plus later runnable request-builder tests
  - evidence: Phase 1 and Phase 2 specs both reference same top-level request fields and same ownership rules

- proof target: shared result contract stays phase-stable
  - method: detailed-spec review plus later UI-contract tests
  - evidence: standard, deep, and deep-plus-NotebookLM all normalize into one result family

- proof target: deep owns separate prompt-profile resolution
  - method: later config-resolution test with same card/input and different modes
  - evidence: resolved request shows distinct `prompt_profile` values when configured differently

- proof target: settings topology preserves SSOT
  - method: later config and UI-contract tests
  - evidence: provider credentials exist in provider-owned storage only; mode tabs resolve provider/model without duplicating connection fields

- proof target: NotebookLM remains optional
  - method: later fallback-path test
  - evidence: deep analysis still yields normalized result when NotebookLM is disabled, unconfigured, or unavailable

- proof target: notebook identity SSOT is stable
  - method: later notebook-config persistence test
  - evidence: runtime query path consumes `notebook_id`; title changes do not alter identity lookup

- proof target: child specs stay bounded
  - method: review child detailed specs against this master spec
  - evidence: no child spec redefines request envelope, result envelope, or panel ownership

Preferred runnable proof artifact targets for later implementation specs:

- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- one narrow runtime-config or request-builder test file if current UI-contract file becomes too crowded

# Completion Criteria

- master spec approved as parent architecture for deep-analysis rollout
- Phase 1 detailed spec authored within boundaries defined here
- Phase 2 detailed spec authored within boundaries defined here
- child specs inherit shared SSOT contracts without contradiction
- implementation planning may begin only after child detailed specs are accepted
