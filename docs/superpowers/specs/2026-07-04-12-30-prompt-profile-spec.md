---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: prompt-profiles-and-template-overrides
targets:
  - __init__.py
  - config.json
  - README.md
  - Config.md
  - test_ai_analysis_ui_contract.py
---

# Goal

Replace single custom-prompt toggle with one prompt-profile system that supports multiple built-in evaluation modes plus one custom mode.

Requested behavior:

- addon must support multiple prompt behaviors, not one global default + one custom freeform path only
- profile choice must be driven by card template name, because scoring scope is already template-based
- strict factual cards such as STEM templates must be able to require precise correctness
- open-ended templates such as speaking tests must be able to score communicative adequacy without over-anchoring to one predefined answer
- current custom system prompt and custom analysis prompt template must remain available as one `custom` profile
- no extra external prompt file is required in V1

# Key Deliverables

- One built-in prompt-profile registry in code
- One effective-profile resolver based on default profile + exact card-template override
- One `custom` profile that reuses existing custom prompt text fields
- One config contract for default profile and per-template override map
- One UI surface for selecting default profile and editing per-template overrides
- One docs update describing profile behavior, intended use, and override syntax
- Runnable proof that template overrides pick correct profile and that note type name does not affect profile selection

# Task/Wave Breakdown

## Wave 1: Config contract

- Add `prompt_profile` string config key
- Add `template_prompt_profile_overrides` object config key
- Keep `custom_system_prompt` and `custom_analysis_prompt_template`
- Keep `use_custom_prompt` only as backward-compat input, not as new source of truth

Runtime and persistence SSOT:

- `prompt_profile` is the only authoritative persisted and runtime profile selector
- `template_prompt_profile_overrides` is the only authoritative persisted and runtime override map
- `use_custom_prompt` must never be consulted after merged runtime config is produced
- save path must always write `prompt_profile`
- save path must always write `template_prompt_profile_overrides`
- save path must always write `use_custom_prompt: false` so legacy key cannot keep influencing reopened configs

Exact defaults:

- `prompt_profile`: `"default"`
- `template_prompt_profile_overrides`: `{}`

Backward-compat rule:

- if saved config lacks `prompt_profile` and old `use_custom_prompt` is `true`, effective default profile becomes `custom`
- otherwise missing `prompt_profile` falls back to `default`
- backward-compat migration happens only at config-load merge boundary
- once user saves config from new UI, persisted config must no longer depend on legacy `use_custom_prompt`

## Wave 2: Built-in profile registry

Add exactly four V1 profiles:

- `default`
- `strict_stem`
- `speaking_flexible`
- `custom`

Rules:

- built-in profiles live in code beside existing language-aware prompt builders
- built-in profiles expose both system prompt text and analysis prompt template text
- `custom` profile uses existing `custom_system_prompt` and `custom_analysis_prompt_template` fields, with current fallback-to-language-default behavior when either field is blank

Registry contract:

- one central registry function or constant owns built-in profile definitions
- no prompt text may be duplicated across UI preview path and runtime analysis path
- built-in profile lookup takes `(profile, language)` only
- if requested language text is missing for a built-in profile, fallback is same profile in English

Minimum built-in profile contract:

- `default`
  - must mention question context
  - must consider expected answer, accepted answers, and user answer together
  - must produce constructive educational feedback
- `strict_stem`
  - must explicitly instruct precision on numeric result, sign, unit, and material completeness
  - must explicitly reject vague semantic similarity as sufficient when factual result is wrong
  - must treat mathematically or scientifically equivalent answers as acceptable
- `speaking_flexible`
  - must explicitly treat expected answer as anchor example, not exclusive truth
  - must explicitly score relevance, communicative adequacy, grammar, and completeness
  - must explicitly allow alternative valid responses that satisfy prompt intent
- `custom`
  - must preserve current placeholder behavior and current fallback behavior for blank custom fields

## Wave 3: Effective-profile resolution

Add one shared resolver:

- input: current `card`, merged config
- source of truth: card template name only
- lookup order:
  1. exact card-template-name hit in `template_prompt_profile_overrides`
  2. global `prompt_profile`
  3. backward-compat fallback from old `use_custom_prompt`
  4. `default`

Resolver boundary:

