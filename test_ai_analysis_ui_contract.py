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
            "Hint": "Base hint",
            "Back2": "",
            "Back2_variants": "",
            "Hint2": "Second hint",
            "Back3": "",
            "Back3_variants": "",
            "Hint3": "Third hint",
            "Back4": "",
            "Back4_variants": "",
            "Hint4": "Fourth hint",
            "Back5": "",
            "Back5_variants": "",
            "Hint5": "Fifth hint",
            "Back6": "",
            "Back6_variants": "",
            "Hint6": "Sixth hint",
        })
        self._model = {"name": model_name, "tmpls": [{"name": template_name} for _ in range(6)]}

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
    base = pathlib.Path(__file__).parent
    parts = []
    for name in (
        "__init__.py",
        "locales.py",
        "config_model.py",
        "ai_runtime.py",
        "reviewer_ui.py",
    ):
        path = base / name
        if path.exists():
            parts.append(path.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def build_current_analysis_cache_key(addon, card, user_answer: str, config=None, analysis_mode: str = "standard") -> str:
    payload = addon.build_analysis_prompt_payload(card, user_answer)
    runtime = addon.resolve_ai_runtime_config(config or addon.get_config(), analysis_mode=analysis_mode)
    return addon.build_analysis_cache_key(
        payload["question_text"],
        payload["canonical_answer"],
        user_answer,
        card_id=getattr(card, "id", None),
        card_ord=getattr(card, "ord", None),
        language=runtime["language"],
        provider=runtime["provider"],
        model=runtime["model"],
        analysis_mode=runtime["analysis_mode"],
        max_tokens=runtime["max_tokens"],
        temperature=runtime["temperature"],
        accepted_answers=payload["accepted_answers"],
        resolved_prompt_contract=addon.build_prompt_contract_hash(
            runtime["config"], runtime["language"], runtime["prompt_profile"], "analysis"
        ),
        analysis_prompt_version=addon.ANALYSIS_PROMPT_VERSION,
    )

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
    assert "if(child!==wrap&&child&&child.parentNode===inputHost){ inputHost.removeChild(child); }" in source
    assert "if(child!==hint&&child&&child.parentNode===hintHost){ hintHost.removeChild(child); }" in source

    merged_legacy = addon.merge_config_with_defaults({"use_custom_prompt": True})
    assert merged_legacy["prompt_profile"] == "custom"
    assert merged_legacy["general"]["language"] == "english"
    assert merged_legacy["general"]["show_anki_compare"] is True
    assert merged_legacy["general"]["show_code_compare"] is True
    assert merged_legacy["modes"]["standard"]["prompt_profile"] == "custom"
    assert merged_legacy["modes"]["deep"]["prompt_profile"] == "custom"
    assert merged_legacy["modes"]["deep"]["enabled"] is False
    assert merged_legacy["modes"]["deep"]["model"] == ""
    assert merged_legacy["providers"]["custom_openai"]["base_url"] == ""
    assert merged_legacy["custom_hint_prompt_template"] == ""

    merged_from_prompt_profile = addon.merge_config_with_defaults({"prompt_profile": "strict_stem"})
    assert merged_from_prompt_profile["modes"]["standard"]["prompt_profile"] == "strict_stem"
    assert merged_from_prompt_profile["modes"]["deep"]["prompt_profile"] == "strict_stem"

    merged_explicit_modes = addon.merge_config_with_defaults(
        {
            "provider": "custom_openai",
            "prompt_profile": "default",
            "standard_prompt_profile": "strict_stem",
            "deep_prompt_profile": "speaking_flexible",
            "deep_analysis_model": "gpt-5.4",
            "max_tokens": 123,
            "temperature": 0.4,
        }
    )
    assert merged_explicit_modes["modes"]["standard"]["provider"] == "custom_openai"
    assert merged_explicit_modes["modes"]["deep"]["provider"] == "custom_openai"
    assert merged_explicit_modes["modes"]["standard"]["prompt_profile"] == "strict_stem"
    assert merged_explicit_modes["modes"]["deep"]["prompt_profile"] == "speaking_flexible"
    assert merged_explicit_modes["modes"]["deep"]["model"] == "gpt-5.4"
    assert merged_explicit_modes["modes"]["standard"]["max_tokens"] == 123
    assert merged_explicit_modes["modes"]["deep"]["max_tokens"] == 123
    assert addon.resolve_prompt_profile({"prompt_profile": "default"}) == "default"
    assert addon.resolve_prompt_profile(
        {
            "prompt_profile": "default",
            "template_prompt_profile_overrides": {"card_1_score": "strict_stem"},
        }
    ) == "default"

    assert set(addon.HINT_UI_TEXTS.keys()) == set(addon.LANGUAGES.keys())
    assert set(addon.AI_UI_TEXTS.keys()) == set(addon.LANGUAGES.keys())
    assert set(addon.LANG_TO_LABELS.keys()) == set(addon.LANGUAGES.keys())
    assert addon.LANGUAGES["english"]["display_name"] == "English"
    assert addon.LANGUAGES["english"]["instruction_name"] == "English"
    assert addon.LANGUAGES["french"]["display_name"] == "Français"
    assert addon.LANGUAGES["french"]["instruction_name"] == "French"
    assert set(addon.LANGUAGE_REGISTRY) == set(addon.LANGUAGES) == set(addon.HINT_UI_TEXTS) == set(addon.AI_UI_TEXTS) == set(addon.LANG_TO_LABELS)
    assert addon.get_hint_ui_texts("french") == addon.LANGUAGE_REGISTRY["french"]["hint_ui"]
    assert addon.get_ai_ui_texts("french") == addon.LANGUAGE_REGISTRY["french"]["ai_ui"]
    assert addon.get_compare_labels({"language": "french"}) == addon.LANGUAGE_REGISTRY["french"]["compare_labels"]
    assert hasattr(addon, 'get_supported_language_options')
    language_options = addon.get_supported_language_options()
    assert language_options[0] == ('english', addon.LANGUAGE_REGISTRY['english']['ui']['display_name'])
    assert ('french', addon.LANGUAGE_REGISTRY['french']['ui']['display_name']) in language_options
    assert addon.get_language_name('french') == addon.LANGUAGE_REGISTRY['french']['ui']['instruction_name']

    addon.call_ai_api = lambda **_kwargs: '{"sample_answers":["In meinem Heimatland sehen viele Kinder täglich fern."]}'
    malformed_json_result = addon.analyze_answer_request(
        {
            "question_text": "Frage",
            "canonical_answer": "Antwort",
            "accepted_answers": ["Antwort"],
            "user_answer": "Antwort",
            "language": "english",
            "provider": "openai",
            "model": "gpt-test",
            "api_key": "test-key",
            "base_url": "",
            "prompt_profile": addon.PROMPT_PROFILE_DEFAULT,
            "max_tokens": 64,
            "temperature": 0.0,
            "availability_reason": "",
            "analysis_mode": "standard",
        },
        card=DummyCard(),
    )
    assert malformed_json_result["tips"].startswith("AI analysis not available: AI returned unsupported JSON schema")
    assert malformed_json_result["scored"] is False


    fr_review_labels = addon.get_compare_labels({"language": "french", "ui_language": "en"})
    en_config_texts = addon.get_config_ui_texts({"language": "french", "ui_language": "en"})
    assert fr_review_labels["expected"] == addon.LANG_TO_LABELS["french"]["expected"]
    assert en_config_texts == addon.CONFIG_UI_TEXTS["en"]

    for language_key in sorted(set(addon.LANGUAGES.keys()) - {"english"}):
        ai_texts = addon.get_ai_ui_texts(language_key)
        assert ai_texts["ai_analysis_sample_answers"] != "Sample Answers"
        assert ai_texts["ai_analysis_question_variants"] != "Alternative Questions"

    addon.save_config(
        {
            "general": {
                "language": "english",
                "show_anki_compare": True,
                "show_code_compare": True,
            },
            "modes": {
                "standard": {
                    "enabled": True,
                    "provider": "custom_openai",
                    "model": "cx/gpt-5.4-mini",
                    "prompt_profile": "strict_stem",
                    "max_tokens": 100,
                    "temperature": 0.7,
                },
                "deep": {
                    "enabled": True,
                    "provider": "custom_openai",
                    "model": "cx/gpt-5.5",
                    "prompt_profile": "speaking_flexible",
                    "max_tokens": 300,
                    "temperature": 0.4,
                },
            },
            "providers": {
                "custom_openai": {
                    "base_url": "http://127.0.0.1:20128/v1",
                    "api_key": "",
                    "custom_models": ["cx/gpt-5.4-mini", "cx/gpt-5.5"],
                }
            },
            "template_prompt_profile_overrides": {"card_1_score": "strict_stem"},
            "use_custom_prompt": True,
            "custom_system_prompt": "System custom",
            "custom_analysis_prompt_template": "Q={question}",
            "custom_hint_prompt_template": "Hint Q={question} A={expected_answer}",
        }
    )
    assert mw.addonManager.config["general"]["language"] == "english"
    assert mw.addonManager.config["modes"]["standard"]["prompt_profile"] == "strict_stem"
    assert mw.addonManager.config["modes"]["deep"]["prompt_profile"] == "speaking_flexible"
    assert mw.addonManager.config["modes"]["standard"]["model"] == "cx/gpt-5.4-mini"
    assert mw.addonManager.config["modes"]["deep"]["model"] == "cx/gpt-5.5"
    assert mw.addonManager.config["providers"]["custom_openai"]["base_url"] == "http://127.0.0.1:20128/v1"
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

    assert hasattr(addon, "resolve_prompt_default_content")
    resolved_file_default = addon.resolve_prompt_default_content("english", "default")
    assert resolved_default == resolved_file_default
    assert resolved_file_default["system_prompt"].startswith("You are an educational assistant")
    resolved_french_default = addon.resolve_prompt_default_content("french", "default")
    assert "Les réponses acceptées sont des alternatives pleinement valides" in resolved_french_default["analysis_prompt_template"]
    assert "Return exactly one JSON object with keys score and tips" in resolved_file_default["analysis_prompt_template"]
    assert "no review_suggestion fields" in resolved_file_default["analysis_prompt_template"]
    assert addon.resolve_prompt_default_content("english", "not-supported") == resolved_file_default

    placeholder_block = source.split("def update_default_prompt_placeholders():", 1)[1].split("def get_selected_prompt_profile()", 1)[0]
    reset_block = source.split("def reset_custom_prompts_to_defaults():", 1)[1].split("def update_custom_prompt_inputs():", 1)[0]
    assert "resolve_prompt_default_content(" in placeholder_block
    assert "resolve_prompt_default_content(" in reset_block

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

    current_config = addon.get_config()
    assert current_config["max_tokens"] == 100
    assert current_config["modes"]["standard"]["max_tokens"] == 100
    assert current_config["modes"]["deep"]["max_tokens"] == 300

    assert hasattr(addon, "build_analysis_cache_key")
    cache_key = build_current_analysis_cache_key(addon, mw.reviewer.card, "2")
    addon.ai_analysis_cache[cache_key] = {"score": 0}
    addon.analysis_results[cache_key] = {"score": 0}
    addon.is_analyzing[cache_key] = False
    addon.invalidate_analysis_state(cache_key)
    assert cache_key not in addon.ai_analysis_cache
    assert cache_key not in addon.analysis_results

    _system, prompt = addon.build_prompt_profile_content(
        {"prompt_profile": "default", "custom_system_prompt": "", "custom_analysis_prompt_template": ""},
        "english",
        "default",
        "13 * 17 = ?",
        "221",
        ["221", "221.0"],
        "2",
    )
    assert "no review_suggestion fields" in prompt
    assert "Accepted answers" in prompt
    assert "221.0" in prompt
    assert "Accepted answers are equally valid alternatives" in prompt
    assert "Do not require exact wording of the expected answer" in prompt
    assert "nearest accepted answer" in prompt
    assert "OUTPUT CONTRACT" in prompt
    assert 'Example: {"score":8,"tips":"..."}' in prompt
    assert "Do not return sample_answers" in prompt
    assert "Do not return question_variants" in prompt

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
    assert 'Example: {"score":8,"tips":"..."}' in strict_prompt
    resolved_strict_default = addon.resolve_prompt_default_content("english", "strict_stem")
    assert "Focus on numeric correctness, sign, unit, and completeness." in resolved_strict_default["analysis_prompt_template"]

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
    assert "Return exactly these four keys" in speaking_prompt
    assert "No objects" in speaking_prompt
    assert 'Example: {"score":7,"tips":"...","sample_answers":["...","..."],"question_variants":["...","..."]}' in speaking_prompt
    resolved_speaking_default = addon.resolve_prompt_default_content("english", "speaking_flexible")
    assert "Accepted answers are equally valid alternatives" in resolved_file_default["analysis_prompt_template"]
    assert "Do not require exact wording of the expected answer" in resolved_file_default["analysis_prompt_template"]
    assert "keys score, tips, sample_answers, question_variants" in resolved_speaking_default["analysis_prompt_template"]
    assert "arrays of plain strings, never objects" in resolved_speaking_default["analysis_prompt_template"]

    cloze_system, cloze_prompt = addon.build_prompt_profile_content(
        {
            "prompt_profile": "cloze_recall",
            "custom_system_prompt": "",
            "custom_analysis_prompt_template": "",
        },
        "english",
        "cloze_recall",
        "This is a |(c1::cat|).",
        "cat",
        ["cat"],
        "cat",
    )
    assert cloze_system
    assert "sample_answers" in cloze_prompt
    assert "Do not return question_variants" in cloze_prompt
    assert "Expected answer" in cloze_prompt
    assert "Accepted answers" in cloze_prompt
    assert "Student answer" in cloze_prompt
    assert "score 10" in cloze_prompt.lower()
    assert "usually treat this as recall-focused, not free speaking" in cloze_prompt.lower()
    assert "a natural paraphrase may score high" in cloze_prompt.lower()
    assert "angaben vs anlagen is a serious error" in cloze_prompt.lower()
    assert "dialogue, roleplay cue, explanation prompt" in cloze_prompt.lower()
    assert "accepted answers are strong anchors" in cloze_prompt.lower()
    assert "near-synonymous verbs or softer modal phrasing" in cloze_prompt.lower()
    assert "Do not use other speaker lines or other cloze groups as sample_answers" in cloze_prompt
    assert "Return exactly these three keys" in cloze_prompt
    assert "Do not return question_variants" in cloze_prompt
    assert 'Example: {"score":10,"tips":"...","sample_answers":["..."]}' in cloze_prompt
    resolved_cloze_default = addon.resolve_prompt_default_content("english", "cloze_recall")
    assert "keys score, tips, sample_answers" in resolved_cloze_default["analysis_prompt_template"]
    assert "Do not return question_variants" in resolved_cloze_default["analysis_prompt_template"]
    assert "usually treat this as recall-focused, not free speaking" in resolved_cloze_default["analysis_prompt_template"].lower()
    assert "a natural paraphrase may score high" in resolved_cloze_default["analysis_prompt_template"].lower()

    custom_system, custom_prompt = addon.build_prompt_profile_content(
        {
            "prompt_profile": "custom",
            "custom_system_prompt": "System",
            "custom_analysis_prompt_template": "Q={question}",
        },
        "english",
        "custom",
        "Question?",
        "Answer",
        ["Answer"],
        "User",
    )
    assert custom_system == "System"
    assert custom_prompt.startswith("Q=Question?")
    assert "OUTPUT CONTRACT" in custom_prompt
    assert "cat" in cloze_prompt

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

    addon.call_ai_api = lambda **kwargs: '{"sample_answers":[{"answer":"4\n5","score":0,"tips":"Not target sentence. Write German text: \"Am Freitagnachmittag hätte ich Zeit. Wie wäre es mit Freitag um sechzehn Uhr?\""}]}'
    parsed_nested_json = addon.analyze_answer_with_ai("Wann hast du Zeit?", "Am Freitagnachmittag hätte ich Zeit. Wie wäre es mit Freitag um sechzehn Uhr?", ["Am Freitagnachmittag hätte ich Zeit. Wie wäre es mit Freitag um sechzehn Uhr?"], "4\n5")
    assert parsed_nested_json["score"] == 0
    assert parsed_nested_json["tips"].startswith("Not target sentence.")
    assert parsed_nested_json["sample_answers"] == ["4\n5"]
    assert parsed_nested_json["question_variants"] == []

    addon.save_config({
        "enabled": True,
        "prompt_profile": "cloze_recall",
        "language": "english",
        "provider": "openai",
        "openai_api_key": "token",
        "openai_model": "gpt-4.1-mini",
    })

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
    assert custom_prompt.startswith("Q=13 * 17 = ? A=221 U=2")
    assert "OUTPUT CONTRACT" in custom_prompt

    assert addon.build_custom_system_placeholder(
        {"custom_system_placeholder": "If empty, language default system prompt is used."}
    ) == "If empty, language default system prompt is used."
    assert addon.should_show_custom_prompt_fields("default", "default") is False
    assert addon.should_show_custom_prompt_fields("custom", "default") is True
    assert addon.should_show_custom_prompt_fields("default", "custom") is True
    assert "General" in source
    assert "Standard" in source
    assert "Deep" in source
    assert "Providers" in source
    assert "Use Deep Analysis" in source
    assert "Use Standard Analysis" in source
    assert "Standard Mode is required." in source
    assert 'mode_widgets["standard"]["enabled"].toggled.connect(mode_widgets["deep"]["update_enabled_state"])' in source
    assert "class TemperatureSpinBox(QSpinBox):" in source
    assert "temp_spin = TemperatureSpinBox()" in source
    assert "temp_spin = QDoubleSpinBox()" not in source
    assert "def configure_numeric_spinbox(" in source
    assert "QDoubleSpinBox::up-button" not in source
    assert "QDoubleSpinBox::down-button" not in source
    assert "QDoubleSpinBox::up-arrow" not in source
    assert "QDoubleSpinBox::down-arrow" not in source
    assert source.count("configure_numeric_spinbox(") >= 2
    assert "providers_layout.addWidget(test_button)" in source
    assert "`n        layout.addWidget(test_button)`n" not in source
    assert "Standard model:" not in source
    assert "Deep model:" not in source
    assert "🧠" not in source
    assert hasattr(addon, "refresh_open_review_surfaces_after_config_save")
    analysis_refresh_calls = []
    hint_refresh_calls = []
    original_refresh_ai_analysis = addon.refresh_ai_analysis
    original_refresh_current_front_hint_panel = addon.refresh_current_front_hint_panel
    addon.refresh_ai_analysis = lambda *args, **kwargs: analysis_refresh_calls.append((args, kwargs))
    addon.refresh_current_front_hint_panel = lambda *args, **kwargs: hint_refresh_calls.append((args, kwargs))
    addon.refresh_open_review_surfaces_after_config_save()
    addon.refresh_ai_analysis = original_refresh_ai_analysis
    addon.refresh_current_front_hint_panel = original_refresh_current_front_hint_panel
    assert analysis_refresh_calls
    assert hint_refresh_calls
    save_block = source.split("def save_and_close():", 1)[1].split("save_button.clicked.connect(save_and_close)", 1)[0]
    assert "refresh_open_review_surfaces_after_config_save()" in save_block
    assert "dialog.resize(760, 900)" not in read_addon_source()
    assert ".aqi-shell {\n  max-width: none;\n}" in source
    assert ".aqi-front-hint-wrap {\n  max-width: 800px;\n}" in source

    highlighted_compare = addon._code_compare_block(
        "No, it only proves that the current solution is optimal for the <mark>full LP relaxation</mark>.",
        "",
        "",
        {"expected": "Expected", "provided": "Your answer"},
    )
    assert "<mark>full LP relaxation</mark>" in highlighted_compare

    rich_expected_compare = addon._code_compare_block(
        r"<p>Typically</p><ul><li>a time limit (<anki-mathjax>t &gt; t_{\max}</anki-mathjax>) or</li><li>a maximum number of iterations.</li></ul>",
        "",
        "",
        {"expected": "Expected", "provided": "Your answer"},
    )
    assert "<ul>" in rich_expected_compare
    assert "<li>a time limit" in rich_expected_compare
    assert "<li>a maximum number of iterations.</li>" in rich_expected_compare
    assert r"\(t &gt; t_{\max}\)" in rich_expected_compare

    colored_expected = (
        'It controls the VND neighborhoods.<br>'
        '<span style="color:rgb(255, 69, 0)">intensification</span>.'
    )
    colored_expected_html = addon._render_expected_answer_html(colored_expected)
    assert '<br><span style="color:rgb(255, 69, 0)">intensification</span>.' in colored_expected_html
    colored_compare = addon._code_compare_block(
        colored_expected,
        "",
        "",
        {"expected": "Expected", "provided": "Your answer"},
    )
    colored_native = addon._render_native_typed_diff(
        "<code id=typeans>plain text</code>",
        colored_expected,
        "",
    )
    assert colored_expected_html in colored_compare
    assert colored_expected_html in colored_native
    assert 'class="mathjax_process aqi-expected-rich"' in colored_native

    bold_expected = (
        'It is <strong>chosen randomly</strong>, <b>increased gradually</b>, '
        '<u>underlined</u>, <em>emphasized</em>, <s>struck</s>, H<sub>2</sub>O, and x<sup>2</sup>.'
    )
    bold_expected_html = addon._render_expected_answer_html(bold_expected)
    assert "<strong>chosen randomly</strong>" in bold_expected_html
    assert "<b>increased gradually</b>" in bold_expected_html
    assert "<u>underlined</u>" in bold_expected_html
    assert "<em>emphasized</em>" in bold_expected_html
    assert "<s>struck</s>" in bold_expected_html
    assert "H<sub>2</sub>O" in bold_expected_html
    assert "x<sup>2</sup>" in bold_expected_html
    assert addon._render_expected_answer_html(
        '<strong onclick="alert(1)" style="color:red">safe</strong>'
    ) == "<strong>safe</strong>"
    assert bold_expected_html in addon._code_compare_block(
        bold_expected,
        "",
        "",
        {"expected": "Expected", "provided": "Your answer"},
    )
    assert bold_expected_html in addon._render_native_typed_diff(
        "<code id=typeans>plain text</code>",
        bold_expected,
        "",
    )

    multiline_expected_html = addon._render_expected_answer_html("first line\nsecond line")
    assert multiline_expected_html == "first line<br>second line"
    multiline_native = addon._render_native_typed_diff(
        "<code id=typeans>plain text</code>",
        "first line\nsecond line",
        "",
    )
    assert multiline_expected_html in multiline_native

    hostile_color_html = addon._render_expected_answer_html(
        '<span onclick="alert(1)" style="color:red;background:url(javascript:alert(1))">Safe</span>'
    )
    assert hostile_color_html == '<span style="color:red">Safe</span>'
    assert "onclick" not in hostile_color_html
    assert "background" not in hostile_color_html
    assert "javascript" not in hostile_color_html

    native_mismatch = addon._render_native_typed_diff(
        '<code id=typeans><span class=typeBad>x</span><br><span id=typearrow>&darr;</span><br><span class=typeMissed>old</span></code>',
        colored_expected,
        "x",
    )
    assert '<span class=typeBad>x</span>' in native_mismatch
    assert '<span class=typeMissed>old</span>' not in native_mismatch
    assert colored_expected_html in native_mismatch

    rich_alternatives = addon.build_visible_expected_alternatives(
        [colored_expected],
        "different answer",
    )
    assert rich_alternatives == [colored_expected]
    rich_alternative_chips = addon._build_expected_variant_chip_list(rich_alternatives)
    assert colored_expected_html in rich_alternative_chips
    assert 'class="aqi-choice-chip sqv-choice-chip aqi-expected-rich"' in rich_alternative_chips

    formatted_expected_compare = addon._code_compare_block(
        """<p>Typically</p>
<ul>
<li>first</li>
<li>second</li>
</ul>""",
        "",
        "",
        {"expected": "Expected", "provided": "Your answer"},
    )
    assert "</p><ul>" in formatted_expected_compare
    assert "</li><li>" in formatted_expected_compare

    adjacent_marks_compare = addon._code_compare_block(
        "<mark>full</mark> <mark>LP relaxation</mark>",
        "",
        "",
        {"expected": "Expected", "provided": "Your answer"},
    )
    assert "</mark> <mark>" in adjacent_marks_compare

    hostile_expected_compare = addon._code_compare_block(
        '<ul onclick="alert(1)"><li>Safe<script>alert(1)</script></li></ul>',
        "",
        "",
        {"expected": "Expected", "provided": "Your answer"},
    )
    assert "onclick" not in hostile_expected_compare
    assert "<script>" not in hostile_expected_compare

    mixed_content = """<code>reset</code> initializes the environment:<p></p>
<pre><code class="hljs python language-python">{
    <span class="hljs-string">"Cur_DP"</span>: <span class="hljs-number">1</span>
    literal = &amp;lt;
}</code></pre>
<p>The first decision point is <code>1</code>.</p>"""
    mixed_content_html = addon._render_expected_answer_html(mixed_content)
    assert '<span class="aqi-expected-inline-code">reset</span> initializes the environment:' in mixed_content_html
    assert '<span class="aqi-expected-code hljs language-python">' in mixed_content_html
    assert '<span class="hljs-string">&quot;Cur_DP&quot;</span>' in mixed_content_html
    assert "literal = &amp;lt;" in mixed_content_html
    assert '<p>The first decision point is <span class="aqi-expected-inline-code">1</span>.</p>' in mixed_content_html
    assert "<p></p>" not in mixed_content_html
    assert "dictionary:<br><br>" not in mixed_content_html
    assert "</span><br><br><p>" not in mixed_content_html
    assert ".aqi-expected-code {" in source
    assert "font-family: ui-monospace" in source

    original_config = addon.get_config()
    addon.save_config(
        {
            "enabled": False,
            "language": "english",
            "show_anki_compare": True,
            "show_code_compare": True,
        }
    )
    original_back = mw.reviewer.card.note()["Back"]
    mw.reviewer.card.note()["Back"] = "<mark>221</mark>"
    disabled_ai_rendered = addon.render_enhanced_comparison(
        "<div>anki compare</div>",
        "<mark>221</mark>",
        "17",
        "[[type:Back]]",
    )
    mw.reviewer.card.note()["Back"] = original_back
    assert 'class="aqi-shell"' in disabled_ai_rendered
    assert "aqi-compare" in disabled_ai_rendered
    assert "<mark>221</mark>" in disabled_ai_rendered
    assert "aqi-analysis-panel-wrap" not in disabled_ai_rendered
    assert "typesetPromise" in disabled_ai_rendered

    deep_without_standard = addon.resolve_ai_runtime_config(
        {
            "modes": {
                "standard": {"enabled": False},
                "deep": {"enabled": True, "model": "gpt-5.4"},
            }
        },
        analysis_mode="deep",
    )
    assert deep_without_standard["availability_reason"] == "Standard Mode is required"
    addon.save_config(original_config)

    mismatch = addon.make_variant_mismatch_result("Variant mismatch", "english")
    assert mismatch["status"] == "variant_mismatch"
    assert mismatch["score"] is None

    cache_key = build_current_analysis_cache_key(addon, mw.reviewer.card, "2")
    addon.analysis_results[cache_key] = {"scored": True, "score": 0, "tips": "Wrong."}
    rendered = addon.render_enhanced_comparison("<div>anki compare</div>", "221", "2", "[[type:Back]]")
    native_math_rendered = addon.render_enhanced_comparison(
        r"<code id=typeans>\(\lambda_i^*=0\)</code>",
        "221",
        "2",
        "[[type:Back]]",
    )
    assert '<code id=typeans class="mathjax_process aqi-expected-rich">' in native_math_rendered
    assert "Question Context" not in rendered
    assert addon.get_ui_texts("english")["review_suggestion"] in rendered
    assert "Regenerate Analysis" not in rendered
    assert "Improvement Tips" not in rendered
    assert "🤖" not in rendered
    assert "❌" not in rendered
    assert "aqi-panel-head" in rendered
    assert "aqi-ai-action-btn" in rendered
    assert "aqi-panel-body" in rendered
    assert 'class="aqi-shell"' in rendered
    assert '<pre class="ak-pre"><code' not in rendered
    assert "font-family: -apple-system" not in rendered
    assert "Wrong." in rendered
    assert "⟳" in rendered
    assert "Regenerate" in rendered

    assert addon.render_ai_rich_text("Line one<br>Line two") == "<p>Line one<br>Line two</p>"

    addon.analysis_results[cache_key] = {
        "scored": True,
        "score": 7,
        "tips": "Good base answer. Solve \\(x^2 = 4\\).",
        "sample_answers": ["I went to see family.", "I spent time with my family and relaxed at home. Solve \\(x^2 = 4\\)."],
        "question_variants": ["What did you do over the weekend?", "How did you spend your weekend?"],
    }
    rendered_structured = addon.build_ai_analysis_panel_html(cache_key, "english")
    assert addon.get_ui_texts("english")["review_suggestion"] in rendered_structured
    assert addon.get_ai_ui_texts("english")["ai_analysis_sample_answers"] in rendered_structured
    assert addon.get_ai_ui_texts("english")["ai_analysis_question_variants"] in rendered_structured
    assert rendered_structured.count('class="aqi-section-label"') == 3
    assert "I went to see family." in rendered_structured
    assert "What did you do over the weekend?" in rendered_structured
    assert rendered_structured.count("AI Analysis") == 1
    assert r"\(x^2 = 4\)" in rendered_structured

    panel_config_before = dict(mw.addonManager.config)
    addon.save_config(
        {
            "general": {
                "language": "english",
                "show_anki_compare": True,
                "show_code_compare": True,
            },
            "modes": {
                "standard": {
                    "enabled": True,
                    "provider": "custom_openai",
                    "model": "cx/gpt-5.4-mini",
                    "prompt_profile": "strict_stem",
                    "max_tokens": 100,
                    "temperature": 0.7,
                },
                "deep": {
                    "enabled": True,
                    "provider": "custom_openai",
                    "model": "cx/gpt-5.5",
                    "prompt_profile": "speaking_flexible",
                    "max_tokens": 300,
                    "temperature": 0.4,
                },
            },
            "providers": {
                "custom_openai": {
                    "base_url": "http://127.0.0.1:20128/v1",
                    "api_key": "",
                    "custom_models": ["cx/gpt-5.4-mini", "cx/gpt-5.5"],
                }
            },
        }
    )
    standard_panel_key = "standard-panel-key"
    deep_panel_key = "deep-panel-key"
    addon.analysis_results[standard_panel_key] = {"scored": True, "score": 7, "tips": "Good.", "analysis_mode": "standard", "standard_cache_key": standard_panel_key}
    addon.analysis_results[deep_panel_key] = {"scored": True, "score": 6, "tips": "Think deeper.", "analysis_mode": "deep", "standard_cache_key": standard_panel_key}
    addon.current_analysis_context.update({"card_id": mw.reviewer.card.id, "cache_key": standard_panel_key, "analysis_mode": "standard", "standard_cache_key": standard_panel_key})
    rendered_standard_panel = addon.build_ai_analysis_panel_html(standard_panel_key, "english")
    assert "Deep Analysis" in rendered_standard_panel
    assert "Show standard" not in rendered_standard_panel
    assert 'data-analysis-mode="standard"' in rendered_standard_panel
    addon.current_analysis_context.update({"card_id": mw.reviewer.card.id, "cache_key": deep_panel_key, "analysis_mode": "deep", "standard_cache_key": standard_panel_key})
    rendered_deep_panel = addon.build_ai_analysis_panel_html(deep_panel_key, "english")
    assert "Deep Analysis" not in rendered_deep_panel
    assert "Show standard" in rendered_deep_panel
    assert 'data-analysis-mode="deep"' in rendered_deep_panel
    addon.save_config({
        "enabled": True,
        "language": "english",
        "provider": "openai",
        "openai_api_key": "token",
        "openai_model": "gpt-4.1-mini",
        "standard_prompt_profile": "strict_stem",
        "deep_prompt_profile": "speaking_flexible",
        "deep_analysis_model": "   ",
    })
    rendered_standard_panel_without_deep = addon.build_ai_analysis_panel_html(standard_panel_key, "english")
    assert "Deep Analysis" not in rendered_standard_panel_without_deep
    addon.save_config(panel_config_before)
    addon.current_analysis_context.update({
        "card_id": mw.reviewer.card.id,
        "cache_key": standard_panel_key,
        "analysis_mode": "standard",
        "standard_cache_key": standard_panel_key,
        "expected_provided_tuple": ("221", "17"),
        "type_pattern": "[[type:Back]]",
    })
    handled, _ = addon.handle_js_message((False, None), "run_deep_analysis", None)
    assert handled is True
    assert addon.current_analysis_context["analysis_mode"] == "deep"
    addon.current_analysis_context.update({
        "card_id": mw.reviewer.card.id,
        "cache_key": deep_panel_key,
        "analysis_mode": "deep",
        "standard_cache_key": standard_panel_key,
        "expected_provided_tuple": ("221", "17"),
        "type_pattern": "[[type:Back]]",
    })
    handled, _ = addon.handle_js_message((False, None), "show_standard_ai_analysis", None)
    assert handled is True
    assert addon.current_analysis_context["analysis_mode"] == "standard"
    assert addon.current_analysis_context["cache_key"] == standard_panel_key

    exact_match_cache_key = build_current_analysis_cache_key(addon, mw.reviewer.card, "I visited my grandmother.")
    addon.call_ai_api = lambda **kwargs: '{\n  "score": 1,\n  "tips": "Too low.",\n  "sample_answers": ["I visited my grandmother."],\n  "question_variants": []\n}'
    parsed_exact_match = addon.analyze_answer_with_ai("How was your weekend?", "I visited my grandmother.", ["I visited my grandmother."], "I visited my grandmother.")
    assert parsed_exact_match["score"] == 10
    addon.analysis_results[exact_match_cache_key] = parsed_exact_match

    speaking_cache_key = build_current_analysis_cache_key(addon, mw.reviewer.card, "I went to see family.")
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

    loading_analysis_key = build_current_analysis_cache_key(addon, mw.reviewer.card, "17")
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

    perfect_cache_key = build_current_analysis_cache_key(addon, mw.reviewer.card, "221")
    addon.analysis_results[perfect_cache_key] = {"scored": True, "score": 10, "tips": "Perfect."}
    perfect_rendered = addon.render_enhanced_comparison("<div>anki compare</div>", "221", "221", "[[type:Back]]")
    assert 'data-score-tier="excellent"' in perfect_rendered
    assert "--aqi-score-bg:" not in perfect_rendered
    assert "Perfect." in perfect_rendered

    alt_card = DummyCard(model_name="card_1", template_name="card_1_score")
    alt_card.note()["Front"] = "What is your name?"
    alt_card.note()["Back"] = "My name is Long"
    alt_card.note()["Back_variants"] = "<b>I'm Long</b>;;Long is my name;;[sound:name.mp3];;I'm Long"
    alt_card.question = lambda: "What is your name? [[type:Back]]"
    mw.reviewer.card = alt_card
    alt_cache_key = build_current_analysis_cache_key(addon, alt_card, "Long")
    addon.analysis_results[alt_cache_key] = {
        "scored": True,
        "score": 4,
        "tips": "Too short.",
        "sample_answers": ["Sample only answer"],
    }
    alt_rendered = addon.render_enhanced_comparison("<div>anki compare</div>", "My name is Long", "Long", "[[type:Back]]")
    assert "My name is Long" in alt_rendered
    assert '<pre class="ak-pre"><code' not in alt_rendered
    assert "I&#x27;m Long" in alt_rendered
    assert "Long is my name" in alt_rendered
    assert "[sound:name.mp3]" not in alt_rendered
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

    previous_config = dict(mw.addonManager.config)
    addon.save_config(
        {
            "general": {
                "language": "english",
                "show_anki_compare": True,
                "show_code_compare": True,
            },
            "modes": {
                "standard": {
                    "enabled": True,
                    "provider": "custom_openai",
                    "model": "cx/gpt-5.4-mini",
                    "prompt_profile": "strict_stem",
                    "max_tokens": 100,
                    "temperature": 0.7,
                },
                "deep": {
                    "enabled": True,
                    "provider": "custom_openai",
                    "model": "cx/gpt-5.5",
                    "prompt_profile": "speaking_flexible",
                    "max_tokens": 300,
                    "temperature": 0.4,
                },
            },
            "providers": {
                "custom_openai": {
                    "base_url": "http://127.0.0.1:20128/v1",
                    "api_key": "",
                    "custom_models": ["cx/gpt-5.4-mini", "cx/gpt-5.5"],
                }
            },
        }
    )
    assert hasattr(addon, "build_analysis_request")
    standard_request = addon.build_analysis_request(mw.reviewer.card, "17", "standard")
    deep_request = addon.build_analysis_request(mw.reviewer.card, "17", "deep")
    assert standard_request["analysis_mode"] == "standard"
    assert deep_request["analysis_mode"] == "deep"
    assert standard_request["question_text"] == deep_request["question_text"] == "13 * 17 = ?"
    assert standard_request["canonical_answer"] == deep_request["canonical_answer"] == "221"
    assert standard_request["accepted_answers"] == deep_request["accepted_answers"] == ["221", "two hundred twenty-one", "221.0"]
    assert standard_request["provider"] == deep_request["provider"] == "custom_openai"
    assert standard_request["model"] == "cx/gpt-5.4-mini"
    assert deep_request["model"] == "cx/gpt-5.5"
    assert standard_request["prompt_profile"] == "strict_stem"
    assert deep_request["prompt_profile"] == "speaking_flexible"
    assert standard_request["max_tokens"] == 100
    assert deep_request["max_tokens"] == 300
    assert standard_request["temperature"] == 0.7
    assert deep_request["temperature"] == 0.4
    assert standard_request["use_notebooklm"] is False
    assert deep_request["use_notebooklm"] is False
    assert standard_request["notebook_id"] == deep_request["notebook_id"] == ""
    assert standard_request["context_sources"] == deep_request["context_sources"] == []
    standard_mode_cache_key = addon.build_analysis_cache_key(
        standard_request["question_text"],
        standard_request["canonical_answer"],
        standard_request["user_answer"],
        card_id=getattr(mw.reviewer.card, "id", None),
        card_ord=getattr(mw.reviewer.card, "ord", None),
        language=standard_request["language"],
        provider=standard_request["provider"],
        model=standard_request["model"],
        accepted_answers=standard_request["accepted_answers"],
        resolved_prompt_contract=addon.build_prompt_contract_hash(
            addon.get_config(),
            standard_request["language"],
            standard_request["prompt_profile"],
            "analysis",
        ),
        analysis_mode=standard_request["analysis_mode"],
        analysis_prompt_version=addon.ANALYSIS_PROMPT_VERSION,
    )
    deep_mode_cache_key = addon.build_analysis_cache_key(
        deep_request["question_text"],
        deep_request["canonical_answer"],
        deep_request["user_answer"],
        card_id=getattr(mw.reviewer.card, "id", None),
        card_ord=getattr(mw.reviewer.card, "ord", None),
        language=deep_request["language"],
        provider=deep_request["provider"],
        model=deep_request["model"],
        accepted_answers=deep_request["accepted_answers"],
        resolved_prompt_contract=addon.build_prompt_contract_hash(
            addon.get_config(),
            deep_request["language"],
            deep_request["prompt_profile"],
            "analysis",
        ),
        analysis_mode=deep_request["analysis_mode"],
        analysis_prompt_version=addon.ANALYSIS_PROMPT_VERSION,
    )
    assert standard_mode_cache_key != deep_mode_cache_key
    addon.save_config(
        {
            "general": {
                "language": "english",
                "show_anki_compare": True,
                "show_code_compare": True,
            },
            "modes": {
                "standard": {
                    "enabled": True,
                    "provider": "custom_openai",
                    "model": "cx/gpt-5.4-mini",
                    "prompt_profile": "strict_stem",
                    "max_tokens": 100,
                    "temperature": 0.7,
                },
                "deep": {
                    "enabled": False,
                    "provider": "custom_openai",
                    "model": "   ",
                    "prompt_profile": "speaking_flexible",
                    "max_tokens": 300,
                    "temperature": 0.4,
                },
            },
            "providers": {
                "custom_openai": {
                    "base_url": "http://127.0.0.1:20128/v1",
                    "api_key": "",
                    "custom_models": ["cx/gpt-5.4-mini"],
                }
            },
        }
    )
    blank_deep_runtime = addon.resolve_ai_runtime_config(addon.get_config(), analysis_mode="deep")
    assert blank_deep_runtime["analysis_mode"] == "deep"
    assert blank_deep_runtime["model"] == ""
    assert blank_deep_runtime["availability_reason"] == "Deep analysis disabled"
    addon.save_config(
        {
            "general": {
                "language": "english",
                "show_anki_compare": True,
                "show_code_compare": True,
            },
            "modes": {
                "standard": {
                    "enabled": True,
                    "provider": "custom_openai",
                    "model": "cx/gpt-5.4-mini",
                    "prompt_profile": "strict_stem",
                    "max_tokens": 100,
                    "temperature": 0.7,
                },
                "deep": {
                    "enabled": True,
                    "provider": "custom_openai",
                    "model": "   ",
                    "prompt_profile": "speaking_flexible",
                    "max_tokens": 300,
                    "temperature": 0.4,
                },
            },
            "providers": {
                "custom_openai": {
                    "base_url": "http://127.0.0.1:20128/v1",
                    "api_key": "",
                    "custom_models": ["cx/gpt-5.4-mini"],
                }
            },
        }
    )
    blank_deep_model_runtime = addon.resolve_ai_runtime_config(addon.get_config(), analysis_mode="deep")
    assert blank_deep_model_runtime["analysis_mode"] == "deep"
    assert blank_deep_model_runtime["model"] == ""
    assert blank_deep_model_runtime["availability_reason"] == "Deep analysis model not configured"
    addon.save_config(
        {
            "enabled": True,
            "language": "english",
            "provider": "openai",
            "openai_api_key": "token",
            "provider": "custom_openai",
            "custom_openai_base_url": "http://127.0.0.1:20128/v1",
            "custom_openai_api_key": "",
            "custom_openai_model": "cx/gpt-5.4-mini",
            "standard_prompt_profile": "strict_stem",
            "deep_prompt_profile": "speaking_flexible",
            "custom_openai_deep_model": "cx/gpt-5.5",
        }
    )
    install_sync_background(mw)
    api_calls = []
    addon.call_ai_api = lambda **kwargs: api_calls.append(kwargs) or '{"score": 6, "tips": "Think deeper.", "sample_answers": ["221"], "question_variants": ["17 * 13 = ?"]}'
    standard_request = addon.build_analysis_request(mw.reviewer.card, "17", "standard")
    deep_request = addon.build_analysis_request(mw.reviewer.card, "17", "deep")
    standard_cache_key = addon.build_analysis_cache_key(
        standard_request["question_text"],
        standard_request["canonical_answer"],
        standard_request["user_answer"],
        card_id=getattr(mw.reviewer.card, "id", None),
        card_ord=getattr(mw.reviewer.card, "ord", None),
        language=standard_request["language"],
        provider=standard_request["provider"],
        model=standard_request["model"],
        analysis_mode=standard_request["analysis_mode"],
        max_tokens=standard_request["max_tokens"],
        temperature=standard_request["temperature"],
        accepted_answers=standard_request["accepted_answers"],
        resolved_prompt_contract=addon.build_prompt_contract_hash(
            addon.get_config(),
            standard_request["language"],
            standard_request["prompt_profile"],
            "analysis",
        ),
        analysis_prompt_version=addon.ANALYSIS_PROMPT_VERSION,
    )
    deep_cache_key = addon.build_analysis_cache_key(
        deep_request["question_text"],
        deep_request["canonical_answer"],
        deep_request["user_answer"],
        card_id=getattr(mw.reviewer.card, "id", None),
        card_ord=getattr(mw.reviewer.card, "ord", None),
        language=deep_request["language"],
        provider=deep_request["provider"],
        model=deep_request["model"],
        analysis_mode=deep_request["analysis_mode"],
        max_tokens=deep_request["max_tokens"],
        temperature=deep_request["temperature"],
        accepted_answers=deep_request["accepted_answers"],
        resolved_prompt_contract=addon.build_prompt_contract_hash(
            addon.get_config(),
            deep_request["language"],
            deep_request["prompt_profile"],
            "analysis",
        ),
        analysis_prompt_version=addon.ANALYSIS_PROMPT_VERSION,
    )
    addon.store_ai_analysis(("221", "17"), "[[type:Back]]", analysis_mode="deep")
    assert api_calls[-1]["model"] == "cx/gpt-5.5"
    assert addon.current_analysis_context["analysis_mode"] == "deep"
    assert addon.current_analysis_context["cache_key"] == deep_cache_key
    assert addon.current_analysis_context["standard_cache_key"] == standard_cache_key
    assert addon.analysis_results[deep_cache_key]["score"] == 6
    addon.regenerate_ai_analysis()
    assert api_calls[-1]["model"] == "cx/gpt-5.5"
    assert addon.current_analysis_context["analysis_mode"] == "deep"
    assert addon.current_analysis_context["cache_key"] == deep_cache_key
    notebooklm_source = read_addon_source()
    assert "Use NotebookLM MCP" in notebooklm_source
    assert "Refresh NotebookLM Session" in notebooklm_source
    assert "Refresh Notebook List" in notebooklm_source
    assert "Target Notebook" in notebooklm_source

    addon.save_config(
        {
            "general": {
                "language": "english",
                "show_anki_compare": True,
                "show_code_compare": True,
            },
            "modes": {
                "standard": {
                    "enabled": True,
                    "provider": "custom_openai",
                    "model": "cx/gpt-5.4-mini",
                    "prompt_profile": "strict_stem",
                    "max_tokens": 100,
                    "temperature": 0.7,
                },
                "deep": {
                    "enabled": True,
                    "provider": "custom_openai",
                    "model": "cx/gpt-5.5",
                    "prompt_profile": "speaking_flexible",
                    "max_tokens": 300,
                    "temperature": 0.4,
                    "use_notebooklm": True,
                    "notebook_id": "nb-123",
                    "notebook_title": "Notebook One",
                },
            },
            "providers": {
                "custom_openai": {
                    "base_url": "http://127.0.0.1:20128/v1",
                    "api_key": "",
                    "custom_models": ["cx/gpt-5.4-mini", "cx/gpt-5.5"],
                }
            },
        }
    )
    notebooklm_runtime = addon.resolve_ai_runtime_config(addon.get_config(), analysis_mode="deep")
    assert notebooklm_runtime["mode_settings"]["use_notebooklm"] is True
    assert notebooklm_runtime["mode_settings"]["notebook_id"] == "nb-123"
    assert notebooklm_runtime["mode_settings"]["notebook_title"] == "Notebook One"

    notebooklm_request = addon.build_analysis_request(mw.reviewer.card, "17", "deep")
    assert notebooklm_request["use_notebooklm"] is True
    assert notebooklm_request["notebook_id"] == "nb-123"
    assert notebooklm_request["notebook_title"] == "Notebook One"
    notebooklm_disabled_request = dict(notebooklm_request)
    notebooklm_disabled_request["use_notebooklm"] = False
    notebooklm_disabled_request["notebook_id"] = ""
    notebooklm_disabled_request["notebook_title"] = ""
    assert addon.build_analysis_request_cache_key(mw.reviewer.card, notebooklm_request) != addon.build_analysis_request_cache_key(mw.reviewer.card, notebooklm_disabled_request)

    listed_notebooks = []
    queried_notebooks = []
    notebooklm_prompts = []
    original_list_notebooklm_notebooks = addon.list_notebooklm_notebooks
    addon.list_notebooklm_notebooks = lambda *args, **kwargs: listed_notebooks.append((args, kwargs)) or []
    addon.query_notebooklm_context = lambda notebook_id, query_text, timeout_s=None: queried_notebooks.append((notebook_id, query_text, timeout_s)) or "NotebookLM confirms 221 is correct."
    addon.call_ai_api = lambda **kwargs: notebooklm_prompts.append(kwargs["messages"][-1]["content"]) or '{"score": 8, "tips": "Good."}'
    notebooklm_result = addon.analyze_answer_request(notebooklm_request, card=mw.reviewer.card)
    assert queried_notebooks and queried_notebooks[-1][0] == "nb-123"
    assert listed_notebooks == []
    assert notebooklm_result["sources_used"] == ["notebooklm"]
    assert notebooklm_result["warnings"] == []
    assert "NotebookLM" in notebooklm_prompts[-1]

    normalized_context, was_trimmed = addon.normalize_notebooklm_context_text("A  \n" * 5000)
    assert len(normalized_context) <= 4000
    assert was_trimmed is True

    missing_notebook_request = dict(notebooklm_request)
    missing_notebook_request["notebook_id"] = ""
    missing_notebook_request["notebook_title"] = ""
    addon.call_ai_api = lambda **kwargs: '{"score": 5, "tips": "Fallback."}'
    missing_notebook_result = addon.analyze_answer_request(missing_notebook_request, card=mw.reviewer.card)
    assert any("no target notebook selected" in warning.lower() for warning in missing_notebook_result["warnings"])
    assert missing_notebook_result["sources_used"] == []

    addon.list_notebooklm_notebooks = original_list_notebooklm_notebooks

    original_start_notebooklm_session = addon._start_notebooklm_session
    original_stop_notebooklm_session = addon._stop_notebooklm_session
    original_notebooklm_tool_call = addon._notebooklm_tool_call
    addon._start_notebooklm_session = lambda: {"proc": object(), "next_id": 2}
    addon._stop_notebooklm_session = lambda session: None
    addon._notebooklm_tool_call = lambda session, name, arguments, timeout_s: {"result": {"structuredContent": {"status": "error", "error": "RPC Error 16: Authentication expired"}}}
    try:
        addon.list_notebooklm_notebooks()
        raise AssertionError("Expected notebook_list error to raise")
    except RuntimeError as exc:
        assert "Authentication expired" in str(exc)
    finally:
        addon._start_notebooklm_session = original_start_notebooklm_session
        addon._stop_notebooklm_session = original_stop_notebooklm_session
        addon._notebooklm_tool_call = original_notebooklm_tool_call

    install_sync_background(mw)
    addon.query_notebooklm_context = lambda notebook_id, query_text, timeout_s=None: "NotebookLM confirms 221."
    addon.call_ai_api = lambda **kwargs: '{"score": 9, "tips": "Deep with NotebookLM."}'
    notebooklm_cache_key = addon.build_analysis_request_cache_key(mw.reviewer.card, notebooklm_request)
    addon.invalidate_analysis_state(notebooklm_cache_key)
    addon.store_ai_analysis(("221", "17"), "[[type:Back]]", analysis_mode="deep")
    assert addon.analysis_results[notebooklm_cache_key]["score"] == 9
    assert notebooklm_cache_key not in addon.ai_analysis_cache

    addon.save_config(previous_config)

    plain_card = DummyCard(model_name="card_1")
    mw.reviewer.card = plain_card
    plain_payload = addon.build_analysis_prompt_payload(plain_card, "17")
    plain_cache_key = build_current_analysis_cache_key(addon, plain_card, plain_payload["user_answer"])
    addon.store_ai_analysis(("221", "17"), "[[type:Back]]")
    assert plain_cache_key not in addon.is_analyzing
    assert addon.render_enhanced_comparison("<div>plain compare</div>", "221", "17", "[[type:Back]]") == "<div>plain compare</div>"

    note_type_score_only_card = DummyCard(model_name="card_1_score", template_name="card_1")
    assert addon.should_score_card(note_type_score_only_card) is False

    template_score_card = DummyCard(model_name="card_1", template_name="card_1_score")
    mw.reviewer.card = template_score_card
    assert addon.should_score_card(template_score_card) is True

    template_score_contains_card = DummyCard(model_name="card_1", template_name="card_1_score_clozeanything1")
    assert addon.should_score_card(template_score_contains_card) is True
    assert addon.get_card_capabilities(template_score_contains_card)["scoreable"] is True

    template_score_contains_card.note()["Front"] = "This is a |(c1::cat|)."
    template_score_contains_card.note()["Back"] = ""
    template_score_contains_card.note()["Back_variants"] = ""
    template_score_contains_card.note()["Back"] = ""
    template_score_contains_card.note()["Back_variants"] = ""
    cloze_canonical, cloze_answers = addon.build_accepted_answer_pool(template_score_contains_card)
    assert cloze_canonical == "cat"
    assert cloze_answers == ["cat"]

    cloze_payload = addon.build_analysis_prompt_payload(template_score_contains_card, "cat")
    assert cloze_payload["front_text_raw"] == "This is a |(c1::cat|)."
    assert cloze_payload["cloze_targets"] == ["cat"]

    template_score_contains_card.note()["Back"] = "dog"
    cloze_conflict_canonical, cloze_conflict_answers = addon.build_accepted_answer_pool(template_score_contains_card)
    assert cloze_conflict_canonical == "dog"
    assert cloze_conflict_answers == ["dog"]

    template_score_contains_card.note()["Back"] = "cat"
    template_score_contains_card.note()["Back_variants"] = "kitty;;feline"
    cloze_back_canonical, cloze_back_answers = addon.build_accepted_answer_pool(template_score_contains_card)
    assert cloze_back_canonical == "cat"
    assert cloze_back_answers == ["cat", "kitty", "feline"]

    template_score_contains_card.note()["Back"] = ""
    template_score_contains_card.note()["Back_variants"] = ""
    template_score_contains_card.note()["Back2"] = "dog"
    template_score_contains_card.note()["Back2_variants"] = "hound;;canine"
    template_score_contains_card.note()["Front"] = "This is a |(c1::cat|) and a |(c2::dog|)."
    grouped_targets = addon.extract_grouped_cloze_targets_from_front(template_score_contains_card.note()["Front"])
    assert grouped_targets == {1: ["cat"], 2: ["dog"]}

    standard_front = "This is a ((c1::cat)) and a ((c2::dog))."
    assert addon.extract_grouped_cloze_targets_from_front(standard_front) == {1: ["cat"], 2: ["dog"]}

    mixed_front = "This is a ((c1::cat)) and a |(c2::dog|)."
    assert addon.extract_grouped_cloze_targets_from_front(mixed_front) == {1: ["cat"], 2: ["dog"]}
    assert addon.resolve_slot_field_names(1) == {
        "answer_field": "Back",
        "answer_variants_field": "Back_variants",
        "hint_field": "Hint",
    }
    assert addon.resolve_slot_field_names(2) == {
        "answer_field": "Back2",
        "answer_variants_field": "Back2_variants",
        "hint_field": "Hint2",
    }
    assert addon.resolve_slot_field_names(3) == {
        "answer_field": "Back3",
        "answer_variants_field": "Back3_variants",
        "hint_field": "Hint3",
    }
    assert addon.resolve_slot_field_names(4) == {
        "answer_field": "Back4",
        "answer_variants_field": "Back4_variants",
        "hint_field": "Hint4",
    }
    assert addon.resolve_slot_field_names(5) == {
        "answer_field": "Back5",
        "answer_variants_field": "Back5_variants",
        "hint_field": "Hint5",
    }
    assert addon.resolve_slot_field_names(6) == {
        "answer_field": "Back6",
        "answer_variants_field": "Back6_variants",
        "hint_field": "Hint6",
    }
    assert addon.resolve_answer_field_names(1) == ("Back", "Back_variants")
    assert addon.resolve_answer_field_names(2) == ("Back2", "Back2_variants")
    assert addon.resolve_answer_field_names(3) == ("Back3", "Back3_variants")
    assert addon.resolve_answer_field_names(4) == ("Back4", "Back4_variants")
    assert addon.resolve_answer_field_names(5) == ("Back5", "Back5_variants")
    assert addon.resolve_answer_field_names(6) == ("Back6", "Back6_variants")
    assert addon.get_active_cloze_index(template_score_contains_card) == 1
    assert addon.get_manual_hint_html(template_score_contains_card) == "Base hint"

    multi_contract = addon.build_answer_contract(template_score_contains_card)
    assert multi_contract["mode"] == "single"
    assert multi_contract["active_cloze_index"] == 1
    assert multi_contract["canonical_segments"] == ["cat"]
    assert multi_contract["canonical_joined_answer"] == "cat"
    assert multi_contract["accepted_joined_answers"] == ["cat"]
    assert multi_contract["cloze_targets"] == ["cat"]
    assert multi_contract["is_valid"] is True
    multi_cloze_canonical, multi_cloze_answers = addon.build_accepted_answer_pool(template_score_contains_card)
    assert multi_cloze_canonical == "cat"
    assert multi_cloze_answers == ["cat"]

    multi_payload = addon.build_analysis_prompt_payload(template_score_contains_card, "cat")
    assert multi_payload["question_text"] == addon.get_active_visible_question(template_score_contains_card)
    assert multi_payload["active_cloze_index"] == 1
    assert multi_payload["canonical_answer"] == "cat"
    assert multi_payload["expected_answer"] == "cat"
    assert multi_payload["accepted_answers"] == ["cat"]
    assert multi_payload["cloze_targets"] == ["cat"]

    template_score_contains_card.note()["Front"] = standard_front
    template_score_contains_card.ord = 1
    assert addon.get_active_cloze_index(template_score_contains_card) == 2
    ord2_contract = addon.build_answer_contract(template_score_contains_card)
    assert ord2_contract["mode"] == "single"
    assert ord2_contract["active_cloze_index"] == 2
    assert ord2_contract["canonical_segments"] == ["dog"]
    assert ord2_contract["canonical_joined_answer"] == "dog"
    assert ord2_contract["accepted_joined_answers"] == ["dog", "hound", "canine"]
    ord2_payload = addon.build_analysis_prompt_payload(template_score_contains_card, "dog")
    assert ord2_payload["active_cloze_index"] == 2
    assert ord2_payload["canonical_answer"] == "dog"
    assert ord2_payload["expected_answer"] == "dog"
    assert ord2_payload["accepted_answers"] == ["dog", "hound", "canine"]
    assert ord2_payload["cloze_targets"] == ["dog"]
    assert addon.get_manual_hint_html(template_score_contains_card) == "Second hint"
    assert addon.is_accepted_answer_match("hound", ["cat"], card=template_score_contains_card) is True

    template_score_contains_card.note()["Back3"] = "owl"
    template_score_contains_card.note()["Back3_variants"] = ""
    template_score_contains_card.note()["Back4"] = "fox"
    template_score_contains_card.note()["Back4_variants"] = ""
    template_score_contains_card.note()["Back5"] = "wolf"
    template_score_contains_card.note()["Back5_variants"] = ""
    template_score_contains_card.note()["Back6"] = "bear"
    template_score_contains_card.note()["Back6_variants"] = ""
    template_score_contains_card.ord = 2
    assert addon.get_manual_hint_html(template_score_contains_card) == "Third hint"
    template_score_contains_card.ord = 3
    assert addon.get_manual_hint_html(template_score_contains_card) == "Fourth hint"

    template_score_contains_card.ord = 3
    sparse_contract = addon.build_answer_contract(template_score_contains_card)
    assert sparse_contract["active_cloze_index"] == 4
    assert sparse_contract["is_valid"] is False
    assert "c4" in sparse_contract["invalid_reason"]

    template_score_contains_card.note()["Front"] = "This is a |(c1::cat|) and a |(c2::dog|) and a |(c3::owl|) and a |(c4::fox|) and a |(c5::wolf|) and a |(c6::bear|)."
    template_score_contains_card.ord = 4
    assert addon.get_manual_hint_html(template_score_contains_card) == "Fifth hint"
    c5_contract = addon.build_answer_contract(template_score_contains_card)
    assert c5_contract["is_valid"] is True
    assert c5_contract["active_cloze_index"] == 5
    assert c5_contract["canonical_joined_answer"] == "wolf"

    template_score_contains_card.ord = 5
    assert addon.get_manual_hint_html(template_score_contains_card) == "Sixth hint"
    c6_contract = addon.build_answer_contract(template_score_contains_card)
    assert c6_contract["is_valid"] is True
    assert c6_contract["active_cloze_index"] == 6
    assert c6_contract["canonical_joined_answer"] == "bear"

    template_score_contains_card.ord = 1
    del template_score_contains_card.note()["Back2"]
    del template_score_contains_card.note()["Back2_variants"]
    missing_field_contract = addon.build_answer_contract(template_score_contains_card)
    assert missing_field_contract["is_valid"] is False
    assert "Back2" in missing_field_contract["invalid_reason"]
    del template_score_contains_card.note()["Hint2"]
    assert addon.get_manual_hint_html(template_score_contains_card) == ""
    template_score_contains_card.note()["Back2"] = "dog"
    template_score_contains_card.note()["Back2_variants"] = "hound;;canine"
    template_score_contains_card.note()["Hint2"] = "Second hint"

    unresolved_cloze_card = DummyCard(model_name="card_1_score_clozeanything1", template_name="card_1_score_clozeanything1")
    unresolved_cloze_card.note()["Hint"] = "Should not leak"
    unresolved_cloze_card.ord = None
    unresolved_cloze_card.question = lambda: "This is a |(c1::cat|). [[type:Back]]"
    unresolved_contract = addon.build_answer_contract(unresolved_cloze_card)
    assert unresolved_contract["is_valid"] is False
    assert addon.get_manual_hint_html(unresolved_cloze_card) == ""

    template_score_contains_card.ord = 0
    multiline_front = "|(c1::Also unser Deutschkurskollege liegt im Krankenhaus.\nWir sollten ihn diese Woche besuchen.|)\n|(c1::Wann hast du Zeit?|)"
    template_score_contains_card.note()["Front"] = multiline_front
    template_score_contains_card.note()["Back"] = "Wann hast du Zeit?"
    template_score_contains_card.note()["Back_variants"] = ""
    multiline_targets = addon.extract_cloze_targets_from_front(multiline_front)
    assert multiline_targets == [
        "Also unser Deutschkurskollege liegt im Krankenhaus.\nWir sollten ihn diese Woche besuchen.",
        "Wann hast du Zeit?",
    ]
    grouped_multiline_targets = addon.extract_grouped_cloze_targets_from_front(multiline_front)
    assert grouped_multiline_targets == {
        1: [
            "Also unser Deutschkurskollege liegt im Krankenhaus.\nWir sollten ihn diese Woche besuchen.",
            "Wann hast du Zeit?",
        ]
    }
    multiline_contract = addon.build_answer_contract(template_score_contains_card)
    assert multiline_contract["mode"] == "multi_segment"
    assert multiline_contract["is_valid"] is False
    assert multiline_contract["canonical_joined_answer"] == "Also unser Deutschkurskollege liegt im Krankenhaus. Wir sollten ihn diese Woche besuchen. Wann hast du Zeit?"
    assert multiline_contract["canonical_display_answer"] == "Also unser Deutschkurskollege liegt im Krankenhaus.\nWir sollten ihn diese Woche besuchen.\nWann hast du Zeit?"

    multiline_display_model = addon.build_expected_display_model(template_score_contains_card, multiline_contract["canonical_joined_answer"])
    assert multiline_display_model == {
        "primary_expected": "Also unser Deutschkurskollege liegt im Krankenhaus.\nWir sollten ihn diese Woche besuchen.\nWann hast du Zeit?",
        "alternative_expected_answers": [],
    }

    template_score_contains_card.note()["Back"] = "Also unser Deutschkurskollege liegt im Krankenhaus.<br>Wir sollten ihn diese Woche besuchen.<br>Wann hast du Zeit?"
    template_score_contains_card.note()["Back_variants"] = "Unser Deutschkurskollege liegt im Krankenhaus.<br>Wir sollten ihn diese Woche besuchen.<br>Wann passt es dir?"
    multiline_valid_contract = addon.build_answer_contract(template_score_contains_card)
    assert multiline_valid_contract["mode"] == "multi_segment"
    assert multiline_valid_contract["is_valid"] is True
    assert multiline_valid_contract["canonical_display_answer"] == "Also unser Deutschkurskollege liegt im Krankenhaus.<br>Wir sollten ihn diese Woche besuchen.<br>Wann hast du Zeit?"
    assert multiline_valid_contract["accepted_joined_answers"] == [
        "Also unser Deutschkurskollege liegt im Krankenhaus.<br>Wir sollten ihn diese Woche besuchen.<br>Wann hast du Zeit?",
        "Unser Deutschkurskollege liegt im Krankenhaus.<br>Wir sollten ihn diese Woche besuchen.<br>Wann passt es dir?",
    ]
    multiline_canonical, multiline_answers = addon.build_accepted_answer_pool(template_score_contains_card)
    assert multiline_canonical == "Also unser Deutschkurskollege liegt im Krankenhaus. Wir sollten ihn diese Woche besuchen. Wann hast du Zeit?"
    assert multiline_answers == [
        "Also unser Deutschkurskollege liegt im Krankenhaus.<br>Wir sollten ihn diese Woche besuchen.<br>Wann hast du Zeit?",
        "Unser Deutschkurskollege liegt im Krankenhaus.<br>Wir sollten ihn diese Woche besuchen.<br>Wann passt es dir?",
    ]
    multiline_valid_display_model = addon.build_expected_display_model(template_score_contains_card, multiline_canonical)
    assert multiline_valid_display_model == {
        "primary_expected": "Also unser Deutschkurskollege liegt im Krankenhaus.<br>Wir sollten ihn diese Woche besuchen.<br>Wann hast du Zeit?",
        "alternative_expected_answers": [
            "Unser Deutschkurskollege liegt im Krankenhaus.<br>Wir sollten ihn diese Woche besuchen.<br>Wann passt es dir?",
        ],
    }
    template_score_contains_card.note()["Back"] = "Wann hast du Zeit?"
    template_score_contains_card.note()["Back_variants"] = ""


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

    mw.reviewer.card = template_score_contains_card
    addon.call_ai_api = lambda **kwargs: '{\n  "score": 9,\n  "tips": "Good.",\n  "question_variants": ["ignore me", "ignore me too"]\n}'
    unavailable_or_cloze = addon.analyze_answer_with_ai("This is a |(c1::cat|) and a |(c2::dog|).", "", ["cat", "dog"], "cat")
    assert unavailable_or_cloze.get("scored") is False
    assert "not available" in unavailable_or_cloze["tips"].lower() or "multiple cloze" in unavailable_or_cloze["tips"].lower()

    template_score_contains_card.note()["Front"] = "This is a |(c1::cat|)."
    template_score_contains_card.note()["Back"] = ""
    template_score_contains_card.note()["Back_variants"] = ""
    addon.call_ai_api = lambda **kwargs: '{\n  "score": 7,\n  "tips": "Fine.",\n  "question_variants": ["ignore me", "ignore me too"]\n}'
    parsed_cloze = addon.analyze_answer_with_ai("This is a |(c1::cat|).", "cat", ["cat"], "cat")
    assert parsed_cloze["score"] == 10
    assert parsed_cloze["sample_answers"] == []
    assert parsed_cloze["question_variants"] == []

    addon.save_config({"enabled": False, "prompt_profile": "default"})
    mw.reviewer.card = template_score_card

    addon.current_hint_context.update({"cache_key": "keep-me", "card_id": 1})
    addon.front_hint_panel_state.update({"cache_key": "keep-me", "is_open": True})
    mw.addonManager.config = {"enabled": True, "use_custom_prompt": True, "provider": "openai"}
    persisted_before = dict(mw.addonManager.config)
    resolved_cfg = addon.get_config()
    assert resolved_cfg["prompt_profile"] == "custom"
    assert mw.addonManager.config == persisted_before
    assert addon.current_hint_context["cache_key"] == "keep-me"
    assert addon.front_hint_panel_state["cache_key"] == "keep-me"

    template_score_card.note()["Hint"] = "<script>alert(1)</script><b>Factor pairs</b> **bold**"
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
    assert "<script>" not in front_rendered
    assert "alert(1)" not in front_rendered
    assert "<b>Factor pairs</b>" not in front_rendered
    assert "Factor pairs" in front_rendered
    assert "<strong>bold</strong>" in front_rendered
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
    assert any("aqi-front-hint-body" in command for command in mw.reviewer.web.commands[-2:])
    assert "syncTypedAnswerFooter()" in mw.reviewer.web.commands[-1]

    stale_card = DummyCard(model_name="card_1_score", template_name="card_1_score")
    stale_card.id = 2
    stale_card._note["Front"] = "19 * 19 = ?"
    stale_card._note["Back"] = "361"
    stale_card._note["Hint"] = "Second card hint"
    stale_card.question = lambda: "19 * 19 = ? [[type:Back]]"
    preserved_hint_context = dict(addon.current_hint_context)
    active_card = mw.reviewer.card
    mw.reviewer.web.commands.clear()
    mw.reviewer.card = stale_card
    addon.refresh_current_front_hint_panel(loading_hint_context["cache_key"])
    assert not mw.reviewer.web.commands
    assert addon.current_hint_context == preserved_hint_context
    mw.reviewer.card = active_card

    addon.save_config({"enabled": False, "prompt_profile": "default"})
    unavailable_hint = addon.suggest_ai_hint()
    assert unavailable_hint["status"] == "unavailable"
    assert unavailable_hint["hint_text"] == ""
    assert unavailable_hint["error_text"]
    assert addon.normalize_hint_result('{"hint":"Focus on conditions, not only the position."}') == {
        "status": "ready",
        "hint_text": "Focus on conditions, not only the position.",
        "error_text": "",
    }

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
    assert 'Return exactly one JSON object with key "hint"' in api_calls[0]["messages"][1]["content"]
    assert addon.current_hint_context["question_text"] == "13 * 17 = ?"
    assert addon.front_hint_panel_state["is_open"] is True
    assert mw.reviewer.web.commands
    assert any("&lt;221&gt;" in command for command in mw.reviewer.web.commands[-3:])
    ready_hint_rendered = addon.render_front_hint_panel("<div>front side</div>", template_score_card, "Question")
    assert addon.get_hint_ui_texts("english")["ai_hint_label"] in ready_hint_rendered
    assert 'class="aqi-section-label"' in ready_hint_rendered
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

    reviewer_context = type("Reviewer", (), {})()
    web_content = types.SimpleNamespace(head="", body="")
    addon.inject_multiline_type_input(web_content, reviewer_context)
    assert ".aqi-section-label {" in web_content.head
    assert "font-family: var(--aqi-font-body) !important;" in web_content.head
    assert ".aqi-active-question," in web_content.head
    assert ".aqi-choice-list," in web_content.head
    assert ".aqi-active-question,\n.sqv-active-question {\n  font-family: inherit;" in web_content.head
    assert ".aqi-choice-list,\n.sqv-choice-list {\n  font-family: inherit;" in web_content.head

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
    assert "syncTypedAnswerFooter()" in mw.reviewer.web.commands[-1]
    assert any("aqi-front-hint-body" in command for command in mw.reviewer.web.commands[-2:])
    addon.refresh_ai_analysis_panel_dom("<div class='aqi-analysis-panel-wrap'>patched</div>")
    assert "aqi-analysis-panel-wrap" in mw.reviewer.web.commands[-1]
    assert "MathJax" in mw.reviewer.web.commands[-1] or "typeset" in mw.reviewer.web.commands[-1]


if __name__ == "__main__":
    main()





