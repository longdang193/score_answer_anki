---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: global-prompt-profiles-only
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/config.json
  - packages/score_answer_anki/README.md
  - packages/score_answer_anki/Config.md
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
---

# Goal

Simplify `score_answer_anki` prompt configuration to one global prompt-profile selector plus one `custom` mode that shows the same two freeform prompt fields from the old UI.

Requested behavior:

- keep prompt profiles:
  - `default`
  - `strict_stem`
  - `speaking_flexible`
  - `custom`
- remove per-template prompt-profile override behavior entirely
- remove JSON override editing from UI entirely
- when selected global profile is `custom`, show exactly two fields:
  - `Custom system prompt (optional)`
  - `Custom analysis prompt template`
- when selected global profile is not `custom`, hide those two fields
- keep card-template-name-only scoring gate unchanged

# Key Deliverables

- One global persisted prompt-profile config key
- One central built-in prompt-profile registry in code
- One `custom` profile path reusing old two-field custom prompt UX
- One simplified config dialog with:
  - profile dropdown
  - hidden/shown custom fields based on `custom`
- One docs update removing JSON override language
- Runnable proof that global profile selection, custom-field visibility, and legacy migration work

# Task/Wave Breakdown

## Wave 1: Config contract simplification

- Keep `prompt_profile` as sole persisted prompt-profile selector
- Remove `template_prompt_profile_overrides` from runtime authority and shipped config
- Keep `use_custom_prompt` only as backward-compat input during config merge
- If old config has `use_custom_prompt: true` and no explicit `prompt_profile`, resolve to `custom`
- After save, always persist explicit `prompt_profile`
- After save, always persist `use_custom_prompt: false`
- After save, persisted config must not contain `template_prompt_profile_overrides`

Exact defaults:

- `prompt_profile`: `"default"`

## Wave 2: Prompt registry

- Keep one central registry for built-in profiles:
  - `default`
  - `strict_stem`
  - `speaking_flexible`
- Keep `custom` as freeform path using:
  - `custom_system_prompt`
  - `custom_analysis_prompt_template`
- Treat those two custom fields as one global persisted pair, not a per-language map
- Keep current placeholder support:
  - `{question}`
  - `{expected_answer}`
  - `{accepted_answers}`
  - `{user_answer}`
  - `{language}`
- Keep same-profile English fallback when profile-language text is missing

## Wave 3: Runtime routing

- Remove template-override resolver logic entirely
- Runtime prompt generation reads only global `prompt_profile`
- Scoring eligibility remains separate and still depends on card template name ending `_score`
- Prompt profile selection must not inspect note type name or card template name

## Wave 4: UI simplification

- Keep one `Default prompt profile` dropdown
- Remove JSON override label, textarea, parser, and validation path
- If selected profile is `custom`, show:
  - `Custom system prompt (optional)`
  - `Custom analysis prompt template`
  - reset button
- If selected profile is not `custom`, hide those custom fields and controls
- Reset fills those two custom fields from built-in base prompts for current language
- Current language changes placeholder/reset source text only; stored custom field values stay global

## Wave 5: Docs and proof

- Remove user-facing docs about per-template overrides and JSON syntax
- Document four global profiles and when to use them
- Document that `custom` exposes the old two-field flow
- Add or update runnable checks for:
  - legacy `use_custom_prompt` migration
  - global `prompt_profile` fallback
  - saved config omits `template_prompt_profile_overrides`
  - custom-profile prompt rendering
  - built-in strict STEM prompt semantics
  - built-in speaking-flexible prompt semantics
  - custom-field visibility state helper or equivalent UI-adjacent logic

# Design Decisions

## Why remove per-template overrides

User rejected JSON override UX. Simpler version chooses one global profile at a time.

- lower UI complexity
- no mapping syntax to learn
- closer to old mental model
- easier docs and testing

## Why keep `custom`

Old two-field custom prompt flow is familiar and still useful.

- no lost flexibility for manual prompt authors
- smaller migration from prior UI
- no extra prompt file or advanced editor needed

# Invariants

- one persisted SSOT exists for prompt-profile selection: `prompt_profile`
- saved config omits `template_prompt_profile_overrides`
- scoring gate still depends only on card template name ending `_score`
- prompt profile does not vary by template in this simplified version
- custom prompt fields are visible only when global profile is `custom`
- no JSON override editor exists in this version
- current custom prompt placeholders remain supported
- custom prompt field values are stored as one global pair, not per-language values

# Acceptance Criteria

- config persists `prompt_profile`
- old configs with `use_custom_prompt: true` still resolve to `custom` when `prompt_profile` is absent
- saved config omits `template_prompt_profile_overrides`
- config dialog shows prompt-profile dropdown and no JSON override field
- choosing `custom` shows the old two custom prompt fields
- choosing any non-`custom` profile hides the two custom prompt fields
- runtime prompt generation uses selected global profile only
- docs no longer mention per-template prompt overrides

# Non-Goals

- no per-template prompt-profile override behavior
- no JSON override editor
- no row-based template override UI
- no note-type-based prompt routing
- no question-text-based prompt routing
- no `Copy default prompts` button

# Risks and Mitigations

## Risk: user still wants STEM and speaking profiles active at same time

Mitigation:

- defer per-template UI to later dedicated design
- keep runtime/profile code centralized so future re-expansion is possible

## Risk: legacy config drift

Mitigation:

- collapse old `use_custom_prompt` behavior into explicit `prompt_profile` on save

# Validation Plan

- proof target: global profile is sole runtime selector
  - method: runnable check with different `prompt_profile` values and no override inputs
  - evidence: runtime prompt builder changes only with global profile

- proof target: legacy migration works
  - method: config-merge check with `use_custom_prompt: true` and missing `prompt_profile`
  - evidence: merged config resolves to `custom`

- proof target: saved config is SSOT-clean
  - method: save-path check after dialog save or narrow save helper check
  - evidence: saved config contains `prompt_profile`, contains `use_custom_prompt: false`, and omits `template_prompt_profile_overrides`

- proof target: custom field visibility follows profile selection
  - method: UI-adjacent state helper test or narrow config-dialog logic test
  - evidence: `custom` shows fields; non-`custom` hides fields

- proof target: custom field grain stays global
  - method: prompt-content check across language changes without per-language custom storage
  - evidence: stored custom strings remain unchanged; only placeholder/reset source text varies by current language

- proof target: docs match simplified UX
  - method: review changed docs
  - evidence: no JSON override guidance remains

Minimum runnable proof artifact:

- extension of existing `test_ai_analysis_ui_contract.py`

# Completion Criteria

- simplified spec approved
- implementation removes JSON override UI and logic
- global profile dropdown plus old custom two-field flow works
- docs and tests match simplified behavior exactly
