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

    def _showAnswer(self):
        return None


class DummyMW:
    def __init__(self):
        self.addonManager = DummyAddonManager()
        self.form = types.SimpleNamespace(menuTools=DummyMenu())
        self.reviewer = DummyReviewer()
        self.pm = None
        self.taskman = types.SimpleNamespace(run_in_background=lambda task, on_done: None)


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


def main():
    addon, mw = load_addon_module()

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
    assert "aqi-regenerate-btn" in rendered
    assert "aqi-panel-body" in rendered
    assert 'class="aqi-shell"' in rendered
    assert "font-family: -apple-system" not in rendered
    assert "Wrong." in rendered
    assert "⟳" in rendered

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
    assert addon.should_score_card(template_score_card) is True

    handled, _ = addon.handle_js_message((False, None), "regenerate_ai_analysis", None)
    assert handled is True


if __name__ == "__main__":
    main()