- resolver returns only effective prompt profile name
- resolver must not decide whether card is scoreable
- resolver must not mutate config
- resolver must not inspect question text or answer text

Template-key matching contract:

- override lookup key is current card template name after `.strip()`
- persisted override keys must be stored trimmed
- leading or trailing whitespace in override keys is invalid and blocks save
- matching is exact and case-sensitive after trim
- missing template name or out-of-range template ordinal means "no override"

Explicit non-rule:

- note type name must not affect profile selection
- question text content must not auto-detect STEM or speaking mode in V1

Separate runtime gate:

- scoring eligibility remains owned by existing template-based scoring gate
- caller order must be:
  1. check `should_score_card(card)`
  2. if false, skip AI scoring path entirely
  3. if true, resolve prompt profile
- profile resolution must stay valid and testable independently of scoring eligibility

## Wave 4: Prompt semantics

### `default`

- preserve current balanced educational behavior
- use question context, expected answer, accepted answers, and user answer together
- allow semantically correct alternatives when card data supports them

### `strict_stem`

- prefer precision over generosity
- treat wrong sign, wrong unit, wrong numeric result, wrong formula outcome, and materially incomplete answer as meaningful errors
- accept only mathematically or scientifically equivalent alternatives
- do not reward vague “close enough” wording when factual precision is required

### `speaking_flexible`

- evaluate communicative success, relevance, grammar, fluency, and completeness more than exact phrase match
- treat canonical expected answer as anchor example, not exclusive truth
- accept alternative valid responses when they address prompt appropriately
- avoid harsh penalties for wording differences that preserve meaning

### `custom`

- preserve current freeform behavior
- continue supporting placeholders:
  - `{question}`
  - `{expected_answer}`
  - `{accepted_answers}`
  - `{user_answer}`
  - `{language}`

## Wave 5: UI changes

Replace current single boolean custom-prompt mode with profile-driven UI.

Required controls:

- `Default prompt profile` dropdown with values:
  - `Default`
  - `Strict STEM`
  - `Speaking Flexible`
  - `Custom`
- `Per-template prompt profile overrides` editor
- existing custom system prompt textarea
- existing custom analysis prompt template textarea
- existing reset/copy-default prompt actions

V1 override editor shape:

- one JSON object textarea
- exact syntax:
  ```json
  {
    "card_1_score": "strict_stem",
    "speaking_1_score": "speaking_flexible"
  }
  ```

Validation rules:

- override JSON must parse to object
- each key must be non-empty string
- each value must be one of `default`, `strict_stem`, `speaking_flexible`, `custom`
- each key must equal `key.strip()`
- invalid JSON or unknown profile blocks save with readable warning
- failed override validation blocks entire save and leaves prior persisted config unchanged

UI behavior rules:

- custom prompt textareas are hidden unless global profile dropdown is `Custom` or explicit "Edit custom profile" expander is opened
- helper text must state custom fields are used only when effective profile resolves to `custom`
- reset action resets custom textareas only for `custom` profile
- copy-default action copies built-in system/template for currently selected global profile and current language
- reset/copy actions must not try to infer effective template override at click time

## Wave 6: Runtime wiring

Prompt generation path must stop asking “custom or not?” and instead ask “which effective profile applies to this card?”

Required runtime changes:

- add one function to resolve effective profile from current card + config
- add one function to resolve built-in system/template by `profile + language`
- route AI analysis prompt creation through resolved profile
- route placeholder previews and reset/copy UI actions through selected profile

## Wave 7: Docs and proof

- document profile meanings and when to use each one
- document exact JSON override syntax
- document that profile selection is based on card template name only
- add targeted runnable tests for:
  - default-profile fallback
  - backward compat from `use_custom_prompt`
  - template override resolution
  - note type ignored by resolver
  - custom profile placeholder path still works

# Design Decisions

## Why profiles instead of many freeform prompt boxes

Profiles are smaller, safer, and easier to maintain.

- user gets good defaults fast
- built-ins stay reviewable in code
- `custom` remains escape hatch
- no extra file format or prompt DSL is introduced

## Why template-name overrides instead of question-text heuristics

Template name is already stable project structure. Question-text heuristics are brittle.

- `17 * 13 * 1 = ?` looking STEM-like is not reliable architecture
- `speaking_1_score` is explicit and deterministic
- one exact override map is simpler than classifier logic

