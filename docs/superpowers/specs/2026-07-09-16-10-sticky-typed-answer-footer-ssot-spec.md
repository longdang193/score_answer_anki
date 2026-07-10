---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: sticky-typed-answer-footer-ssot
parent_workstream: none
targets:
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\__init__.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_question_variants_contract.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_ai_analysis_ui_contract.py
  - C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\Config.md
related_features:
  - typed-answer-input
  - front-hint-panel
  - question-variants
  - ai-analysis-ui
related_stages:
  - design
---

# Goal

Dock the typed-answer input and front-hint surface into one sticky reviewer footer with one source of truth for layout ownership, one symmetric relocation path across all admissible typed-question cases, and one explicit scroll-inset contract so the final visible word of the question remains above the footer when the reviewer is scrolled to the end.

Current root bug:

- typed-answer input is rendered inline with question content, so long questions force user scroll ping-pong between question tail and answer box
- hint UI is rendered as separate appended block, so input and hint do not share one layout owner
- current render path has two admissible input construction modes:
  - server-side `#typeans` replacement inside `_to_textarea_on_question(...)`
  - fallback client-side DOM swap when raw input survives
- without one shared footer owner, any sticky fix risks solving one render path but not the other
- without one explicit bottom inset, sticky footer can cover the tail of the question, including the last word at end-of-scroll

This spec defines one reviewer-footer contract for typed-question cards only. Equivalent typed-question states must use the same footer ownership and same bottom-inset rule regardless of question variants, hint state, or input construction path.

# Key Deliverables

1. One explicit sticky-footer owner in `__init__.py` for typed-question review layout.
2. One shared DOM synchronization helper that relocates existing input and hint surfaces into that footer.
3. One shared reviewer-scroll-root contract that owns all bottom-inset writes and end-of-scroll checks.
4. One shared bottom-inset contract that keeps question tail fully visible above footer height.
5. One symmetric CSS contract for sticky footer, question bottom spacing, and footer child layout.
6. Focused regression tests proving all admissible typed-question cases follow the same footer behavior.
7. One executable geometry proof for end-of-scroll last-word visibility.
8. Small user-facing documentation note describing sticky footer behavior and question-tail visibility guarantee.

# Task/Wave Breakdown

## Wave 1: Define one footer owner and bounded scope

Required change:

- define one authoritative reviewer footer contract, preferred shape:
  - markup anchor: `#aqi-review-footer`
  - sync helper: `sync_typed_answer_footer()`
  - bottom-inset updater: `sync_typed_answer_footer_offset()`
  - scroll-root helper: `get_reviewer_scroll_root()`
- footer owner must exist only for typed-question front-side render surfaces
- non-typed cards and answer-side compare surfaces must not render or retain footer shell

Required footer structure:

- one root shell: `#aqi-review-footer`
- one content wrapper: `.aqi-review-footer__content`
- existing `.aqi-type-input-wrap` moves into footer unchanged as input block
- existing `.aqi-front-hint-wrap` moves into footer unchanged as hint block
- footer must reuse existing input and hint markup instead of cloning or rebuilding hint semantics

Required scope boundary:

- in scope:
  - question-side typed-answer input
  - front-hint toggle/panel on typed-question cards
  - question-end visibility above sticky footer
  - focused tests and bounded doc note
- out of scope:
  - answer-side compare layout redesign
  - AI hint semantics
  - scoring semantics
  - prompt/cache semantics
  - external CSS files
  - config toggles for sticky mode

## Wave 2: Symmetric relocation contract across all admissible typed-question cases

Required change:

- one relocation helper must own footer assembly for every admissible typed-question case
- helper must operate after either input render path succeeds:
  - server-side replacement path from `_to_textarea_on_question(...)`
  - fallback swap path when raw `input#typeans` survives to client-side JS
- helper must also pick up hint markup after `render_front_hint_panel(...)` appends it
- helper must own lifecycle convergence on initial render, repeated sync, hint refresh, card switch, and answer reveal

Admissible typed-question cases that must be uniform:

1. `Front_variants` empty
2. `Front_variants` non-empty
3. manual hint absent
4. manual hint present
5. AI hint idle
6. AI hint loading
7. AI hint ready
8. AI hint unavailable
9. server-side textarea replacement path active
10. fallback client-side input swap path active
11. question short enough that page does not scroll
12. question long enough that page scrolls past one viewport
13. initial question render on fresh card
14. repeated footer sync on unchanged DOM
15. hint panel refresh or replacement after `refresh_front_hint_panel_dom(...)`
16. card switch from one typed-question card to another
17. answer reveal after question-side sticky footer was active
18. observer or resize hook rebind attempt on already-synced DOM

Required symmetry rules:

