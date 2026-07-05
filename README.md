# Score Answer AI for Anki

AI-powered semantic evaluation for Anki `type:` cards, with multilingual feedback, configurable prompts, and multi-provider support.

![good evaluation](images/good_2.png)
![bad evaluation](images/bad_answer.png)

## What This Add-on Does

- Evaluates typed answers semantically (not only exact text matching)
- Gives structured feedback:
  - score (0-10) when available
  - improvement tips
  - optional rerun via compact refresh action
- Runs analysis in background to keep review flow responsive
- Supports multiple LLM providers from one config screen
- Supports multilingual analysis and UI localization

> This add-on is designed for Anki cards using typed answers (`{{type:...}}`).
> AI scoring UI runs only when card template name ends with `_score`.

## Key Features

- **Multi-provider support**: OpenAI, Gemini, Claude, DeepSeek, Groq, OpenRouter, Custom OpenAI-Compatible
- **Analysis language control**: choose output language independently of your answer language
- **Interface language auto mode**: config UI can follow Anki UI language
- **Prompt profiles**:
  - built-in `default`, `strict_stem`, `speaking_flexible`, and `custom`
  - exact card-template-name overrides via JSON
  - optional custom system prompt
  - optional custom analysis prompt template with variables
  - reset/copy actions for selected profile
- **Custom model IDs**:
  - add your own model IDs in provider tabs
  - persist custom IDs in config
- **OpenRouter resiliency**:
  - recommended `openrouter/free`
  - fallback-aware connection test behavior
- **Error-safe scoring**:
  - provider errors no longer show fake `5/10`
  - displays `N/A` when analysis is unavailable
  - compact refresh action can request a fresh analysis

## Supported Languages

Analysis feedback and UI labels currently support:

- English
- French
- Spanish
- German
- Russian
- Japanese
- Chinese
- Korean

## Installation

1. Open Anki.
2. Go to `Tools -> Add-ons -> Install from file...` (or install by AnkiWeb code if published).
3. Restart Anki.

## Quick Start

![Config access from Tools](images/config_botton_from_tools.png)

1. Open `Tools -> AI Multi-Provider Configuration`.
2. Select provider and model.
3. Add your API key, or for `Custom OpenAI-Compatible` enter base URL + model and leave API key blank if your local router does not need one.
4. Click `Test API Connection`.
5. Select `Analysis language`.
6. Save and review your `type:` cards as usual.

## Question and Answer Variants

Use dedicated fields.

- `Front`: canonical display question
- `Front_variants`: optional alternate question phrasings separated by `;;`
- `Back`: canonical display answer
- `Back_variants`: optional accepted-answer variants separated by `;;`

Example:

- `Front`: `13 * 17 = ?`
- `Front_variants`: `17 * 13 = ?;;221 = 13 * ?`
- `Back`: `221`
- `Back_variants`: `two hundred twenty-one;;221.0`

Behavior:

- add-on builds one question pool from `Front` + `Front_variants`
- add-on builds one accepted-answer pool from `Back` + `Back_variants`
- one eligible question is shown per card exposure and stays stable for answer side and AI regenerate
- obviously incompatible question variants are filtered before display
- native Anki typed-answer compare and scheduling stay unchanged; accepted-answer variants affect add-on AI advice only

V1 limits:

- `Front_variants` and `Back_variants` use literal `;;`
- one card should still represent one concept
- no positional mapping exists between question variants and answer variants
- plain-text question rendering works best; rich HTML/media variants are not variant-aware in V1

## Configuration Guide

### General Settings

- **AI Provider**: active provider used for analysis
- **Analysis language**: language for AI feedback (`tips`) and prompt intent
- **Enable AI analysis**: global on/off
- **Feedback length**: max AI response length (`lower = shorter, faster feedback`)
- **Temperature**: response creativity/variance
- **Show Anki compare**: toggle native Anki comparison block
- **Show code compare**: toggle side-by-side extracted text comparison

### Prompt Profiles

