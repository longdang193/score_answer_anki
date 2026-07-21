from __future__ import annotations

from aqt import mw

HINT_UI_TEXTS = {
    "english": {
        "hint_toggle": "Hint",
        "hint_label": "Hint",
        "ai_hint_label": "AI Hint",
        "suggest_hint": "Suggest Hint",
        "hint_unavailable": "AI hint not available",
    },
    "french": {
        "hint_toggle": "Indice",
        "hint_label": "Indice",
        "ai_hint_label": "Indice IA",
        "suggest_hint": "Suggérer un indice",
        "hint_unavailable": "Indice IA non disponible",
    },
    "spanish": {
        "hint_toggle": "Pista",
        "hint_label": "Pista",
        "ai_hint_label": "Pista IA",
        "suggest_hint": "Sugerir pista",
        "hint_unavailable": "Pista IA no disponible",
    },
    "german": {
        "hint_toggle": "Hinweis",
        "hint_label": "Hinweis",
        "ai_hint_label": "KI-Hinweis",
        "suggest_hint": "Hinweis vorschlagen",
        "hint_unavailable": "KI-Hinweis nicht verfügbar",
    },
    "russian": {
        "hint_toggle": "Подсказка",
        "hint_label": "Подсказка",
        "ai_hint_label": "Подсказка ИИ",
        "suggest_hint": "Предложить подсказку",
        "hint_unavailable": "Подсказка ИИ недоступна",
    },
    "japanese": {
        "hint_toggle": "ヒント",
        "hint_label": "ヒント",
        "ai_hint_label": "AIヒント",
        "suggest_hint": "ヒントを提案",
        "hint_unavailable": "AIヒントは利用できません",
    },
    "chinese": {
        "hint_toggle": "提示",
        "hint_label": "提示",
        "ai_hint_label": "AI 提示",
        "suggest_hint": "生成提示",
        "hint_unavailable": "AI 提示不可用",
    },
    "korean": {
        "hint_toggle": "힌트",
        "hint_label": "힌트",
        "ai_hint_label": "AI 힌트",
        "suggest_hint": "힌트 제안",
        "hint_unavailable": "AI 힌트를 사용할 수 없습니다",
    },
}

AI_UI_TEXTS = {
    "english": {"loading_title": "AI in progress...", "loading_body": "Please wait while AI works", "loading_note": "Automatic refresh...", "regenerate": "Regenerate", "ai_analysis_sample_answers": "Sample Answers", "ai_analysis_question_variants": "Alternative Questions"},
    "french": {"loading_title": "IA en cours...", "loading_body": "Veuillez patienter pendant que l'IA travaille", "loading_note": "Actualisation automatique...", "regenerate": "Relancer", "ai_analysis_sample_answers": "Exemples de réponses", "ai_analysis_question_variants": "Questions alternatives"},
    "spanish": {"loading_title": "IA en progreso...", "loading_body": "Por favor espera mientras la IA trabaja", "loading_note": "Actualización automática...", "regenerate": "Regenerar", "ai_analysis_sample_answers": "Ejemplos de respuestas", "ai_analysis_question_variants": "Preguntas alternativas"},
    "german": {"loading_title": "KI läuft...", "loading_body": "Bitte warten Sie, während die KI arbeitet", "loading_note": "Automatische Aktualisierung...", "regenerate": "Neu erzeugen", "ai_analysis_sample_answers": "Beispielantworten", "ai_analysis_question_variants": "Alternative Fragen"},
    "russian": {"loading_title": "ИИ в процессе...", "loading_body": "Подождите, пока ИИ работает", "loading_note": "Автоматическое обновление...", "regenerate": "Повторить", "ai_analysis_sample_answers": "Примеры ответов", "ai_analysis_question_variants": "Альтернативные вопросы"},
    "japanese": {"loading_title": "AI処理中...", "loading_body": "AIの処理が完了するまでお待ちください", "loading_note": "自動更新...", "regenerate": "再生成", "ai_analysis_sample_answers": "回答例", "ai_analysis_question_variants": "別の質問例"},
    "chinese": {"loading_title": "AI 处理中...", "loading_body": "请稍候，AI 正在工作", "loading_note": "自动刷新...", "regenerate": "重新生成", "ai_analysis_sample_answers": "示例答案", "ai_analysis_question_variants": "替代问题"},
    "korean": {"loading_title": "AI 진행 중...", "loading_body": "AI가 작업하는 동안 잠시만 기다려 주세요", "loading_note": "자동 새로고침...", "regenerate": "다시 생성", "ai_analysis_sample_answers": "예시 답변", "ai_analysis_question_variants": "대체 질문"},
}

