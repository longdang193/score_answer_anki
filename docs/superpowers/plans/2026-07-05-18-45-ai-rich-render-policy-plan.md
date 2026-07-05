---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: ai-rich-render-policy
parent_spec: packages/score_answer_anki/docs/superpowers/specs/2026-07-05-18-20-ai-rich-render-policy-spec.md
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
  - packages/score_answer_anki/README.md
  - packages/score_answer_anki/Config.md
  - packages/score_answer_anki/scripts/sync_to_anki.ps1
---

# Goal

Implement approved AI rich-render policy in `score_answer_anki` so `AI Hint` and `AI Analysis` share one safe rich-text render path for bounded markdown and canonical MathJax delimiters, while manual note-field `Hint` keeps its current trusted HTML behavior.

Bounded implementation scope:

- one shared `render_ai_rich_text(...)` path for both AI surfaces
- one local bounded parser in `packages/score_answer_anki/__init__.py`
- support only:
  - paragraphs
  - `**bold**`
  - `*italic*`
  - inline code
  - fenced code blocks
  - unordered lists
  - ordered lists
  - canonical `\(...\)` and `\[...\]` math delimiters
- no `$...$` / `$$...$$` parsing
- one shared post-refresh formula-typeset hook for runtime DOM updates
- no change to manual `Hint` field ownership or trust level

Out of scope:

- full CommonMark support
- raw AI HTML pass-through
- links/images/tables/blockquotes
- prompt/profile redesign beyond optional docs wording
- desktop LaTeX image-generation workflow
- adding markdown or sanitization dependencies in V1

# Key Deliverables

- One shared AI rich-render helper in `packages/score_answer_anki/__init__.py`
- One explicit SSOT AI transform pipeline: escape source text -> bounded markdown conversion -> sanitize final HTML -> fallback on failure
- One block-safe wrapper contract for both AI hint and AI analysis bodies
- One shared post-refresh formula-typeset helper reused by hint and analysis refresh paths
- One focused contract-test expansion in `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- One docs update in `packages/score_answer_anki/README.md` and `packages/score_answer_anki/Config.md`

# Task Breakdown

## Task 1: Add shared AI rich-render primitives

Files:
- `packages/score_answer_anki/__init__.py`

Steps:
- Add one bounded helper family for AI content only, for example:
  - `escape_ai_source_text(text)`
  - `render_ai_markdown_subset(text)`
  - `sanitize_ai_rendered_html(html_text)`
  - `render_ai_rich_text(text)` as sole public composition point
- Keep helper ownership local to `score_answer_anki`; do not invent shared repo-wide abstraction.
- Implement one local bounded parser only. Do not add new dependency in V1.
- Implement smallest parser that works for bounded subset:
  - fenced code blocks first
  - ordered/unordered list blocks
  - paragraph splitting
  - inline transforms for code, bold, italic inside non-code regions
- Preserve canonical `\(...\)` and `\[...\]` delimiters as plain text through conversion.
- Treat raw AI input as text, not HTML.
- If helper fails on malformed input, fall back to escaped plain text.
- If local parser proves insufficient during execution, stop and amend spec/plan; do not substitute a library ad hoc.

Verification:
- one `render_ai_rich_text(...)` helper exists
- no separate hint-only or analysis-only AI formatting path exists
- helper contract matches spec subset exactly
- canonical math delimiters survive helper output unchanged
- no dependency is added for markdown or sanitization in V1

## Task 2: Route AI hint and analysis through shared rich-render path

Files:
- `packages/score_answer_anki/__init__.py`

Steps:
- Replace current escaped-plain-text AI hint body branch with shared rich-render output.
- Replace current raw `tips` insertion branch with shared rich-render output.
- Route unavailable/error AI text through same safe render path or same escaped-fallback path consistently; do not keep a special-case legacy branch.
- Change AI body wrappers from inline-only structures to block-safe containers.
- Preserve existing class names where possible for current styling:
  - keep `aqi-front-hint-ai` if wrapper tag changes
  - keep `aqi-section-copy` semantics where still valid
  - keep analysis panel wrapper and body class contracts stable unless minimal CSS adjustment is required
- If wrapper-tag change requires CSS change, keep it local and minimal in `packages/score_answer_anki/__init__.py` stylesheet block.
- Keep manual `Hint` rendering untouched on existing trusted note-field path.
- Keep titles, labels, score badge, regenerate button, and loading fragments unchanged unless wrapper shape must change for valid HTML.

Verification:
- manual `Hint` path is unchanged
- ready, unavailable, and error AI body states call same render helper or same explicit fallback contract
- `AI Hint` and `AI Analysis` call same render helper
- lists/code blocks are no longer nested in invalid `<p><span>` structure
- existing styling selectors remain stable or are minimally adjusted in same file
- loading and action helpers remain SSOT for equivalent UI fragments

## Task 3: Add shared post-refresh formula-typeset hook

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Add one thin shared post-refresh helper, for example `run_post_refresh_typeset(...)`, responsible for formula re-typeset after DOM replacement.
- Lock one exact runtime contract in code comments/docstring and tests:
  - helper emits one deterministic JS hook call after fragment refresh
  - hook no-ops safely when runtime formula support is absent
  - hook never throws into reviewer UI on missing runtime objects
- Reuse same helper from both:
  - front-side hint panel refresh path
  - answer-side AI analysis refresh path
- Integrate hook into existing DOM fragment refresh flow with smallest diff.
- Keep DOM refresh grain unchanged: panel-only refresh, not full-card rerender.

Verification:
- one shared post-refresh helper exists
- both hint and analysis refresh paths reuse same helper after DOM replacement
- emitted hook call is deterministic and asserted in tests
- helper no-ops safely when runtime formula typesetting support is absent
- no `_showAnswer()` or timed-polling regression is introduced by this change

## Task 4: Expand focused contract proof

Files:
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

Steps:
- Add one narrow helper-level or HTML-level proof for bounded markdown subset:
  - bold renders structurally
  - italic renders structurally
  - inline code renders structurally
  - fenced code block renders structurally
  - unordered list renders structurally
  - ordered list renders structurally
- Add one proof that canonical `\(...\)` and `\[...\]` delimiters survive final render path.
- Add one proof that hostile AI HTML is not treated as trusted source HTML.
- Add one proof that malformed markup falls back safely without exception.
- Add one proof that manual `Hint` remains on old trusted HTML path while AI content is sanitized separately.
- Add one proof that `AI Hint` unavailable/error state uses same bounded rendering contract as ready state.
- Add one proof that `AI Analysis` unavailable/error state uses same bounded rendering contract as ready state.
- Add one proof that both hint and analysis refresh paths invoke same post-refresh typeset helper entrypoint.
- Add one proof that missing runtime support yields safe no-op hook behavior without raising.
- Keep tests assert-based and local; do not add snapshot framework or browser automation.

Verification:
- tests fail on pre-patch AI plain-text contract
- tests pass on post-patch bounded rich-render contract
- tests prove shared helper ownership instead of only surface symptoms
- tests cover ready and non-ready AI body states symmetrically

## Task 5: Update docs to match bounded support

Files:
- `packages/score_answer_anki/README.md`
- `packages/score_answer_anki/Config.md`

Steps:
- Document supported AI formatting subset exactly:
  - paragraphs, bold, italic, inline code, fenced code blocks, ordered/unordered lists, canonical math delimiters
- Document explicit exclusions:
  - raw HTML, links, images, tables, blockquotes, `$...$` / `$$...$$`
- Document that manual `Hint` field behavior is unchanged and remains separate from AI rendering policy.
- Document formula behavior honestly:
  - canonical `\(...\)` / `\[...\]` supported
  - runtime rendering depends on shared post-refresh typeset support
  - fallback preserves delimiters as safe text if unavailable

Verification:
- docs match implemented subset and exclusions
- docs do not overclaim full markdown or arbitrary LaTeX support

## Task 6: Run focused verification and sync add-on

Files:
- `packages/score_answer_anki/scripts/sync_to_anki.ps1`

Steps:
- Run:
  - `python packages/score_answer_anki/test_ai_analysis_ui_contract.py`
  - `python -m py_compile packages/score_answer_anki/__init__.py packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- Sync add-on with:
  - `powershell -ExecutionPolicy Bypass -File packages/score_answer_anki/scripts/sync_to_anki.ps1`
