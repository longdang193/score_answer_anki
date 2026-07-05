---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: prompt-profiles-and-template-overrides
parent_spec: docs/superpowers/specs/2026-07-04-12-30-prompt-profile-spec.md
targets:
  - __init__.py
  - config.json
  - README.md
  - Config.md
  - test_ai_analysis_ui_contract.py
---

# Goal

Implement one prompt-profile system for `score_answer_anki` that supports built-in evaluation modes, one custom mode, and exact card-template-name overrides, while keeping profile selection reproducible, template-based, and backward-compatible with legacy `use_custom_prompt` configs.

# Key Deliverables

- One persisted SSOT config contract using `prompt_profile` and `template_prompt_profile_overrides`
- One config-load migration path from legacy `use_custom_prompt` to explicit `prompt_profile`
- One central built-in prompt-profile registry with four V1 profiles:
  - `default`
  - `strict_stem`
  - `speaking_flexible`
  - `custom`
- One pure resolver that maps current card template name + config to effective prompt profile
- One exact, trimmed, case-sensitive template-override lookup contract
- One UI update replacing boolean custom-prompt mode with profile-driven controls
- One docs update for profile meanings, template override JSON syntax, and template-only resolution boundary
- Runnable proof that migration, resolver behavior, save validation, and custom-profile fallback work end to end

# Task Breakdown

## Task 1: Convert config contract to one persisted SSOT

Files:
- `__init__.py`
- `config.json`
- `test_ai_analysis_ui_contract.py`

Steps:
- Add `prompt_profile` default to shipped config and runtime default config
- Add `template_prompt_profile_overrides` default as empty object to shipped config and runtime default config
- Keep legacy `use_custom_prompt` only as load-time backward-compat input
- Add one merge helper or merge branch that resolves missing `prompt_profile` from legacy `use_custom_prompt`
- Add one load-time normalization helper for persisted override map values
- Ensure save path always persists explicit `prompt_profile`
- Ensure save path always persists explicit `template_prompt_profile_overrides`
- Ensure save path always writes `use_custom_prompt: false` so reopened configs cannot drift back to legacy mode

Normalization rules:
- if persisted `template_prompt_profile_overrides` is not an object, normalize to `{}`
- if persisted override value is not one of `default`, `strict_stem`, `speaking_flexible`, `custom`, ignore that entry at runtime
- persisted malformed entries must not crash config load

Verification:
- Legacy config with only `use_custom_prompt: true` resolves to `prompt_profile == "custom"`
- Fresh config resolves to `prompt_profile == "default"`
- Save/reopen round trip preserves explicit `prompt_profile` and override map
- Save/reopen round trip collapses legacy config to new SSOT keys
- Persisted invalid override-map type falls back to `{}` safely
- Persisted invalid override values are ignored safely

## Task 2: Add central prompt-profile registry

Files:
- `__init__.py`
- `test_ai_analysis_ui_contract.py`

Steps:
- Extract built-in prompt text ownership into one central registry helper or constant
- Define built-in system prompt and analysis template for `default`, `strict_stem`, and `speaking_flexible`
- Route `custom` profile through existing `custom_system_prompt` and `custom_analysis_prompt_template`
- Keep current placeholder support for custom template:
  - `{question}`
  - `{expected_answer}`
  - `{accepted_answers}`
  - `{user_answer}`
  - `{language}`
- Add same-profile English fallback when requested language text is missing
- Remove duplicate prompt-text ownership between runtime path and preview/reset/copy UI path

Required prompt assertions:
- `strict_stem` built-in prompt text must mention numeric result, sign, and unit precision
- `speaking_flexible` built-in prompt text must mention communicative adequacy and alternative valid responses
- tests may assert exact strings or must-contain clauses, but contract coverage must be executable

Verification:
- Each V1 profile resolves to one system prompt and one analysis template
- Missing profile-language entry falls back to same profile in English
- Custom profile still uses freeform fields and placeholders
- Built-in prompt semantics are asserted by targeted test, not by manual inspection only

## Task 3: Add pure template-based profile resolver

Files:
- `__init__.py`
- `test_ai_analysis_ui_contract.py`

Steps:
- Add one helper to read current card template name using existing template-based card logic
- Add one pure resolver that accepts `template_name: str` and merged config and returns effective profile name only
- Keep card-to-template-name extraction outside resolver
- Implement lookup order:
  1. exact trimmed template-name hit in `template_prompt_profile_overrides`
  2. global `prompt_profile`
  3. backward-compat fallback from legacy `use_custom_prompt` during config merge only
  4. `default`
- Enforce exact, case-sensitive match after trim
- Reject override keys with leading/trailing whitespace on save
- Keep resolver independent from scoring eligibility checks

Verification:
- Override for `speaking_1_score` resolves to `speaking_flexible`
- Note type name does not change resolver output
- Wrong-case template key does not match runtime template name
- Missing or invalid template ordinal yields no override hit, not crash

