import importlib.util
import pathlib
import sys
import types


class HookList(list):
    pass


class DummySignal:
    def connect(self, fn):
        self.fn = fn


class DummyAction:
    def __init__(self):
        self.triggered = DummySignal()


class DummyMenu:
    def addAction(self, *_args, **_kwargs):
        return DummyAction()


class DummyAddonManager:
    def __init__(self):
        self.config = {}

    def getConfig(self, _name):
        return self.config

    def writeConfig(self, _name, config):
        self.config = dict(config)


class DummyNote(dict):
    def __init__(self, model_name="card_1_score", template_name=None):
        if template_name is None:
            template_name = model_name
        super().__init__({
            "Front": "13 * 17 = ?",
            "Front_variants": "17 * 13 = ?",
            "Back": "221",
            "Back_variants": "two hundred twenty-one;;221.0",
        })
        self._model = {"name": model_name, "tmpls": [{"name": template_name}]}

    def model(self):
        return self._model


class DummyCard:
    def __init__(self, model_name="card_1_score", template_name=None):
        self.id = 1
        self.ord = 0
        self._note = DummyNote(model_name=model_name, template_name=template_name)

    def note(self):
        return self._note

    def question(self):
        return "13 * 17 = ? [[type:Back]]"


class DummyReviewer:
    def __init__(self):
        self.card = DummyCard()
        self.show_answer_calls = 0

    def _showAnswer(self):
        self.show_answer_calls += 1
        return None


class DummyMW:
    def __init__(self):
        self.addonManager = DummyAddonManager()
        self.form = types.SimpleNamespace(menuTools=DummyMenu())
        self.reviewer = DummyReviewer()
        self.pm = None
        self.taskman = types.SimpleNamespace(run_in_background=lambda task, on_done: None)


class DummyWebView:
    def __init__(self):
        self.commands = []

    def eval(self, command):
        self.commands.append(command)


class DummyFuture:
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error

    def result(self):
        if self._error is not None:
            raise self._error
        return self._result


def install_sync_background(mw):
    def run_in_background(task, on_done):
        try:
            result = task()
            future = DummyFuture(result=result)
        except Exception as exc:
            future = DummyFuture(error=exc)
        on_done(future)
    mw.taskman = types.SimpleNamespace(run_in_background=run_in_background)


