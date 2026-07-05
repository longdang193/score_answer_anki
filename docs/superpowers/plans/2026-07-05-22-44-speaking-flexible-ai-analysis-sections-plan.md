---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: speaking-flexible-ai-analysis-sections
parent_spec: packages/score_answer_anki/docs/superpowers/specs/2026-07-05-22-36-speaking-flexible-ai-analysis-sections-spec.md
targets:
  - packages/score_answer_anki/__init__.py
  - packages/score_answer_anki/test_ai_analysis_ui_contract.py
---

# Speaking Flexible AI Analysis Sections Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `Speaking Flexible` AI Analysis so successful scored responses can render `sample_answers` and `question_variants` as structured body sections, while preserving current fallback behavior for unavailable and unscored states.

**Architecture:** Keep one backward-compatible parse path in `packages/score_answer_anki/__init__.py`, add one small normalization helper for structured analysis extras, then route `AI Analysis` body rendering through one section builder plus one shared section renderer. Reuse existing `render_ai_rich_text(...)`, existing AI UI text lookup, and existing analysis panel shell instead of inventing a new component layer.

**Tech Stack:** Python stdlib, existing add-on HTML string rendering, existing assert-based contract test file, existing sync script.

---

# Goal

Implement approved `Speaking Flexible` structured-analysis contract in smallest safe way:

- prompt asks for `sample_answers` and `question_variants`
- parser accepts those fields without breaking old `score` + `tips` payloads
- one normalizer becomes SSOT for optional structured fields
- one section builder and one section renderer own UI composition
- successful scored payloads may show extra sections
- unavailable or unscored payloads keep current fallback body

# Key Deliverables

- One prompt update inside `PROMPT_PROFILE_SPEAKING_FLEXIBLE`
- One normalization helper for `sample_answers` and `question_variants`
- One `AI Analysis` section builder using `title_key`-based ownership
- One shared section renderer reusing `render_ai_rich_text(...)`
- One focused contract-test expansion in `packages/score_answer_anki/test_ai_analysis_ui_contract.py`

# Task Breakdown

### Task 1: Lock prompt contract with failing tests

**Files:**
- Modify: `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- Modify: `packages/score_answer_anki/__init__.py`

**Step 1: Write failing prompt-contract assertions**

Add assertions near existing `speaking_flexible` prompt checks:

```python
assert "sample_answers" in speaking_prompt
assert "question_variants" in speaking_prompt
assert "2–3" in speaking_prompt or "2-3" in speaking_prompt
assert "build from learner answer" in speaking_prompt.lower()
```

**Step 2: Run test to verify it fails**

Run:

```powershell
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- fail on missing prompt language for new fields

**Step 3: Patch `Speaking Flexible` prompt only**

Inside `PROMPT_PROFILE_SPEAKING_FLEXIBLE` in `packages/score_answer_anki/__init__.py`:

- keep current communicative-adequacy rules
- append explicit structured-output requirements:
  - return `sample_answers`
  - return `question_variants`
  - each list must contain `2–3` items
  - at least one sample answer must be built from learner answer

Keep prompt change local to `Speaking Flexible`; do not broaden other profiles.

**Step 4: Run test to verify prompt assertions pass**

Run:

```powershell
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- prompt assertions pass
- later new assertions may still fail until later tasks land

**Step 5: Commit checkpoint**

```powershell
git -C packages/score_answer_anki add test_ai_analysis_ui_contract.py __init__.py
git -C packages/score_answer_anki commit -m "test: lock speaking flexible prompt contract"
```

Skip commit during live execution if batching changes in one local branch is preferred.

---

### Task 2: Add canonical structured-field normalizer

**Files:**
- Modify: `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- Modify: `packages/score_answer_anki/__init__.py`

**Step 1: Write failing normalization tests**

Add narrow assertions for parser output after `analyze_answer_with_ai(...)`:

```python
addon.call_ai_api = lambda **kwargs: '''{
  "score": 7,
  "tips": "Good answer.",
  "sample_answers": ["A", "B", 3, "   "],
  "question_variants": ["Q1", "Q2", "Q3", "Q4"]
}'''
parsed = addon.analyze_answer_with_ai(...)
assert parsed["sample_answers"] == ["A", "B"]
assert parsed["question_variants"] == ["Q1", "Q2", "Q3"]
```

