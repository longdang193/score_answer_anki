# Anki Type answer Analysis AI Add-on

## Overview
![good evaluation](/images/good_2.png) ![good evaluation](/images/bad_answer.png) 

This Anki add-on enhances your flashcard review experience by providing intelligent AI-powered analysis of your answers. Instead of just showing whether your answer matches the expected one, the AI evaluates the quality of your response and provides constructive feedback to help you learn more effectively.

⚠️ : This add-on works with Anki's type-answer question-answer.

⚠️ : AI scoring UI runs only when card template name ends with `_score`.

## Purpose

### What it does:
- **Intelligent Answer Evaluation**: AI analyzes your answers semantically, not just text matching
- **Constructive Feedback**: Provides specific tips to improve your understanding
- **Refresh analysis action**: Lets you rerun AI feedback when you want a fresh result
- **Multi-Language Support**: Works in English, French, Spanish, and German
- **Multiple AI Providers**: Choose from OpenAI, Google Gemini, Anthropic Claude, DeepSeek, OpenRouter, Groq, or Custom OpenAI-Compatible
⚠️ : I tested Google Gemini and OpenRouter using their free evaluation keys.

### Why use it:
- **Better Learning**: Get personalized feedback on why your answer was right or wrong
- **Semantic Understanding**: AI recognizes when your answer is conceptually correct even if worded differently
- **Efficiency**: Focus more time on concepts you struggle with
- **Motivation**: Positive reinforcement when you're improving

## Configuration Options

⚠️ :  <b>After setup config it's mandatory to restart anki<b>

### General Settings

#### AI Provider
![config0](/images/config_0.png)
![config0](/images/config.png)
- **Purpose**: Choose which AI service to use for analysis
- **Options**: OpenAI, Google Gemini, Anthropic Claude, DeepSeek, Groq, OpenRouter, Custom OpenAI-Compatible
- **Default**: OpenAI
- **Note**: Only the selected provider's tab will be enabled in the configuration
⚠️ : For basic use, I recommend using a Gemini key, since the free key allows you to run 2 or 3 complete review sessions

#### Language
- **Purpose**: Set the language for AI feedback and interface
- **Options**: 
  - English (default)
  - Français (French)
  - Español (Spanish) 
  - Deutsch (German)
- **Impact**: Changes AI prompt language and interface text

#### Enable AI Analysis
- **Purpose**: Toggle the entire AI analysis feature on/off
- **Default**: Enabled
- **When disabled**: Shows standard Anki comparison only

#### Feedback Length
- **Purpose**: Limit the length of AI responses
- **Range**: 50-4000 tokens
- **Default**: 200
- **Impact**: Lower = shorter, faster feedback; higher = more detailed feedback

#### Temperature (0-1)
- **Purpose**: Control AI creativity/randomness
- **Range**: 0.0 (deterministic) to 1.0 (creative)
- **Default**: 0.7
- **Recommendation**: 0.3-0.7 for educational feedback

#### Default Prompt Profile
- **Purpose**: Choose evaluation style for scoreable card templates
- **Options**:
  - `default`: balanced educational feedback
  - `strict_stem`: precise grading for numeric/factual answers
  - `speaking_flexible`: flexible grading for speaking-style responses
  - `custom`: use your own prompt fields

#### Custom Prompt Fields
- **Custom system prompt**: shown only when selected profile is `custom`
- **Custom analysis prompt template**: shown only when selected profile is `custom`
- **Custom hint prompt template**: shown only when selected profile is `custom`
- **Storage**: one global custom prompt trio, not per-language values
- **Supported variables**:
  - `{question}`
  - `{expected_answer}`
  - `{accepted_answers}`
  - `{user_answer}`
  - `{language}`
- **Hint prompt variables**:
  - `{question}`
  - `{expected_answer}`
  - `{hint}`
  - `{language}`

### Provider-Specific Settings

Each AI provider has its own tab with specific configuration:\n

⚠️ :  <b>After config restart anki<b>