- **Default prompt profile**:
  - `default`: balanced educational feedback
  - `strict_stem`: precise STEM grading; emphasizes numeric result, sign, unit, and completeness
  - `speaking_flexible`: speaking-oriented grading; emphasizes communicative adequacy and allows alternative valid responses
  - `custom`: uses your own prompt text fields
- **Custom system prompt**: shown only when selected profile is `custom`; stored as one global field
- **Custom analysis prompt template**: shown only when selected profile is `custom`; stored as one global field; supports:
  - `{question}`
  - `{expected_answer}`
  - `{accepted_answers}`
  - `{user_answer}`
  - `{language}`
- **Custom hint prompt template**: shown only when selected profile is `custom`; stored as one global field; supports:
  - `{question}`
  - `{expected_answer}`
  - `{hint}`
  - `{language}`
- **Reset prompts to defaults**: resets custom fields for `custom` profile using selected analysis language

### Provider Tabs

Each provider tab includes:

- API key field
- model selector
- editable model field
- `Add model ID` input/button to append custom model IDs

`Custom OpenAI-Compatible` also includes:

- base URL root field, for example `http://127.0.0.1:20128/v1`
- validation that rejects full `/chat/completions` endpoint input
- optional API key support for local routers

Custom model IDs are saved per provider in config and restored on restart.

> Always test a model ID before using it in real reviews.  
> Some models may intermittently fail or be temporarily unavailable for unknown provider-side reasons.

## OpenRouter Notes

OpenRouter availability can vary by model/provider at runtime.

Recommended defaults:

- `openrouter/free` for highest compatibility
- use specific `:free` variants only when needed
- always run `Test API Connection` after changing model ID

If selected model test fails, the add-on may successfully validate via `openrouter/free` fallback.

## Scoring Behavior

- Normal case: shows score and improvement tips
- Provider/API/parsing failure: shows `N/A` (not a fake numeric score)
- Keeps failure details in feedback text for easier troubleshooting

## Troubleshooting

### "Connection error" or "Provider returned error"

- Verify API key and provider account status
- Try another model ID
- For OpenRouter, start with `openrouter/free`
- For `Custom OpenAI-Compatible`, enter base URL root only, not `/chat/completions`
- Reduce traffic / retry later (temporary provider saturation can happen)

### Custom OpenAI-Compatible quick example

- Provider: `Custom OpenAI-Compatible`
- Base URL: `http://127.0.0.1:20128/v1`
- Model: your router model ID
- API key: leave blank if your local router does not require auth
- Then run `Test API Connection`

### Always getting English feedback

- Check `Analysis language` in config
- Ensure custom prompts do not force English
- Use reset prompt defaults for the selected analysis language

### Model works in one provider but not another

- Model IDs are provider-specific
- Use `Add model ID` and test each ID explicitly

## Privacy

- Card question/answer content is sent to selected AI provider for analysis
- The add-on stores temporary in-memory cache for active session flow
- No long-term local analytics storage is implemented by default
- Provider-side retention policies depend on the provider you choose

## Compatibility

- Tested on modern Anki 25.x builds
- Uses Anki reviewer hooks for typed-answer comparison and rendering

## Screenshots

![Main feedback](images/very_good.png)
![Loading state](images/analysis_by_AI.png)
![Config UI 1](images/config.png)
![Config UI 2](images/config_0.png)
![Latest changes](images/changes_made_languages_customprompt_modeid.png)
![Config access from Tools](images/config_botton_from_tools.png)

## Contributing

Issues and improvements are welcome.  
When reporting bugs, include:

- Anki version
- add-on version/commit
- provider + model ID
- exact error text
- steps to reproduce



## Front-side Hint Panel

- Owned by `score_answer_anki`, not by note-template-local hint buttons
- Runs on front side only for eligible typed `_score` cards
- Optional `Hint` note field is shown as stored field content
- `Suggest Hint` uses configured provider and prompt profile, but generated hint is session-only text and is not auto-saved
- If AI is unavailable, `Suggest Hint` stays visible but disabled with a reason
