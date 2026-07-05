---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: ai-analysis-refresh-ssot
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
  - packages/score_answer_anki/test_question_variants_contract.py
---

# Goal

Fix answer-side AI refresh SSOT violation in `score_answer_anki` by replacing legacy full-answer rerender refresh with one targeted analysis-panel DOM refresh contract that reuses same low-level DOM fragment patch helper as front-side hint refresh, while preserving existing cache ownership, question-variant invariants, and answer-side analysis content.

Root-cause scope locked for this patch:

- current front-side AI refresh authority is targeted DOM patch
- current answer-side AI refresh authority is `mw.reviewer._showAnswer()` full rerender
- answer-side loading branch also installs timed self-refresh polling
- this split creates avoidable latency, drift, and extra rerender surface

Out of scope:

- provider/network/model latency optimization
- prompt-content changes
- cache-key redesign
- broader answer-side UI redesign

# Key Deliverables

- One answer-side analysis-panel refresh authority in `packages/score_answer_anki/__init__.py` that patches only analysis DOM, not full reviewer answer HTML
- One shared low-level DOM fragment patch helper reused by both front-side hint and answer-side analysis refresh paths
- One stable answer-side analysis-panel wrapper/selector contract reusable by initial render and refresh paths
- One extracted analysis-panel HTML builder so initial render and async refresh reuse same markup path
- Removal of answer-side timed loading polling and normal-path `_showAnswer()` dependency for AI completion refresh
- One focused contract-proof update in `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

# Task Breakdown

## Task 1: Lock answer-side refresh contract and target DOM grain

Files:
- `packages/score_answer_anki/__init__.py`

Steps:
- Define one exact answer-side DOM ownership boundary for AI analysis refresh:
  - analysis panel only
  - not Anki diff block
  - not whole answer side
- Add one stable wrapper id/class around answer-side analysis region, for example one `aqi-analysis-panel-wrap` container.
- Keep wrapper identity deterministic across:
  - loading state
  - ready state
  - unavailable state
  - regenerate transition
- Lock one shared low-level DOM patch primitive, for example `refresh_dom_fragment(selector, html)`, as SSOT for reviewer fragment replacement.
- Keep existing front-side hint refresh semantics unchanged, but route its DOM replacement through same low-level helper.

Verification:
- one selector exists for answer-side AI panel replacement
- one shared low-level DOM patch primitive exists and is reused by both front-side and answer-side refresh paths
- initial render and refresh target same DOM grain
- no ambiguity remains about whether refresh owns panel-only or full-answer HTML

## Task 2: Extract shared answer-side panel render helper

Files:
- `packages/score_answer_anki/__init__.py`

Steps:
- Extract one helper that renders answer-side AI panel body from current analysis state, for example:
  - loading fragment
  - unavailable fragment
  - ready fragment with score/tips/regenerate action
- Route `render_enhanced_comparison(...)` through this helper instead of open-coded answer-side branches.
- Keep score badge, tier styling, tips text, and regenerate action semantics unchanged.
- Reuse existing shared AI UI helpers already introduced for loading/action symmetry; do not duplicate loading/action markup again.

Verification:
- initial answer-side HTML and refresh HTML come from one helper path
- loading/regenerate styling still comes from existing shared AI UI helper path
- score/tips rendering semantics stay unchanged

## Task 3: Replace legacy full rerender refresh with targeted DOM patch

Files:
- `packages/score_answer_anki/__init__.py`

Steps:
- Extract one shared low-level DOM patch helper, for example `refresh_dom_fragment(selector, html)`, and route front-side hint DOM replacement through it.
- Add one answer-side DOM patch wrapper, for example `refresh_ai_analysis_panel_dom(panel_html)`, only as thin feature-specific call-site over shared low-level helper.
- Add one context-aware refresh helper, for example `refresh_current_ai_analysis_panel(request_identity=None)`, that:
  - accepts immutable request identity captured at analysis launch
  - rebuilds panel HTML from current analysis context
  - no-ops when card/context mismatch makes refresh stale
  - patches only answer-side analysis wrapper
- Change `refresh_ai_analysis()` to use targeted panel refresh as normal path.
- Remove timed loading polling script from answer-side loading render.
- Remove normal-path `_showAnswer()` refresh dependency for AI completion and regenerate.
- If a compatibility fallback is kept, restrict it to missing-webview-edge cases only; do not let it remain authoritative.

Verification:
- AI completion refresh does not require `_showAnswer()` in standard reviewer/webview path
- loading render no longer injects timed `setTimeout(...refresh_ai_analysis...)` polling
- regenerate refresh uses same targeted panel refresh path
- front-side hint and answer-side analysis both reuse one shared low-level DOM patch helper

## Task 4: Preserve invariants and guard stale refreshes

Files:
- `packages/score_answer_anki/__init__.py`
- `packages/score_answer_anki/test_question_variants_contract.py`

Steps:
- Ensure targeted answer-side refresh does not mutate active question variant state.
- Extend analysis request identity contract so launch-time context stores at minimum:
  - `card_id`
  - `cache_key`
  - optional `question_text` snapshot only if current code needs it for safer stale-guarding
- Ensure answer-side targeted refresh does not rebuild from stale context when current card id or cache key changed.
- Keep current cache ownership:
  - `ai_analysis_cache`
  - `analysis_results`
  - `is_analyzing`
  - `current_analysis_context`
- Do not add second cache or second refresh-state registry unless needed for stale-guard correctness.
- Callback completion must refresh only when launch-time request identity still matches current reviewer state.

Verification:
- same-exposure visible question stays fixed during loading completion and regenerate
- stale completion for prior key/card no-ops instead of repainting wrong answer-side panel
- no duplicate analysis refresh state store is introduced

## Task 5: Add focused contract proof

Files:
- `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- `packages/score_answer_anki/test_question_variants_contract.py`