Add one short-list case:

```python
addon.call_ai_api = lambda **kwargs: '''{
  "score": 7,
  "tips": "Good answer.",
  "sample_answers": ["Only one"],
  "question_variants": []
}'''
parsed = addon.analyze_answer_with_ai(...)
assert parsed["sample_answers"] == []
assert parsed["question_variants"] == []
```

**Step 2: Run test to verify it fails**

Run:

```powershell
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- fail because structured fields are not normalized yet

**Step 3: Add one helper in `__init__.py`**

Add smallest helper near existing AI parse helpers, for example:

```python
def normalize_ai_analysis_string_list(value, min_items=2, max_items=3):
    if not isinstance(value, list):
        return []
    cleaned = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if len(cleaned) > max_items:
        cleaned = cleaned[:max_items]
    if len(cleaned) < min_items:
        return []
    return cleaned
```

Then, after successful `json.loads(...)` and score normalization, add:

```python
result["sample_answers"] = normalize_ai_analysis_string_list(result.get("sample_answers"))
result["question_variants"] = normalize_ai_analysis_string_list(result.get("question_variants"))
```

Do not normalize these fields on unavailable/unscored fallback path.

**Step 4: Run test to verify it passes**

Run:

```powershell
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- structured normalization assertions pass
- later rendering assertions may still fail until next tasks land

**Step 5: Commit checkpoint**

```powershell
git -C packages/score_answer_anki add test_ai_analysis_ui_contract.py __init__.py
git -C packages/score_answer_anki commit -m "feat: normalize structured ai analysis fields"
```

---

### Task 3: Centralize section labels under existing AI UI text SSOT

**Files:**
- Modify: `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- Modify: `packages/score_answer_anki/__init__.py`

**Step 1: Write failing text-ownership assertions**

Add assertions against UI text source:

```python
texts = addon.get_ai_ui_texts("english")
assert texts["ai_analysis_sample_answers"]
assert texts["ai_analysis_question_variants"]
```

Add HTML assertion later expecting labels to come from those keys, not hardcoded literals.

**Step 2: Run test to verify it fails**

Run:

```powershell
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- fail because keys do not exist yet

**Step 3: Patch `AI_UI_TEXTS` only**

Inside existing `AI_UI_TEXTS` source used by `get_ai_ui_texts(...)`, add two new keys for each supported language:

- `ai_analysis_sample_answers`
- `ai_analysis_question_variants`

Smallest safe version:
- add English values first
- for every other supported language, either provide the intended localized value now or use the exact English fallback value consistently
- do not guess ad hoc per-language translations during implementation

Do not add these labels to `LANGUAGES` or any new dictionary.

**Step 4: Run test to verify keys exist**

Run:

```powershell
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- new UI-text assertions pass

**Step 5: Commit checkpoint**

```powershell
git -C packages/score_answer_anki add test_ai_analysis_ui_contract.py __init__.py
git -C packages/score_answer_anki commit -m "feat: add ai analysis section labels"
```

---

### Task 4: Add shared analysis section builder and renderer

**Files:**
- Modify: `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- Modify: `packages/score_answer_anki/__init__.py`

**Step 1: Write failing render-contract assertions**

Add one successful structured payload directly into cache:

```python
addon.analysis_results[cache_key] = {
    "scored": True,
    "score": 7,
    "tips": "Good base answer.",
    "sample_answers": ["I went to see family.", "I spent time with my family and relaxed at home."],
    "question_variants": ["What did you do over the weekend?", "How did you spend your weekend?"],
}
rendered = addon.build_ai_analysis_panel_html(cache_key, "english")
assert "Good base answer." in rendered
assert addon.get_ai_ui_texts("english")["ai_analysis_sample_answers"] in rendered
assert addon.get_ai_ui_texts("english")["ai_analysis_question_variants"] in rendered
assert "I went to see family." in rendered
assert "What did you do over the weekend?" in rendered
assert rendered.count("AI Analysis") == 1
```

