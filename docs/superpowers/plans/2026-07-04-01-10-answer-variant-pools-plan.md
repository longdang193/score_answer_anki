---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: answer-variant-pools
parent_spec: docs/superpowers/specs/2026-07-04-00-56-answer-variant-pools-spec.md
targets:
  - __init__.py
  - README.md
  - Config.md
  - test_question_variants_contract.py
  - test_ai_analysis_ui_contract.py
---

# Goal

Implement field-based question and answer variant pools for typed-answer cards using `Front`, `Front_variants`, `Back`, and `Back_variants`, while keeping native Anki compare and scheduling unchanged and making AI analysis question-aware and accepted-answer-pool-aware.

# Key Deliverables

- One shared parser for `Front_variants` and `Back_variants` using `;;`
- One shared visible-question pool builder using `Front` + `Front_variants`
- One shared accepted-answer pool builder using `Back` + `Back_variants`
- One deterministic local compatibility gate with outputs `compatible | incompatible | unsupported`
- One shared active-question exposure state keyed by card and pool identity
- One bounded mismatch path that suppresses AI scoring for incompatible canonical `Front`
- One explicit AI-input contract that includes chosen question, canonical `Back`, accepted-answer pool list, and user answer
- Docs updated for field roles and native-vs-advisory correctness boundary
- Runnable proof artifacts for parsing, gating, exposure-state stability, mismatch handling, and AI-input construction

# Task Breakdown

## Task 1: Build question and answer pool helpers

Files:
- `__init__.py`
- `test_question_variants_contract.py`

Steps:
- Add one helper to read canonical `Front`, `Front_variants`, `Back`, and `Back_variants` from current note/card
- Add one shared parser for variant fields that splits on literal `;;`, trims outer whitespace, drops empties, and preserves punctuation/case
- Add one visible-question pool builder that returns ordered deduped pool from `Front` + `Front_variants`
- Add one accepted-answer pool builder that returns canonical `Back` plus ordered deduped accepted-answer list from `Back` + `Back_variants`
- Keep normalization minimal and identical across all call sites

Verification:
- Visible-question pool helper returns canonical `Front` first plus parsed `Front_variants`
- Accepted-answer pool helper returns canonical `Back` first plus parsed `Back_variants`
- Dedupe and trim behavior are stable and deterministic

## Task 2: Add deterministic compatibility gate

Files:
- `__init__.py`
- `test_question_variants_contract.py`

Steps:
- Add one local deterministic gate helper with outputs `compatible | incompatible | unsupported`
- Limit V1 gate to bounded obvious-contradiction checks the code can prove locally
- Exclude variants marked `incompatible` from visible candidate pool
- Keep variants marked `unsupported` eligible in V1 rather than falsely rejecting them
- If canonical `Front` is marked `incompatible`, mark card invalid for add-on scoring path

Verification:
- Arithmetic contradiction cases such as `221 = 13 * ?` vs canonical `Back = 221` are marked `incompatible`
- Equivalent arithmetic paraphrases such as `13 * 17 = ?` and `17 * 13 = ?` remain eligible
- Non-bounded language-style examples return `unsupported`, not `incompatible`

## Task 3: Update exposure state and visible question rendering

Files:
- `__init__.py`
- `test_question_variants_contract.py`

Steps:
- Replace current front-only variant state with one shared exposure-state object storing at least `card_id`, `question_pool_hash`, `answer_pool_hash`, and `chosen_variant`
- Choose one eligible question variant exactly once per exposure
- Reset exposure state when card identity or either pool identity changes
- Render chosen question prominently and other eligible variants as smaller secondary choices
- Ensure answer-side render and regenerate-analysis path reuse same chosen question without reshuffle

Verification:
- Same exposure keeps same chosen question through answer reveal and regenerate
- New exposure may reseed choice without reusing stale state
- Incompatible variants never appear in rendered secondary choice list

## Task 4: Align AI analysis with accepted-answer pool and mismatch path

Files:
- `__init__.py`
- `test_question_variants_contract.py`
- `test_ai_analysis_ui_contract.py`

Steps:
- Replace ad hoc AI prompt assembly with one helper that builds explicit contract payload/text from:
  - chosen visible question
  - canonical `Back`
  - accepted-answer pool list
  - user answer
- Run pre-analysis mismatch guard before scoring
- If canonical `Front` or chosen question is marked `incompatible`, return bounded `variant_mismatch` result with `score: null`
- Keep native Anki compare display untouched even when AI advisory logic accepts alternate answers from `Back_variants`
- Make AI panel wording clearly advisory when mismatch or alternate-answer acceptance occurs

Verification:
- Prompt/input builder includes full accepted-answer pool explicitly
- Mismatch path returns non-scored bounded result instead of fake low score
- Advisory path can reference accepted-answer pool without changing scheduler/native compare behavior

## Task 5: Update docs and proof artifacts

Files:
- `README.md`
- `Config.md`
- `test_question_variants_contract.py`
- `test_ai_analysis_ui_contract.py`

Steps:
- Document roles of `Front`, `Front_variants`, `Back`, and `Back_variants`
- Document one-concept-per-card invariant and no positional mapping rule
- Document native Anki compare vs add-on advisory boundary
- Add assert-based tests covering:
  - question-pool parsing
  - answer-pool parsing
  - deterministic compatibility filtering
  - exposure-state stability
  - mismatch result contract
  - AI-input contract shape

Verification:
- `python test_question_variants_contract.py` exits cleanly
- `python test_ai_analysis_ui_contract.py` exits cleanly
- Docs match actual implementation boundaries and field semantics

# Risks / Rollback

- Risk: deterministic gate over-rejects non-math cards
  - rollback: keep only clearly incompatible variants excluded; leave uncertain cases as `unsupported`
- Risk: accepted-answer pool logic conflicts with native compare expectations
  - rollback: keep native compare display untouched and restrict add-on changes to advisory messaging only
- Risk: state drift across question/answer/regenerate paths
  - rollback: centralize question choice in one exposure-state helper and test all call paths against it
- Risk: prompt contract drifts from local acceptance logic
  - rollback: one shared answer-pool helper feeds both local logic and AI-input builder

# Final Verification

- `python test_question_variants_contract.py`
- `python test_ai_analysis_ui_contract.py`
- `python test_custom_openai_contract.py`
- `python -m py_compile __init__.py test_question_variants_contract.py test_ai_analysis_ui_contract.py test_custom_openai_contract.py`
- Manual Anki check with sample note using:
  - `Front`
  - `Front_variants`
  - `Back`
  - `Back_variants`
- Manual Anki check confirms:
  - only eligible question variants appear
  - chosen question remains stable for one exposure
  - incompatible canonical question yields bounded mismatch instead of fake score
  - native compare UI still behaves normally

# Completion Criteria

- Field-based variant pools work end to end for supported V1 cards
- Visible-question pool and accepted-answer pool each have one SSOT helper
- Deterministic gate behavior is explicit, bounded, and test-covered
- Native compare vs advisory AI boundary remains intact
- Proof scripts and syntax compile pass
- Docs match actual field-role semantics and limitations