Steps:
- Add one test proving answer-side loading render exposes stable analysis-panel wrapper.
- Add one test proving targeted answer-side refresh writes through reviewer `web.eval(...)` path instead of calling `_showAnswer()` in normal path.
- Add one test proving answer-side loading render no longer contains timed polling script.
- Add one test proving regenerate still triggers loading-state refresh through targeted panel path.
- Add one test proving initial answer-side render and targeted refresh both source HTML from same extracted answer-side panel render helper/state mapping.
- Extend existing variant proof only if needed to assert targeted refresh preserves same visible question across completion/regenerate.
- Keep tests narrow and assert-based; no UI snapshot suite.

Verification:
- tests fail on pre-patch split refresh contract
- tests pass on post-patch targeted refresh contract

## Task 6: Run focused verification and sync add-on

Files:
- `packages/score_answer_anki/scripts/sync_to_anki.ps1`

Steps:
- Run:
  - `python packages/score_answer_anki/test_ai_analysis_ui_contract.py`
  - `python packages/score_answer_anki/test_question_variants_contract.py`
  - `python -m py_compile packages/score_answer_anki/__init__.py packages/score_answer_anki/test_ai_analysis_ui_contract.py packages/score_answer_anki/test_question_variants_contract.py`
- Sync add-on with:
  - `powershell -ExecutionPolicy Bypass -File packages/score_answer_anki/scripts/sync_to_anki.ps1`
- Manual Anki check on one eligible `_score` card:
  - answer side shows loading panel immediately
  - answer side updates in place when AI result arrives
  - no whole-answer flicker/rebuild loop while waiting
  - regenerate updates same panel in place
  - visible question variant stays same for same exposure

Verification:
- focused tests pass
- synced add-on matches patched worktree
- manual answer-side behavior shows panel-only refresh, not full-card churn

# Risks / Rollback

- Risk: answer-side DOM patch selector mismatches actual rendered HTML
  - rollback: keep one bounded compatibility fallback, but leave shared low-level DOM patch helper authoritative and test selector presence
- Risk: regenerate/completion callback paints stale panel after card changed
  - rollback: gate targeted refresh on launch-time `card_id` and `cache_key` match
- Risk: extraction accidentally changes score/tips markup
  - rollback: keep helper limited to moving existing markup, not redesigning content
- Risk: removing polling exposes missing callback refresh bug
  - rollback: fix callback-driven refresh path directly; do not restore timed polling as primary behavior

# Final Verification

- [x] `python packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- [x] `python packages/score_answer_anki/test_question_variants_contract.py`
- [x] `python -m py_compile packages/score_answer_anki/__init__.py packages/score_answer_anki/test_ai_analysis_ui_contract.py packages/score_answer_anki/test_question_variants_contract.py`
- [x] `powershell -ExecutionPolicy Bypass -File packages/score_answer_anki/scripts/sync_to_anki.ps1`
- [ ] Manual Anki check verifies:
  - [ ] answer-side loading panel mounts once and stays in place
  - [ ] AI completion swaps only analysis panel content
  - [ ] no timed refresh loop / whole-answer flicker appears while waiting
  - [ ] regenerate refreshes same panel in place
  - [ ] same-exposure visible question variant stays fixed

# Completion Criteria

- answer-side AI refresh has one clear panel-only refresh authority
- normal answer-side AI completion/regenerate path no longer depends on `_showAnswer()`
- answer-side loading no longer uses timed polling refresh
- existing shared AI loading/action helpers remain SSOT for equivalent UI fragments
- one shared low-level DOM fragment patch helper is reused by both front-side and answer-side refresh flows
- targeted refresh preserves question-variant and stale-context invariants
- focused proof and manual Anki check both confirm panel-only refresh semantics without semantic drift

