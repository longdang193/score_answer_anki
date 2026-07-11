from __future__ import annotations

import json
import pathlib

from aqt import mw

from locales import *
from locales import _detect_ui_lang_code

ADDON_CONFIG_KEY = pathlib.Path(__file__).resolve().parent.name

def normalize_analysis_mode(value) -> str:
    return "deep" if str(value or "").strip().lower() == "deep" else "standard"

def get_provider_model_config_key(provider: str, analysis_mode: str = "standard") -> str:
    mode = normalize_analysis_mode(analysis_mode)
    return f"{provider}_{'deep_' if mode == 'deep' else ''}model"

def resolve_prompt_profile_for_mode(merged_config: dict, analysis_mode: str = "standard") -> str:
    mode_settings = get_mode_settings(merged_config, analysis_mode)
    mode_profile = normalize_prompt_profile(mode_settings.get("prompt_profile"))
    if mode_profile:
        return mode_profile
    mode = normalize_analysis_mode(analysis_mode)
    if mode == "deep":
        return normalize_prompt_profile(merged_config.get("deep_prompt_profile")) or normalize_prompt_profile(merged_config.get("standard_prompt_profile")) or normalize_prompt_profile(merged_config.get("prompt_profile")) or PROMPT_PROFILE_DEFAULT
    return normalize_prompt_profile(merged_config.get("standard_prompt_profile")) or normalize_prompt_profile(merged_config.get("prompt_profile")) or PROMPT_PROFILE_DEFAULT

def resolve_model_for_mode(merged_config: dict, provider: str, analysis_mode: str = "standard") -> str:
    mode_settings = get_mode_settings(merged_config, analysis_mode)
    fallback_model = get_provider_default_model(provider) if normalize_analysis_mode(analysis_mode) == "standard" else ""
    return str(mode_settings.get("model", fallback_model) or fallback_model).strip()

def resolve_ai_runtime_config(config=None, language: str | None = None, analysis_mode: str = "standard") -> dict:
    merged_config = merge_config_with_defaults(config)
    resolved_analysis_mode = normalize_analysis_mode(analysis_mode)
    general_settings = merged_config.get("general", {}) if isinstance(merged_config.get("general"), dict) else {}
    mode_settings = get_mode_settings(merged_config, resolved_analysis_mode)
    resolved_language = (language or general_settings.get("language", merged_config.get("language", "english")) or "english").strip() or "english"
    provider = str(mode_settings.get("provider", merged_config.get("provider", "openai")) or "openai").strip() or "openai"
    provider_settings = get_provider_settings(merged_config, provider)
    model = resolve_model_for_mode(merged_config, provider, resolved_analysis_mode)
    api_key = str(provider_settings.get("api_key", merged_config.get(f"{provider}_api_key", "")) or "").strip()
    base_url = str(provider_settings.get("base_url", merged_config.get(f"{provider}_base_url", "")) or "").strip()
    prompt_profile = resolve_prompt_profile_for_mode(merged_config, resolved_analysis_mode)
    mode_enabled = bool(mode_settings.get("enabled", True if resolved_analysis_mode == "standard" else False))
    max_tokens = int(mode_settings.get("max_tokens", merged_config.get("max_tokens", 200)) or merged_config.get("max_tokens", 200))
    temperature = float(mode_settings.get("temperature", merged_config.get("temperature", 0.7)) or merged_config.get("temperature", 0.7))
    availability_reason = ""
    if resolved_analysis_mode == "deep" and not mode_enabled:
        availability_reason = "Deep analysis disabled"
    elif resolved_analysis_mode == "standard" and not mode_enabled:
        availability_reason = "AI disabled"
    elif resolved_analysis_mode == "deep" and not model:
        availability_reason = "Deep analysis model not configured"
    elif provider == CUSTOM_OPENAI_PROVIDER:
        if not base_url:
            availability_reason = "Custom OpenAI base URL not configured"
        elif not model:
            availability_reason = "Custom OpenAI model not configured"
    elif not api_key:
        provider_name = PROVIDERS.get(provider, {}).get("name", provider)
        availability_reason = f"{provider_name} API key not configured"
    return {
        "config": merged_config,
        "general": general_settings,
        "mode_settings": mode_settings,
        "provider_settings": provider_settings,
        "analysis_mode": resolved_analysis_mode,
        "language": resolved_language,
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
        "prompt_profile": prompt_profile,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "availability_reason": availability_reason,
    }