- Manual Anki check on one eligible `_score` card for both front-side hint and answer-side analysis:
  - bold renders as emphasis
  - italic renders as emphasis
  - inline code renders as code
  - list renders with bullets or numbering
  - fenced code block renders as block code
  - canonical math delimiters render as formulas when runtime typeset hook is available
  - same canonical math delimiters remain visible as safe text if typeset hook is unavailable
  - raw AI HTML does not execute or render as trusted HTML
  - ready and unavailable/error AI states remain visually bounded and safe
  - manual `Hint` HTML still behaves exactly as before

Verification:
- focused tests pass
- add-on sync succeeds
- manual check confirms both AI surfaces share same bounded behavior

# Risks / Rollback

- Risk: local markdown subset parser grows messy and drifts
  - rollback: keep one `render_ai_rich_text(...)` entrypoint and simplify subset rather than adding more branches
- Risk: code/list wrapper refactor accidentally changes loading/action layout or CSS
  - rollback: keep loading/action helpers untouched, preserve current class names where possible, and keep CSS adjustment local/minimal
- Risk: post-refresh typeset hook depends on runtime object not always present
  - rollback: make helper strict no-op on absence and keep canonical delimiters visible as text
- Risk: sanitizer/escape order changes visible output unexpectedly
  - rollback: preserve explicit transform order from spec and lock it with helper-level tests

# Final Verification

- [ ] `python packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- [ ] `python -m py_compile packages/score_answer_anki/__init__.py packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- [ ] `powershell -ExecutionPolicy Bypass -File packages/score_answer_anki/scripts/sync_to_anki.ps1`
- [ ] Manual Anki check verifies:
  - [ ] `AI Hint` and `AI Analysis` share same bounded rich formatting behavior
  - [ ] manual `Hint` remains unchanged
  - [ ] canonical math delimiters typeset when runtime hook is available
  - [ ] canonical math delimiters remain visible safe text when runtime hook is unavailable
  - [ ] unavailable/error AI states remain bounded and safe
  - [ ] hostile AI HTML does not execute

# Completion Criteria

- one shared `render_ai_rich_text(...)` helper owns AI rich rendering
- manual `Hint` remains on prior trusted HTML path
- supported AI formatting subset is implemented exactly as specified and no larger
- canonical `\(...\)` / `\[...\]` math support is preserved through render pipeline
- one shared post-refresh formula-typeset helper is reused by hint and analysis refresh flows
- focused proof and manual Anki check confirm bounded rich rendering without trust-boundary drift
