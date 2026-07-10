---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: sticky-typed-answer-footer-ssot
parent_spec: docs/superpowers/specs/2026-07-09-16-10-sticky-typed-answer-footer-ssot-spec.md
targets:
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\__init__.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_question_variants_contract.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_ai_analysis_ui_contract.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\Config.md
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\scripts\sync_to_anki.ps1
related_features:
  - typed-answer-input
  - front-hint-panel
  - question-variants
  - ai-analysis-ui
related_stages:
  - implementation
---

# Goal

Implement sticky typed-answer footer in `score_answer_anki` with one shared footer owner, one shared reviewer scroll-root helper, one shared bottom-inset contract, and one lifecycle-safe relocation path that works uniformly across all admissible typed-question cases.

This plan stays narrow:

- question-side typed-answer layout only
- no scoring, prompt, cache, or answer-side compare redesign
- existing input and hint builders remain semantic authorities
- footer logic composes existing surfaces instead of replacing them

# Key Deliverables

1. One shared reviewer-footer runtime in `__init__.py`:
   - `#aqi-review-footer`
   - `sync_typed_answer_footer()`
   - `sync_typed_answer_footer_offset()`
   - `get_reviewer_scroll_root()`
2. One shared CSS contract in `REVIEWER_SHARED_CSS` for footer layout and offset reservation.
3. One lifecycle-safe singleton contract for footer shell and resize observer.
4. Focused regression coverage for both input construction paths, repeated sync, hint refresh, card switch, and answer reveal.
5. One executable reviewer-DOM geometry proof for end-of-scroll last-word visibility.
6. One bounded documentation note in `Config.md`.
7. One synced addon copy for live Anki verification.

# Task/Wave Breakdown

## Task 1: Add failing contract tests before runtime changes

- Extend `test_question_variants_contract.py` first.
- Add failing assertions for:
  - footer owner markers in question-side typed render
  - `get_reviewer_scroll_root()` presence in emitted runtime
  - footer offset variable contract
  - singleton footer / singleton observer markers
  - negative answer-side / non-typed behavior
- Extend `test_ai_analysis_ui_contract.py` for:
  - hint refresh keeps targeting one live footer-mounted hint surface
  - repeated refresh does not require new hint selector ownership
- Keep tests bounded to current repo style: direct assertions, no framework add-ons.

### Verification

- Run red first:
  - `py -3 test_question_variants_contract.py`
  - `py -3 test_ai_analysis_ui_contract.py`
- Confirm failures are footer-contract gaps, not unrelated syntax/setup errors.

## Task 2: Add shared footer runtime and scroll-root SSOT

- Update `__init__.py` around current typed-input and reviewer CSS ownership:
  - `REVIEWER_SHARED_CSS` at current CSS owner
  - `_to_textarea_on_question(...)`
  - `inject_multiline_type_input(...)`
- Add one shared runtime block that owns:
  - locating current typed input node
  - locating current `.aqi-front-hint-wrap`
  - ensuring exactly one `#aqi-review-footer`
  - ensuring exactly one active resize observer or equivalent hook
  - resolving one authoritative reviewer scroll root through `get_reviewer_scroll_root()`
- Keep scroll-root fallback isolated inside `get_reviewer_scroll_root()` only.
- Do not duplicate scroll-root logic anywhere else.

### Verification

- Run:
  - `py -3 test_question_variants_contract.py`
- Confirm tests prove:
  - footer owner exists once
  - scroll-root helper exists once
  - non-typed/answer-side paths stay clean

## Task 3: Recompose question-side input and hint into one footer owner

- Keep `_to_textarea_on_question(...)` responsible for input markup only.
- Keep `build_front_hint_panel_html(...)` and `render_front_hint_panel(...)` responsible for hint semantics only.
- Add one post-render sync path that moves live nodes, not cloned nodes, into footer shell.
- Apply same sync path after both input construction modes:
  - server-side textarea replacement path
  - fallback raw-input upgrade path
- Because `refresh_front_hint_panel_dom(...)` is HIGH blast radius, preserve `.aqi-front-hint-wrap` selector contract and route footer relocation around it rather than rewriting refresh semantics.

### Verification

- Run:
  - `py -3 test_question_variants_contract.py`
  - `py -3 test_ai_analysis_ui_contract.py`
- Confirm:
  - both input paths converge to same footer owner
  - hint refresh still updates same live surface
  - repeated sync stays idempotent

## Task 4: Add bottom-inset and geometry-proof path

- Add CSS for:
  - sticky footer root
  - footer content/input/hint sub-layout
  - bottom inset reservation on one authoritative reviewer scroll root only