DEFAULT_CONFIG = {
    "provider": "openai",
    "language": "english",
    "openai_api_key": "",
    "openai_model": "gpt-4.1-mini",
    "openai_deep_model": "",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-flash",
    "gemini_deep_model": "",
    "claude_api_key": "",
    "claude_model": "claude-3-5-haiku-latest",
    "claude_deep_model": "",
    "deepseek_api_key": "",
    "deepseek_model": "deepseek-chat",
    "deepseek_deep_model": "",
    "groq_api_key": "",
    "groq_model": "llama-3.3-70b-versatile",
    "groq_deep_model": "",
    "openrouter_api_key": "",
    "openrouter_model": "openrouter/free",
    "openrouter_deep_model": "",
    "custom_openai_base_url": "",
    "custom_openai_api_key": "",
    "custom_openai_model": "",
    "custom_openai_deep_model": "",
    "custom_openai_custom_models": [],
    "enabled": True,
    "max_tokens": 200,
    "temperature": 0.7,
    "show_anki_compare": True,
    "show_code_compare": True,
    "ui_language": "auto",  # 'auto' | 'en' | 'fr' | 'es' | 'de' | 'pt' | 'it' | 'ru' | 'ja' | 'zh' | 'ko'
    "prompt_profile": "default",
    "standard_prompt_profile": "default",
    "deep_prompt_profile": "default",
    "deep_analysis_model": "",
    "use_custom_prompt": False,
    "custom_system_prompt": "",
    "custom_analysis_prompt_template": "",
    "custom_hint_prompt_template": ""
}

PROMPT_PROFILE_DEFAULT = "default"

PROMPT_PROFILE_STRICT_STEM = "strict_stem"

PROMPT_PROFILE_SPEAKING_FLEXIBLE = "speaking_flexible"

PROMPT_PROFILE_CLOZE_RECALL = "cloze_recall"

PROMPT_PROFILE_CUSTOM = "custom"

PROMPT_PROFILE_CHOICES = (
    PROMPT_PROFILE_DEFAULT,
    PROMPT_PROFILE_STRICT_STEM,
    PROMPT_PROFILE_SPEAKING_FLEXIBLE,
    PROMPT_PROFILE_CLOZE_RECALL,
    PROMPT_PROFILE_CUSTOM,
)

def normalize_prompt_profile(value) -> str | None:
    profile = str(value or "").strip()
    return profile if profile in PROMPT_PROFILE_CHOICES else None

def should_show_custom_prompt_fields(*profiles: str) -> bool:
    return any(normalize_prompt_profile(profile) == PROMPT_PROFILE_CUSTOM for profile in profiles)

def build_custom_system_placeholder(ui) -> str:
    return ui.get("custom_system_placeholder", "If empty, language default system prompt is used.")

def get_score_tier(score, is_scored: bool) -> str:
    if not is_scored:
        return "na"
    if score <= 3:
        return "low"
    if score <= 5:
        return "mid"
    if score <= 8:
        return "high"
    return "excellent"


CUSTOM_OPENAI_PROVIDER = "custom_openai"

PROVIDER_KEYS = ("openai", "gemini", "claude", "deepseek", "groq", "openrouter", CUSTOM_OPENAI_PROVIDER)

def _default_provider_model_value(provider: str) -> str:
    return str(DEFAULT_CONFIG.get(f"{provider}_model", "") or "").strip()

