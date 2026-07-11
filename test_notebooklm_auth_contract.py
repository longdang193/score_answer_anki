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

class DummyReviewer:
    card = None

class DummyMW:
    def __init__(self):
        self.addonManager = DummyAddonManager()
        self.form = types.SimpleNamespace(menuTools=DummyMenu())
        self.reviewer = DummyReviewer()
        self.pm = None
        self.taskman = types.SimpleNamespace(run_in_background=lambda task, on_done: None)

class DummyWebView:
    def eval(self, _command):
        return None

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
    return module

def main():
    addon = load_addon_module()
    assert addon.classify_notebooklm_error("RPC Error 16: Authentication expired") == "auth"

    recorded = {}

    class FakeProc:
        def __init__(self):
            self.stdin = object()
            self.stdout = object()

    addon.os.name = "nt"
    addon.subprocess.CREATE_NO_WINDOW = 134217728
    addon.subprocess.PIPE = object()
    addon.subprocess.DEVNULL = object()

    def fake_popen(_args, **kwargs):
        recorded.update(kwargs)
        return FakeProc()

    addon.subprocess.Popen = fake_popen
    addon._notebooklm_send = lambda _proc, _msg: None
    addon._notebooklm_recv = lambda _proc, _timeout_s: {"result": {}}
    addon._start_notebooklm_session()
    assert recorded["creationflags"] == addon.subprocess.CREATE_NO_WINDOW

    calls = []
    addon._start_notebooklm_session = lambda: {"proc": object(), "next_id": 1}
    addon._stop_notebooklm_session = lambda _session: None

    def fake_tool_call(_session, name, _arguments, _timeout_s):
        calls.append(name)
        if name == "refresh_auth":
            return {"result": {"structuredContent": {"status": "success", "message": "Auth tokens reloaded from disk cache."}}}
        if name == "notebook_list":
            return {"result": {"structuredContent": {"status": "error", "error": "RPC Error 16: Authentication expired"}}}
        raise AssertionError(name)

    addon._notebooklm_tool_call = fake_tool_call
    state = addon.refresh_notebooklm_session()

    assert calls == ["refresh_auth", "notebook_list"]
    assert state["status"] == "Auth required"
    assert state["notebooks"] == []

if __name__ == "__main__":
    main()