---
layer: change
artifact_type: spec
status: implemented_verified
template_id: detailed-specification
name: hint-panel-ai-suggestions
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/config.json
  - packages/score_answer_anki/README.md
  - packages/score_answer_anki/Config.md
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
---

# Goal

Add one pre-answer front-side hint panel to `score_answer_anki` for eligible typed-answer review cards.

Requested behavior:

- feature belongs to `score_answer_anki`, not note-template-specific hint buttons under `note_types/`
- feature runs on front side before answer reveal
- feature uses same eligibility gate as AI scoring UI unless later changed explicitly:
  - card template name ends with `_score`
  - card uses typed-answer flow supported by add-on
- user clicks `Hint`
- panel opens inline on front side without revealing answer
- panel shows manual `Hint` field content first when present
- panel shows one `Suggest Hint` action
- clicking `Suggest Hint` asks configured AI provider for one concise hint using:
  - active visible question
  - canonical answer
  - existing manual `Hint` when present
  - current analysis language
  - active global prompt profile hint slot
- returned AI hint appears in same panel under manual hint
- user may regenerate AI hint for current front-side exposure
- generated AI hint never overwrites note field content automatically

# Key Deliverables

- One front-side hint-panel render path owned by `packages/score_answer_anki/__init__.py`
- One SSOT field contract for optional manual `Hint`
- One SSOT prompt-profile contract with both analysis and hint prompt slots
- One background AI-hint generation path reusing provider/config transport helpers
- One stable current-exposure hint context and cache identity
- One targeted in-place panel refresh path that does not require full card rerender
- One localized UI-text bundle extension for hint actions, loading, and unavailable states
- One docs update covering ownership, privacy, and no-auto-save behavior
- One runnable proof artifact for front-side rendering, prompt-slot resolution, cache invalidation, and regenerate handling

# Task/Wave Breakdown

## Wave 1: Ownership, gating, and front-side entry

- Feature owner is `score_answer_anki` reviewer integration only
- Do not modify or depend on note-template-local hint buttons under `note_types/`
- Reuse existing card eligibility gate from `score_answer_anki` for V1
- Add one explicit `Hint` control to add-on-owned front-side UI
- `Hint` control opens or toggles one inline panel on front side; no modal dialog in V1
- Feature must work before answer reveal and must not call answer-side rerender helpers to update state

## Wave 2: Manual hint field contract and render contract

- Manual hint field is slot-driven
- Base slot uses `Hint`; active cloze slot `x > 1` uses `Hint{x}`
- Mapped hint field is optional
- Missing mapped hint field is treated as empty manual hint, not as error
- Manual hint source of truth is current mapped note field value only
- Manual hint renders using same HTML semantics as note field content already uses in Anki; V1 must not reinterpret stored field HTML as plain text
- AI hint renders as plain text only
- AI hint render path must HTML-escape generated content before insertion
- Manual and AI hint must remain visually distinct and separately labeled

Exact V1 panel content order:

1. `Hint` label + manual hint body when manual hint is non-empty
2. `AI Hint` label + AI hint body when generated hint is available or AI error state exists
3. action row containing `Suggest Hint` or `Suggest Again`

## Wave 3: Prompt-profile SSOT and config contract

- Global `prompt_profile` remains SSOT selector for both scoring and hint generation
- Each prompt profile owns these slots:
  - `system_prompt`
  - `analysis_prompt_template`
  - `hint_prompt_template`
- Built-in profiles must define all three slots:
  - `default`
  - `strict_stem`
  - `speaking_flexible`
- `custom` profile uses persisted global custom fields:
  - `custom_system_prompt`
  - `custom_analysis_prompt_template`
  - `custom_hint_prompt_template`
- `custom_hint_prompt_template` is new persisted config surface for this change
- Non-`custom` profiles hide all freeform custom prompt fields in UI except existing read-only profile selection controls
- Hint generation must not use a separate provider-specific or template-specific prompt system in V1

## Wave 4: AI request and result contracts

AI hint input contract must include exactly:

- `question_text`: active visible question for current front-side exposure
- `canonical_answer`: canonical `Back` value
- `manual_hint`: current `Hint` field content or empty string
- `language`: configured analysis language
- `prompt_profile`: resolved global prompt profile name