def _build_default_general_config() -> dict:
    return {
        "language": DEFAULT_CONFIG.get("language", "english"),
        "show_anki_compare": bool(DEFAULT_CONFIG.get("show_anki_compare", True)),
        "show_code_compare": bool(DEFAULT_CONFIG.get("show_code_compare", True)),
    }

def _build_default_mode_config(mode: str) -> dict:
    default_provider = DEFAULT_CONFIG.get("provider", "openai")
    config = {
        "enabled": True if mode == "standard" else False,
        "provider": default_provider,
        "model": _default_provider_model_value(default_provider) if mode == "standard" else "",
        "prompt_profile": DEFAULT_CONFIG.get("standard_prompt_profile" if mode == "standard" else "deep_prompt_profile", PROMPT_PROFILE_DEFAULT),
        "max_tokens": DEFAULT_CONFIG.get("max_tokens", 200),
        "temperature": DEFAULT_CONFIG.get("temperature", 0.7),
    }
    if mode == "deep":
        config.update({
            "use_notebooklm": False,
            "notebook_id": "",
            "notebook_title": "",
        })
    return config

def _build_default_providers_config() -> dict:
    providers = {}
    for provider_key in PROVIDER_KEYS:
        block = {
            "api_key": str(DEFAULT_CONFIG.get(f"{provider_key}_api_key", "") or ""),
            "custom_models": list(DEFAULT_CONFIG.get(f"{provider_key}_custom_models", []) or []),
        }
        if provider_key == CUSTOM_OPENAI_PROVIDER:
            block["base_url"] = str(DEFAULT_CONFIG.get("custom_openai_base_url", "") or "")
        providers[provider_key] = block
    return providers

def get_mode_settings(config: dict, analysis_mode: str = "standard") -> dict:
    mode = normalize_analysis_mode(analysis_mode)
    modes = config.get("modes", {}) if isinstance(config, dict) else {}
    mode_settings = modes.get(mode, {}) if isinstance(modes, dict) else {}
    return dict(mode_settings) if isinstance(mode_settings, dict) else {}

def get_provider_settings(config: dict, provider: str) -> dict:
    providers = config.get("providers", {}) if isinstance(config, dict) else {}
    provider_settings = providers.get(provider, {}) if isinstance(providers, dict) else {}
    return dict(provider_settings) if isinstance(provider_settings, dict) else {}

