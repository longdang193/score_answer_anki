---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: ai-rich-render-policy
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/README.md
  - packages/score_answer_anki/Config.md
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
---

# Goal

Replace plain-text-only AI rendering in `score_answer_anki` with one bounded rich-render policy shared by `AI Hint` and `AI Analysis`, while preserving current trust boundaries and keeping implementation small.

Requested behavior:

- `AI Hint` and `AI Analysis` render a safe rich-text subset instead of literal markdown markers
- supported output in V1 includes:
  - paragraphs
  - bold
  - italic
  - inline code
  - fenced code blocks
  - unordered lists
  - ordered lists
  - canonical LaTeX formulas via MathJax delimiters
- note-field manual `Hint` behavior remains unchanged
- raw AI HTML is never trusted or passed through directly
- both AI surfaces use one shared render policy/helper path

# Key Deliverables

- One SSOT helper in `packages/score_answer_anki/__init__.py`, e.g. `render_ai_rich_text(text)`
- One explicit trust-boundary split between:
  - trusted note-field HTML for manual `Hint`
  - untrusted AI text for `AI Hint` and `AI Analysis`
- One bounded markdown/math/sanitization contract shared by both AI surfaces
- One explicit runtime formula-typesetting contract for DOM-refresh paths
- One block-safe wrapper contract for AI bodies
- One runnable proof artifact covering markdown, code, lists, hostile HTML neutralization, formula delimiter preservation, and post-refresh typeset hook behavior
- One docs update describing supported formatting and exclusions

# Task/Wave Breakdown

## Wave 1: Ownership and shared path

- Manual `Hint` field remains on its current trusted note-field HTML path
- `AI Hint` and `AI Analysis` stop using open-coded string insertion for body content and route through one shared helper
- No separate formatting policy for hint vs analysis in V1
- Rich AI output ownership remains inside `score_answer_anki`, not note templates

## Wave 2: Supported syntax contract

Supported AI formatting contract in V1:

- paragraphs
- `**bold**`
- `*italic*`
- inline code via backticks
- fenced code blocks
- unordered lists
- ordered lists
- inline math via `\(...\)`
- display math via `\[...\]`

Explicit V1 exclusions:

- raw AI HTML as a feature
- links
- images
- tables
- blockquotes
- arbitrary CSS classes/styles
- embedded media
- `$...$` and `$$...$$` shorthand math normalization

Rules:

- unsupported markdown/HTML degrades safely to text or sanitized plain structure
- malformed markup must not break panel rendering
- parse failure falls back to escaped plain text for affected block

## Wave 3: Formula contract

AI formula rendering in V1 is defined only for canonical MathJax delimiters already present in AI text:

- `\(...\)` for inline math
- `\[...\]` for display math

Rules:

- renderer preserves canonical math delimiters through markdown conversion and sanitization
- renderer does not normalize `$...$` or `$$...$$` in V1
- renderer does not generate `[latex]...[/latex]`, `[$]...[/$]`, or `[$$]...[/$$]`
- prompt-side guidance may instruct AI to emit `\(...\)` and `\[...\]` only

Reason:

- this is smallest reproducible formula contract
- avoids ambiguous dollar parsing and currency/code drift
- keeps math semantics identical between hint and analysis

## Wave 4: Exact transform pipeline

AI content transform must be one explicit SSOT pipeline:

1. treat AI response as untrusted plain text input
2. escape raw HTML-significant characters from source text
3. apply bounded markdown-subset conversion on escaped text
4. preserve canonical math delimiters through conversion
5. sanitize final generated HTML to tiny allowlist
6. if pipeline fails, render escaped plain text fallback

Rules:

- no implementation may parse raw AI HTML as trusted markup before escaping
- no separate hint-only or analysis-only pipeline variants
- sanitizer output is authoritative final HTML shape

## Wave 5: DOM structure and post-refresh typesetting

DOM wrapper rules:

- rich AI content renders inside block container, not inline `span`
- `AI Hint` body wrapper becomes block-safe rich container
- `AI Analysis` body wrapper becomes block-safe rich container
- lists and code blocks must not be nested inside invalid `<p>` wrappers

Post-refresh formula rule:

- any path that swaps AI fragment HTML at runtime must call one shared post-refresh formula-typeset hook after DOM replacement
- both hint and analysis refresh paths reuse same hook
- if reviewer runtime lacks usable MathJax re-typesetting support, visible content must still preserve canonical delimiters as safe text

# Design Decisions

## Trusted vs untrusted content

Manual note-field `Hint` remains trusted field content for this feature.

Rules:

- current manual hint pass-through behavior stays intact
- AI-generated content is untrusted and never shares manual-hint pass-through path
- no config switch enables raw AI HTML pass-through in V1

Reason:

- smallest safe change preserves existing field semantics
- root cause bug belongs only to AI render path
- allowing AI HTML directly creates unnecessary XSS and layout risk

## One renderer for both AI surfaces

One shared helper owns:

- markdown subset conversion
- final HTML allowlist shape
- fallback behavior
- formula delimiter preservation

One shared post-refresh helper owns:

- formula re-typeset trigger after DOM replacement

Reason:

- avoids hint/analysis drift
- keeps tests and docs symmetrical
- shortest safe maintenance path

