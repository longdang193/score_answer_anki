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
        self.last_get_name = None
        self.last_write_name = None

    def getConfig(self, name):
        self.last_get_name = name
        return self.config

    def writeConfig(self, name, config):
        self.last_write_name = name
        self.config = dict(config)


class DummyReviewer:
    def __init__(self):
        self.card = None
        self.web = types.SimpleNamespace(eval=lambda _command: None)

    def _showAnswer(self):
        return None


class DummyMW:
    def __init__(self):
        self.addonManager = DummyAddonManager()
        self.form = types.SimpleNamespace(menuTools=DummyMenu())
        self.reviewer = DummyReviewer()
        self.pm = None
        self.taskman = types.SimpleNamespace(run_in_background=lambda task, on_done: None)


def install_fake_aqt() -> None:
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


def load_addon_module():
    install_fake_aqt()
    spec = importlib.util.spec_from_file_location(
        "addon_under_test", pathlib.Path(__file__).with_name("__init__.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    root = pathlib.Path(__file__).parent
    init_source = (root / "__init__.py").read_text(encoding="utf-8")
    assert init_source.count("def ") == 0
    assert "reviewer_ui" in init_source

    sync_source = (root / "scripts" / "sync_to_anki.ps1").read_text(encoding="utf-8")
    for required_name in (
        "__init__.py",
        "locales.py",
        "config_model.py",
        "ai_runtime.py",
        "reviewer_ui.py",
        "configs",
        "prompt_defaults.json",
    ):
        assert required_name in sync_source

    addon = load_addon_module()
    addon.save_config(addon.merge_config_with_defaults({}))
    expected_config_key = root.name
    actual_config_key = sys.modules["aqt"].mw.addonManager.last_write_name
    assert actual_config_key == expected_config_key
    for module_name in ("locales", "config_model", "ai_runtime", "reviewer_ui"):
        path = root / f"{module_name}.py"
        spec = importlib.util.spec_from_file_location(f"test_{module_name}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    legacy = addon.merge_config_with_defaults(
        {
            "provider": "custom_openai",
            "custom_openai_api_key": "key-1",
            "custom_openai_base_url": "https://example.test/v1",
            "prompt_profile": "strict_stem",
            "deep_analysis_model": "gpt-5.4",
            "max_tokens": 111,
            "temperature": 0.3,
        }
    )
    persisted_legacy = addon.build_persisted_config(legacy)
    reparsed_legacy = addon.merge_config_with_defaults(persisted_legacy)
    assert reparsed_legacy["providers"]["custom_openai"]["base_url"] == "https://example.test/v1"
    assert reparsed_legacy["modes"]["deep"]["model"] == "gpt-5.4"

    normalized = addon.merge_config_with_defaults(
        {
            "general": {"language": "german"},
            "modes": {
                "standard": {"provider": "openai", "model": "gpt-4.1-mini", "prompt_profile": "default"},
                "deep": {"enabled": True, "provider": "custom_openai", "model": "gpt-5.4", "prompt_profile": "strict_stem"},
            },
            "providers": {
                "custom_openai": {"api_key": "key-2", "base_url": "https://example.test/api"}
            },
        }
    )
    persisted_normalized = addon.build_persisted_config(normalized)
    reparsed_normalized = addon.merge_config_with_defaults(persisted_normalized)
    assert reparsed_normalized["general"]["language"] == "german"
    assert reparsed_normalized["providers"]["custom_openai"]["api_key"] == "key-2"
    assert reparsed_normalized["modes"]["deep"]["provider"] == "custom_openai"


if __name__ == "__main__":
    main()