LANG_TO_LABELS = {
    "english":   {"expected": "Expected",  "provided": "Your answer", "empty": "No answer entered"},
    "french":    {"expected": "Attendu",   "provided": "Saisi", "empty": "Aucune réponse saisie"},
    "spanish":   {"expected": "Esperado",  "provided": "Ingresado", "empty": "No se ingresó ninguna respuesta"},
    "german":    {"expected": "Erwartet",  "provided": "Eingegeben", "empty": "Keine Antwort eingegeben"},
    "russian":   {"expected": "Ожидаемый ответ", "provided": "Ваш ответ", "empty": "Ответ не введён"},
    "japanese":  {"expected": "期待される回答", "provided": "あなたの回答", "empty": "回答が入力されていません"},
    "chinese":   {"expected": "期望答案", "provided": "你的回答", "empty": "未输入答案"},
    "korean":    {"expected": "정답", "provided": "내 답변", "empty": "입력한 답변 없음"},
}

def _get_language_bundle(language="english") -> dict:
    key = str(language or "english").lower()
    return LANGUAGE_REGISTRY.get(key, LANGUAGE_REGISTRY["english"])

def get_compare_labels(config: dict) -> dict:
    key = (config or {}).get("language", "english")
    base = _get_language_bundle(key)["compare_labels"]
    overrides = (config or {}).get("labels", {}) or {}
    return {
        "expected": overrides.get("expected", base["expected"]),
        "provided": overrides.get("provided", base["provided"]),
        "empty": base["empty"],
    }

def _detect_ui_lang_code() -> str:
    # Try to detect Anki UI language, fall back to 'en'
    try:
        from aqt import mw
        pm = getattr(mw, "pm", None)
        if pm:
            # common possibilities across Anki versions
            for attr in ("uiLanguage", "language", "lang"):
                if hasattr(pm, attr):
                    val = getattr(pm, attr)
                    if callable(val):
                        val = val()
                    if isinstance(val, str) and val:
                        return val.lower()[:2]
            meta = getattr(pm, "meta", None)
            if isinstance(meta, dict):
                for k in ("locale", "lang", "language"):
                    v = meta.get(k)
                    if isinstance(v, str) and v:
                        return v.lower()[:2]
        # try aqt.lang if present
        try:
            import aqt.lang as _alang
            lang = getattr(_alang, "current_lang", None)
            if isinstance(lang, str) and lang:
                return lang.lower()[:2]
        except Exception:
            pass
    except Exception:
        pass
    return "en"