#### OpenAI
- **Models Available**: gpt-3.5-turbo, gpt-4, gpt-4-turbo, gpt-4o, gpt-4o-mini
- **API Key**: Get from https://platform.openai.com/api-keys
- **Cost**: Pay-per-use, varies by model
- **Recommended Model**: gpt-3.5-turbo (cost-effective) or gpt-4o-mini (better quality)

#### Google Gemini
- **Models Available**: gemini-1.5-flash, gemini-1.5-pro, gemini-1.0-pro
- **API Key**: Get from https://aistudio.google.com/app/apikey
- **Cost**: Free tier available, then pay-per-use
- **Recommended Model**: gemini-1.5-flash (fast and efficient)

#### Anthropic Claude
- **Models Available**: claude-3-haiku-20240307, claude-3-sonnet-20240229, claude-3-opus-20240229
- **API Key**: Get from https://console.anthropic.com/
- **Cost**: Pay-per-use
- **Recommended Model**: claude-3-haiku-20240307 (fastest and cheapest)

#### DeepSeek
- **Models Available**: deepseek-chat, deepseek-coder
- **API Key**: Get from https://platform.deepseek.com/api_keys
- **Cost**: Very competitive pricing
- **Recommended Model**: deepseek-chat (general purpose)

#### Groq
- **Models Available**: llama3-8b-8192, llama3-70b-8192, mixtral-8x7b-32768, gemma-7b-it
- **API Key**: Get from https://console.groq.com/keys
- **Cost**: Free tier available with rate limits
- **Recommended Model**: llama3-8b-8192 (fast inference)

#### OpenRouter
- **Models Available**: "deepseek/deepseek-r1:free", "openai/gpt-oss-20b:free", "qwen/qwen3-coder:free" ,"google/gemma-3n-e2b-it:free" ,"tencent/hunyuan-a13b-instruct:free"
- **API Key**: Get from https://console.groq.com/keys
- **Cost**: Free tier available with rate limits
- ⚠️ : **Recommended Model**: tencent/hunyuan-a13b-instruct:free

#### Custom OpenAI-Compatible
- **Use case**: Local or self-hosted OpenAI-compatible routers such as 9router
- **Base URL**: Enter base URL root only, for example `http://127.0.0.1:20128/v1`
- **Do not enter**: `http://127.0.0.1:20128/v1/chat/completions`
- **Model**: Enter your local router model ID
- **API Key**: Optional; leave blank if your router does not require auth
- **Connection test**: Requires base URL + model, not API key


## Setup Instructions

### 1. Choose Your AI Provider
1. Open Anki
2. Go to **Tools → AI Multi-Provider Configuration**
3. Select your preferred AI provider from the dropdown
4. Notice that only the selected provider's tab is enabled

### 2. Configure API Access
1. Click on the tab for your selected provider
2. Get an API key from the provider's website (links provided in each tab)
3. Enter your API key in the field, or for `Custom OpenAI-Compatible` enter base URL root and optional API key
4. Select your preferred model
5. Click "Test API Connection" to verify everything works

### 3. Adjust Settings
1. Choose your preferred language for feedback
2. Adjust feedback length if needed (200 is usually sufficient)
3. Set temperature (0.7 is a good balance)
4. Click "Save"

### 4. Start Using
![loadspinner](/images/analysis_by_AI.png)
![review](/images/very_good.png)
- Review your flashcards as normal
- After answering, you'll see both Anki's standard comparison and the AI analysis
- The AI provides:
  - A score from 0-10
  - Specific improvement tips
  - A compact refresh action if you want a fresh answer
- On supported typed-answer cards, the answer box stays docked at the bottom with the hint controls so you can keep the input visible while reading long questions.
- When you scroll to the end of a long typed-answer question, the add-on reserves space above the docked footer so the last visible word is not hidden behind the input area.

## AI Scoring System

The AI evaluates your answers on a 0-10 scale:

- **0-3 (Again)**: Incorrect or very incomplete answer
  - *Action*: Review the material again immediately
  - *Color*: Red ❌

- **4-5 (Hard)**: Partially correct but with significant errors
  - *Action*: Review soon with shorter intervals
  - *Color*: Orange ⚠️

- **6-8 (Good)**: Correct answer with minor imperfections
  - *Action*: Standard review interval
  - *Color*: Green ✅

