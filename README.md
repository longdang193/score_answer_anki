# Score Answer AI for Anki

AI-powered semantic evaluation for Anki `type:` cards, with multilingual feedback, configurable prompts, and multi-provider support.

![good evaluation](/images/good_2.png)
![bad evaluation](/images/bad_answer.png)

## What This Add-on Does

- Evaluates typed answers semantically (not only exact text matching)
- Gives structured feedback:
  - score (0-10) when available
  - improvement tips
  - review suggestion (`Again`, `Hard`, `Good`, `Easy`)
- Runs analysis in background to keep review flow responsive
- Supports multiple LLM providers from one config screen
- Supports multilingual analysis and UI localization

> This add-on is designed for Anki cards using typed answers (`{{type:...}}`).

## Key Features

- **Multi-provider support**: OpenAI, Gemini, Claude, DeepSeek, Groq, OpenRouter
- **Analysis language control**: choose output language independently of your answer language
- **Interface language auto mode**: config UI can follow Anki UI language
- **Custom prompt system**:
  - optional custom system prompt
  - optional custom analysis prompt template with variables
  - reset to language defaults
  - copy defaults to clipboard
- **Custom model IDs**:
  - add your own model IDs in provider tabs
  - persist custom IDs in config
- **OpenRouter resiliency**:
  - recommended `openrouter/free`
  - fallback-aware connection test behavior
- **Error-safe scoring**:
  - provider errors no longer show fake `5/10`
  - displays `N/A` when analysis is unavailable

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

![Config access from Tools](/images/config_botton_from_tools.png)

1. Open `Tools -> AI Multi-Provider Configuration`.
2. Select provider and model.
3. Add your API key.
4. Click `Test API Connection`.
5. Select `Analysis language`.
6. Save and review your `type:` cards as usual.

## Configuration Guide

### General Settings

- **AI Provider**: active provider used for analysis
- **Analysis language**: language for AI feedback (`tips`) and prompt intent
- **Enable AI analysis**: global on/off
- **Max tokens**: max output size
- **Temperature**: response creativity/variance
- **Show Anki compare**: toggle native Anki comparison block
- **Show code compare**: toggle side-by-side extracted text comparison

### Prompt Customization

- **Use custom prompt template**:
  - disabled: fields are read-only and show default placeholders
  - enabled: fields become editable
- **Custom system prompt**: optional replacement for default system message
- **Custom analysis prompt template**: supports:
  - `{question}`
  - `{expected_answer}`
  - `{user_answer}`
  - `{language}`
- **Reset prompts to defaults**: injects default prompts for selected analysis language
- **Copy default prompts**: copies language-specific defaults to clipboard

### Provider Tabs

Each provider tab includes:

- API key field
- model selector
- editable model field
- `Add model ID` input/button to append custom model IDs

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

- Normal case: shows score and review suggestion
- Provider/API/parsing failure: shows `N/A` (not a fake numeric score)
- Keeps failure details in feedback text for easier troubleshooting

## Troubleshooting

### "Connection error" or "Provider returned error"

- Verify API key and provider account status
- Try another model ID
- For OpenRouter, start with `openrouter/free`
- Reduce traffic / retry later (temporary provider saturation can happen)

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

- Main feedback: `/images/very_good.png`
- Loading state: `/images/analysis_by_AI.png`
- Config UI: `/images/config.png`, `/images/config_0.png`
- Latest changes (languages/prompt/model IDs): `/images/changes_made_languages_customprompt_modeid.png`
- Config entry point in Tools: `/images/config_botton_from_tools.png`

## Contributing

Issues and improvements are welcome.  
When reporting bugs, include:

- Anki version
- add-on version/commit
- provider + model ID
- exact error text
- steps to reproduce