AI hint output contract must normalize to one dict shape:

- `status`: `idle | loading | ready | unavailable`
- `hint_text`: generated plain-text hint or empty string
- `error_text`: bounded user-visible error text or empty string

V1 prompt/output rules:

- AI is asked for one concise hint only
- no score
- no rubric
- no markdown requirement
- prompt instructs nudge-only behavior and asks model not to reveal full answer
- parser stores plain text only
- whitespace is normalized before render

## Wave 5: Async flow, refresh path, and exposure invariance

- Add one `hint_cache` keyed by one shared helper
- Add one `is_generating_hint` map keyed identically
- Add one `current_hint_context` structure for active front-side exposure
- `Suggest Hint` starts background task using same transport/task-manager pattern as analysis, but not same answer-side rerender path
- Background completion must refresh hint panel in place on current front-side card
- Hint panel open state must survive AI completion refresh for same exposure
- If generation is already active for same key, second click must not enqueue duplicate work
- If AI hint already exists for same key, `Suggest Again` invalidates cached hint for that key and starts one fresh task
- Provider failure must leave panel open and manual hint intact

## Wave 6: Cache identity and invalidation rules

Hint cache key must be built from:

- `card.id`
- `card.ord`
- active visible question text
- normalized manual hint content
- configured analysis language
- resolved `prompt_profile`
- `hint_prompt_version`

Additional invalidation rules:

- saving config clears hint cache
- changing prompt profile clears hint cache
- changing analysis language clears hint cache
- changing custom hint prompt template clears hint cache

User answer is not part of hint-generation identity in V1.

## Wave 7: AI availability behavior

- Manual hint panel remains available when AI is disabled or unconfigured
- If AI is disabled, `Suggest Hint` is hidden or disabled with localized reason text
- If AI is enabled but unavailable at runtime, panel shows bounded unavailable/error text in `AI Hint` block
- AI unavailability must not block front-side review flow

## Wave 8: Docs and runnable proof

- Document mapped active-slot hint field as optional manual hint source for front-side hint panel
- Document that feature is owned by `score_answer_anki`, not by note-template-local hint buttons
- Document that AI hint is session output, not auto-saved note content
- Document that AI hint request sends question, answer, and existing hint content to configured provider
- Add or extend one runnable contract test proving:
  - missing `Hint` field does not break panel
  - `Suggest Hint` route is registered
  - `Suggest Again` route is registered
  - prompt-profile registry resolves hint prompt slot
  - custom profile persists `custom_hint_prompt_template`
  - hint cache invalidation works on regenerate and config changes
  - panel open state survives AI completion refresh
  - manual hint renders before AI hint when both exist

# Design Decisions

## Front-side only in V1

Feature is explicitly pre-answer front-side only.

- matches requested study flow
- avoids mixing front-side help with answer-side grading chrome
- prevents one spec from owning two UI surfaces

## `score_answer_anki` owns feature

Feature stays inside add-on-owned reviewer integration.

- one owner
- one JS bridge
- one config surface
- no drift across note-template-specific buttons

## Manual hint follows note-field HTML semantics

Manual `Hint` should render according to stored note-field semantics, not a second plain-text interpretation.

- preserves SSOT
- matches how other note content behaves
- avoids divergent render rules for one field

## AI hint is plain text only

Generated content is advisory session output, not stored note content.

- smaller parser surface
- lower injection risk
- easier testability

## Prompt profiles own hint slot too

Global prompt profiles remain one selector for related AI behaviors.

- one selector
- symmetric profile structure
- no second prompt-routing system

# Invariants

- feature is front-side only in V1
- feature owner is `score_answer_anki`
- note-template-local hint buttons are out of scope for this feature
- `Hint` field remains optional
- manual `Hint` content is never overwritten automatically by AI generation
- manual hint uses note-field HTML semantics
- AI hint uses escaped plain-text semantics
- one exposure keeps one visible question variant across display and regenerate
- panel open state persists across AI completion refresh for same exposure
- hint generation uses one global prompt-profile selector and one hint prompt slot per profile
- provider failure never blocks review flow or hides manual hint

# Acceptance Criteria