LANGUAGES = {
    "english": {
        "name": "English",
        "ai_analysis": "AI Analysis",
        "review_suggestion": "Review Suggestion",
        "analyzing": "AI Analysis in progress...",
        "ai_not_available": "AI analysis not available",
        "no_tips_available": "No tips available",
        "suggestions": {
            "Again": "Again",
            "Hard": "Hard", 
            "Good": "Good",
            "Easy": "Easy"
        }
    },
    "french": {
        "name": "Français",
        "ai_analysis": "Analyse IA",
        "review_suggestion": "Suggestion de révision",
        "analyzing": "Analyse IA en cours...",
        "ai_not_available": "Analyse IA non disponible",
        "no_tips_available": "Aucun conseil disponible",
        "suggestions": {
            "Again": "Encore",
            "Hard": "Difficile", 
            "Good": "Correct",
            "Easy": "Facile"
        }
    },
    "spanish": {
        "name": "Español",
        "ai_analysis": "Análisis IA",
        "review_suggestion": "Sugerencia de revisión",
        "analyzing": "Análisis IA en progreso...",
        "ai_not_available": "Análisis IA no disponible",
        "no_tips_available": "Sin consejos disponibles",
        "suggestions": {
            "Again": "De nuevo",
            "Hard": "Difícil", 
            "Good": "Bien",
            "Easy": "Fácil"
        }
    },
    "german": {
        "name": "Deutsch",
        "ai_analysis": "KI-Analyse",
        "review_suggestion": "Wiederholungsvorschlag",
        "analyzing": "KI-Analyse läuft...",
        "ai_not_available": "KI-Analyse nicht verfügbar",
        "no_tips_available": "Keine Tipps verfügbar",
        "suggestions": {
            "Again": "Nochmal",
            "Hard": "Schwer", 
            "Good": "Gut",
            "Easy": "Einfach"
        }
    },
    "russian": {
        "name": "Русский",
        "ai_analysis": "Анализ ИИ",
        "review_suggestion": "Рекомендация по повторению",
        "analyzing": "Идет анализ ИИ...",
        "ai_not_available": "Анализ ИИ недоступен",
        "no_tips_available": "Советы недоступны",
        "suggestions": {
            "Again": "Снова",
            "Hard": "Трудно",
            "Good": "Хорошо",
            "Easy": "Легко"
        }
    },
    "japanese": {
        "name": "日本語",
        "ai_analysis": "AI分析",
        "review_suggestion": "復習の提案",
        "analyzing": "AI分析中...",
        "ai_not_available": "AI分析は利用できません",
        "no_tips_available": "利用できるヒントがありません",
        "suggestions": {
            "Again": "もう一度",
            "Hard": "難しい",
            "Good": "良い",
            "Easy": "簡単"
        }
    },
    "chinese": {
        "name": "中文",
        "ai_analysis": "AI 分析",
        "review_suggestion": "复习建议",
        "analyzing": "AI 正在分析...",
        "ai_not_available": "AI 分析不可用",
        "no_tips_available": "暂无可用建议",
        "suggestions": {
            "Again": "重来",
            "Hard": "困难",
            "Good": "良好",
            "Easy": "简单"
        }
    },
    "korean": {
        "name": "한국어",
        "ai_analysis": "AI 분석",
        "review_suggestion": "복습 제안",
        "analyzing": "AI 분석 진행 중...",
        "ai_not_available": "AI 분석을 사용할 수 없습니다",
        "no_tips_available": "사용 가능한 팁이 없습니다",
        "suggestions": {
            "Again": "다시",
            "Hard": "어려움",
            "Good": "좋음",
            "Easy": "쉬움"
        }
    }
}

LANGUAGE_INSTRUCTION_NAMES = {
    "english": "English",
    "french": "French",
    "spanish": "Spanish",
    "german": "German",
    "russian": "Russian",
    "japanese": "Japanese",
    "chinese": "Chinese",
    "korean": "Korean",
}

for language_key, language_entry in LANGUAGES.items():
    language_entry.setdefault("display_name", language_entry.get("name", LANGUAGE_INSTRUCTION_NAMES.get(language_key, "English")))
    language_entry.setdefault("instruction_name", LANGUAGE_INSTRUCTION_NAMES.get(language_key, language_entry.get("display_name", "English")))

LANGUAGE_REGISTRY = {
    language_key: {
        "ui": language_entry,
        "hint_ui": HINT_UI_TEXTS.get(language_key, HINT_UI_TEXTS["english"]),
        "ai_ui": AI_UI_TEXTS.get(language_key, AI_UI_TEXTS["english"]),
        "compare_labels": LANG_TO_LABELS.get(language_key, LANG_TO_LABELS["english"]),
    }
    for language_key, language_entry in LANGUAGES.items()
}