## Task 4: Separate scoring gate from prompt resolution

Files:
- `__init__.py`
- `test_ai_analysis_ui_contract.py`

Steps:
- Keep existing template-based `should_score_card(card)` as sole scoring-eligibility gate
- Ensure AI analysis call sites use this order:
  1. `should_score_card(card)`
  2. if false, skip AI scoring path entirely
  3. if true, resolve effective prompt profile
- Ensure resolver is not used to decide whether card is scoreable
- Remove any residual note-type or question-text-based prompt routing

Verification:
- Non-scoreable template skips AI scoring even if global profile is `strict_stem`
- Scoreable template without override uses global profile
- Scoreable template with override uses override profile

## Task 5: Rewire runtime prompt assembly to profile path

Files:
- `__init__.py`
- `test_ai_analysis_ui_contract.py`

Steps:
- Replace boolean “use custom prompt or not” branches with profile-driven routing
- Add one runtime helper that resolves built-in system/template by `(profile, language)`
- Add one runtime helper that builds final system/template pair for current card from effective profile + config
- Route AI analysis prompt creation through this single helper path
- Keep accepted-answer pool, question context, and user-answer interpolation behavior unchanged outside prompt text ownership

Verification:
- `strict_stem` path returns stricter built-in prompt pair without using custom text fields
- `speaking_flexible` path returns flexible built-in prompt pair without using custom text fields
- `custom` path preserves current fallback behavior for blank freeform fields

## Task 6: Replace config UI with profile-driven controls

Files:
- `__init__.py`

Steps:
- Replace `use_custom_prompt` checkbox as primary selector with `Default prompt profile` dropdown
- Add dropdown choices:
  - `Default`
  - `Strict STEM`
  - `Speaking Flexible`
  - `Custom`
- Add one JSON textarea for `Per-template prompt profile overrides`
- Keep custom system/template textareas visible only when global profile is `Custom`
- Update helper text so custom fields are clearly scoped to `custom` profile only
- Update reset/copy-default actions so they operate on selected global profile and current language only
- Block save atomically when override JSON is invalid or contains unknown profile names or whitespace-padded keys

Verification:
- UI can save valid override JSON object
- Invalid override JSON blocks save and leaves prior persisted config unchanged
- Reset/copy actions reflect selected global profile, not effective template override state

## Task 7: Update docs and runnable proof

Files:
- `README.md`
- `Config.md`
- `test_ai_analysis_ui_contract.py`

Steps:
- Document four V1 profiles and intended use cases
- Document exact template-override JSON syntax with one strict STEM example and one speaking example
- Document template-name-only resolution rule
- Document legacy migration behavior only if user-facing docs need it; otherwise keep migration internal
- Extend existing assert-based UI contract test to cover:
  - SSOT merge behavior
  - legacy migration
  - persisted invalid override-map type fallback
  - persisted invalid override-value fallback
  - template override resolution
  - note type ignored by resolver
  - invalid JSON save blocking
  - custom-profile fallback behavior

Verification:
- `python test_ai_analysis_ui_contract.py` exits cleanly
- Docs match final config keys and UI labels

# Risks / Rollback

- Risk: new profile registry duplicates existing prompt builders
  - rollback: keep one central registry and route both UI preview and runtime through same helper only
- Risk: legacy config continues to drift after save
  - rollback: force explicit `prompt_profile` write and `use_custom_prompt: false` on every save
- Risk: JSON override editor causes partial-save bugs
  - rollback: validate before any config write and keep save atomic
- Risk: scoring eligibility logic becomes entangled with profile routing
  - rollback: keep `should_score_card(card)` and `resolve_prompt_profile(card, config)` as separate helpers with separate tests

# Final Verification

- Blocking targeted checks:
  - `python test_ai_analysis_ui_contract.py`
  - `python -m py_compile __init__.py test_ai_analysis_ui_contract.py`
- Adjacent safety checks:
  - `python test_question_variants_contract.py`
  - `python test_custom_openai_contract.py`
  - `python -m py_compile test_question_variants_contract.py test_custom_openai_contract.py`
- Manual config-dialog check confirms:
  - dropdown shows four V1 profiles
  - valid override JSON saves and reloads unchanged
  - invalid override JSON blocks save
  - custom fields are only exposed through custom-profile path
- Manual Anki check confirms:
  - scoreable STEM template uses strict profile when configured globally
  - speaking template override uses flexible profile when configured by template name
  - non-scoreable template still skips AI scoring regardless of profile config

# Completion Criteria

- Runtime profile selection has one SSOT config contract and one resolver
- Prompt text ownership is centralized with no duplicate built-in prompt sources
- Legacy `use_custom_prompt` no longer acts as primary runtime or persisted authority
- UI supports global profile + exact template overrides without extra files
- Runnable proof covers migration, resolution, validation, and fallback behavior
- Docs match actual config keys, UI, and template-only resolution boundary