- eligible front-side `_score` review card shows add-on-owned `Hint` control before answer reveal
- clicking `Hint` opens inline front-side panel without revealing answer
- if note has `Hint`, panel shows it under `Hint` label using note-field HTML semantics
- if note lacks `Hint`, panel still opens and does not error
- if AI is disabled, manual hint still works and AI action is hidden or disabled with localized reason
- clicking `Suggest Hint` starts background AI generation without freezing front-side review UI
- while generation runs, duplicate click for same context is blocked or disabled
- when generation succeeds, AI hint appears under `AI Hint` as escaped plain text
- `Suggest Again` reruns AI hint generation for same front-side exposure
- regenerate uses same visible question context and does not reshuffle variants
- AI hint does not auto-save into note fields
- saving config or changing prompt-profile-related inputs invalidates hint cache
- built-in and custom prompt profiles resolve a hint prompt slot from one SSOT profile registry

# Non-Goals

- No answer-side hint panel in V1
- No automatic write-back of AI hint into `Hint` field
- No manual accept/reject workflow for saving AI hint to note in V1
- No dedicated hint-edit UI inside panel
- No multi-hint history list
- No template-specific hint prompt override in V1
- No user-answer-based hint generation in V1
- No dependency on note-template-local hint buttons

# Risks and Mitigations

## Risk: front-side refresh accidentally uses answer-side rerender path

Mitigation:

- explicit front-side-only ownership
- targeted in-place panel refresh requirement
- validation covers panel-open persistence after completion

## Risk: AI hint reveals too much

Mitigation:

- dedicated hint prompt slot per profile
- prompt instructs nudge-only behavior
- AI output remains labeled and separate from manual hint

## Risk: prompt config drifts between analysis and hint

Mitigation:

- one profile registry with three named slots only
- one global selector for both features
- one custom hint template field for custom profile

## Risk: duplicate background requests from repeated clicks

Mitigation:

- one `is_generating_hint` gate by shared key
- regenerate invalidates then starts one fresh task only when prior task not active

## Risk: missing `Hint` field causes brittle field access

Mitigation:

- tolerant field lookup defaults to empty string
- tests cover note without `Hint`

# Validation Plan

- proof target: feature is front-side only
  - method: runnable contract test or helper test for front-side path selection
  - evidence: hint feature helper binds to front-side render path and not answer-side enhanced comparison path

- proof target: manual hint follows field-HTML semantics while AI hint stays plain text
  - method: runnable render test
  - evidence: manual `Hint` markup renders as field content and AI hint output is escaped text

- proof target: panel tolerates missing manual `Hint`
  - method: runnable contract test with note lacking `Hint`
  - evidence: panel HTML renders and no exception occurs

- proof target: hint JS routes exist
  - method: runnable message-handler test
  - evidence: `handle_js_message(..., "suggest_ai_hint", ...)` and `handle_js_message(..., "regenerate_ai_hint", ...)` return handled state

- proof target: prompt-profile registry owns hint slot
  - method: runnable prompt-registry test
  - evidence: each built-in profile resolves `system_prompt`, `analysis_prompt_template`, and `hint_prompt_template`; custom profile resolves persisted custom hint template

- proof target: duplicate in-flight generation is blocked
  - method: runnable state test with `is_generating_hint[key] = True`
  - evidence: second trigger does not enqueue new generation path

- proof target: regenerate invalidates current cache and preserves exposure context
  - method: runnable cache/context test
  - evidence: old cached hint is removed and same visible-question context is reused for rerun

- proof target: config changes invalidate hint cache
  - method: runnable config-save test
  - evidence: saving profile/language/custom-hint changes clears hint cache

- proof target: panel open state survives AI completion refresh
  - method: runnable UI-adjacent state test or narrow helper test
  - evidence: open panel remains open after background completion refresh for same exposure

- proof target: AI availability behavior is bounded
  - method: runnable config-state and failure-path tests
  - evidence: disabled AI hides/disables action; provider failure leaves manual hint visible and shows bounded error text

# Completion Criteria

- spec approved
- owner, surface, and gate are unambiguous
- manual and AI hint render contracts are explicit
- prompt-profile SSOT includes hint prompt slot and custom hint template field
- front-side refresh and cache invalidation behavior are explicit
- validation plan names concrete proof targets and evidence paths
