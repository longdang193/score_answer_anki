---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: deep-analysis-phase-1-core
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
related_stages:
  - design
  - implementation
---

# Goal

Implement Phase 1 of `Deep Analysis`: add deep-mode analysis without NotebookLM MCP, while staying inside the shared SSOT contracts defined by `docs/superpowers/specs/2026-07-10-18-09-deep-analysis-phased-ssot-master-spec.md`.

Requested behavior:

- keep current automatic standard `AI Analysis` behavior on score-eligible cards
- add one manual `Deep Analysis` action for harder questions
- let deep mode use a stronger configured model than standard mode
- let deep mode use its own prompt profile
- keep one shared request builder, cache family, result family, panel shell, and regenerate flow
- do not add any NotebookLM MCP behavior in this phase

Supersession note:

- this spec supersedes the single-profile ownership from `docs/superpowers/specs/2026-07-04-13-35-global-prompt-profiles-only-spec.md` for analysis-mode prompt selection
- after this phase, prompt-profile ownership for analysis becomes mode-aware:
  - `standard_prompt_profile`
  - `deep_prompt_profile`
- legacy `prompt_profile` remains backward-compat input only during migration and is no longer authoritative once new keys exist

Admissible cases for this phase are exactly:

- score-eligible cards that already trigger current automatic standard analysis
- standard analysis requests created during answer reveal
- manual deep-analysis requests created from same reviewed answer context
- deep-analysis requests when deep mode is enabled and deep model is configured
- deep-analysis requests when deep mode is enabled and deep model is missing
- deep-analysis requests when deep mode is disabled

Uniform rule:

- Phase 1 always resolves one normalized request with `use_notebooklm: false`, `notebook_id: ""`, `notebook_title: ""`, and `context_sources: []`

# Key Deliverables

1. One mode-aware analysis request builder for `standard` and `deep`.
2. One mode/provider-separated config contract with four settings tabs: `General`, `Standard`, `Deep`, `Providers`.
3. One manual `Deep Analysis` trigger in review UI, layered on top of current automatic standard analysis.
4. One shared result envelope that records analysis mode and keeps deep-mode fallback behavior explicit.
5. One cache-key extension that prevents collisions between standard and deep runs for same card and answer.
6. One docs update describing four-tab settings topology, deep enablement, and separate mode/provider ownership.
7. Focused runnable proof for config migration, request resolution, deep-trigger behavior, and standard-vs-deep cache separation.

# Task/Wave Breakdown

## Wave 1: Config contract and migration

Replace flat prompt/model ownership with one symmetric config topology.

Canonical Phase 1 persisted config shape:

```json
{
  "general": {
    "language": "english",
    "show_anki_compare": true,
    "show_code_compare": true
  },
  "modes": {
    "standard": {
      "enabled": true,
      "provider": "custom_openai",
      "model": "cx/gpt-5.4-mini",
      "prompt_profile": "cloze_recall",
      "max_tokens": 100,
      "temperature": 0.7
    },
    "deep": {
      "enabled": false,
      "provider": "custom_openai",
      "model": "cx/gpt-5.5",
      "prompt_profile": "cloze_recall",
      "max_tokens": 300,
      "temperature": 0.4
    }
  },
  "providers": {
    "custom_openai": {
      "base_url": "http://127.0.0.1:20128/v1",
      "api_key": "",
      "custom_models": []
    }
  }
}
```

Config ownership rules:

- `general` owns shared review/UI settings only
- `modes.standard` and `modes.deep` own runtime behavior only
- `providers.<provider_key>` owns shared provider connection settings only
- provider credentials and base URLs must not be duplicated under mode tabs
- `Use Deep Analysis` checkbox is exact UI for `modes.deep.enabled`
- `Use Standard Analysis` checkbox is exact UI for `modes.standard.enabled`

Mode ownership rules:

- both mode blocks share same schema: `enabled`, `provider`, `model`, `prompt_profile`, `max_tokens`, `temperature`
- `standard` and `deep` differ only by values, never by schema
- `model` is mode-owned because stronger/deeper model choice is part of mode behavior
- `provider` is mode-owned so standard and deep may select same or different providers uniformly

Provider ownership rules:

- each provider block owns `api_key`
- `Custom OpenAI-Compatible` provider block also owns `base_url`
- provider block owns provider-scoped `custom_models` registry
- builtin provider models remain code-owned defaults, not persisted duplicated payload

Exact migration rules from current flat config:

1. move legacy `language`, `show_anki_compare`, and `show_code_compare` into `general`
2. map legacy global `enabled` into `modes.standard.enabled`; if missing, default `true`
3. map legacy deep availability into `modes.deep.enabled`; if legacy deep model is non-blank, default `true`, else default `false`
4. map legacy global `provider` into both `modes.standard.provider` and `modes.deep.provider` when mode-specific provider is absent
5. map legacy provider-specific standard model into `modes.standard.model`
6. map legacy `deep_analysis_model` into `modes.deep.model`
7. map legacy `standard_prompt_profile` / `deep_prompt_profile`; if absent, derive from legacy `prompt_profile` as before
8. copy legacy `max_tokens` and `temperature` into both mode blocks on first migration only
9. move legacy provider connection fields into `providers.<provider_key>` blocks
10. keep legacy flat keys readable during migration, but save path must emit canonical nested shape only

Save-path rules:

- save path must always persist `general`, `modes`, and `providers` blocks explicitly
- save path must not persist global `deep_analysis_model` as runtime authority
- save path must not persist duplicate provider credentials under mode blocks
- save path must continue to persist shared custom prompt fields only once

Prompt-profile choice set for both standard and deep:

- `default`
- `strict_stem`
- `speaking_flexible`
- `cloze_recall`
- `custom`

Custom-profile rule:

- both standard and deep may resolve to `custom`
- both modes share the current global custom prompt fields
- this phase does not add separate deep-only custom prompt textareas

## Wave 2: Resolved request contract for Phase 1

Add one mode-aware request builder.

Preferred helper shape:

```python
build_analysis_request(card, user_answer: str, analysis_mode: str) -> dict
```

