from __future__ import annotations

import pathlib
import sys

_THIS_DIR = pathlib.Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import locales as _locales
import config_model as _config_model
import ai_runtime as _ai_runtime
import reviewer_ui as _reviewer_ui

for _module in (_locales, _config_model, _ai_runtime, _reviewer_ui):
    globals().update({name: getattr(_module, name) for name in dir(_module) if not name.startswith("__")})

for _module in (_ai_runtime, _reviewer_ui):
    _module.ADDON_EXPORTS = globals()