CONFIG_UI_TEXTS = {
    "en": {
        "menu_title": "AI Multi-Provider Configuration",
        "window_title": "AI Multi-Provider Configuration",
        "show_anki_compare": "Show Anki default comparison",
        "show_code_compare": "Show code comparison block",
        "ai_provider": "AI Provider:",
        "analysis_language": "Analysis language:",
        "enable_ai": "Enable AI analysis",
        "max_tokens": "Feedback length:",
        "feedback_length_help": "Lower = shorter, faster feedback.",
        "temperature": "Temperature (0-1):",
        "use_custom_prompt": "Use custom prompt template",
        "custom_system_prompt": "Custom system prompt (optional):",
        "custom_analysis_prompt": "Custom analysis prompt template (supports {question}, {expected_answer}, {user_answer}, {language}):",
        "custom_system_placeholder": "If empty, language default system prompt is used.",
        "reset_custom_prompt": "Reset prompts to defaults",
        "copied_default_prompts": "Default prompts copied to clipboard.",
        "add_model_id": "Add model ID",
        "model_id_placeholder": "provider/model-id",
        "test_api": "Test API Connection",
        "testing": "Testing...",
        "save": "Save",
        "cancel": "Cancel",
        "saved": "Configuration saved!",
        "enter_api_key": "Please enter an API key to test the connection.",
        "connection_success": "Connection successful with {provider}!\n\nResponse: {response}",
        "connection_error": "Connection error with {provider}:\n\n{error}",
    },
    "fr": {
        "menu_title": "Configuration IA multi-fournisseurs",
        "window_title": "Configuration IA multi-fournisseurs",
        "show_anki_compare": "Afficher la comparaison par defaut d'Anki",
        "show_code_compare": "Afficher le bloc de comparaison de code",
        "ai_provider": "Fournisseur IA :",
        "analysis_language": "Langue d'analyse :",
        "enable_ai": "Activer l'analyse IA",
        "max_tokens": "Feedback length :",
        "temperature": "Temperature (0-1) :",
        "use_custom_prompt": "Utiliser un prompt personnalise",
        "custom_system_prompt": "Prompt systeme personnalise (optionnel) :",
        "custom_analysis_prompt": "Template du prompt d'analyse (variables {question}, {expected_answer}, {user_answer}, {language}) :",
        "custom_system_placeholder": "Si vide, le prompt systeme par defaut de la langue est utilise.",
        "reset_custom_prompt": "Reinitialiser les prompts par defaut",
        "copied_default_prompts": "Prompts par defaut copies dans le presse-papiers.",
        "add_model_id": "Ajouter un ID de modele",
        "model_id_placeholder": "provider/model-id",
        "test_api": "Tester la connexion API",
        "testing": "Test en cours...",
        "save": "Enregistrer",
        "cancel": "Annuler",
        "saved": "Configuration enregistree !",
        "enter_api_key": "Veuillez saisir une cle API pour tester la connexion.",
        "connection_success": "Connexion reussie avec {provider} !\n\nReponse : {response}",
        "connection_error": "Erreur de connexion avec {provider} :\n\n{error}",
    },
    "es": {
        "menu_title": "Configuracion IA multi-proveedor",
        "window_title": "Configuracion IA multi-proveedor",
        "show_anki_compare": "Mostrar comparacion por defecto de Anki",
        "show_code_compare": "Mostrar bloque de comparacion de codigo",
        "ai_provider": "Proveedor de IA:",
        "analysis_language": "Idioma de analisis:",
        "enable_ai": "Activar analisis IA",
        "max_tokens": "Feedback length:",
        "temperature": "Temperatura (0-1):",
        "use_custom_prompt": "Usar plantilla de prompt personalizada",
        "custom_system_prompt": "Prompt de sistema personalizado (opcional):",
        "custom_analysis_prompt": "Plantilla del prompt de analisis (variables {question}, {expected_answer}, {user_answer}, {language}):",
        "custom_system_placeholder": "Si esta vacio, se usa el prompt de sistema por defecto del idioma.",
        "test_api": "Probar conexion API",
        "testing": "Probando...",
        "save": "Guardar",
        "cancel": "Cancelar",
        "saved": "Configuracion guardada!",
        "enter_api_key": "Introduce una clave API para probar la conexion.",
        "connection_success": "Conexion correcta con {provider}!\n\nRespuesta: {response}",
        "connection_error": "Error de conexion con {provider}:\n\n{error}",
    },
    "de": {
        "menu_title": "Mehranbieter-KI-Konfiguration",
        "window_title": "Mehranbieter-KI-Konfiguration",
        "show_anki_compare": "Anki-Standardvergleich anzeigen",
        "show_code_compare": "Codevergleichsblock anzeigen",
        "ai_provider": "KI-Anbieter:",
        "analysis_language": "Analysesprache:",
        "enable_ai": "KI-Analyse aktivieren",
        "max_tokens": "Feedback length:",
        "temperature": "Temperatur (0-1):",
        "use_custom_prompt": "Benutzerdefinierte Prompt-Vorlage verwenden",
        "custom_system_prompt": "Benutzerdefinierter System-Prompt (optional):",
        "custom_analysis_prompt": "Analyse-Prompt-Vorlage (Variablen {question}, {expected_answer}, {user_answer}, {language}):",
        "custom_system_placeholder": "Wenn leer, wird der sprachspezifische Standard-Systemprompt verwendet.",
        "test_api": "API-Verbindung testen",
        "testing": "Teste...",
        "save": "Speichern",
        "cancel": "Abbrechen",
        "saved": "Konfiguration gespeichert!",
        "enter_api_key": "Bitte API-Schlussel eingeben, um die Verbindung zu testen.",
        "connection_success": "Verbindung mit {provider} erfolgreich!\n\nAntwort: {response}",
        "connection_error": "Verbindungsfehler mit {provider}:\n\n{error}",
    },
    "ru": {
        "menu_title": "Настройка ИИ (мульти-провайдер)",
        "window_title": "Настройка ИИ (мульти-провайдер)",
        "show_anki_compare": "Показывать стандартное сравнение Anki",
        "show_code_compare": "Показывать блок сравнения кода",
        "ai_provider": "Провайдер ИИ:",
        "analysis_language": "Язык анализа:",
        "enable_ai": "Включить анализ ИИ",
        "max_tokens": "Feedback length:",
        "temperature": "Температура (0-1):",
        "use_custom_prompt": "Использовать пользовательский шаблон промпта",
        "custom_system_prompt": "Пользовательский системный промпт (опционально):",
        "custom_analysis_prompt": "Шаблон промпта анализа (переменные {question}, {expected_answer}, {user_answer}, {language}):",
        "custom_system_placeholder": "Если пусто, используется системный промпт языка по умолчанию.",
        "test_api": "Проверить API",
        "testing": "Проверка...",
        "save": "Сохранить",
        "cancel": "Отмена",
        "saved": "Конфигурация сохранена!",
        "enter_api_key": "Введите API-ключ для проверки соединения.",
        "connection_success": "Успешное подключение к {provider}!\n\nОтвет: {response}",
        "connection_error": "Ошибка подключения к {provider}:\n\n{error}",
    },
    "ja": {
        "menu_title": "AI マルチプロバイダー設定",
        "window_title": "AI マルチプロバイダー設定",
        "show_anki_compare": "Anki の標準比較を表示",
        "show_code_compare": "コード比較ブロックを表示",
        "ai_provider": "AI プロバイダー:",
        "analysis_language": "分析言語:",
        "enable_ai": "AI 分析を有効化",
        "max_tokens": "Feedback length:",
        "temperature": "温度 (0-1):",
        "use_custom_prompt": "カスタムプロンプトテンプレートを使用",
        "custom_system_prompt": "カスタムシステムプロンプト (任意):",
        "custom_analysis_prompt": "分析プロンプトテンプレート ({question}, {expected_answer}, {user_answer}, {language} を使用可能):",
        "custom_system_placeholder": "空の場合は言語デフォルトのシステムプロンプトを使用します。",
        "test_api": "API 接続テスト",
        "testing": "テスト中...",
        "save": "保存",
        "cancel": "キャンセル",
        "saved": "設定を保存しました！",
        "enter_api_key": "接続テストのため API キーを入力してください。",
        "connection_success": "{provider} への接続に成功しました！\n\n応答: {response}",
        "connection_error": "{provider} への接続エラー:\n\n{error}",
    },
    "zh": {
        "menu_title": "AI 多供应商配置",
        "window_title": "AI 多供应商配置",
        "show_anki_compare": "显示 Anki 默认对比",
        "show_code_compare": "显示代码对比块",
        "ai_provider": "AI 提供商：",
        "analysis_language": "分析语言：",
        "enable_ai": "启用 AI 分析",
        "max_tokens": "Feedback length:",
        "temperature": "温度 (0-1)：",
        "use_custom_prompt": "使用自定义提示词模板",
        "custom_system_prompt": "自定义系统提示词（可选）：",
        "custom_analysis_prompt": "自定义分析提示词模板（支持 {question}, {expected_answer}, {user_answer}, {language}）：",
        "custom_system_placeholder": "为空时将使用当前语言的默认系统提示词。",
        "test_api": "测试 API 连接",
        "testing": "测试中...",
        "save": "保存",
        "cancel": "取消",
        "saved": "配置已保存！",
        "enter_api_key": "请先输入 API Key 再测试连接。",
        "connection_success": "已成功连接 {provider}！\n\n响应：{response}",
        "connection_error": "连接 {provider} 失败：\n\n{error}",
    },
    "ko": {
        "menu_title": "AI 멀티 제공자 설정",
        "window_title": "AI 멀티 제공자 설정",
        "show_anki_compare": "Anki 기본 비교 표시",
        "show_code_compare": "코드 비교 블록 표시",
        "ai_provider": "AI 제공자:",
        "analysis_language": "분석 언어:",
        "enable_ai": "AI 분석 사용",
        "max_tokens": "Feedback length:",
        "temperature": "온도 (0-1):",
        "use_custom_prompt": "사용자 정의 프롬프트 템플릿 사용",
        "custom_system_prompt": "사용자 정의 시스템 프롬프트 (선택):",
        "custom_analysis_prompt": "분석 프롬프트 템플릿 ({question}, {expected_answer}, {user_answer}, {language} 지원):",
        "custom_system_placeholder": "비어 있으면 언어 기본 시스템 프롬프트를 사용합니다.",
        "test_api": "API 연결 테스트",
        "testing": "테스트 중...",
        "save": "저장",
        "cancel": "취소",
        "saved": "설정이 저장되었습니다!",
        "enter_api_key": "연결 테스트를 위해 API 키를 입력하세요.",
        "connection_success": "{provider} 연결 성공!\n\n응답: {response}",
        "connection_error": "{provider} 연결 오류:\n\n{error}",
    },
}