def merge_config_with_defaults(config):
    source_config = config or {}
    merged = {
        "ui_language": source_config.get("ui_language", DEFAULT_CONFIG.get("ui_language", "auto")),
        "prompt_profile": PROMPT_PROFILE_DEFAULT,
        "use_custom_prompt": False,
        "custom_system_prompt": str(source_config.get("custom_system_prompt", DEFAULT_CONFIG.get("custom_system_prompt", "")) or ""),
        "custom_analysis_prompt_template": str(source_config.get("custom_analysis_prompt_template", DEFAULT_CONFIG.get("custom_analysis_prompt_template", "")) or ""),
        "custom_hint_prompt_template": str(source_config.get("custom_hint_prompt_template", DEFAULT_CONFIG.get("custom_hint_prompt_template", "")) or ""),
        "general": _build_default_general_config(),
        "modes": {
            "standard": _build_default_mode_config("standard"),
            "deep": _build_default_mode_config("deep"),
        },
        "providers": _build_default_providers_config(),
    }

    general = source_config.get("general", {}) if isinstance(source_config.get("general"), dict) else {}
    modes = source_config.get("modes", {}) if isinstance(source_config.get("modes"), dict) else {}
    standard_mode = modes.get("standard", {}) if isinstance(modes.get("standard"), dict) else {}
    deep_mode = modes.get("deep", {}) if isinstance(modes.get("deep"), dict) else {}
    providers = source_config.get("providers", {}) if isinstance(source_config.get("providers"), dict) else {}

    merged_prompt_profile = normalize_prompt_profile(source_config.get("prompt_profile"))
    if merged_prompt_profile is None:
        merged_prompt_profile = PROMPT_PROFILE_CUSTOM if bool(source_config.get("use_custom_prompt", False)) else PROMPT_PROFILE_DEFAULT

    merged["general"]["language"] = str(general.get("language", source_config.get("language", merged["general"]["language"])) or "english").strip() or "english"
    merged["general"]["show_anki_compare"] = bool(general.get("show_anki_compare", source_config.get("show_anki_compare", merged["general"]["show_anki_compare"])))
    merged["general"]["show_code_compare"] = bool(general.get("show_code_compare", source_config.get("show_code_compare", merged["general"]["show_code_compare"])))

    standard_profile = normalize_prompt_profile(standard_mode.get("prompt_profile")) or normalize_prompt_profile(source_config.get("standard_prompt_profile")) or merged_prompt_profile
    deep_profile = normalize_prompt_profile(deep_mode.get("prompt_profile")) or normalize_prompt_profile(source_config.get("deep_prompt_profile")) or standard_profile
    merged["prompt_profile"] = standard_profile

    legacy_standard_provider = str(source_config.get("provider", DEFAULT_CONFIG.get("provider", "openai")) or "openai").strip() or "openai"
    standard_provider = str(standard_mode.get("provider", legacy_standard_provider) or legacy_standard_provider).strip() or "openai"
    deep_provider = str(deep_mode.get("provider", standard_provider) or standard_provider).strip() or standard_provider

    legacy_standard_model = str(source_config.get(f"{standard_provider}_model", _default_provider_model_value(standard_provider)) or "").strip()
    legacy_deep_model = str(source_config.get(get_provider_model_config_key(deep_provider, "deep"), source_config.get("deep_analysis_model", "")) or "").strip()

    standard_model = str(standard_mode.get("model", legacy_standard_model or _default_provider_model_value(standard_provider)) or legacy_standard_model or _default_provider_model_value(standard_provider)).strip()
    deep_model = str(deep_mode.get("model", legacy_deep_model) or legacy_deep_model).strip()

    legacy_tokens = int(source_config.get("max_tokens", DEFAULT_CONFIG.get("max_tokens", 200)) or DEFAULT_CONFIG.get("max_tokens", 200))
    legacy_temperature = float(source_config.get("temperature", DEFAULT_CONFIG.get("temperature", 0.7)) or DEFAULT_CONFIG.get("temperature", 0.7))

    standard_enabled = bool(standard_mode.get("enabled", source_config.get("enabled", True)))
    deep_enabled = bool(deep_mode.get("enabled", bool(deep_model)))

    merged["modes"]["standard"] = {
        "enabled": standard_enabled,
        "provider": standard_provider,
        "model": standard_model,
        "prompt_profile": standard_profile,
        "max_tokens": int(standard_mode.get("max_tokens", legacy_tokens) or legacy_tokens),
        "temperature": float(standard_mode.get("temperature", legacy_temperature) or legacy_temperature),
    }
    merged["modes"]["deep"] = {
        "enabled": deep_enabled,
        "provider": deep_provider,
        "model": deep_model,
        "prompt_profile": deep_profile,
        "max_tokens": int(deep_mode.get("max_tokens", legacy_tokens) or legacy_tokens),
        "temperature": float(deep_mode.get("temperature", legacy_temperature) or legacy_temperature),
        "use_notebooklm": bool(deep_mode.get("use_notebooklm", False)),
        "notebook_id": str(deep_mode.get("notebook_id", "") or "").strip(),
        "notebook_title": str(deep_mode.get("notebook_title", "") or "").strip(),
    }

    for provider_key in PROVIDER_KEYS:
        provider_block = providers.get(provider_key, {}) if isinstance(providers.get(provider_key), dict) else {}
        merged_provider = dict(merged["providers"].get(provider_key, {}))
        merged_provider["api_key"] = str(provider_block.get("api_key", source_config.get(f"{provider_key}_api_key", merged_provider.get("api_key", ""))) or "")
        custom_models = provider_block.get("custom_models", source_config.get(f"{provider_key}_custom_models", merged_provider.get("custom_models", [])))
        merged_provider["custom_models"] = list(custom_models) if isinstance(custom_models, list) else []
        if provider_key == CUSTOM_OPENAI_PROVIDER:
            merged_provider["base_url"] = str(provider_block.get("base_url", source_config.get("custom_openai_base_url", merged_provider.get("base_url", ""))) or "")
        merged["providers"][provider_key] = merged_provider

    merged["standard_prompt_profile"] = merged["modes"]["standard"]["prompt_profile"]
    merged["deep_prompt_profile"] = merged["modes"]["deep"]["prompt_profile"]
    merged["deep_analysis_model"] = merged["modes"]["deep"]["model"]
    merged["language"] = merged["general"]["language"]
    merged["show_anki_compare"] = merged["general"]["show_anki_compare"]
    merged["show_code_compare"] = merged["general"]["show_code_compare"]
    merged["provider"] = merged["modes"]["standard"]["provider"]
    merged["enabled"] = merged["modes"]["standard"]["enabled"]
    merged["max_tokens"] = merged["modes"]["standard"]["max_tokens"]
    merged["temperature"] = merged["modes"]["standard"]["temperature"]

    for provider_key in PROVIDER_KEYS:
        provider_settings = merged["providers"][provider_key]
        merged[f"{provider_key}_api_key"] = provider_settings.get("api_key", "")
        merged[f"{provider_key}_custom_models"] = list(provider_settings.get("custom_models", []))
        if provider_key == CUSTOM_OPENAI_PROVIDER:
            merged["custom_openai_base_url"] = provider_settings.get("base_url", "")
        merged[f"{provider_key}_model"] = _default_provider_model_value(provider_key)
        merged[f"{provider_key}_deep_model"] = ""
    merged[f"{merged['modes']['standard']['provider']}_model"] = merged["modes"]["standard"]["model"]
    merged[f"{merged['modes']['deep']['provider']}_deep_model"] = merged["modes"]["deep"]["model"]

    merged["use_custom_prompt"] = False
    merged.pop("template_prompt_profile_overrides", None)
    return merged