- no case-specific sticky logic keyed by variant presence, hint state, or AI status
- no second helper may assemble a competing footer shell
- no caller may style input and hint as separate bottom-docked systems
- relocation must move existing live nodes, not duplicate them
- footer sync may be called many times and must remain idempotent
- one reviewer DOM may contain at most one `#aqi-review-footer`
- one reviewer DOM may contain at most one active footer-resize observer or equivalent live resize hook
- card switch and answer reveal paths must disconnect or invalidate stale footer observers before new sync work begins

Preferred lazy rule:

- keep `build_front_hint_panel_html(...)` semantics unchanged
- keep `_to_textarea_on_question(...)` responsible for input markup only
- use one shared post-render DOM sync to compose final footer from those existing parts

## Wave 3: Question-tail visibility and scroll-inset contract

Required change:

- sticky footer must publish one explicit footer-height offset, preferred shape:
  - CSS custom property: `--aqi-review-footer-offset`
- one shared helper must resolve one authoritative reviewer scroll root, preferred shape:
  - `get_reviewer_scroll_root()`
- all bottom-inset writes and end-of-scroll geometry checks must target only that resolved root
- if runtime compatibility requires fallback between `document.scrollingElement`, `document.documentElement`, and `document.body`, that fallback must live inside `get_reviewer_scroll_root()` only
- resolved reviewer scroll root must consume footer offset as bottom padding so the last question word remains visible when scrolled to the end

Required visibility rules:

- end-of-scroll must show the final rendered word of question content above footer chrome
- footer expansion from opening hint panel must increase bottom inset automatically
- footer contraction from closing hint panel must decrease bottom inset automatically
- offset must respond to textarea height and hint-panel height changes, not just initial render

Allowed implementation shapes:

- `ResizeObserver` on footer root, or
- bounded mutation/update hook reused from existing reviewer sync path

Disallowed behaviors:

- hardcoded fixed bottom padding that ignores open hint height
- duplicating scroll-root selection logic in more than one helper or call site
- separate padding formulas for variant vs non-variant cards
- relying on user zoom/window size assumptions
- allowing footer to overlap question tail at end-of-scroll in any admissible case

Required spacing contract:

- sticky footer may have local safe padding and background
- scrollable question surface must reserve at least:
  - footer live height
  - one bounded breathing-space constant so tail text is not visually glued to footer edge

## Wave 4: CSS SSOT for footer and question inset

Required change:

- all reviewer CSS for sticky footer and bottom inset must live under one existing CSS owner in `REVIEWER_SHARED_CSS`
- footer selectors must be grouped with existing typed-input and hint selectors rather than introduced as scattered ad hoc blocks

Required selector contract:

- root sticky selector: `#aqi-review-footer`
- question bottom inset selector: one authoritative reviewer scroll-root selector only
- child layout selectors:
  - `.aqi-review-footer__content`
  - `.aqi-review-footer__input`
  - `.aqi-review-footer__hint`

Rules:

- only one selector family may control sticky footer positioning
- only one selector family may control bottom inset reservation
- footer background must be opaque enough that question text never visually bleeds through under footer
- existing `.aqi-type-input-wrap` and `.aqi-front-hint-wrap` keep semantic ownership of their internal controls

## Wave 5: Executable contract proof

Required failing tests before implementation:

- one contract test proving typed-question render includes sticky-footer hooks or sync markers
- one contract test proving injected CSS contains footer selector and bottom-offset contract
- one contract test proving bottom inset is tied to footer offset variable, not fixed magic padding only
- one contract test proving non-typed or answer-side render does not inject sticky footer markup
- one executable reviewer-DOM geometry proof proving end-of-scroll final-question-node bottom stays above footer top after offset sync

Required passing tests after implementation:

- typed-question markup always converges to one footer owner
- hint refresh path still updates same footer-mounted hint surface
- long-question contract preserves visible tail space above footer

# Design Decisions

1. Footer layout ownership lives in one post-render sync helper.
   - Reason: input and hint already originate in different bounded render paths; one compositor is smallest SSOT.
2. Existing input and hint HTML stay authoritative for their own semantics.
   - Reason: lower blast radius than rewriting hint and input generation into one monolith.
3. Footer moves live nodes instead of cloning markup.
   - Reason: avoids stale duplicate controls, duplicate IDs, and refresh drift.
4. Bottom visibility is solved with live footer-height inset, not guessed static spacing.
   - Reason: hint open/close and viewport changes alter real footer height.
5. Sticky behavior applies only to admissible typed-question cards.
   - Reason: no need to perturb answer-side compare or non-typed review flows.
6. CSS remains embedded in `__init__.py`.
   - Reason: smallest diff; existing reviewer styling already lives there.

# Acceptance Criteria