## Tiny markdown subset only

Renderer supports only bounded structure listed in this spec.

Reason:

- user request needs styling, code, lists, formulas
- full markdown feature surface is not needed
- smaller allowlist lowers sanitizer complexity

## Canonical math only in V1

Formula support for AI content is canonical `\(...\)` and `\[...\]` only.

Reason:

- removes ambiguous `$` parsing
- keeps parser smaller and more reproducible
- matches approved lazy version

# Invariants

- manual `Hint` field remains separate from AI rich renderer
- AI content remains advisory only
- AI content remains untrusted input at all times
- `AI Hint` and `AI Analysis` use one shared render-policy helper
- formula support for AI runtime content is canonical MathJax-delimiter-based only in V1
- unsupported constructs never execute as active HTML/JS/CSS

# Acceptance Criteria

- AI hint text `Use **bold** text` renders visible bold emphasis instead of literal `**`
- AI hint text `Use *italic* text` renders visible italic emphasis instead of literal `*`
- AI hint text ``Use `code` here`` renders visible inline code instead of literal backticks
- AI analysis text with ordered or unordered markdown lists renders list structure instead of flattened marker text
- AI hint or analysis text with fenced code block renders block code inside valid block container
- AI hint or analysis text containing `\(x^2+y^2\)` preserves canonical inline formula delimiters through render pipeline and renders as formula when shared post-refresh typeset hook is available
- AI hint or analysis text containing `\[\int_0^1 x^2 dx\]` preserves canonical display formula delimiters through render pipeline and renders as formula when shared post-refresh typeset hook is available
- raw AI HTML such as `<script>alert(1)</script><b>hi</b>` does not execute script and is not treated as trusted source HTML
- malformed markdown or malformed math does not crash panel render; content falls back safely
- manual note-field `Hint` still renders with prior field HTML semantics and does not route through AI sanitizer
- rich AI content wrappers use block-safe structure and no longer place lists/code blocks inside invalid inline wrappers
- both hint and analysis runtime refresh paths call same post-refresh formula-typeset hook after DOM replacement

# Non-Goals

- No raw AI HTML pass-through mode
- No support for links, images, tables, blockquotes, or arbitrary embedded HTML in V1
- No promise of full CommonMark feature parity
- No migration of manual note-field `Hint` onto AI sanitizer path
- No `$...$` / `$$...$$` shorthand math parsing in V1
- No desktop LaTeX image-generation pipeline integration for dynamic AI content in V1

# Risks and Mitigations

## Risk: sanitizer strips too much and surprises users

Mitigation:

- keep supported subset explicit in docs
- test exact subset examples for both hint and analysis
- use plain-text fallback instead of blank output

## Risk: hint and analysis drift again

Mitigation:

- one shared rich-render helper only
- one shared contract test set for both surfaces

## Risk: runtime formula render still differs by client/runtime

Mitigation:

- define canonical delimiters as `\(...\)` and `\[...\]`
- assign one explicit post-refresh typeset hook owner
- keep safe text fallback when runtime formula typesetting is unavailable

## Risk: code blocks or lists break panel layout

Mitigation:

- replace inline wrappers with block-safe containers
- add UI contract tests for list and code-block HTML shape

# Validation Plan

- proof target: AI hint and analysis share one rich-render policy
  - method: source inspection plus targeted helper test
  - evidence: both call one shared `render_ai_rich_text(...)` helper

- proof target: raw AI HTML is never trusted input
  - method: runnable transform test
  - evidence: source HTML-significant characters are escaped before markdown conversion path and disallowed active tags never survive final HTML

- proof target: markdown emphasis renders structurally
  - method: runnable render test
  - evidence: `**bold**` and `*italic*` produce allowed emphasis tags, not literal markers

- proof target: code formatting renders structurally
  - method: runnable render test
  - evidence: inline code yields `code`; fenced block yields `pre` + `code`

- proof target: list formatting renders structurally
  - method: runnable render test
  - evidence: unordered and ordered markdown list input yields `ul/ol/li` structure

- proof target: canonical math delimiters survive pipeline
  - method: runnable render test
  - evidence: `\(...\)` and `\[...\]` remain present in final rich HTML/text flow for MathJax processing

- proof target: post-refresh typeset hook is SSOT
  - method: source inspection plus narrow runtime-adjacent test
  - evidence: both hint and analysis refresh helpers call same post-refresh formula-typeset helper after DOM replacement

- proof target: malformed markup degrades safely
  - method: runnable failure-path test
  - evidence: render returns escaped visible content and no exception bubbles to reviewer UI

- proof target: manual hint remains on prior trusted path
  - method: runnable contract test
  - evidence: manual `Hint` HTML still passes through while AI content is sanitized separately

- proof target: panel wrapper structure is block-safe
  - method: render inspection
  - evidence: AI bodies use block container, not invalid inline wrappers around list/code output

# Completion Criteria

- spec approved
- supported AI rich-format subset is explicit and bounded
- trust-boundary split between manual hint HTML and AI content is explicit
- runtime formula contract is explicit and reproducible
- validation plan names concrete proof for markdown, formulas, sanitization, fallback behavior, and shared post-refresh hook behavior