Add one formula-in-list-item case:

```python
assert r"\(x^2 = 4\)" in rendered
```

Add one end-to-end structured path assertion from raw AI JSON to final HTML:

```python
addon.call_ai_api = lambda **kwargs: '{\n  "score": 7,\n  "tips": "Good base answer.",\n  "sample_answers": ["I went to see family.", "I spent time with my family and relaxed at home."],\n  "question_variants": ["What did you do over the weekend?", "How did you spend your weekend?"]\n}'
parsed = addon.analyze_answer_with_ai("How was your weekend?", "I visited my grandmother.", ["I visited my grandmother."], "I went to see family.")
addon.analysis_results[cache_key] = parsed
rendered = addon.build_ai_analysis_panel_html(cache_key, "english")
assert addon.get_ai_ui_texts("english")["ai_analysis_sample_answers"] in rendered
assert "I went to see family." in rendered
```

**Step 2: Run test to verify it fails**

Run:

```powershell
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- fail because panel only renders `tips`

**Step 3: Add one section builder helper**

In `packages/score_answer_anki/__init__.py`, add smallest helper, for example:

```python
def build_ai_analysis_sections(ai_analysis: dict) -> list[dict]:
    return [
        {"key": "tips", "title_key": None, "kind": "rich_text", "value": ai_analysis.get("tips", "")},
        {"key": "sample_answers", "title_key": "ai_analysis_sample_answers", "kind": "string_list", "value": ai_analysis.get("sample_answers", [])},
        {"key": "question_variants", "title_key": "ai_analysis_question_variants", "kind": "string_list", "value": ai_analysis.get("question_variants", [])},
    ]
```

Then add one renderer helper, for example:

```python
def render_ai_analysis_section(section: dict, texts: dict) -> str:
    ...
```

Rules:
- `tips` renders untitled through `render_ai_rich_text(...)`
- visible section labels are resolved in renderer from `title_key` via existing `get_ai_ui_texts(...)` output
- list sections render only when list has items
- each item uses `render_ai_rich_text(...)`
- no duplicate `AI Analysis` body title
- no hardcoded English label literals inside section-builder path

**Step 4: Patch `build_ai_analysis_panel_html(...)` only**

Replace direct `rendered_tips` body insertion with:
- call `build_ai_analysis_sections(ai_analysis)`
- filter omitted sections
- render each section with `render_ai_analysis_section(section, ai_texts)`
- join rendered section HTML into panel body

Keep current shell intact:
- score badge
- regenerate button
- panel card classes
- loading branch

**Step 5: Run test to verify it passes**

Run:

```powershell
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- section labels and items appear
- only one `AI Analysis` title remains
- formulas inside list items survive same rich render path

**Step 6: Commit checkpoint**

```powershell
git -C packages/score_answer_anki add test_ai_analysis_ui_contract.py __init__.py
git -C packages/score_answer_anki commit -m "feat: render structured ai analysis sections"
```

---

### Task 5: Preserve unavailable and unscored semantics with failing tests first

**Files:**
- Modify: `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- Modify: `packages/score_answer_anki/__init__.py`

**Step 1: Write failing fallback-state assertions**

Add one unavailable payload case:

```python
addon.analysis_results[cache_key] = addon.make_analysis_unavailable("AI disabled", "english")
rendered = addon.build_ai_analysis_panel_html(cache_key, "english")
assert addon.get_ai_ui_texts("english").get("ai_analysis_sample_answers", "Sample Answers") not in rendered
assert addon.get_ai_ui_texts("english").get("ai_analysis_question_variants", "Alternative Questions") not in rendered
```

Add one unscored payload case:

```python
addon.analysis_results[cache_key] = {"scored": False, "score": None, "tips": "Unavailable."}
rendered = addon.build_ai_analysis_panel_html(cache_key, "english")
assert "N/A" in rendered
assert addon.get_ai_ui_texts("english")["ai_analysis_sample_answers"] not in rendered
```

**Step 2: Run test to verify it fails if sections leak**

Run:

```powershell
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- fail if section builder runs for degraded states