1. On any typed-question card, answer input stays visible at bottom while question content scrolls independently above it.
2. Hint toggle and hint panel live in same sticky footer system as answer input.
3. `Front_variants` presence or absence does not change footer behavior.
4. Manual hint presence or absence does not change footer ownership or bottom-inset contract.
5. AI hint states `idle`, `loading`, `ready`, and `unavailable` all remain functional inside same footer-mounted hint surface.
6. Both input render paths converge to same final footer owner.
7. Scrolling to end of long question leaves final visible word above footer, not hidden behind it.
8. Opening and closing hint panel updates reserved bottom space automatically.
9. Non-typed question cards do not render sticky footer.
10. Answer-side compare surfaces do not inherit question-side sticky footer layout.
11. Existing hint refresh DOM updates still target one live hint surface after relocation.
12. Focused tests prove footer SSOT and question-tail visibility contract.

# Non-Goals

- no answer-side compare layout redesign
- no AI hint generation changes
- no scoring or cache-key changes
- no config setting to disable sticky footer in this phase
- no editor-like toolbar framework
- no module split of `__init__.py`
- no full reviewer page virtualization or custom scroll container framework

# Invariants

1. One sticky footer owner for typed-question review layout.
2. One bottom-inset authority derived from live footer height.
3. One authoritative reviewer scroll root owns all offset writes and geometry checks.
4. Equivalent typed-question states must share same relocation and inset logic.
5. Input and hint semantics remain owned by existing builders; footer only composes layout.
6. Footer sync is idempotent and safe on repeated refreshes.
7. Reviewer DOM has at most one active footer shell and one active resize observer for that shell.
8. Last-word visibility at end-of-scroll is a hard contract, not best effort.

# Risks and Mitigations

## Risk: hint refresh path breaks after footer relocation

- Mitigation: move live `.aqi-front-hint-wrap` node, keep its selector stable, and add focused refresh-path tests.

## Risk: one render path docks correctly while other path stays inline

- Mitigation: one shared sync helper must run after both server-side and fallback input paths; tests cover both.

## Risk: footer height changes still cover question tail

- Mitigation: derive inset from live measured footer height and re-sync on hint open/close and footer resize.

## Risk: implementation writes offset to wrong scroll root

- Mitigation: one explicit `get_reviewer_scroll_root()` helper owns runtime fallback and all inset writes and geometry checks reuse it.

## Risk: repeated refreshes accumulate duplicate footer shells or observers

- Mitigation: require singleton footer/observer invariants and add lifecycle-focused repeated-sync tests.

## Risk: sticky footer leaks onto answer-side compare surface

- Mitigation: gate footer creation on typed-question front-side capability only and assert negative answer-side tests.

## Risk: CSS ownership drifts into scattered selectors

- Mitigation: keep footer positioning and inset selectors in `REVIEWER_SHARED_CSS` only.

## Risk: high-blast-radius hint builder edit creates avoidable regressions

- Mitigation: keep hint HTML contract stable; relocate DOM after render instead of rewriting hint-generation semantics.

# Validation Plan

- proof target: one explicit sticky-footer owner exists
  - method: inspection
  - evidence: one authoritative helper and one authoritative root selector in `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\__init__.py`

- proof target: one authoritative reviewer scroll root owns all inset writes
  - method: inspection plus test
  - evidence: one `get_reviewer_scroll_root()` helper in `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\__init__.py` and focused assertions in `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_question_variants_contract.py`

- proof target: both typed-input construction paths converge to same footer behavior
  - method: test
  - evidence: focused assertions in `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_question_variants_contract.py`

- proof target: repeated sync, hint refresh, card switch, and answer reveal preserve singleton footer ownership
  - method: test
  - evidence: focused assertions in `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_question_variants_contract.py` and `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_ai_analysis_ui_contract.py`

- proof target: hint states remain mounted inside same footer system
  - method: test
  - evidence: focused assertions in `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_ai_analysis_ui_contract.py`

- proof target: bottom inset is derived from footer offset contract
  - method: test
  - evidence: CSS/JS contract assertions in `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_question_variants_contract.py`

- proof target: end-of-scroll last-word visibility is encoded as layout contract
  - method: executable geometry test plus manual run
  - evidence: one reviewer-DOM measurement check proving final-question-node bottom is at or above footer top after end-of-scroll sync, plus one manual long-question reviewer check recorded in implementation follow-through

- proof target: non-typed and answer-side surfaces stay unaffected
  - method: test
  - evidence: negative assertions in `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_question_variants_contract.py` and `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\test_ai_analysis_ui_contract.py`

- proof target: package documentation notes sticky-footer behavior
  - method: inspection
  - evidence: one bounded note in `C:\Users\HOANG PHI LONG DANG\repos\anki_scrips\packages\score_answer_anki\Config.md`

# Completion Criteria

1. Spec approved.
2. Follow-on implementation plan can reference one footer owner and one offset contract with no unresolved UI branch.
3. All admissible typed-question states have explicit sticky-footer semantics.
4. Long-question tail visibility is defined as mandatory behavior.
5. Footer composition reuses existing input and hint semantics instead of inventing parallel renderers.
6. Focused tests and bounded doc update are identified as required proof, not optional cleanup.