- **9-10 (Easy)**: Excellent and complete answer
  - *Action*: Longer review intervals
  - *Color*: Blue 🌟

## Cost Considerations

### Free Options:
- **Google Gemini**: Generous free tier
- **Groq**: Free tier with rate limits
- **OpenRouter**: Free tier with rate limits

### Paid Options:
- **OpenAI**: Moderate pricing, excellent quality
- **Anthropic Claude**: Premium pricing, high quality

### Cost Optimization Tips:
1. Start with free tiers (Gemini or Groq)
2. Use shorter max_tokens (100-200) for basic feedback
3. Choose efficient models (gpt-3.5-turbo, gemini-1.5-flash, claude-3-haiku)
4. Monitor your usage through provider dashboards

## Troubleshooting

### Common Issues:

#### "API key not configured"
- Ensure you've entered the API key for your selected provider
- Test the connection using the test button
- `Custom OpenAI-Compatible` can leave API key blank if router does not require auth

#### "Connection error"
- Check your internet connection
- Verify your API key is correct and has sufficient credits
- Try switching to a different provider
- For `Custom OpenAI-Compatible`, make sure you entered base URL root instead of `/chat/completions`

#### "AI analysis not available"
- Check if AI analysis is enabled in settings
- Verify your selected provider's API key is working
- Try reducing max_tokens if you're hitting limits

#### Interface appears in wrong language
- Change the language setting in the configuration
- Restart Anki after changing language settings

### Performance Tips:
- The add-on caches recent analyses to avoid duplicate API calls
- Analysis happens asynchronously to avoid blocking your reviews
- Cache automatically clears after 10 entries to manage memory

### Question and Answer Variants

Use four fields for typed-answer variant cards:

- `Front`: canonical display question
- `Front_variants`: optional alternate question phrasings separated by `;;`
- `Back`: canonical display answer
- `Back_variants`: optional accepted-answer variants separated by `;;`

Example:

- `Front`: `13 * 17 = ?`
- `Front_variants`: `17 * 13 = ?`
- `Back`: `221`
- `Back_variants`: `two hundred twenty-one;;221.0`

Rules in V1:

- one eligible question is picked from `Front` + `Front_variants`
- chosen question stays stable for answer reveal and regenerate-analysis
- add-on filters obviously incompatible question variants before display
- `Back_variants` extends add-on AI acceptance only
- native Anki typed compare still uses normal Anki behavior
- no positional mapping exists between `Front_variants` and `Back_variants`

## Privacy and Data

- Your answers are sent to the selected AI provider for analysis
- No data is stored permanently by the add-on (only temporary cache)
- Each provider has their own data retention policies
- Consider using local or privacy-focused providers if data privacy is a concern
- `Custom OpenAI-Compatible` supports local OpenAI-compatible routers for this use case

## Support

For issues specific to this add-on, check:
1. Your API key configuration
2. Internet connectivity
3. Provider service status
4. Anki add-on compatibility
5. let me know !


## Compatibility

⚠️ This add-on was tested with Anki 2.1.x (release 25.07.5).


#### Front-side hint panel
- Owner: `score_answer_anki`
- Surface: front side only
- Gate: `_score` template plus supported typed-answer front-side path
- Manual mapped hint field passes through stored field content
- Active-slot mapping is: `c1 -> Hint`, `c2 -> Hint2`, `c3 -> Hint3`, `c4 -> Hint4`; non-cloze score cards use `Hint`
- Missing mapped hint field behaves as empty manual hint
- AI hint and AI analysis use same bounded rich-format renderer
- Supported AI formatting: paragraphs, `**bold**`, `*italic*`, inline code, fenced code blocks, ordered/unordered lists, canonical `\(...\)` and `\[...\]` math delimiters
- Unsupported AI formatting in V1: raw HTML, links, images, tables, blockquotes, `$...$`, `$$...$$`
- If runtime formula typesetting is unavailable, canonical math delimiters remain visible as safe text
- AI hint is session-only and is not auto-saved
- If AI is unavailable, `Suggest Hint` remains visible but disabled with a reason