**Step 3: Gate section-builder path**

Inside `build_ai_analysis_panel_html(...)`:
- keep current `is_scored` detection
- only build extra sections when payload is successful scored analysis
- for unavailable/unscored states, keep existing single-body fallback path using `tips` only

Do not fork section logic in multiple places. One guard before section-builder call is enough.

**Step 4: Run test to verify fallback behavior passes**

Run:

```powershell
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- no extra sections on unavailable or unscored payloads
- current fallback body still renders

**Step 5: Commit checkpoint**

```powershell
git -C packages/score_answer_anki add test_ai_analysis_ui_contract.py __init__.py
git -C packages/score_answer_anki commit -m "fix: preserve fallback ai analysis semantics"
```

---

### Task 6: Final verification and sync

**Files:**
- Modify: `packages/score_answer_anki/__init__.py`
- Modify: `packages/score_answer_anki/test_ai_analysis_ui_contract.py`
- Run: `packages/score_answer_anki/scripts/sync_to_anki.ps1`

**Step 1: Run focused contract test**

Run:

```powershell
py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- all assertions pass

**Step 2: Run syntax proof**

Run:

```powershell
py -3 -m py_compile packages\score_answer_anki\__init__.py packages\score_answer_anki\test_ai_analysis_ui_contract.py
```

Expected:
- no output
- exit code `0`

**Step 3: Sync add-on into Anki**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File packages\score_answer_anki\scripts\sync_to_anki.ps1
```

Expected:
- sync success message with target add-on path

**Step 4: Manual Anki check**

Open one `_score` card using `Speaking Flexible` prompt profile and confirm:

- analysis panel title appears once
- score badge still renders
- feedback body still renders through current rich-text path
- `Sample Answers` section appears only when AI returns cleaned 2–3 items
- `Alternative Questions` section appears only when AI returns cleaned 2–3 items
- formula text inside list items typesets same way as formula text in `tips`
- unavailable or unscored responses do not show extra sections

**Step 5: Final commit**

```powershell
git -C packages/score_answer_anki add __init__.py test_ai_analysis_ui_contract.py
git -C packages/score_answer_anki commit -m "feat: add structured speaking analysis sections"
```

Skip if commits were already created task-by-task and squashing is preferred later.

---

# Risks / Rollback

- Risk: list cleanup logic drifts from render rules
  - rollback: keep one `normalize_ai_analysis_string_list(...)` helper as sole cardinality owner
- Risk: section labels drift from current localization path
  - rollback: keep new labels inside existing AI UI text lookup only
- Risk: unavailable/unscored payload accidentally enters structured path
  - rollback: gate section builder behind one existing `is_scored` check
- Risk: plan accidentally broadens to hint UI
  - rollback: keep all rendering edits scoped to `build_ai_analysis_panel_html(...)` and `Speaking Flexible` prompt block only

# Final Verification

- [ ] `py -3 packages\score_answer_anki\test_ai_analysis_ui_contract.py`
- [ ] `py -3 -m py_compile packages\score_answer_anki\__init__.py packages\score_answer_anki\test_ai_analysis_ui_contract.py`
- [ ] `powershell -ExecutionPolicy Bypass -File packages\score_answer_anki\scripts\sync_to_anki.ps1`
- [ ] Manual Anki check verifies:
  - [ ] one `AI Analysis` header only
  - [ ] `Sample Answers` label comes from existing UI text path
  - [ ] `Alternative Questions` label comes from existing UI text path
  - [ ] optional sections show only for cleaned 2–3 item lists
  - [ ] unavailable/unscored states keep current fallback behavior
  - [ ] math inside list items renders same way as math inside `tips`

# Completion Criteria

- `Speaking Flexible` prompt requests structured extras with explicit cardinality rules
- successful scored analysis payloads normalize `sample_answers` and `question_variants` through one SSOT helper
- `AI Analysis` panel renders extra sections through one section builder and one renderer
- section labels reuse current AI UI text lookup
- unavailable and unscored analysis states remain unchanged
- focused tests and syntax checks pass