def build_persisted_config(config):
    merged = merge_config_with_defaults(config)
    return {
        "general": dict(merged.get("general", {})),
        "modes": {
            "standard": dict(get_mode_settings(merged, "standard")),
            "deep": dict(get_mode_settings(merged, "deep")),
        },
        "providers": {provider_key: dict(merged.get("providers", {}).get(provider_key, {})) for provider_key in PROVIDER_KEYS},
        "ui_language": merged.get("ui_language", DEFAULT_CONFIG.get("ui_language", "auto")),
        "prompt_profile": merged.get("prompt_profile", PROMPT_PROFILE_DEFAULT),
        "use_custom_prompt": False,
        "custom_system_prompt": merged.get("custom_system_prompt", ""),
        "custom_analysis_prompt_template": merged.get("custom_analysis_prompt_template", ""),
        "custom_hint_prompt_template": merged.get("custom_hint_prompt_template", ""),
    }

def get_provider_default_model(provider):
    models = PROVIDERS.get(provider, {}).get("models", [])
    return models[0] if models else ""


def get_config():
    """Récupère la configuration depuis les métadonnées d'Anki"""
    try:
        saved_config = mw.addonManager.getConfig(ADDON_CONFIG_KEY) or {}
        return merge_config_with_defaults(saved_config)
    except Exception as e:
        print(f"Error loading config: {e}")
        return merge_config_with_defaults(None)


def save_config(config):
    """Sauvegarde la configuration dans les métadonnées d'Anki"""
    try:
        mw.addonManager.writeConfig(ADDON_CONFIG_KEY, build_persisted_config(config))
        try:
            from reviewer_ui import reset_hint_state

            reset_hint_state()
        except Exception:
            pass
    except Exception as e:
        print(f"Error saving config: {e}")

