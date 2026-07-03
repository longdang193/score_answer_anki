---
layer: change
artifact_type: plan
status: proposed
name: custom-openai-provider-implementation
parent_spec: docs/superpowers/specs/2026-07-03-14-30-custom-openai-provider-spec.md
targets:
  - __init__.py
  - config.json
  - README.md
  - Config.md
  - test_custom_openai_contract.py
---

# Goal

Implement `custom_openai` provider with base URL root, optional API key, shared OpenAI-compatible request/response handling, and bounded validation.

# Key Deliverables

- Config defaults and runtime merge for `custom_openai_*` keys
- UI support for provider selection, base URL, model, and optional API key
- Request path for `custom_openai` using `<base_url>/chat/completions`
- Clear validation error for full endpoint input ending with `/chat/completions`
- One tiny runnable proof artifact for config merge and URL/header resolution
- Docs update for setup, example config, and limits

# Task Breakdown

## Task 1: Consolidate config defaults and upgrade behavior

Files:
- `__init__.py`
- `config.json`

Steps:
- Add `custom_openai_base_url`, `custom_openai_api_key`, `custom_openai_model`, and `custom_openai_custom_models` defaults to runtime config
- Mirror same defaults in shipped `config.json`
- Change config loading so saved config is merged over runtime defaults instead of returned raw

Verification:
- Old config without `custom_openai_*` keys still resolves with exact new defaults
- Existing saved keys remain unchanged after merge

## Task 2: Add bounded transport logic for custom OpenAI-compatible provider

Files:
- `__init__.py`

Steps:
- Add provider metadata for `custom_openai`
- Add one small helper for custom provider request resolution:
  - validate base URL root
  - reject input ending with `/chat/completions`
  - build final URL as `base_url.rstrip("/") + "/chat/completions"`
  - omit `Authorization` header when API key is blank
- Route `custom_openai` through existing OpenAI-compatible message formatter and response parser
- Keep Gemini and Claude branches unchanged

Verification:
- `custom_openai` sends requests to correct endpoint for example `http://127.0.0.1:20128/v1`
- Blank API key produces no `Authorization` header
- Full endpoint input is rejected before request send
- Existing OpenAI-compatible providers still use prior endpoint/header logic

## Task 3: Extend config UI and connection-test behavior

Files:
- `__init__.py`

Steps:
- Add `Custom OpenAI-Compatible` to provider selector
- Add provider tab inputs for base URL, API key, and editable model
- Reuse existing custom-model persistence pattern for `custom_openai_custom_models`
- Update save path to persist new fields
- Change `Test API Connection` validation rules:
  - built-in providers still require API key
  - `custom_openai` requires base URL and model, not API key
  - `custom_openai` rejects full endpoint input with clear message

Verification:
- User can save and reopen custom provider values
- Test button works with blank key for local router
- Test button still blocks blank key for built-in providers

## Task 4: Add tiny runnable proof artifact

Files:
- `test_custom_openai_contract.py`

Steps:
- Add one small assert-based script with no framework
- Cover only pure contract checks:
  - config merge backfills missing keys
  - valid base URL root resolves to expected endpoint
  - full endpoint input is rejected
  - blank API key omits `Authorization`

Verification:
- `python test_custom_openai_contract.py` exits cleanly

Note:
- This file is added because spec requires one runnable proof artifact. If strict target lock from spec is enforced, update spec target list first.

## Task 5: Update user docs

Files:
- `README.md`
- `Config.md`

Steps:
- Add `custom_openai` to provider list
- Add setup example for 9router using base URL `http://127.0.0.1:20128/v1`
- Explain that user must enter base URL root, not full `/chat/completions` endpoint
- Document optional API key behavior for local routers
- Document `Test API Connection` expectations and likely failure cases

Verification:
- Docs match implemented field names and validation rules exactly

# Risks / Rollback

- Risk: config merge changes existing load semantics
  - rollback: revert `get_config()` merge change only if it breaks existing configs
- Risk: UI grows inconsistent with existing provider tabs
  - rollback: keep same tab pattern and reuse existing combo persistence flow
- Risk: proof script drifts from runtime helper behavior
  - rollback: keep script scoped to pure helper contracts only

# Final Verification

- `python test_custom_openai_contract.py`
- Open add-on config in Anki and save custom provider with:
  - provider: `Custom OpenAI-Compatible`
  - base URL: `http://127.0.0.1:20128/v1`
  - model: local router model id
  - API key: blank
- Run `Test API Connection` against working local router
- Confirm built-in provider still rejects blank API key in test UI
- Confirm docs mention base URL root and optional API key exactly once each

# Completion Criteria

- `custom_openai` works for OpenAI-compatible local endpoint without custom parser code
- Old saved configs load safely with merged defaults
- Invalid full-endpoint input is rejected clearly
- One runnable proof artifact passes
- Docs and UI use exact same field names and rules