Phase 1 resolved request shape:

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
    "use_notebooklm": False,
    "notebook_id": "",
    "notebook_title": "",
    "context_sources": [],
}
```

Resolution rules:

- `standard` request resolves provider, model, prompt profile, `max_tokens`, and `temperature` from `modes.standard`
- `deep` request resolves provider, model, prompt profile, `max_tokens`, and `temperature` from `modes.deep`
- both modes resolve provider connection data from shared `providers` storage
- both modes resolve shared `language` from `general.language`
- request builder must remain source of truth for mode-specific request resolution
- downstream AI call path must consume resolved request data rather than re-deriving mode-specific values ad hoc

Deep-model blank rule:

- if `analysis_mode == "deep"` and `modes.deep.enabled == false`, deep request is legal but resolves to unavailable result with explicit reason `Deep analysis disabled`
- if `analysis_mode == "deep"` and deep model is blank after trim, deep request is legal but resolves to unavailable result with explicit reason `Deep analysis model not configured`
- runtime must not silently fall back to standard model for deep mode

Reason:

- user asked for stronger configured model, not hidden reuse of same fast model
- explicit failure keeps deep-mode semantics truthful

## Wave 3: Shared cache and current-request ownership

Extend request identity and cache identity so standard and deep results do not collide.

Exact ordered cache-key field list:

1. `card_id`
2. `card_ord`
3. hashed `question_text`
4. hashed `canonical_answer`
5. hashed `language`
6. hashed resolved `provider`
7. hashed resolved `model`
8. hashed resolved `prompt_profile`
9. hashed resolved `max_tokens`
10. hashed resolved `temperature`
11. hashed resolved `prompt_contract`
12. hashed `analysis_mode`
13. hashed `user_answer`
14. hashed `accepted_answers`
15. hashed `analysis_prompt_version`

Cache ownership rules:

- Phase 1 keeps current base cache identity grain and extends it rather than inventing a second cache family
- resolved `prompt_contract` remains authoritative for prompt-content drift
- resolved `prompt_profile` is still included explicitly so mode-profile identity is visible and testable even if two profiles temporarily render same prompt text
- `use_notebooklm` and `notebook_id` remain neutral Phase 1 values and do not need separate cache entropy beyond the always-fixed request values for this phase

Preferred state ownership upgrade:

```python
current_analysis_context = {
    "card_id": int | None,
    "expected_provided_tuple": tuple[str, str],
    "type_pattern": str | None,
    "request": dict,
    "standard_cache_key": str | None,
    "cache_key": str,
}
```

Rules:

- regenerate must rerun current normalized request from stored request identity, not reconstruct mode heuristically
- request identity must be sufficient to know whether current panel represents standard or deep mode
- current standard automatic analysis and manual deep analysis may both exist in cache for same card, but current panel context points to one active request at a time
- when current panel represents deep mode, `standard_cache_key` points to sibling standard result for same reviewed answer context

## Wave 4: Review UI trigger and panel behavior

Keep current automatic standard analysis on answer reveal.

Add one manual `Deep Analysis` trigger to existing `AI Analysis` panel.

Required trigger behavior:

- standard analysis continues to start automatically via existing reveal path
- `Deep Analysis` is manual only in Phase 1
- clicking `Deep Analysis` starts one deep request for current reviewed answer context
- deep request reuses same question, accepted-answer, user-answer, and card context as standard request

Button placement rule:

- add `Deep Analysis` button in same panel header action area as current `Regenerate` button
- keep panel title `AI Analysis`
- do not create separate deep-analysis panel shell

Visibility rule:

- `Deep Analysis` button appears only when current panel request mode is `standard`
- `Regenerate` remains available for whichever mode is currently displayed
- when current panel mode is `deep`, `Deep Analysis` button is hidden for that panel instance

Return-path rule:

- when current panel mode is `deep` and `standard_cache_key` resolves to cached standard result, panel shows `Show standard` action
- `Show standard` switches current panel context back to cached standard result without recomputing it
- if sibling standard result is unavailable for same context, `Show standard` action is hidden rather than triggering heuristic rebuild

Deep-model availability rule:

- if deep mode is enabled but `modes.deep.model` is blank, do not render `Deep Analysis` button in normal review flow
- runtime unavailable fallback still exists as safety net for direct helper calls or stale UI state

Mode badge rule:

- panel header adds one small mode badge or equivalent localized mode indicator
- standard result shows `Standard`
- deep result shows `Deep`
- score badge remains separate from mode indicator

Loading rule:

- when deep request is in progress, loading state must identify that current mode is deep
- loading shell remains same component family as current analysis spinner

Unavailable rule:

- if deep request resolves unavailable, panel stays inside same shell with deep mode indicator and explicit reason text
- unavailable deep result must not create second alert system or modal-only fallback

## Wave 5: Runtime call path and result normalization

Route both modes through one analysis executor family.

Required call-path refactor boundary:

- current `store_ai_analysis(...)` becomes mode-aware
- current `analyze_answer_with_ai(...)` must accept resolved mode-aware request inputs directly or through one thin wrapper
- current provider call helper remains shared

Required result normalization for Phase 1:

```python
{
    "status": "ready" | "unavailable",
    "analysis_mode": "standard" | "deep",
    "scored": bool,
    "score": int | None,
    "tips": str,
    "sections": list[dict],
    "warnings": list[str],
    "sources_used": list[str],
}
```

Phase 1 result rules:

- successful standard and deep results normalize into same top-level family
- `analysis_mode` is explicit in normalized result
- `sections` stays in normalized result to preserve master-spec result shape and current structured-render path
- `warnings` defaults to `[]`
- `sources_used` defaults to `[]`
- deep result must not fabricate NotebookLM-related metadata in this phase
- existing structured analysis fields needed by current shared section builder, such as `sample_answers` and `question_variants`, remain legal compatibility fields in Phase 1, but `sections` is authoritative render input contract

Section-rendering rule:

- current section-building and rich-rendering path remains shared
- Phase 1 must not regress existing structured section behavior already exercised by `sample_answers` and `question_variants`
- any mode-specific rendering metadata must come from normalized result and shared UI text lookup only

## Wave 6: Config dialog changes

Replace mixed layout with four top-level tabs:

- `General`
- `Standard`
- `Deep`
- `Providers`

`General` tab owns:

- `language`
- `show_anki_compare`
- `show_code_compare`

`Standard` tab required controls:

- `Use Standard Analysis` checkbox
- `Provider` dropdown
- `Model` dropdown / editable combo
- `Prompt profile` dropdown
- `Max tokens`
- `Temperature`
- mode-scoped `Test API Connection` button

`Deep` tab required controls:

- `Use Deep Analysis` checkbox
- `Provider` dropdown
- `Model` dropdown / editable combo
- `Prompt profile` dropdown
- `Max tokens`
- `Temperature`
- mode-scoped `Test API Connection` button

`Providers` tab owns:

- one provider sub-tab per provider
- shared provider `API Key` inputs
- shared provider `Base URL` input where applicable
- provider-scoped custom-model registry editor
- provider help text

Control behavior rules:

- `Standard` and `Deep` tabs must be structurally symmetric
- `Use Deep Analysis` unchecked means all other controls in `Deep` tab are disabled except the checkbox itself
- `Use Standard Analysis` unchecked disables standard-mode runtime behavior and hides standard auto-analysis path
- `Providers` tab controls never duplicate into `Standard` or `Deep` tabs
- current custom prompt fields remain one shared block
- shared custom block is visible iff standard or deep prompt profile resolves to `custom`
- if neither selected mode-profile is `custom`, shared custom block is hidden and read-only
- no new per-mode custom prompt textareas

Action-label rules:

- delete brain icon from review action area
- `Deep Analysis` action is plain text label only
- `Show standard` action is plain text label only

Model input rules:

- trim on save
- empty deep model is allowed in config but means deep trigger unavailable even when deep mode is enabled
- no provider-side model validation at save time beyond non-destructive trim in Phase 1

## Wave 7: Docs and runnable proof

Update docs:

- `Config.md`
- `README.md`

Required doc changes:

- explain difference between automatic standard analysis and manual deep analysis
- explain `Standard`-tab prompt profile vs `Deep`-tab prompt profile
- explain four-tab settings topology and mode/provider ownership
- explain `Use Deep Analysis` behavior and deep-tab disable/enable behavior
- explicitly state NotebookLM is not part of Phase 1

Required runnable proof targets:

- config migration from legacy flat `prompt_profile` into `modes.standard.prompt_profile` and `modes.deep.prompt_profile`
- standard and deep request resolution differ only in intended mode-owned fields
- standard and deep cache keys differ for same card/user answer
- deep trigger hidden when deep mode is disabled
- deep trigger hidden when deep mode is enabled but deep model is blank
- deep trigger visible when deep mode is enabled, deep model is configured, and current panel mode is standard
- deep result stores and renders `analysis_mode == "deep"`
- deep panel exposes `Show standard` only when sibling cached standard result exists
- regenerate reruns deep when deep result is active
- standard automatic path stays unchanged for score-eligible cards
- current structured section rendering for `sample_answers` and `question_variants` remains intact in both modes

# Design Decisions

## Decision 1: Standard remains automatic; deep is manual

Reason:

- preserves current fast path
- avoids extra latency on every review
- matches user intent that only some harder questions need deeper analysis

## Decision 2: Deep-model blank is explicit unavailability, not silent fallback

Reason:

- deep mode should mean stronger configured model
- silent fallback would make deep label misleading
- explicit unavailability is easier to test and document

## Decision 3: One shared custom prompt block remains enough for Phase 1

Reason:

- user requested separate deep prompt profile, not separate deep custom prompt editor
- avoids doubling prompt-editor UI before there is proven need
- shortest diff that still preserves explicit mode-owned profile selection

## Decision 4: One panel shell owns both modes

Reason:

- keeps UI symmetry with master spec
- avoids duplicate loading, refresh, and score-badge components
- user sees deep as stronger pass over same answer, not as disconnected tool

## Decision 5: Mode tabs own provider/model choice; provider tabs own credentials

Reason:

- preserves one truth for provider connection data
- keeps `Standard` and `Deep` tabs fully symmetric
- supports same-provider and cross-provider standard/deep pairs uniformly
- removes need for global `deep_analysis_model` special case in target design

# Invariants

1. Current score-card gate remains sole owner of whether analysis runs at all.
2. Standard analysis still auto-runs on answer reveal when `modes.standard.enabled == true`.
3. Deep analysis never auto-runs in Phase 1.
4. `Standard` and `Deep` tabs share same mode schema.
5. `Providers` tab is sole owner of provider credentials and base URLs.
6. Standard mode uses `modes.standard.prompt_profile` only.
7. Deep mode uses `modes.deep.prompt_profile` only.
8. Standard mode uses `modes.standard.provider` and `modes.standard.model` only.
9. Deep mode uses `modes.deep.provider` and `modes.deep.model` only.
10. Blank deep model never causes silent fallback to standard model.
11. Deep-disabled state never exposes normal-review deep trigger.
12. Cache identity distinguishes mode, provider, model, prompt profile, `max_tokens`, and `temperature`.
13. Shared custom prompt fields remain single-owner even when both modes use `custom`.
14. Review action labels remain text-only; no brain icon.
15. Phase 1 docs do not mention NotebookLM setup as part of deep-mode operation.

# Acceptance Criteria

1. Config dialog exposes four top-level tabs: `General`, `Standard`, `Deep`, `Providers`.
2. `Standard` and `Deep` tabs expose same field families: `enabled`, `provider`, `model`, `prompt_profile`, `max_tokens`, `temperature`.
3. `Providers` tab is sole edit surface for provider credentials and base URLs.
4. Legacy flat config migrates into canonical `general`, `modes`, and `providers` blocks.
5. Standard and deep requests resolve from their own mode blocks and shared provider blocks.
6. Standard and deep cache entries do not collide for same card and answer.
7. Clicking `Deep Analysis` on a standard panel launches deep request for same answer context.
8. Deep results render inside same `AI Analysis` panel shell with clear deep-mode indicator.
9. `Regenerate` reruns whichever mode is currently displayed.
10. If deep mode is disabled, normal review UI does not expose deep trigger.
11. If deep mode is enabled but deep model is blank, normal review UI does not expose deep trigger.
12. Deep panel can return to cached standard result through explicit `Show standard` action when sibling standard result exists.
13. Existing structured section rendering remains intact for scored results in both modes.
14. Review action area uses text-only labels; no brain icon.
15. Phase 1 docs do not mention NotebookLM setup as part of deep-mode operation.

# Non-Goals

- no NotebookLM checkbox
- no NotebookLM auth flow
- no notebook selector
- no notebook context retrieval
- no duplicated provider credential editors inside `Standard` or `Deep` tabs
- no separate deep-only panel shell
- no separate deep-only custom prompt textareas
- no deep auto-run on answer reveal

# Risks and Mitigations

## Risk: prompt-profile migration creates two competing truths

Mitigation:

- make `standard_prompt_profile` and `deep_prompt_profile` explicit runtime authorities
- use legacy `prompt_profile` only as load-time migration input

## Risk: mode/provider ownership drifts back into duplicated fields

Mitigation:

- keep `Providers` tab as sole provider-credential edit surface
- keep `Standard` and `Deep` tabs schema-identical
- route runtime resolution through one mode resolver plus one provider resolver

## Risk: deep button confuses current panel state

Mitigation:

- show deep trigger only on standard panel state
- add explicit mode badge for displayed result
- keep regenerate bound to current request identity

## Risk: custom prompt editor becomes ambiguous when only one mode is `custom`

Mitigation:

- helper text must state shared custom fields are used by any mode whose profile resolves to `custom`
- keep one editor block instead of duplicate editors with drifting content

## Risk: standard and deep share accidental cache entries

Mitigation:

- require `analysis_mode`, resolved `model`, resolved `prompt_profile`, and resolved `prompt_contract` in cache identity

# Validation Plan

- proof target: legacy profile migration works
  - method: config-merge tests with legacy `prompt_profile` only and with explicit new keys
  - evidence: merged runtime config resolves deterministic `standard_prompt_profile` and `deep_prompt_profile`

- proof target: deep uses mode-owned model and profile
  - method: request-builder test for same card/user answer under `standard` and `deep`
  - evidence: resolved request differs in `analysis_mode`, `model`, and `prompt_profile` only where expected

- proof target: deep-disabled state is explicit non-availability
  - method: deep-request runtime test with `modes.deep.enabled == false`
  - evidence: normalized unavailable result reason is `Deep analysis disabled`

- proof target: blank deep model is explicit non-availability
  - method: deep-request runtime test with empty `modes.deep.model`
  - evidence: normalized unavailable result reason is `Deep analysis model not configured`

- proof target: standard and deep cache identities diverge
  - method: cache-key test using same card, question, answer, and user answer
  - evidence: standard and deep keys are unequal

- proof target: settings topology preserves SSOT
  - method: config and UI-contract tests
  - evidence: provider credentials are stored and edited in provider-owned surface only; mode tabs resolve provider/model without duplicating credentials

- proof target: panel action ownership stays coherent
  - method: UI-contract test for standard-panel render and deep-panel render
  - evidence: standard panel shows deep trigger only when deep mode is enabled and deep model configured; deep panel hides trigger; deep panel shows `Show standard` only when sibling standard cache exists; both keep shared shell

- proof target: regenerate reruns active mode
  - method: narrow state/handler test around current request identity
  - evidence: deep result active then regenerate causes deep request path, not standard request path

- proof target: standard return path is explicit and cache-backed
  - method: narrow state/handler test around `standard_cache_key`
  - evidence: deep result active then `Show standard` switches panel back to cached standard result without recomputation

- proof target: phase excludes NotebookLM cleanly
  - method: request/result inspection tests
  - evidence: deep requests resolve `use_notebooklm: false`, `notebook_id: ""`, `context_sources: []`, and `sources_used: []`

- proof target: structured section behavior does not regress
  - method: existing UI-contract tests plus one deep-mode render test
  - evidence: `sample_answers` and `question_variants` still render through shared section path in scored results

Minimum runnable proof artifact:

- extend `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- add one narrow runtime-config/request-resolution test file only if UI-contract file becomes too crowded

# Completion Criteria

- Phase 1 child spec approved
- implementation can proceed without reopening master-spec SSOT boundaries
- standard automatic analysis remains intact
- deep manual analysis is fully specified without NotebookLM dependency
- docs and runnable proofs are bounded to Phase 1 only
