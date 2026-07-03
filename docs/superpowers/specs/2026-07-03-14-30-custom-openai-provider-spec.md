---
layer: change
artifact_type: spec
status: proposed
name: custom-openai-provider-support
targets:
  - __init__.py
  - config.json
  - README.md
  - Config.md
---

# Goal

Add one new AI provider option for OpenAI-compatible endpoints with user-defined base URL, model, and optional API key.

Primary target: local or self-hosted routers such as 9router at `http://127.0.0.1:20128/v1`.

# Key Deliverables

- New provider key: `custom_openai`
- New config fields:
  - `custom_openai_base_url`
  - `custom_openai_api_key`
  - `custom_openai_model`
  - `custom_openai_custom_models`
- Config UI tab for custom OpenAI-compatible provider
- Request dispatch using OpenAI-compatible `/chat/completions`
- Connection test support for custom provider
- User docs update for setup and limits

# Task/Wave Breakdown

## Wave 1: Config surface

- Add default config values in runtime defaults and shipped `config.json`
- Merge loaded saved config over runtime defaults so missing new keys are backfilled on upgrade
- Add provider entry to provider selector
- Add provider tab with fields for base URL, API key, and model

## Wave 2: Request path

- Route `custom_openai` through existing OpenAI-compatible payload formatter
- Build request URL from configured base URL
- Reuse existing OpenAI-compatible response parsing
- Allow empty API key without blocking request construction

## Wave 3: Docs and checks

- Update user docs with example 9router config
- Update connection test behavior notes
- Verify selected provider saves, reloads, and tests correctly

# Design Decisions

## Provider shape

Add dedicated provider `custom_openai` instead of generic custom provider.

Reason:
- Current code already supports one shared OpenAI-compatible request/response path
- Small diff
- Lower UI and parsing complexity
- Covers stated need without speculative generic config

## Base URL contract

User enters base URL root, for example:
- `http://127.0.0.1:20128/v1`
- `https://my-host.example.com/openai/v1`

Runtime builds final endpoint as:
- `base_url.rstrip("/") + "/chat/completions"`

Addon does not ask user to type full endpoint path.

If user enters a URL already ending with `/chat/completions`, addon rejects it with a clear validation error and asks for base URL root instead.

Reason:
- reject is simpler than silent normalization
- avoids ambiguous rewrites
- keeps one stable input contract

## API key behavior

API key is optional for `custom_openai`.

Behavior:
- if key exists, send `Authorization: Bearer <key>`
- if key missing, omit `Authorization` header

Reason:
- many local OpenAI-compatible routers do not require auth

## Config defaults and authority

Runtime `DEFAULT_CONFIG` is authoritative source of config defaults.

Rules:
- `get_config()` must return merged config: `DEFAULT_CONFIG` plus saved config overrides
- new keys must be added to `DEFAULT_CONFIG` and mirrored in shipped `config.json`
- `config.json` is seed/default artifact, not separate runtime authority

Exact new defaults:
- `custom_openai_base_url`: `""`
- `custom_openai_api_key`: `""`
- `custom_openai_model`: `""`
- `custom_openai_custom_models`: `[]`

## Model behavior

Model field stays editable and supports:
- built-in default placeholder/example model
- user-added model IDs
- saved custom model list, same pattern as other providers

## Test connection behavior

`Test API Connection` for `custom_openai` uses same lightweight test message as other providers.

Validation rules:
- require non-empty base URL
- do not require API key
- require non-empty model

Implementation requirement:
- current blank-API-key blocker in connection-test UI must remain for built-in providers
- blank-API-key blocker must be skipped only when provider is `custom_openai`
- base URL validation must run before connection request for `custom_openai`

## Error handling

Custom provider uses existing OpenAI-compatible JSON parser and existing HTTP/URL error handling path.

Extra requirement:
- error messages for `custom_openai` should mention configured provider name, not `OpenAI`

# Invariants

- Existing providers keep current behavior unchanged
- `openai`, `deepseek`, `groq`, `openrouter`, and `custom_openai` share one OpenAI-compatible response parser
- Gemini and Claude keep their special request/response handling
- Saved configs from older addon versions still load without migration failure
- Missing `custom_openai_*` keys fall back to safe defaults
- No user-entered base URL should be mutated beyond trimming trailing `/`
- Full endpoint input ending with `/chat/completions` is rejected, not rewritten

# Acceptance Criteria

- Provider dropdown shows `Custom OpenAI-Compatible` option
- User can save base URL `http://127.0.0.1:20128/v1`, model, and optional API key
- Reloading config preserves saved custom provider values
- Connection test succeeds against working OpenAI-compatible local server without API key
- Connection test rejects `.../chat/completions` input and explains expected base URL root
- Analysis requests for `custom_openai` hit `<base_url>/chat/completions`
- Response content from standard OpenAI-compatible `choices[0].message.content` is parsed without special-case code outside shared parser branch
- If custom provider returns HTTP error, addon shows readable provider-specific error
- Existing built-in providers still save, test, and run as before

# Non-Goals

- No fully generic provider builder
- No custom headers editor
- No custom request body template
- No custom response parser DSL
- No streaming support
- No per-provider advanced timeout/retry controls

# Risks and Mitigations

## Risk: OpenAI-compatible server is not actually compatible

Mitigation:
- keep scope narrow
- document expected `/chat/completions` contract
- surface raw provider error message when available

## Risk: User enters full endpoint instead of base URL root

Mitigation:
- label field as base URL
- docs include exact example values
- reject input ending with `/chat/completions` with clear message

## Risk: Optional API key logic breaks providers that expect auth

Mitigation:
- optional auth behavior applies only to `custom_openai`
- built-in providers keep current required-key behavior

# Validation Plan

- proof target: custom provider config persists
  - method: manual save/reopen check plus config merge inspection
  - evidence: saved values reappear in config dialog after reopen and missing new keys are present in returned runtime config

- proof target: custom provider request URL is correct
  - method: targeted runnable check plus runtime test
  - evidence: request sent to `http://127.0.0.1:20128/v1/chat/completions` for example config

- proof target: invalid full-endpoint input is blocked
  - method: runnable check plus manual UI validation
  - evidence: `http://127.0.0.1:20128/v1/chat/completions` is rejected before request send with clear error

- proof target: optional API key path works
  - method: runnable check plus manual connection test with blank key against local router
  - evidence: success dialog or valid model response

- proof target: existing providers unchanged
  - method: inspection and spot-check connection tests
  - evidence: at least one existing provider still uses prior endpoint and headers path

- proof target: upgrade path from old config is safe
  - method: runnable check using old config dict missing `custom_openai_*` keys
  - evidence: merged config returns exact new default values without dropping old saved keys

Minimum runnable proof artifact:
- one tiny assert-based self-check or small test file for config merge and custom provider URL/header resolution

# Completion Criteria

- Spec approved
- Implementation limited to files in `targets`
- User can configure and use one OpenAI-compatible custom endpoint without replacing existing provider flows
- No generic-provider scaffolding added