## Why JSON textarea for overrides in V1

Smallest diff.

- no new table widget complexity
- config stays one plain object
- power users can edit quickly
- docs can show one exact copy-paste example

If this becomes painful later, upgrade path is dedicated rows UI with add/remove buttons.

# Invariants

- one persisted runtime SSOT exists for profile selection: `prompt_profile`
- one persisted runtime SSOT exists for overrides: `template_prompt_profile_overrides`
- card template name remains only scoring scope selector
- card template name remains only prompt-profile resolution selector
- built-in providers and model selection stay unchanged
- accepted-answer pool behavior stays unchanged
- current custom prompt placeholders remain supported
- blank custom fields in `custom` profile still fall back safely to language defaults
- no filesystem prompt bundles are introduced in V1
- no profile auto-detection from question text exists in V1

# Acceptance Criteria

- config contains `prompt_profile` and `template_prompt_profile_overrides`
- old configs with `use_custom_prompt: true` resolve to `custom` at load time when `prompt_profile` is absent
- after first save from new UI, persisted config writes `prompt_profile` explicitly and writes `use_custom_prompt: false`
- user can set global profile to `strict_stem` and get stricter evaluation without editing freeform prompts
- user can set template override `{ "speaking_1_score": "speaking_flexible" }` and speaking template uses flexible prompt behavior even when global profile is `strict_stem`
- profile resolution ignores note type name completely
- invalid override JSON is blocked on save with clear error
- invalid override JSON does not partially save unrelated fields
- `custom` profile continues to use existing freeform fields and placeholders
- docs show at least one strict STEM example and one speaking override example

# Non-Goals

- no AI classifier that guesses profile from question text
- no per-note override field
- no external prompt pack files
- no per-provider prompt differences
- no prompt version history UI
- no multiple named custom profiles in V1

# Risks and Mitigations

## Risk: Too many profiles create confusion

Mitigation:

- ship only four V1 profiles
- make `default` and `custom` semantics explicit
- add one short docs table: use case → profile

## Risk: JSON override editor is error-prone

Mitigation:

- validate on save
- show exact example inline
- keep scope to exact template-name → profile mapping only

## Risk: Built-in prompts drift from actual card styles

Mitigation:

- keep profile registry centralized
- make `custom` available as escape hatch
- add focused tests for resolver, not subjective scoring output

# Validation Plan

- proof target: scoring gate and profile resolver stay separate
  - method: runnable test with non-scoreable template and valid global profile
  - evidence: scoring gate returns false while profile resolver behavior remains independently testable

- proof target: resolver ignores note type name
  - method: runnable test with note type ending `_score` and template not ending `_score`
  - evidence: returned effective profile is derived only from trimmed template name and config, not note type name

- proof target: resolver honors exact template override
  - method: runnable test with override map and template `speaking_1_score`
  - evidence: returned effective profile is `speaking_flexible`

- proof target: override-key normalization contract is enforced
  - method: save-path test with key containing leading/trailing whitespace and with wrong-case key
  - evidence: whitespace key is rejected, wrong-case key persists but does not match different-case template at runtime

- proof target: backward compat works
  - method: runnable config-merge check with missing `prompt_profile` and `use_custom_prompt: true`
  - evidence: effective global profile resolves to `custom`

- proof target: new save path collapses legacy config to SSOT
  - method: save/reopen round-trip test from legacy config
  - evidence: reopened config contains explicit `prompt_profile`, explicit override map, and `use_custom_prompt: false`

- proof target: built-in profile preview/reset path works
  - method: targeted UI-adjacent helper test
  - evidence: selected profile returns expected built-in system/template strings for current language

- proof target: invalid override JSON blocks save atomically
  - method: save-path test with invalid JSON after changing other form fields
  - evidence: no partial config mutation is persisted

Minimum runnable proof artifact:

- one small assert-based test file or extension of existing prompt/UI contract test covering resolver and fallback logic

# Completion Criteria

- spec approved
- implementation updates config merge, prompt registry, UI, docs, and runnable proof
- no code path still depends on `use_custom_prompt` as primary source of truth
- runtime prompt selection reads from one resolver and one registry only
- user can configure strict STEM globally and speaking flexibility by template override without editing custom text fields
