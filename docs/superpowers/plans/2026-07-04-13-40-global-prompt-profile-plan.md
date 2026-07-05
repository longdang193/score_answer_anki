---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: global-prompt-profiles-only
parent_spec: docs/superpowers/specs/2026-07-04-13-35-global-prompt-profile-spec.md
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/config.json
  - packages/score_answer_anki/README.md
  - packages/score_answer_anki/Config.md
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
---

# Goal

Simplify `score_answer_anki` prompt configuration to one global profile dropdown and one old-style `custom` prompt flow, removing per-template overrides and JSON UI entirely.

# Key Deliverables

- One persisted global `prompt_profile` config key
- One central prompt-profile registry for built-in profiles plus `custom`
- One runtime path that reads only global profile for prompt selection
- One simplified config dialog with no JSON override editor
- One old-style custom prompt section shown only for `custom`
- Docs and runnable proof aligned to simplified global-only behavior
- One SSOT-clean save path that omits `template_prompt_profile_overrides`

# Task Breakdown

## Task 1: Remove override config authority

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/config.json`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Remove `template_prompt_profile_overrides` from shipped config
- Remove override normalization/parser logic from runtime authority
- Keep `prompt_profile` as sole prompt-profile selector
- Keep legacy `use_custom_prompt` only for config-merge fallback to `custom`
- Ensure save path always writes explicit `prompt_profile` and `use_custom_prompt: false`
- Ensure save path omits `template_prompt_profile_overrides`

Verification:
- merged legacy config still resolves to `custom`
- no runtime config path depends on override map
- saved config contains no `template_prompt_profile_overrides`

## Task 2: Keep central prompt-profile registry

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Keep or simplify one central built-in prompt registry
- Ensure built-in profiles remain:
  - `default`
  - `strict_stem`
  - `speaking_flexible`
- Keep `custom` on existing two-field path
- Keep custom fields as one global persisted pair, not per-language storage
- Keep English fallback for missing profile-language text
- Keep executable assertions for strict STEM and speaking semantics

Verification:
- built-in profile content resolves correctly
- custom profile still renders freeform prompt text with placeholders

## Task 3: Simplify runtime routing

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Remove template-based prompt-profile resolver logic
- Replace it with one helper that returns global `prompt_profile`
- Keep scoring gate separate and unchanged: card template name ending `_score`
- Ensure prompt selection does not depend on note type name or card template name

Verification:
- changing global profile changes prompt behavior
- card template name affects scoring gate only, not prompt-profile selection

## Task 4: Simplify config dialog

Files:
- `packages/score_answer_anki/__init__.py`

Steps:
- Keep `Default prompt profile` dropdown
- Remove JSON override label, textarea, and validation path
- Show custom system/template fields only when selected profile is `Custom`
- Hide those fields for non-`custom` profiles
- Keep reset action only for `Custom`
- Reset fills built-in base prompts for current language into global custom fields
- Language changes update placeholder/reset source text only; stored custom values remain global

Verification:
- dialog shows no JSON override UI
- `Custom` selection shows old two-field prompt editor
- non-`Custom` selection hides old two-field prompt editor
- no `Copy default prompts` button exists

## Task 5: Update docs and proof

Files:
- `packages/score_answer_anki/README.md`
- `packages/score_answer_anki/Config.md`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- remove JSON/per-template override guidance
- document four global profiles and intended use cases
- document that `custom` restores old two-field behavior
- extend existing contract test for:
  - legacy migration
  - save output omits `template_prompt_profile_overrides`
  - global-profile routing
  - custom prompt rendering
  - custom-field visibility state
  - global custom-field grain across language changes

Verification:
- `python test_ai_analysis_ui_contract.py` exits cleanly
- docs mention no JSON override behavior

# Risks / Rollback

- Risk: user later needs mixed STEM + speaking behavior in same deck
  - rollback: future design can add friendly row UI, not JSON
- Risk: partial removal leaves dead override code
  - rollback: remove docs, UI, and runtime references together in one change

# Final Verification

- `python packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- `python -m py_compile packages/score_answer_anki/__init__.py packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- Adjacent safety checks:
  - `python packages/score_answer_anki/test_question_variants_contract.py`
  - `python packages/score_answer_anki/test_custom_openai_contract.py`
  - `python -m py_compile packages/score_answer_anki/test_question_variants_contract.py packages/score_answer_anki/test_custom_openai_contract.py`
- Manual config-dialog check confirms:
  - dropdown shows four profiles
  - no JSON override field exists
  - `Custom` shows old two prompt fields
  - non-`Custom` hides them
  - no `Copy default prompts` button exists

# Completion Criteria

- prompt configuration is global-only
- old two custom fields are preserved only for `Custom`
- no JSON override UI or docs remain
- no `Copy default prompts` button remains
- tests and docs match simplified behavior exactly
