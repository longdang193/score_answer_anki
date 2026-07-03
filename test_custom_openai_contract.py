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


class DummyMW:
    def __init__(self):
        self.addonManager = DummyAddonManager()
        self.form = types.SimpleNamespace(menuTools=DummyMenu())
        self.reviewer = None
        self.pm = None


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
    return module


def main():
    addon = load_addon_module()

    assert "custom_openai" in addon.PROVIDERS

    merged = addon.merge_config_with_defaults({"provider": "custom_openai"})
    assert merged["custom_openai_base_url"] == ""
    assert merged["custom_openai_api_key"] == ""
    assert merged["custom_openai_model"] == ""
    assert merged["custom_openai_custom_models"] == []

    request = addon.resolve_custom_openai_request("http://127.0.0.1:20128/v1/", "")
    assert request["url"] == "http://127.0.0.1:20128/v1/chat/completions"
    assert request["headers"] == {"Content-Type": "application/json"}

    auth_request = addon.resolve_custom_openai_request("http://127.0.0.1:20128/v1", "secret")
    assert auth_request["headers"]["Authorization"] == "Bearer secret"

    try:
        addon.resolve_custom_openai_request("http://127.0.0.1:20128/v1/chat/completions", "")
    except ValueError as exc:
        assert "base URL" in str(exc)
    else:
        raise AssertionError("full endpoint input must be rejected")


if __name__ == "__main__":
    main()
