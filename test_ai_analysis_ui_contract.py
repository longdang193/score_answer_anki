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


class DummyCard:
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

    prompt = addon.get_language_specific_prompt("english", "13 * 17 = ?", "221", "2")
    assert "review_suggestion" not in prompt

    addon.analysis_results[cache_key] = {"scored": True, "score": 0, "tips": "Wrong."}
    rendered = addon.render_enhanced_comparison("<div>anki compare</div>", "221", "2", "[[type:Back]]")
    assert "Question Context" not in rendered
    assert "Review Suggestion" not in rendered
    assert "Regenerate Analysis" in rendered

    handled, _ = addon.handle_js_message((False, None), "regenerate_ai_analysis", None)
    assert handled is True


if __name__ == "__main__":
    main()