def load_addon_module():
    fake_gui_hooks = types.SimpleNamespace(
        webview_will_set_content=HookList(),
        webview_did_receive_js_message=HookList(),
        card_will_show=HookList(),
        reviewer_will_compare_answer=HookList(),
        reviewer_will_render_compared_answer=HookList(),
    )
    fake_aqt = types.ModuleType("aqt")
    fake_aqt.gui_hooks = fake_gui_hooks
    fake_aqt.mw = DummyMW()
    fake_aqt.mw.reviewer.web = DummyWebView()

    fake_utils = types.ModuleType("aqt.utils")
    fake_utils.showInfo = lambda *args, **kwargs: None
    fake_utils.showWarning = lambda *args, **kwargs: None

    sys.modules["aqt"] = fake_aqt
    sys.modules["aqt.utils"] = fake_utils

    spec = importlib.util.spec_from_file_location(
        "addon_under_test", pathlib.Path(__file__).with_name("__init__.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, fake_aqt.mw


def read_addon_source() -> str:
    return pathlib.Path(__file__).with_name("__init__.py").read_text(encoding="utf-8")


def main():
    addon, mw = load_addon_module()
    source = read_addon_source()

    assert "def build_ai_loading_fragment(" in source
    assert source.count("build_ai_loading_fragment(") >= 3
    assert "def build_ai_action_button(" in source
    assert source.count("build_ai_action_button(") >= 3
    assert "def refresh_dom_fragment(" in source
    assert source.count("refresh_dom_fragment(") >= 3
    assert "def build_ai_analysis_panel_html(" in source
    assert source.count("build_ai_analysis_panel_html(") >= 2

    merged_legacy = addon.merge_config_with_defaults({"use_custom_prompt": True})
    assert merged_legacy["prompt_profile"] == "custom"
    assert merged_legacy["custom_hint_prompt_template"] == ""
    assert addon.resolve_prompt_profile({"prompt_profile": "default"}) == "default"
    assert addon.resolve_prompt_profile(
        {
            "prompt_profile": "default",
            "template_prompt_profile_overrides": {"card_1_score": "strict_stem"},
        }
    ) == "default"

    addon.save_config(
        {
            "prompt_profile": "strict_stem",
            "template_prompt_profile_overrides": {"card_1_score": "strict_stem"},
            "use_custom_prompt": True,
            "custom_system_prompt": "System custom",
            "custom_analysis_prompt_template": "Q={question}",
            "custom_hint_prompt_template": "Hint Q={question} A={expected_answer}",
        }
    )
    assert mw.addonManager.config["prompt_profile"] == "strict_stem"
    assert mw.addonManager.config["use_custom_prompt"] is False
    assert mw.addonManager.config["custom_hint_prompt_template"] == "Hint Q={question} A={expected_answer}"
    assert "template_prompt_profile_overrides" not in mw.addonManager.config
    assert addon.should_show_custom_prompt_fields("custom") is True
    assert addon.should_show_custom_prompt_fields("strict_stem") is False

    resolved_default = addon.resolve_prompt_profile_content(
        {"prompt_profile": "default"},
        "english",
        "default",
    )
    assert resolved_default["system_prompt"]
    assert resolved_default["analysis_prompt_template"]
    assert resolved_default["hint_prompt_template"]

    resolved_custom = addon.resolve_prompt_profile_content(
        {
            "prompt_profile": "custom",
            "custom_system_prompt": "System custom",
            "custom_analysis_prompt_template": "Q={question} A={expected_answer} U={user_answer}",
            "custom_hint_prompt_template": "Hint for Q={question} A={expected_answer} H={hint}",
        },
        "english",
        "custom",
    )
    assert resolved_custom["system_prompt"] == "System custom"
    assert resolved_custom["analysis_prompt_template"] == "Q={question} A={expected_answer} U={user_answer}"
    assert resolved_custom["hint_prompt_template"] == "Hint for Q={question} A={expected_answer} H={hint}"

    assert max(addon.get_config()["max_tokens"], 100) >= 200

    assert hasattr(addon, "build_analysis_cache_key")
    cache_key = addon.build_analysis_cache_key("13 * 17 = ?", "221", "2")
    addon.ai_analysis_cache[cache_key] = {"score": 0}
    addon.analysis_results[cache_key] = {"score": 0}
    addon.is_analyzing[cache_key] = False
    addon.invalidate_analysis_state(cache_key)
    assert cache_key not in addon.ai_analysis_cache
    assert cache_key not in addon.analysis_results

    prompt = addon.get_language_specific_prompt("english", "13 * 17 = ?", "221", ["221", "221.0"], "2")
    assert "review_suggestion" not in prompt
    assert "Accepted answers" in prompt
    assert "221.0" in prompt

    strict_system, strict_prompt = addon.build_prompt_profile_content(
        {
            "prompt_profile": "strict_stem",
            "custom_system_prompt": "",
            "custom_analysis_prompt_template": "",
        },
        "english",
        "strict_stem",
        "13 * 17 = ?",
        "221",
        ["221", "221.0"],
        "2",
    )
    assert "numeric" in strict_prompt.lower()
    assert "sign" in strict_prompt.lower()
    assert "unit" in strict_prompt.lower()

    speaking_system, speaking_prompt = addon.build_prompt_profile_content(
        {
            "prompt_profile": "speaking_flexible",
            "custom_system_prompt": "",
            "custom_analysis_prompt_template": "",
        },
        "english",
        "speaking_flexible",
        "How was your weekend?",
        "I visited my grandmother.",
        ["I visited my grandmother."],
        "I went to see family.",
    )
    assert "communicative adequacy" in speaking_prompt.lower()
    assert "alternative valid responses" in speaking_prompt.lower()
    assert "sample_answers" in speaking_prompt
    assert "question_variants" in speaking_prompt
    assert "2–3" in speaking_prompt or "2-3" in speaking_prompt
    assert "build from learner answer" in speaking_prompt.lower()
    assert "higher-scoring full answer" in speaking_prompt.lower()
    assert "do not repeat learner answer unchanged" in speaking_prompt.lower()

    assert r"\(" in addon.get_language_lock_instruction("english")
    assert "Do not use $...$" in addon.get_language_lock_instruction("english")

    assert "Escape backslashes" in addon.get_language_lock_instruction("english")

    addon.save_config({
        "enabled": True,
        "prompt_profile": "default",
        "language": "english",
        "provider": "openai",
        "openai_api_key": "token",
        "openai_model": "gpt-4.1-mini",
    })
    addon.call_ai_api = lambda **kwargs: '{\n  "score": 0,\n  "tips": "Incorrect answer. Solve \\(x^2 = 4\\)."\n}'
    parsed_math_json = addon.analyze_answer_with_ai("x^2 + 1 = 5", "2", ["2"], "3")
    assert parsed_math_json["score"] == 0
    assert parsed_math_json["tips"] == "Incorrect answer. Solve \\(x^2 = 4\\)."
    assert "score" not in parsed_math_json["tips"]

    custom_system, custom_prompt = addon.build_prompt_profile_content(
        {
            "prompt_profile": "custom",
            "custom_system_prompt": "System custom",
            "custom_analysis_prompt_template": "Q={question} A={expected_answer} U={user_answer}",
        },
        "english",
        "custom",
        "13 * 17 = ?",
        "221",
        ["221", "221.0"],
        "2",
    )
    assert custom_system == "System custom"
    assert custom_prompt == "Q=13 * 17 = ? A=221 U=2"

    assert addon.build_custom_system_placeholder(
        {"custom_system_placeholder": "If empty, language default system prompt is used."}
    ) == "If empty, language default system prompt is used."
    assert "dialog.resize(760, 900)" not in read_addon_source()

    mismatch = addon.make_variant_mismatch_result("Variant mismatch", "english")
    assert mismatch["status"] == "variant_mismatch"
    assert mismatch["score"] is None

    addon.analysis_results[cache_key] = {"scored": True, "score": 0, "tips": "Wrong."}
    rendered = addon.render_enhanced_comparison("<div>anki compare</div>", "221", "2", "[[type:Back]]")
    assert "Question Context" not in rendered
    assert "Review Suggestion" not in rendered
    assert "Regenerate Analysis" not in rendered
    assert "Improvement Tips" not in rendered
    assert "🤖" not in rendered
    assert "❌" not in rendered
    assert "aqi-panel-head" in rendered
    assert "aqi-ai-action-btn" in rendered
    assert "aqi-panel-body" in rendered
    assert 'class="aqi-shell"' in rendered
    assert "font-family: -apple-system" not in rendered
    assert "Wrong." in rendered
    assert "⟳" in rendered
    assert "Regenerate" in rendered

    addon.analysis_results[cache_key] = {
        "scored": True,
        "score": 7,
        "tips": "Good base answer. Solve \\(x^2 = 4\\).",
        "sample_answers": ["I went to see family.", "I spent time with my family and relaxed at home. Solve \\(x^2 = 4\\)."],
        "question_variants": ["What did you do over the weekend?", "How did you spend your weekend?"],
    }
    rendered_structured = addon.build_ai_analysis_panel_html(cache_key, "english")
    assert addon.get_ai_ui_texts("english")["ai_analysis_sample_answers"] in rendered_structured
    assert addon.get_ai_ui_texts("english")["ai_analysis_question_variants"] in rendered_structured
    assert "I went to see family." in rendered_structured
    assert "What did you do over the weekend?" in rendered_structured
    assert rendered_structured.count("AI Analysis") == 1
    assert r"\(x^2 = 4\)" in rendered_structured

    speaking_cache_key = addon.build_analysis_cache_key("How was your weekend?", "I visited my grandmother.", "I went to see family.")
    addon.call_ai_api = lambda **kwargs: '{\n  "score": 7,\n  "tips": "Good base answer.",\n  "sample_answers": ["I went to see family.", "I spent time with my family and relaxed at home."],\n  "question_variants": ["What did you do over the weekend?", "How did you spend your weekend?"]\n}'
    parsed_end_to_end = addon.analyze_answer_with_ai("How was your weekend?", "I visited my grandmother.", ["I visited my grandmother."], "I went to see family.")
    addon.analysis_results[speaking_cache_key] = parsed_end_to_end
    rendered_end_to_end = addon.build_ai_analysis_panel_html(speaking_cache_key, "english")
    assert addon.get_ai_ui_texts("english")["ai_analysis_sample_answers"] in rendered_end_to_end
    assert "I went to see family." in rendered_end_to_end

    addon.analysis_results[cache_key] = addon.make_analysis_unavailable("AI disabled", "english")
    rendered_unavailable = addon.build_ai_analysis_panel_html(cache_key, "english")
    assert addon.get_ai_ui_texts("english")["ai_analysis_sample_answers"] not in rendered_unavailable
    assert addon.get_ai_ui_texts("english")["ai_analysis_question_variants"] not in rendered_unavailable

    addon.analysis_results[cache_key] = {"scored": False, "score": None, "tips": "Unavailable."}
    rendered_unscored = addon.build_ai_analysis_panel_html(cache_key, "english")
    assert "N/A" in rendered_unscored
    assert addon.get_ai_ui_texts("english")["ai_analysis_sample_answers"] not in rendered_unscored

    loading_analysis_key = addon.build_analysis_cache_key("13 * 17 = ?", "221", "17")
    addon.analysis_results.pop(loading_analysis_key, None)
    addon.ai_analysis_cache.pop(loading_analysis_key, None)
    addon.is_analyzing[loading_analysis_key] = True
    loading_rendered = addon.render_enhanced_comparison("<div>anki compare</div>", "221", "17", "[[type:Back]]")
    assert "aqi-analysis-panel-wrap" in loading_rendered
    assert "aqi-loading-card" in loading_rendered
    assert "AI in progress..." in loading_rendered
    assert "Please wait while AI works" in loading_rendered
    assert "setTimeout(" not in loading_rendered
    addon.is_analyzing.pop(loading_analysis_key, None)

    perfect_cache_key = addon.build_analysis_cache_key("13 * 17 = ?", "221", "221")
    addon.analysis_results[perfect_cache_key] = {"scored": True, "score": 10, "tips": "Perfect."}
    perfect_rendered = addon.render_enhanced_comparison("<div>anki compare</div>", "221", "221", "[[type:Back]]")
    assert 'data-score-tier="excellent"' in perfect_rendered
    assert "--aqi-score-bg:" not in perfect_rendered
    assert "Perfect." in perfect_rendered

    alt_card = DummyCard(model_name="card_1", template_name="card_1_score")
    alt_card.note()["Front"] = "What is your name?"
    alt_card.note()["Back"] = "My name is Long"
    alt_card.note()["Back_variants"] = "I'm Long;;Long is my name"
    alt_card.question = lambda: "What is your name? [[type:Back]]"
    mw.reviewer.card = alt_card
    alt_cache_key = addon.build_analysis_cache_key("What is your name?", "My name is Long", "Long")
    addon.analysis_results[alt_cache_key] = {
        "scored": True,
        "score": 4,
        "tips": "Too short.",
        "sample_answers": ["Sample only answer"],
    }
    alt_rendered = addon.render_enhanced_comparison("<div>anki compare</div>", "My name is Long", "Long", "[[type:Back]]")
    assert "My name is Long" in alt_rendered
    assert "I&#x27;m Long" in alt_rendered
    assert "Long is my name" in alt_rendered
    panel_start = alt_rendered.index("aqi-analysis-panel-wrap")
    assert alt_rendered.index("I&#x27;m Long") < panel_start
    assert alt_rendered.index("Long is my name") < panel_start
    assert alt_rendered.index("Sample only answer") > panel_start

    mw.reviewer.card = DummyCard()
    payload = addon.build_analysis_prompt_payload(mw.reviewer.card, "17")
    assert payload["question_text"] == "13 * 17 = ?"
    assert payload["canonical_answer"] == "221"
    assert payload["accepted_answers"] == ["221", "two hundred twenty-one", "221.0"]
    assert payload["user_answer"] == "17"

    plain_card = DummyCard(model_name="card_1")
    mw.reviewer.card = plain_card
    plain_payload = addon.build_analysis_prompt_payload(plain_card, "17")
    plain_cache_key = addon.build_analysis_cache_key(
        plain_payload["question_text"],
        plain_payload["canonical_answer"],
        plain_payload["user_answer"],
    )
    addon.store_ai_analysis(("221", "17"), "[[type:Back]]")
    assert plain_cache_key not in addon.is_analyzing
    assert addon.render_enhanced_comparison("<div>plain compare</div>", "221", "17", "[[type:Back]]") == "<div>plain compare</div>"

    note_type_score_only_card = DummyCard(model_name="card_1_score", template_name="card_1")
    assert addon.should_score_card(note_type_score_only_card) is False

    template_score_card = DummyCard(model_name="card_1", template_name="card_1_score")
    mw.reviewer.card = template_score_card
    assert addon.should_score_card(template_score_card) is True
    assert addon.get_card_template_name(template_score_card) == "card_1_score"
    assert addon.resolve_prompt_profile(
        {"prompt_profile": "default", "template_prompt_profile_overrides": {"card_1_score": "strict_stem"}}
    ) == "default"

    handled, _ = addon.handle_js_message((False, None), "regenerate_ai_analysis", None)
    assert handled is True

    addon.current_analysis_context.update(
        {
            "card_id": mw.reviewer.card.id,
            "cache_key": perfect_cache_key,
            "expected_provided_tuple": ("221", "221"),
            "type_pattern": "[[type:Back]]",
        }
    )
    mw.reviewer.web.commands.clear()
    mw.reviewer.show_answer_calls = 0
    addon.refresh_ai_analysis()
    assert mw.reviewer.web.commands
    assert "aqi-analysis-panel-wrap" in mw.reviewer.web.commands[-1]
    assert mw.reviewer.show_answer_calls == 0

    template_score_card.note()["Hint"] = "<b>Factor pairs</b>"
    assert addon.is_supported_typed_answer_card(template_score_card, template_score_card.question(), "Question") is True
    assert addon.is_front_hint_eligible(template_score_card, template_score_card.question(), "Question") is True

    addon.reset_active_question_state()
    addon.get_or_choose_active_question_variant(template_score_card, rng=lambda seq: seq[0])
    hint_context_a = addon.build_front_hint_context(template_score_card)
    analysis_payload_a = addon.build_analysis_prompt_payload(template_score_card, "17")

    addon.reset_active_question_state()
    addon.get_or_choose_active_question_variant(template_score_card, rng=lambda seq: seq[1])
    hint_context_b = addon.build_front_hint_context(template_score_card)
    analysis_payload_b = addon.build_analysis_prompt_payload(template_score_card, "17")

    assert hint_context_a["question_text"] == "13 * 17 = ?"
    assert hint_context_b["question_text"] == "17 * 13 = ?"
    assert hint_context_a["cache_key"] != hint_context_b["cache_key"]
    assert analysis_payload_a["question_text"] == "13 * 17 = ?"
    assert analysis_payload_b["question_text"] == "17 * 13 = ?"
    assert addon.build_analysis_cache_key(
        analysis_payload_a["question_text"],
        analysis_payload_a["canonical_answer"],
        analysis_payload_a["user_answer"],
    ) != addon.build_analysis_cache_key(
        analysis_payload_b["question_text"],
        analysis_payload_b["canonical_answer"],
        analysis_payload_b["user_answer"],
    )
    addon.reset_active_question_state()

    plain_question_card = DummyCard(model_name="card_1", template_name="card_1_score")
    plain_question_card.question = lambda: "No typed answer here"
    assert addon.is_supported_typed_answer_card(plain_question_card, plain_question_card.question(), "Question") is False
    assert addon.is_front_hint_eligible(plain_question_card, plain_question_card.question(), "Question") is False

    addon.save_config({"enabled": False, "prompt_profile": "default"})
    front_rendered = addon.render_front_hint_panel("<div>front side</div>", template_score_card, "Question")
    assert "aqi-front-hint-panel" in front_rendered
    assert "aqi-panel-card aqi-front-hint-card" in front_rendered
    assert "<b>Factor pairs</b>" in front_rendered
    assert "aqi-front-hint-label" not in front_rendered
    assert "Suggest Hint" in front_rendered
    assert "disabled" in front_rendered

    hint_key = addon.build_hint_cache_key(
        card_id=1,
        card_ord=0,
        question_text="13 * 17 = ?",
        canonical_answer="221",
        manual_hint="Factor pairs",
        language="english",
        prompt_profile="default",
        hint_prompt_version="v1",
    )
    addon.hint_cache[hint_key] = {"status": "ready", "hint_text": "Start with 13 x ?", "error_text": ""}
    addon.front_hint_panel_state["cache_key"] = hint_key
    addon.front_hint_panel_state["is_open"] = True
    addon.invalidate_hint_state(hint_key)
    assert hint_key not in addon.hint_cache
    assert addon.front_hint_panel_state == {}

    handled, _ = addon.handle_js_message((False, None), "toggle_hint_panel", None)
    assert handled is True
    handled, _ = addon.handle_js_message((False, None), "suggest_ai_hint", None)
    assert handled is True
    handled, _ = addon.handle_js_message((False, None), "regenerate_ai_hint", None)
    assert handled is True

    loading_hint_context = addon.build_front_hint_context(template_score_card)
    addon.front_hint_panel_state.update({"cache_key": loading_hint_context["cache_key"], "is_open": True})
    addon.hint_cache[loading_hint_context["cache_key"]] = {"status": "loading", "hint_text": "", "error_text": ""}
    loading_hint_rendered = addon.render_front_hint_panel("<div>front side</div>", template_score_card, "Question")
    assert "aqi-loading-card" in loading_hint_rendered
    assert "AI in progress..." in loading_hint_rendered
    assert "Please wait while AI works" in loading_hint_rendered
    assert "aqi-ai-action-btn" in loading_hint_rendered
    assert "disabled" in loading_hint_rendered

    addon.refresh_front_hint_panel_dom("<div id='aqi-front-hint-body'>patched</div>")
    assert mw.reviewer.web.commands
    assert "aqi-front-hint-body" in mw.reviewer.web.commands[-1]

    addon.save_config({"enabled": False, "prompt_profile": "default"})
    unavailable_hint = addon.suggest_ai_hint()
    assert unavailable_hint["status"] == "unavailable"
    assert unavailable_hint["hint_text"] == ""
    assert unavailable_hint["error_text"]

    assert addon.render_front_hint_panel in sys.modules["aqt"].gui_hooks.card_will_show

    install_sync_background(mw)
    api_calls = []
    addon.call_ai_api = lambda **kwargs: api_calls.append(kwargs) or "Start from 13 × 10, not <221>."
    addon.save_config(
        {
            "enabled": True,
            "prompt_profile": "custom",
            "language": "english",
            "provider": "openai",
            "openai_api_key": "token",
            "openai_model": "gpt-4.1-mini",
            "custom_hint_prompt_template": "Q={question} A={expected_answer} H={hint}",
        }
    )
    mw.reviewer.web.commands.clear()
    ready_hint = addon.suggest_ai_hint()
    assert ready_hint["status"] == "ready"
    assert ready_hint["hint_text"] == "Start from 13 × 10, not <221>."
    assert len(api_calls) == 1
    assert addon.current_hint_context["question_text"] == "13 * 17 = ?"
    assert addon.front_hint_panel_state["is_open"] is True
    assert mw.reviewer.web.commands
    assert "&lt;221&gt;" in mw.reviewer.web.commands[-1]
    ready_hint_rendered = addon.render_front_hint_panel("<div>front side</div>", template_score_card, "Question")
    assert "aqi-ai-action-btn" in ready_hint_rendered
    assert "Regenerate" in ready_hint_rendered
    assert "⟳" in ready_hint_rendered

    regen_hint = addon.regenerate_ai_hint()
    assert regen_hint["status"] == "ready"
    assert len(api_calls) == 2
    assert addon.current_hint_context["question_text"] == "13 * 17 = ?"

    rich_hint_html = addon.render_ai_rich_text("Use **bold** and *italic* and `code`")
    assert "<strong>bold</strong>" in rich_hint_html
    assert "<em>italic</em>" in rich_hint_html

    arithmetic_html = addon.render_ai_rich_text("Wrong result. 17 * 13 * 1 = 221")
    assert "17 * 13 * 1 = 221" in arithmetic_html
    assert "<em> 13 </em>" not in arithmetic_html
    assert "<code>code</code>" in rich_hint_html

    rich_list_html = addon.render_ai_rich_text("- one\n- two")
    assert "<ul>" in rich_list_html
    assert "<li>one</li>" in rich_list_html
    assert "<li>two</li>" in rich_list_html

    rich_code_block_html = addon.render_ai_rich_text("```\nprint(1)\n```")
    assert "<pre" in rich_code_block_html
    assert "<code>print(1)</code>" in rich_code_block_html

    math_html = addon.render_ai_rich_text(r"Formula \(x^2+y^2\)")
    assert r"\(x^2+y^2\)" in math_html

    hostile_html = addon.render_ai_rich_text("<script>alert(1)</script><b>hi</b>")
    assert "<script>" not in hostile_html
    assert "&lt;script&gt;" in hostile_html

    fallback_html = addon.render_ai_rich_text(None)
    assert isinstance(fallback_html, str)

    unavailable_hint_context = addon.build_front_hint_context(template_score_card)
    unavailable_hint_key = unavailable_hint_context["cache_key"]
    addon.front_hint_panel_state.update({"cache_key": unavailable_hint_key, "is_open": True})
    addon.hint_cache[unavailable_hint_key] = {"status": "unavailable", "hint_text": "", "error_text": "Use **safe** fallback"}
    unavailable_hint_rendered = addon.build_front_hint_panel_html(template_score_card, template_score_card.question(), "Question")
    assert "<strong>safe</strong>" in unavailable_hint_rendered or "Use **safe** fallback" in unavailable_hint_rendered

    unavailable_analysis_key = addon.build_analysis_cache_key("13 * 17 = ?", "221", "17")
    addon.analysis_results[unavailable_analysis_key] = {"status": "unavailable", "scored": False, "score": None, "tips": "Use **safe** fallback"}
    unavailable_analysis_rendered = addon.build_ai_analysis_panel_html(unavailable_analysis_key, "english")
    assert "<strong>safe</strong>" in unavailable_analysis_rendered or "Use **safe** fallback" in unavailable_analysis_rendered

    addon.refresh_front_hint_panel_dom("<div id='aqi-front-hint-body'>patched</div>")
    assert "aqi-front-hint-body" in mw.reviewer.web.commands[-1]
    addon.refresh_ai_analysis_panel_dom("<div class='aqi-analysis-panel-wrap'>patched</div>")
    assert "aqi-analysis-panel-wrap" in mw.reviewer.web.commands[-1]
    assert "MathJax" in mw.reviewer.web.commands[-1] or "typeset" in mw.reviewer.web.commands[-1]


if __name__ == "__main__":
    main()