def build_provider_model_test_targets(standard_model: str, deep_model: str) -> list[tuple[str, str]]:
    targets = []
    standard_model = str(standard_model or "").strip()
    deep_model = str(deep_model or "").strip()
    if standard_model:
        targets.append(("standard", standard_model))
    if deep_model:
        targets.append(("deep", deep_model))
    return targets

def build_openai_compatible_headers(api_key):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers

def resolve_custom_openai_request(base_url, api_key):
    normalized_base_url = (base_url or "").strip()
    if not normalized_base_url:
        raise ValueError("Please enter a base URL for the custom provider.")

    trimmed_base_url = normalized_base_url.rstrip("/")
    if trimmed_base_url.lower().endswith("/chat/completions"):
        raise ValueError("Please enter the base URL root, not the full /chat/completions endpoint.")

    return {
        "url": trimmed_base_url + "/chat/completions",
        "headers": build_openai_compatible_headers((api_key or "").strip()),
    }

PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "url": "https://api.openai.com/v1/chat/completions",
        "models": ["gpt-4.1-nano", "gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini", "o4-mini"],
        "headers_func": lambda api_key: {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    },
    "gemini": {
        "name": "Google Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-preview-09-2025"],
        "headers_func": lambda api_key: {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }
    },
    "claude": {
        "name": "Anthropic Claude",
        "url": "https://api.anthropic.com/v1/messages",
        "models": ["claude-3-5-haiku-latest", "claude-3-5-sonnet-latest", "claude-3-7-sonnet-latest"],
        "headers_func": lambda api_key: {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
    },
    "deepseek": {
        "name": "DeepSeek",
        "url": "https://api.deepseek.com/chat/completions",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "headers_func": lambda api_key: {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    },
    "groq": {
        "name": "Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "models": ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b", "qwen-qwq-32b"],
        "headers_func": lambda api_key: {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    },
    "openrouter": {
        "name": "OpenRouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "models": [
            "openrouter/free",
            "meta-llama/llama-3.2-3b-instruct:free",
            "openai/gpt-oss-20b:free",
            "openai/gpt-oss-120b:free",
            "deepseek/deepseek-r1:free",
            "qwen/qwen3-coder:free",
            "google/gemma-3n-e2b-it:free",
            "openrouter/auto",
            "openai/gpt-4o-mini-2024-07-18",
            "google/gemini-2.5-flash",
            "anthropic/claude-3.5-haiku"
        ],
        "headers_func": lambda api_key: {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    },
    CUSTOM_OPENAI_PROVIDER: {
        "name": "Custom OpenAI-Compatible",
        "url": "",
        "models": [],
        "headers_func": lambda api_key: build_openai_compatible_headers(api_key)
    }
}

def _format_accepted_answers_for_prompt(accepted_answers) -> str:
    if isinstance(accepted_answers, str):
        return accepted_answers
    if not accepted_answers:
        return ""
    return "; ".join(str(answer) for answer in accepted_answers if str(answer).strip())

def render_prompt_template(template: str, language: str, question_text: str, true_answer: str, accepted_answers: list[str], user_answer: str, hint: str = "", front_text_raw: str = "", cloze_targets: list[str] | None = None) -> str:
    rendered = template
    replacements = {
        "{question}": question_text or "",
        "{expected_answer}": true_answer or "",
        "{accepted_answers}": _format_accepted_answers_for_prompt(accepted_answers),
        "{user_answer}": user_answer or "",
        "{language}": language or "english",
        "{hint}": hint or "",
        "{front_text_raw}": front_text_raw or "",
        "{cloze_targets}": _format_accepted_answers_for_prompt(cloze_targets or []),
    }
    for token, value in replacements.items():
        rendered = rendered.replace(token, value)
    return rendered

PROMPT_DEFAULTS_PATH = pathlib.Path(__file__).with_name("configs") / "prompt_defaults.json"

PROMPT_DEFAULT_FIELDS = (
    "system_prompt",
    "analysis_prompt_template",
    "hint_prompt_template",
)

FILE_PROMPT_PROFILE_NAMES = (
    PROMPT_PROFILE_DEFAULT,
    PROMPT_PROFILE_STRICT_STEM,
    PROMPT_PROFILE_SPEAKING_FLEXIBLE,
    PROMPT_PROFILE_CLOZE_RECALL,
)

def _prompt_defaults_error(message: str) -> ValueError:
    return ValueError(f"prompt_defaults.json: {message}")

def load_prompt_defaults_config() -> dict:
    try:
        raw = PROMPT_DEFAULTS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise _prompt_defaults_error("missing file") from exc
    except OSError as exc:
        raise _prompt_defaults_error(f"read failed: {exc}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _prompt_defaults_error(f"malformed JSON: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise _prompt_defaults_error("root must be object")
    if payload.get("version") != 1:
        raise _prompt_defaults_error("version must equal 1")

    languages = payload.get("languages")
    profiles = payload.get("profiles")
    if not isinstance(languages, dict):
        raise _prompt_defaults_error("languages must be object")
    if not isinstance(profiles, dict):
        raise _prompt_defaults_error("profiles must be object")

    expected_languages = set(LANGUAGE_REGISTRY)
    actual_languages = set(languages)
    if actual_languages != expected_languages:
        missing = sorted(expected_languages - actual_languages)
        extra = sorted(actual_languages - expected_languages)
        raise _prompt_defaults_error(f"language keys mismatch; missing={missing} extra={extra}")

    for language_key, entry in languages.items():
        if not isinstance(entry, dict):
            raise _prompt_defaults_error(f"languages.{language_key} must be object")
        for field in PROMPT_DEFAULT_FIELDS:
            value = entry.get(field)
            if not isinstance(value, str) or not value:
                raise _prompt_defaults_error(f"languages.{language_key}.{field} must be non-empty string")

    expected_profiles = set(FILE_PROMPT_PROFILE_NAMES)
    actual_profiles = set(profiles)
    if actual_profiles != expected_profiles:
        missing = sorted(expected_profiles - actual_profiles)
        extra = sorted(actual_profiles - expected_profiles)
        raise _prompt_defaults_error(f"profile keys mismatch; missing={missing} extra={extra}")

    for profile_name, entry in profiles.items():
        if not isinstance(entry, dict):
            raise _prompt_defaults_error(f"profiles.{profile_name} must be object")
        unknown_fields = sorted(set(entry) - set(PROMPT_DEFAULT_FIELDS))
        if unknown_fields:
            raise _prompt_defaults_error(f"profiles.{profile_name} has unknown fields {unknown_fields}")
        for field, value in entry.items():
            if not isinstance(value, str) or not value:
                raise _prompt_defaults_error(f"profiles.{profile_name}.{field} must be non-empty string")

    return payload

def get_prompt_defaults_for_language(language: str) -> dict[str, str]:
    payload = load_prompt_defaults_config()
    language_key = str(language or "english").lower()
    entry = payload["languages"].get(language_key, payload["languages"]["english"])
    return {field: entry[field] for field in PROMPT_DEFAULT_FIELDS}

def get_prompt_profile_defaults(profile_name: str) -> dict[str, str]:
    payload = load_prompt_defaults_config()
    normalized_profile = normalize_prompt_profile(profile_name)
    entry = payload["profiles"].get(normalized_profile, payload["profiles"][PROMPT_PROFILE_DEFAULT])
    return {field: value for field, value in entry.items() if field in PROMPT_DEFAULT_FIELDS}

def _merge_prompt_default_content(base: dict[str, str], overrides: dict[str, str]) -> dict[str, str]:
    resolved = dict(base)
    for field, value in overrides.items():
        if field == "analysis_prompt_template" and resolved.get(field):
            if "{base_analysis_prompt_template}" in value:
                resolved[field] = value.replace("{base_analysis_prompt_template}", resolved[field])
            elif value.startswith("\n"):
                resolved[field] = resolved[field] + value
            else:
                resolved[field] = value
            continue
        resolved[field] = value
    return resolved

def resolve_prompt_default_content(language: str, profile_name: str) -> dict[str, str]:
    base = get_prompt_defaults_for_language(language)
    overrides = get_prompt_profile_defaults(profile_name)
    return _merge_prompt_default_content(base, overrides)

def resolve_prompt_profile_content(config, language: str, profile_name: str) -> dict[str, str]:
    merged_config = merge_config_with_defaults(config)
    normalized_profile = normalize_prompt_profile(profile_name) or PROMPT_PROFILE_DEFAULT
    default_content = resolve_prompt_default_content(language, PROMPT_PROFILE_DEFAULT)

    if normalized_profile == PROMPT_PROFILE_CUSTOM:
        return {
            "system_prompt": (merged_config.get("custom_system_prompt", "") or "").strip() or default_content["system_prompt"],
            "analysis_prompt_template": (merged_config.get("custom_analysis_prompt_template", "") or "").strip() or default_content["analysis_prompt_template"],
            "hint_prompt_template": (merged_config.get("custom_hint_prompt_template", "") or "").strip() or default_content["hint_prompt_template"],
        }

    return resolve_prompt_default_content(language, normalized_profile)

def build_analysis_output_contract(profile: str) -> str:
    normalized_profile = normalize_prompt_profile(profile) or PROMPT_PROFILE_DEFAULT
    shared_rules = (
        "\n\nOUTPUT CONTRACT:\n"
        "- Return exactly one JSON object.\n"
        "- No markdown. No code fences. No leading or trailing text.\n"
        "- Keys must be lowercase snake_case exactly as specified.\n"
        "- score must be an integer from 0 to 10.\n"
        "- tips must be one JSON string.\n"
    )
    if normalized_profile == PROMPT_PROFILE_SPEAKING_FLEXIBLE:
        return shared_rules + (
            "- Return exactly these four keys: score, tips, sample_answers, question_variants.\n"
            "- sample_answers must be an array of 2 or 3 plain strings. No objects.\n"
            "- question_variants must be an array of 2 or 3 plain strings. No objects.\n"
            "- Do not wrap sample answers inside objects like {\"answer\": ...}.\n"
            'Example: {"score":7,"tips":"...","sample_answers":["...","..."],"question_variants":["...","..."]}'
        )
    if normalized_profile == PROMPT_PROFILE_CLOZE_RECALL:
        return shared_rules + (
            "- Return exactly these three keys: score, tips, sample_answers.\n"
            "- sample_answers must be an array of 0 to 3 plain strings. No objects.\n"
            "- Do not return question_variants.\n"
            'Example: {"score":10,"tips":"...","sample_answers":["..."]}'
        )
    return shared_rules + (
        "- Return exactly these two keys: score, tips.\n"
        "- Do not return sample_answers.\n"
        "- Do not return question_variants.\n"
        'Example: {"score":8,"tips":"..."}'
    )

def build_prompt_profile_content(config, language: str, profile: str, question_text: str, true_answer: str, accepted_answers: list[str], user_answer: str, *, front_text_raw: str = "", cloze_targets: list[str] | None = None) -> tuple[str, str]:
    resolved = resolve_prompt_profile_content(config, language, profile)
    rendered_prompt = render_prompt_template(
        resolved["analysis_prompt_template"],
        language,
        question_text,
        true_answer,
        accepted_answers,
        user_answer,
        front_text_raw=front_text_raw,
        cloze_targets=cloze_targets,
    )
    rendered_prompt += build_analysis_output_contract(profile)
    return resolved["system_prompt"], rendered_prompt
