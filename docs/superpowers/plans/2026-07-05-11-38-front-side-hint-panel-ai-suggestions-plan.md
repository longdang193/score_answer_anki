---
layer: change
artifact_type: plan
status: implemented_verified
template_id: implementation-plan
name: front-side-hint-panel-ai-suggestions
parent_spec: docs/superpowers/specs/2026-07-05-11-23-hint-panel-ai-suggestions-spec.md
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/config.json
  - packages/score_answer_anki/README.md
  - packages/score_answer_anki/Config.md
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
---

# Goal

Implement pre-answer front-side hint panel support in `score_answer_anki` for eligible `_score` typed-answer cards, with optional manual `Hint` field rendering, AI-generated hint suggestions, one hint-prompt slot per global prompt profile, bounded cache/state handling, and runnable contract proof.

Exact V1 scope:

- owner is `score_answer_anki` only
- surface is front side only
- card is eligible only when both are true:
  - existing `_score` template gate passes
  - current front-side render path is typed-answer-compatible for this add-on
- AI-unavailable behavior is one fixed UX:
  - show `Suggest Hint` disabled with localized reason text

# Execution Status

- [x] Task 1 complete: config and prompt-profile hint slot wired
- [x] Task 2 complete: eligibility, hint state, cache identity, reset helpers wired
- [x] Task 3 complete: front-side render path and JS message contract wired
- [x] Task 4 complete: front-side refresh helper, async generation path, bounded result handling wired
- [x] Task 5 complete: config dialog custom hint prompt field wired
- [x] Task 6 complete: docs and contract proof updated
- [x] Manual Anki front-side verification recorded
- [x] Lane branch / merge-path reconciliation recorded

# Key Deliverables

- One add-on-owned front-side `Hint` control and inline hint panel rendered from `packages/score_answer_anki/__init__.py`
- One SSOT manual-hint field contract for optional `Hint`
- One SSOT prompt-profile resolver that returns `system_prompt`, `analysis_prompt_template`, and `hint_prompt_template`
- One persisted `custom_hint_prompt_template` config field
- One background AI hint-generation path with duplicate-request gating and deterministic cache invalidation
- One targeted front-side DOM refresh helper that preserves panel-open state for same exposure
- Docs and runnable proof aligned to front-side-only behavior and no-auto-save boundary

# Task Breakdown

