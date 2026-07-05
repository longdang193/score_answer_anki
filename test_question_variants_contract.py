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
    pass


class DummyCard:
    def __init__(self, card_id=1, note_fields=None, rendered_question=None):
        self.id = card_id
        self._note = DummyNote(
            note_fields
            or {
                "Front": "13 * 17 = ?",
                "Front_variants": "17 * 13 = ?;;221 = 13 * ?",
                "Back": "221",
                "Back_variants": "two hundred twenty-one;;221.0",
            }
        )
        front = self._note.get("Front", "")
        self._rendered_question = rendered_question or f"{front} [[type:Back]]"

    def note(self):
        return self._note

    def question(self):
        return self._rendered_question


class DummyReviewer:
    def __init__(self):
        self.card = DummyCard()
        self.web = DummyWebView()

    def _showAnswer(self):
        return None

class DummyWebView:
    def __init__(self):
        self.commands = []

    def eval(self, command):
        self.commands.append(command)


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


def second_choice(seq):
    return seq[1]


def main():
    addon, _mw = load_addon_module()

    card = DummyCard()

    visible_pool = addon.build_visible_question_pool(card)
    assert visible_pool == ["13 * 17 = ?", "17 * 13 = ?", "221 = 13 * ?"]

    canonical_answer, answer_pool = addon.build_accepted_answer_pool(card)
    assert canonical_answer == "221"
    assert answer_pool == ["221", "two hundred twenty-one", "221.0"]

    dup_card = DummyCard(
        card_id=9,
        note_fields={
            "Front": "13 * 17 = ?",
            "Front_variants": "17 * 13 = ?",
            "Back": "221",
            "Back_variants": "two hundred twenty-one;; ;;221.0;;two hundred twenty-one",
        },
    )
    dup_canonical_answer, dup_answer_pool = addon.build_accepted_answer_pool(dup_card)
    assert dup_canonical_answer == "221"
    assert dup_answer_pool == ["221", "two hundred twenty-one", "221.0"]

    assert hasattr(addon, "build_expected_display_model")
    primary_only_model = addon.build_expected_display_model(None, "221")
    assert primary_only_model == {
        "primary_expected": "221",
        "alternative_expected_answers": [],
    }

    assert addon.evaluate_question_variant_compatibility("13 * 17 = ?", canonical_answer, answer_pool) == "compatible"
    assert addon.evaluate_question_variant_compatibility("17 * 13 = ?", canonical_answer, answer_pool) == "compatible"
    assert addon.evaluate_question_variant_compatibility("221 = 13 * ?", canonical_answer, answer_pool) == "incompatible"
    assert addon.evaluate_question_variant_compatibility("Capital of France?", "Paris", ["Paris"]) == "unsupported"

    eligible = addon.get_eligible_question_variants(card)
    assert eligible == ["13 * 17 = ?", "17 * 13 = ?"]

    chosen = addon.get_or_choose_active_question_variant(card, rng=second_choice)
    assert chosen == "17 * 13 = ?"
    assert addon.get_or_choose_active_question_variant(card, rng=lambda seq: seq[0]) == "17 * 13 = ?"

    rendered = addon.apply_question_variant_to_rendered_question(card.question(), card, "Question")
    assert "17 * 13 = ?" in rendered
    assert "13 * 17 = ?" in rendered
    assert "221 = 13 * ?" not in rendered
    assert "sqv-active-question" in rendered
    assert "sqv-choice-list" in rendered
    assert "#ffffff" not in rendered

    class Reviewer:
        pass

    web_content = types.SimpleNamespace(head="")
    addon.inject_multiline_type_input(web_content, Reviewer())
    assert '@import url("_card-base-shared.css")' in web_content.head
    assert ".aqi-panel-title" in web_content.head
    assert "font-size: 18px;" in web_content.head
    assert "font-family: var(--aqi-font-body) !important;" in web_content.head
    assert "gap: 8px;" in web_content.head
    assert "margin-bottom: 8px;" in web_content.head
    assert "padding: 16px;" in web_content.head
    assert "width: 38px;" in web_content.head
    assert "height: 38px;" in web_content.head
    assert "display: inline-flex;" in web_content.head
    assert "justify-content: center;" in web_content.head
    assert "font-size: 24px;" in web_content.head
    assert "--sqv-question-fg" in web_content.head
    assert "--sqv-input-bg" in web_content.head
    assert "#typeans" in web_content.head
    normalized_head = web_content.head.replace("\r\n", "\n")
    assert ".sqv-active-question {\n  font-size: clamp(28px, 5vw, 36px);" not in normalized_head
    assert ".sqv-active-question {\n  font-family: var(--aqi-font-body) !important;" not in normalized_head
    assert ".sqv-question-block {\n  margin: 0 auto 18px auto;\n  max-width: 780px;\n  text-align: center;" not in normalized_head
    assert ".sqv-choice-list {\n  text-align: center;" in normalized_head

    invalid_card = DummyCard(
        card_id=2,
        note_fields={
            "Front": "221 = 13 * ?",
            "Front_variants": "",
            "Back": "221",
            "Back_variants": "17",
        },
    )
    assert addon.get_question_variant_mismatch_reason(invalid_card) is not None

    addon.active_question_state.clear()
    first_pick = addon.get_or_choose_active_question_variant(card, rng=lambda seq: seq[0])
    second_card = DummyCard(
        card_id=3,
        note_fields={
            "Front": "13 * 17 = ?",
            "Front_variants": "17 * 13 = ?",
            "Back": "221",
            "Back_variants": "221.0",
        },
    )
    second_pick = addon.get_or_choose_active_question_variant(second_card, rng=second_choice)
    assert first_pick == "13 * 17 = ?"
    assert second_pick == "17 * 13 = ?"


    variant_sequence = iter(["17 * 13 = ?", "13 * 17 = ?"])
    original_choose_question_variant = addon.choose_question_variant
    addon.choose_question_variant = lambda candidates, rng=None: next(variant_sequence)
    addon.reset_active_question_state()
    try:
        first_front = addon.apply_question_variant_to_rendered_question(card.question(), card, "Question")
        same_exposure_front = addon.apply_question_variant_to_rendered_question(card.question(), card, "Question")
        answer_render = addon.apply_question_variant_to_rendered_question(card.question(), card, "Answer")
        next_exposure_front = addon.apply_question_variant_to_rendered_question(card.question(), card, "Question")
    finally:
        addon.choose_question_variant = original_choose_question_variant

    assert "17 * 13 = ?" in first_front
    assert "17 * 13 = ?" in same_exposure_front
    assert "17 * 13 = ?" in answer_render
    assert addon.get_active_question_variant(card) == "13 * 17 = ?"
    assert "13 * 17 = ?" in next_exposure_front

    addon.analysis_results["analysis-key"] = {"scored": True, "score": 8, "tips": "Good."}
    addon.current_analysis_context.update({"card_id": card.id, "cache_key": "analysis-key"})
    before_refresh_variant = addon.get_active_question_variant(card)
    assert addon.refresh_current_ai_analysis_panel({"card_id": card.id, "cache_key": "analysis-key"}) is True
    assert addon.get_active_question_variant(card) == before_refresh_variant
    assert _mw.reviewer.web.commands
    assert "aqi-analysis-panel-wrap" in _mw.reviewer.web.commands[-1]

if __name__ == "__main__":
    main()