def get_ui_texts(language="english"):
    """Récupère les textes de l'interface selon la langue"""
    return _get_language_bundle(language)["ui"]

def get_hint_ui_texts(language="english"):
    return _get_language_bundle(language)["hint_ui"]

def get_ai_ui_texts(language="english"):
    return _get_language_bundle(language)["ai_ui"]

def get_supported_language_options() -> list[tuple[str, str]]:
    return [(language_key, _get_language_bundle(language_key)["ui"].get("display_name", language_key.title())) for language_key in LANGUAGES]

def get_config_ui_texts(config=None):
    cfg = config or {}
    sel = str(cfg.get("ui_language", "auto")).lower()
    code = _detect_ui_lang_code() if sel == "auto" else sel[:2]
    return CONFIG_UI_TEXTS.get(code, CONFIG_UI_TEXTS["en"])

def get_language_name(language_key: str) -> str:
    language_entry = _get_language_bundle(language_key)["ui"]
    return language_entry.get("instruction_name", "English")

def get_language_lock_instruction(language_key: str) -> str:
    lang_name = get_language_name(language_key)
    return (
        f'\n\nIMPORTANT OUTPUT LANGUAGE RULES:\n'
        f'- Write "tips" strictly in {lang_name}.\n'
        f'- Do not use another language for "tips".\n'
        f'- If you include mathematical expressions in "tips", use inline \\( ... \\) or display \\[ ... \\].\n'
        f'- Escape backslashes in JSON strings for math delimiters: use \\\\( ... \\\\) or \\\\[ ... \\\\] in raw JSON output.\n'
        f'- Do not use $...$ or $$...$$ for mathematical expressions.\n'
        f'- Return valid JSON only.'
    )