## Task 1: Extend config and prompt-profile registry for hint prompts

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/config.json`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Add `custom_hint_prompt_template` to shipped config with empty-string default.
- Extend config merge/save helpers so `custom_hint_prompt_template` is always present after merge and persisted on save.
- Keep `prompt_profile` as sole selector for both analysis and hint generation.
- Add one SSOT helper, for example `resolve_prompt_profile_content(config, language, profile_name)`, that returns exactly:
  - `system_prompt`
  - `analysis_prompt_template`
  - `hint_prompt_template`
- Expand built-in prompt-profile definitions so each built-in profile provides all three slots.
- Extend custom-profile resolution so `custom` uses:
  - `custom_system_prompt`
  - `custom_analysis_prompt_template`
  - `custom_hint_prompt_template`
- Route config-dialog reset logic, analysis prompt building, and hint prompt building through the same resolver helper.
- Keep one normalization path for prompt-profile names; do not add separate hint-profile routing.

Verification:
- built-in profiles resolve all three slots through one helper
- `custom` profile resolves persisted `custom_hint_prompt_template`
- saved config includes `custom_hint_prompt_template`
- no second selector/config path exists for hint prompting

## Task 2: Add explicit eligibility, hint state, and identity contracts

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Add one helper, for example `is_supported_typed_answer_card(card, front_html_or_kind)`, that defines typed-answer compatibility for front-side hint UI.
- Keep final eligibility check as one helper that requires both:
  - existing `_score` gate
  - typed-answer compatibility helper
- Add one bounded set of hint state stores near existing analysis state:
  - `hint_cache`
  - `is_generating_hint`
  - `current_hint_context`
  - `front_hint_panel_state`
- Define `front_hint_panel_state` grain exactly as one record keyed by current hint cache key with fields:
  - `cache_key`
  - `is_open`
- Reset `front_hint_panel_state` on:
  - card change
  - visible-question change
  - prompt-profile change
  - analysis-language change
  - custom-hint-template change
  - explicit panel close
- Add one helper to read optional `Hint` field from current note, defaulting to empty string.
- Add one helper to build normalized front-side hint context from current card using only:
  - `card.id`
  - `card.ord`
  - active visible question
  - canonical `Back`
  - manual `Hint`
  - analysis language
  - resolved prompt profile
  - hint prompt version constant
- Add one shared `build_hint_cache_key(...)` helper using those exact inputs.
- Add one invalidation helper that clears hint cache and matching panel state for one key.
- Add one full cache-reset helper called from config-save path and startup reset path.
- Keep user answer out of hint context and key.

Verification:
- non-typed `_score` cards do not show front-side hint UI
- typed `_score` cards do show front-side hint UI
- missing `Hint` field yields empty manual hint without exception
- identical front-side context yields same cache key
- profile/language/custom-hint changes clear hint cache and open-state
- hint invalidation does not affect existing answer-analysis cache helpers

## Task 3: Add front-side render path and JS message contract

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Add one front-side render helper wired through `gui_hooks.card_will_show` for question-side content only.
- Keep ownership in add-on code; do not modify `note_types/*` templates or reuse their local hint buttons.
- Render one add-on-owned `Hint` control only for cards passing the combined eligibility helper.
- Render one dedicated DOM container with stable ids for patching, for example:
  - `#aqi-front-hint-panel`
  - `#aqi-front-hint-body`
  - `#aqi-front-hint-actions`
- Render one inline panel placeholder owned by the add-on that can show:
  - manual hint block using note-field pass-through behavior
  - AI hint block using escaped plain text
  - action row with `Suggest Hint` or `Suggest Again`
- Keep panel collapsed by default and openable without revealing answer.
- Add JS message names and Python handler branches for exactly:
  - `toggle_hint_panel`
  - `suggest_ai_hint`
  - `regenerate_ai_hint`
- Keep message handlers front-side-only; do not route through `render_enhanced_comparison()`.

Verification:
- front-side render helper binds to question-side hook only
- eligible cards show `Hint` control before answer reveal
- manual hint block renders before AI hint block
- JS message handler returns handled state for toggle/suggest/regenerate messages
- answer-side enhanced comparison path remains unchanged by this task

## Task 4: Implement exact front-side refresh helper, async generation, and bounded results

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Add one exact front-side refresh helper, for example `refresh_front_hint_panel_dom(render_state)`, that updates the dedicated reviewer DOM container using `mw.reviewer.web.eval(...)` or one equivalent webview-eval helper.
- Keep this helper as sole authority for post-generation front-side panel refresh.
- Do not call `_showAnswer()`, `render_enhanced_comparison()`, or any full-card rerender path from hint-generation completion.
- Add one hint-prompt builder that consumes current hint context and resolved prompt-profile hint slot from `resolve_prompt_profile_content(...)`.
- Keep hint input contract exact:
  - `question_text`
  - `canonical_answer`
  - `manual_hint`
  - `language`
  - `prompt_profile`
- Add one output normalizer returning exactly:
  - `status`
  - `hint_text`
  - `error_text`
- Reuse existing provider/model/auth/transport code paths where possible; do not fork provider logic for hints.
- Add one `suggest_ai_hint()` path that:
  - exits early for ineligible cards
  - returns disabled-state result when AI unavailable
  - stores current hint context
  - blocks duplicate in-flight requests for same key
  - launches background task
  - writes normalized result into `hint_cache`
  - calls only `refresh_front_hint_panel_dom(...)` on completion
- Add one `regenerate_ai_hint()` path that invalidates one hint key then reruns generation for same front-side exposure.
- Preserve `front_hint_panel_state.is_open = true` on success and failure refresh for same key.

Verification:
- duplicate click while request active does not start second request
- regenerate invalidates old hint and reruns with same visible-question context
- AI-unavailable path returns disabled-state result, not hidden action
- provider failure leaves manual hint visible and returns bounded `error_text`
- targeted refresh does not reveal answer or collapse panel
- hint path has no `_showAnswer()` dependency

## Task 5: Extend config dialog for custom hint prompt field

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/config.json`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Add one `Custom hint prompt template` UI field beside existing custom system and analysis prompt fields.
- Show this field only when selected profile is `custom`.
- Keep non-`custom` profiles on read-only built-in prompt behavior with no extra freeform hint UI.
- Extend reset-to-default behavior for `custom` so it fills:
  - system prompt
  - analysis prompt template
  - hint prompt template
  from the selected language defaults resolved through `resolve_prompt_profile_content(...)`.
- Save path must persist `custom_hint_prompt_template` with other custom prompt fields.
- Config-save path must clear hint cache and `front_hint_panel_state` when prompt-profile-related inputs change.

Verification:
- `custom` profile shows three custom prompt inputs
- non-`custom` profiles hide three custom prompt inputs
- reset populates custom hint prompt from built-in default for current language
- save persists `custom_hint_prompt_template` and clears hint cache/open-state when changed

## Task 6: Update docs and tighten contract proof

Files:
- `packages/score_answer_anki/README.md`
- `packages/score_answer_anki/Config.md`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Document that front-side hint panel belongs to `score_answer_anki`, not note-template-local hint buttons.
- Document exact eligibility:
  - `_score` template gate
  - supported typed-answer front-side path
- Document optional `Hint` field behavior:
  - manual hint uses stored field-content pass-through path
  - AI hint is session-only generated plain text
  - AI hint is not auto-saved
- Document AI-unavailable behavior as disabled action with localized reason.
- Document prompt-profile behavior for hints, including new `custom_hint_prompt_template`.
- Extend the existing contract test with assert-based checks for:
  - combined eligibility helper
  - front-side-only ownership
  - missing `Hint` tolerance
  - manual hint pass-through ordering
  - escaped AI-hint rendering
  - toggle/suggest/regenerate message routes
  - built-in profile `hint_prompt_template` slot presence via `resolve_prompt_profile_content(...)`
  - persisted `custom_hint_prompt_template`
  - cache and open-state invalidation on config changes
  - duplicate-request blocking
  - regenerate preserving same context
  - AI-unavailable disabled behavior
  - hint path using dedicated DOM refresh helper instead of `_showAnswer()`

Verification:
- `python packages/score_answer_anki/test_ai_analysis_ui_contract.py` exits cleanly
- docs describe no-auto-save boundary, typed-answer eligibility, and disabled-state AI behavior

# Risks / Rollback

- Risk: front-side UI updates accidentally depend on answer-side rerender flow
  - rollback: keep `refresh_front_hint_panel_dom(...)` as sole refresh helper and assert no `_showAnswer()` dependency in hint path
- Risk: prompt-profile expansion drifts between analysis and hint
  - rollback: keep `resolve_prompt_profile_content(...)` as sole prompt-slot authority for reset and runtime paths
- Risk: manual hint HTML and AI hint text render through same unsafe path
  - rollback: keep separate render helpers and contract tests for pass-through vs escaped-text behavior
- Risk: config updates leave stale hints visible
  - rollback: clear hint cache and `front_hint_panel_state` on save/profile/language/custom-hint changes

# Final Verification

- [x] `python packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- [x] `python packages/score_answer_anki/test_question_variants_contract.py`
- [x] `python packages/score_answer_anki/test_custom_openai_contract.py`
- [x] `python -m py_compile packages/score_answer_anki/__init__.py packages/score_answer_anki/test_ai_analysis_ui_contract.py packages/score_answer_anki/test_question_variants_contract.py packages/score_answer_anki/test_custom_openai_contract.py`
- [x] Manual Anki check with one eligible typed `_score` card containing `Hint` HTML verifies:
  - [x] `Hint` button appears on front side before answer reveal
  - [x] clicking `Hint` opens panel without revealing answer
  - [x] manual `Hint` content passes through field-content render path
  - [x] `Suggest Hint` starts generation and panel stays open
  - [x] generated AI hint appears as escaped plain text
  - [x] `Suggest Again` reruns without reshuffling visible question
- [x] Manual Anki check with AI unavailable verifies:
  - [x] manual hint still appears
  - [x] AI action remains visible but disabled with localized reason

# Completion Criteria

- front-side hint feature works only on add-on-owned eligible typed `_score` question-side UI
- manual `Hint` field and AI hint each have one explicit render contract
- one global prompt-profile resolver owns the hint prompt slot and custom hint template field
- front-side refresh uses one dedicated DOM-patch helper and never full-card rerender
- hint cache, invalidation, and regenerate behavior are deterministic and test-covered
- docs and contract test match actual front-side-only behavior exactly