- Add runtime offset sync using live footer height.
- Re-sync offset after:
  - initial render
  - hint open/close
  - hint refresh
  - footer resize
- Add one executable reviewer-DOM geometry probe that measures:
  - final question node bottom
  - footer top
  - end-of-scroll relation after offset sync
- Keep probe bounded and reusable for live verification; do not build generic tooling.

### Verification

- Run:
  - `py -3 test_question_variants_contract.py`
- Confirm:
  - footer offset contract exists
  - geometry probe hook exists
  - no fixed-padding-only fallback remains

## Task 5: Cover lifecycle transitions and negative surfaces

- Add or extend tests for:
  - repeated sync on unchanged DOM
  - card switch from one typed-question card to another
  - answer reveal after sticky footer was active
  - observer rebind attempt on already-synced DOM
  - non-typed cards do not create footer shell
  - answer-side compare does not inherit footer layout
- Keep lifecycle logic centralized in footer runtime, not spread across unrelated paths.

### Verification

- Run:
  - `py -3 test_question_variants_contract.py`
  - `py -3 test_ai_analysis_ui_contract.py`

## Task 6: Add bounded doc note and syntax/regression pass

- Update `Config.md` with one short note describing:
  - sticky answer footer on typed-question cards
  - hint stays with input
  - long-question tail remains visible above footer
- Keep note descriptive, not design-heavy.
- Run syntax and focused regressions after docs and runtime settle.
- If `scripts/hooks/run_validator.py` exists later, run it; if absent, do not invent replacement validator infrastructure.

### Verification

- Run:
  - `py -3 -m py_compile __init__.py test_question_variants_contract.py test_ai_analysis_ui_contract.py test_custom_openai_contract.py`
  - `py -3 test_question_variants_contract.py`
  - `py -3 test_ai_analysis_ui_contract.py`
  - `py -3 test_custom_openai_contract.py`

## Task 7: Sync deployed addon and live Anki check

- Sync repo copy to deployed addon only after focused regressions pass.
- Verify deployed addon contains footer runtime and geometry probe contract.
- Run one bounded live Anki check with:
  - one short typed-question card
  - one long typed-question card
  - one typed-question card with open hint panel
  - one typed-question card with refreshed AI hint
- Use live check to confirm final word remains visible at end-of-scroll.

### Verification

- Run:
  - `& '.\scripts\sync_to_anki.ps1'`
- Verify deployed addon with `rg` for:
  - `aqi-review-footer`
  - `get_reviewer_scroll_root`
  - `sync_typed_answer_footer_offset`
- Manual live proof:
  - end-of-scroll final word above footer
  - hint open/close updates reserved space
  - answer reveal removes or neutralizes question-side footer behavior

# Verification

- Runtime proof:
  - `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\__init__.py` contains one footer owner, one scroll-root helper, one offset updater, and one singleton observer path.
- Contract proof:
  - `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_question_variants_contract.py` covers both input paths, singleton ownership, offset contract, geometry probe hook, repeated sync, card switch, and negative surfaces.
  - `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_ai_analysis_ui_contract.py` covers hint refresh compatibility and footer-mounted hint behavior.
  - `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_custom_openai_contract.py` remains green to prove prompt/runtime behavior stayed untouched.
- Live proof:
  - deployed addon copy shows sticky footer on typed-question cards and preserves last-word visibility on long questions.

# Rollback / Containment

- If footer relocation breaks hint refresh, keep `.aqi-front-hint-wrap` selector contract unchanged and temporarily disable relocation on refresh path while preserving question-side footer for initial render.
- If scroll-root targeting differs by runtime, keep all fallback logic inside `get_reviewer_scroll_root()` only; do not fork call sites.
- If lifecycle hooks create duplicate shells or observers, keep singleton guards and temporarily disable resize observer in favor of explicit re-sync triggers.
- If geometry proof is hard to automate fully in repo tests, keep automated contract tests plus one live executable probe path; do not add browser/test infrastructure unless current approach cannot prove bug fix.

# Completion Criteria

1. One shared footer runtime owns typed-question layout.
2. One shared reviewer scroll-root helper owns all offset writes and geometry checks.
3. Both input construction paths converge to same footer behavior.
4. Repeated sync, hint refresh, card switch, and answer reveal preserve singleton footer ownership.
5. Long-question end-of-scroll leaves final visible word above footer.
6. Focused tests pass.
7. `Config.md` documents user-visible behavior.
8. Synced deployed addon copy contains final implementation.
