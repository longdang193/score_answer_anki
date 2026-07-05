import ast
import html
import random
import re
from aqt import gui_hooks


ai_analysis_cache = {}
is_analyzing = {}
analysis_results = {}
hint_cache = {}
is_generating_hint = {}
current_analysis_context = {}
current_hint_context = {}
active_question_state = {}
front_hint_panel_state = {}
HINT_PROMPT_VERSION = "v1"

HINT_UI_TEXTS = {
    "english": {
        "hint_toggle": "Hint",
        "hint_label": "Hint",
        "ai_hint_label": "AI Hint",
        "suggest_hint": "Suggest Hint",
        "suggest_hint_again": "Suggest Again",
        "hint_loading": "Generating hint...",
        "hint_unavailable": "AI hint not available",
    },
    "french": {
        "hint_toggle": "Indice",
        "hint_label": "Indice",
        "ai_hint_label": "Indice IA",
        "suggest_hint": "Suggérer un indice",
        "suggest_hint_again": "Suggérer encore",
        "hint_loading": "Génération de l'indice...",
        "hint_unavailable": "Indice IA non disponible",
    },
    "spanish": {
        "hint_toggle": "Pista",
        "hint_label": "Pista",
        "ai_hint_label": "Pista IA",
        "suggest_hint": "Sugerir pista",
        "suggest_hint_again": "Sugerir otra vez",
        "hint_loading": "Generando pista...",
        "hint_unavailable": "Pista IA no disponible",
    },
    "german": {
        "hint_toggle": "Hinweis",
        "hint_label": "Hinweis",
        "ai_hint_label": "KI-Hinweis",
        "suggest_hint": "Hinweis vorschlagen",
        "suggest_hint_again": "Nochmal vorschlagen",
        "hint_loading": "Hinweis wird erzeugt...",
        "hint_unavailable": "KI-Hinweis nicht verfügbar",
    },
    "russian": {
        "hint_toggle": "Подсказка",
        "hint_label": "Подсказка",
        "ai_hint_label": "Подсказка ИИ",
        "suggest_hint": "Предложить подсказку",
        "suggest_hint_again": "Предложить снова",
        "hint_loading": "Генерируется подсказка...",
        "hint_unavailable": "Подсказка ИИ недоступна",
    },
    "japanese": {
        "hint_toggle": "ヒント",
        "hint_label": "ヒント",
        "ai_hint_label": "AIヒント",
        "suggest_hint": "ヒントを提案",
        "suggest_hint_again": "もう一度提案",
        "hint_loading": "ヒントを生成中...",
        "hint_unavailable": "AIヒントは利用できません",
    },
    "chinese": {
        "hint_toggle": "提示",
        "hint_label": "提示",
        "ai_hint_label": "AI 提示",
        "suggest_hint": "生成提示",
        "suggest_hint_again": "重新生成提示",
        "hint_loading": "正在生成提示...",
        "hint_unavailable": "AI 提示不可用",
    },
    "korean": {
        "hint_toggle": "힌트",
        "hint_label": "힌트",
        "ai_hint_label": "AI 힌트",
        "suggest_hint": "힌트 제안",
        "suggest_hint_again": "다시 제안",
        "hint_loading": "힌트 생성 중...",
        "hint_unavailable": "AI 힌트를 사용할 수 없습니다",
    },
}

AI_UI_TEXTS = {
    "english": {"loading_title": "AI in progress...", "loading_body": "Please wait while AI works", "loading_note": "Automatic refresh...", "regenerate": "Regenerate", "ai_analysis_sample_answers": "Sample Answers", "ai_analysis_question_variants": "Alternative Questions"},
    "french": {"loading_title": "IA en cours...", "loading_body": "Veuillez patienter pendant que l'IA travaille", "loading_note": "Actualisation automatique...", "regenerate": "Relancer", "ai_analysis_sample_answers": "Sample Answers", "ai_analysis_question_variants": "Alternative Questions"},
    "spanish": {"loading_title": "IA en progreso...", "loading_body": "Por favor espera mientras la IA trabaja", "loading_note": "Actualización automática...", "regenerate": "Regenerar", "ai_analysis_sample_answers": "Sample Answers", "ai_analysis_question_variants": "Alternative Questions"},
    "german": {"loading_title": "KI läuft...", "loading_body": "Bitte warten Sie, während die KI arbeitet", "loading_note": "Automatische Aktualisierung...", "regenerate": "Neu erzeugen", "ai_analysis_sample_answers": "Sample Answers", "ai_analysis_question_variants": "Alternative Questions"},
    "portuguese": {"loading_title": "IA em andamento...", "loading_body": "Aguarde enquanto a IA trabalha", "loading_note": "Atualização automática...", "regenerate": "Gerar novamente", "ai_analysis_sample_answers": "Sample Answers", "ai_analysis_question_variants": "Alternative Questions"},
    "italian": {"loading_title": "IA in corso...", "loading_body": "Attendi mentre l'IA lavora", "loading_note": "Aggiornamento automatico...", "regenerate": "Rigenera", "ai_analysis_sample_answers": "Sample Answers", "ai_analysis_question_variants": "Alternative Questions"},
    "russian": {"loading_title": "ИИ в процессе...", "loading_body": "Подождите, пока ИИ работает", "loading_note": "Автоматическое обновление...", "regenerate": "Повторить", "ai_analysis_sample_answers": "Sample Answers", "ai_analysis_question_variants": "Alternative Questions"},
    "japanese": {"loading_title": "AI処理中...", "loading_body": "AIの処理が完了するまでお待ちください", "loading_note": "自動更新...", "regenerate": "再生成", "ai_analysis_sample_answers": "Sample Answers", "ai_analysis_question_variants": "Alternative Questions"},
    "chinese": {"loading_title": "AI 处理中...", "loading_body": "请稍候，AI 正在工作", "loading_note": "自动刷新...", "regenerate": "重新生成", "ai_analysis_sample_answers": "Sample Answers", "ai_analysis_question_variants": "Alternative Questions"},
    "korean": {"loading_title": "AI 진행 중...", "loading_body": "AI가 작업하는 동안 잠시만 기다려 주세요", "loading_note": "자동 새로고침...", "regenerate": "다시 생성", "ai_analysis_sample_answers": "Sample Answers", "ai_analysis_question_variants": "Alternative Questions"},
}

QUESTION_VARIANT_SEPARATOR = ";;"
QUESTION_FIELD = "Front"
QUESTION_VARIANTS_FIELD = "Front_variants"
ANSWER_FIELD = "Back"
ANSWER_VARIANTS_FIELD = "Back_variants"
QUESTION_VARIANT_MEDIA_MARKERS = (
    "[sound:",
    "<img",
    "<audio",
    "<video",
    "<object",
    "<embed",
    "<svg",
)

# translations and label helpers
# Map your config["language"] key -> labels
LANG_TO_LABELS = {
    "english":   {"expected": "Expected",  "provided": "Your answer"},
    "french":    {"expected": "Attendu",   "provided": "Saisi"},
    "spanish":   {"expected": "Esperado",  "provided": "Ingresado"},
    "german":    {"expected": "Erwartet",  "provided": "Eingegeben"},
    "portuguese":{"expected": "Esperado",  "provided": "Digitado"},
    "italian":   {"expected": "Atteso",    "provided": "Inserito"},
    "russian":   {"expected": "Ожидаемый ответ", "provided": "Ваш ответ"},
    "japanese":  {"expected": "期待される回答", "provided": "あなたの回答"},
    "chinese":   {"expected": "期望答案", "provided": "你的回答"},
    "korean":    {"expected": "정답", "provided": "내 답변"},
}

def get_compare_labels(config: dict) -> dict:
    key = (config or {}).get("language", "english")
    key = str(key).lower()
    base = LANG_TO_LABELS.get(key, LANG_TO_LABELS["english"])
    # Optional per-user overrides if you want to support them:
    # ex: config["labels"] = {"expected": "Attendu", "provided": "Votre réponse"}
    overrides = (config or {}).get("labels", {}) or {}
    return {
        "expected": overrides.get("expected", base["expected"]),
        "provided": overrides.get("provided", base["provided"]),
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

def _labels_from_config(config: dict) -> dict:
    # read configured language
    sel = (config or {}).get("ui_language", "auto")
    if sel == "auto":
        lang = _detect_ui_lang_code()
    else:
        lang = str(sel).lower()[:2]
    code_to_key = {
        "en": "english",
        "fr": "french",
        "es": "spanish",
        "de": "german",
        "pt": "portuguese",
        "it": "italian",
        "ru": "russian",
        "ja": "japanese",
        "zh": "chinese",
        "ko": "korean",
    }
    base = LANG_TO_LABELS.get(code_to_key.get(lang, "english"), LANG_TO_LABELS["english"])
    # allow future per-user overrides (optional keys)
    overrides = (config or {}).get("labels", {})
    lbl_expected = overrides.get("expected", base["expected"])
    lbl_provided = overrides.get("provided", base["provided"])
    return {"expected": lbl_expected, "provided": lbl_provided}


def extract_code_text(html_or_text: str) -> str:
    """
    Extract readable code from HTML or plaintext while preserving newlines/indentation.
    - Prefers the content inside <pre> blocks if present (common in highlighter output).
    - Strips tags/spans/line-numbering, unescapes entities.
    - Falls back to a generic HTML strip that keeps line breaks.
    """
    if not html_or_text:
        return ""
    s = html_or_text.replace('\r\n', '\n').replace('\r', '\n')

    # Prefer <pre> blocks (e.g., hilite.me wraps code in <pre> inside a table) [hilite.me](http://hilite.me/)
    pre_blocks = re.findall(r'<pre[^>]*>(.*?)</pre>', s, flags=re.IGNORECASE | re.DOTALL)
    if pre_blocks:
        parts = []
        for block in pre_blocks:
            block = re.sub(r'<br\s*/?>', '\n', block, flags=re.IGNORECASE)
            block = re.sub(r'<[^>]+>', '', block)  # strip spans/etc. inside pre
            block = html.unescape(block)
            block = '\n'.join(ln.rstrip() for ln in block.split('\n'))
            parts.append(block.strip('\n'))
        text = '\n\n'.join(parts)

        # Optional: drop leading line numbers if most lines start with digits
        lines = text.split('\n')
        if lines and sum(1 for ln in lines if re.match(r'^\s*\d+\b', ln)) >= max(3, len(lines)//2):
            lines = [re.sub(r'^\s*\d+\b\s*', '', ln) for ln in lines]
            text = '\n'.join(lines)
    else:
        # Generic HTML → text with preserved line breaks
        s = re.sub(r'<script.*?</script>', '', s, flags=re.IGNORECASE | re.DOTALL)
        s = re.sub(r'<style.*?</style>', '', s, flags=re.IGNORECASE | re.DOTALL)
        # Block-level to newline
        s = re.sub(r'</?(p|div|br|li|tr|td|th|blockquote|h[1-6]|ul|ol|pre|table)[^>]*>', '\n', s, flags=re.IGNORECASE)
        s = re.sub(r'<[^>]+>', '', s)  # remove remaining tags
        text = html.unescape(s)

    # Normalize blank lines
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text

# imports near the top
import re, html
from aqt import gui_hooks

def _to_textarea_on_question(text: str, card, kind: str) -> str:
    text = apply_question_variant_to_rendered_question(text, card, kind)

    if not kind or "Question" not in kind:
        return text

    # robust: quoted/unquoted id=typeans
    pat = re.compile(r'(?is)<input(?P<attrs>[^>]*\bid\s*=\s*(?:"|\')?typeans(?:"|\')?[^>]*)>')

    def repl(m):
        attrs = m.group('attrs')
        # strip type= and value= on textarea
        attrs = re.sub(r'\stype\s*=\s*(?:"|\')?[^"\'>\s]+(?:"|\')?', '', attrs, flags=re.I)
        attrs = re.sub(r'\svalue\s*=\s*(?:"|\').*?(?:"|\')', '', attrs, flags=re.I|re.S)
        return (
            f'<textarea{attrs} rows="10" spellcheck="false" '
            'style="width:96%;min-height:180px;'
            "font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;"
            'font-size:16px; line-height:1.4; tab-size:2;"></textarea>'
            '<script>(function(){'
            'function wireTA(ta){ if(!ta||ta.dataset.mlReady) return; ta.dataset.mlReady="1";'
            'function onEnter(e){ if(e.key==="Enter"){'
            ' if(e.ctrlKey||e.metaKey){ e.stopImmediatePropagation(); e.stopPropagation(); e.preventDefault();'
            '  if(typeof pycmd==="function") pycmd("ans");'
            ' } else { e.stopImmediatePropagation(); e.stopPropagation(); /* let default newline happen */ }'
            '} }'
            "['keydown','keypress','keyup'].forEach(function(t){ ta.addEventListener(t,onEnter,true); });"
            '}'
            'var ta=document.getElementById("typeans"); if(ta) wireTA(ta);'
            '})();</script>'
        )

    new_text, replaced = pat.subn(repl, text)

    # Fallback if no match (timing/DOM variants)
    if replaced == 0:
        new_text += """
<script>
(function(){
  function wireTA(ta){
    if(!ta||ta.dataset.mlReady) return; ta.dataset.mlReady="1";
    function onEnter(e){
      if(e.key==='Enter'){
        if(e.ctrlKey||e.metaKey){
          e.stopImmediatePropagation(); e.stopPropagation(); e.preventDefault();
          if (typeof pycmd==='function') pycmd('ans');
        } else {
          e.stopImmediatePropagation(); e.stopPropagation(); // allow newline
        }
      }
    }
    ['keydown','keypress','keyup'].forEach(function(t){ ta.addEventListener(t,onEnter,true); });
  }
  function swap(){
    var e=document.getElementById('typeans'); if(!e) return;
    if(e.tagName.toLowerCase()!=='textarea'){
      var ta=document.createElement('textarea');
      for(var i=0;i<e.attributes.length;i++){ var a=e.attributes[i]; try{ ta.setAttribute(a.name,a.value);}catch(_){} }
      ta.value=e.value||''; ta.rows=10; ta.spellcheck=false;
      ta.style.width='96%'; ta.style.minHeight='180px';
      ta.style.fontFamily='ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace';
      ta.style.fontSize='16px'; ta.style.lineHeight='1.4'; ta.style.tabSize='2';
      e.parentNode.replaceChild(ta,e); e=ta;
    }
    wireTA(e);
  }
  swap();
  var mo=new MutationObserver(function(){ swap(); });
  mo.observe(document.documentElement||document.body,{childList:true,subtree:true});
})();
</script>
"""
    return new_text

def _code_friendly_diff_on_answer(text: str, card, kind: str) -> str:
    if not kind or "Answer" not in kind:
        return text
    return """
<style>
.typeGood, .typeBad, .typeMissed {
  white-space: pre-wrap !important;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace !important;
}
</style>
""" + text


def inject_multiline_type_input(web_content, context):
    """
    Injecte CSS/JS dans le reviewer pour:
    - convertir l'input {{type:...}} en textarea multi-ligne
    - améliorer l'affichage des diffs Anki (.typeGood/Bad/Missed) pour le code
    """
    try:
        # Limiter au reviewer
        if context.__class__.__name__ != "Reviewer":
            return
    except Exception:
        return

    web_content.head += """
<style>
@import url("_card-base-shared.css");

/* Couleurs thème-aware pour les blocs de comparaison */
:root {
  --aqi-font-body: var(--shared-font-body, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
  --aqi-font-heading: var(--shared-font-heading, 'Segoe UI', sans-serif);
  --aqi-surface-bg: #f8f9fa;
  --aqi-surface-border: #6c757d;
  --aqi-copy-strong: #2c3e50;
  --aqi-copy-body: #34495e;
  --aqi-panel-body-bg: rgba(255,255,255,0.7);
  --aqi-control-bg: rgba(255,255,255,0.78);
  --aqi-control-border: rgba(0,0,0,0.08);
  --ak-code-bg: #fafafa;
  --ak-code-fg: #1b1b1b;
  --ak-code-border: #ddd;
  --ak-code-label: #222;
  --sqv-question-fg: #1f2937;
  --sqv-question-muted: #4b5563;
  --sqv-question-shadow: none;
  --sqv-chip-bg: rgba(15, 23, 42, 0.08);
  --sqv-chip-border: rgba(15, 23, 42, 0.12);
  --sqv-input-bg: #ffffff;
  --sqv-input-fg: #111827;
  --sqv-input-border: #cbd5e1;
  --aqi-score-na-bg: #f3f4f6;
  --aqi-score-na-color: #6c757d;
  --aqi-score-low-bg: #ffebee;
  --aqi-score-low-color: #f44336;
  --aqi-score-mid-bg: #fff3e0;
  --aqi-score-mid-color: #ff9800;
  --aqi-score-high-bg: #e8f5e8;
  --aqi-score-high-color: #4caf50;
  --aqi-score-excellent-bg: #e3f2fd;
  --aqi-score-excellent-color: #2196f3;
}

/* Détection du sombre dans Anki + fallback */
body.nightMode, body.night-mode, .nightMode, .night-mode, .isDark, [data-theme="dark"] {
  --aqi-surface-bg: rgba(255,255,255,0.06);
  --aqi-surface-border: #64748b;
  --aqi-copy-strong: var(--shared-night-text, #f5f5f5);
  --aqi-copy-body: var(--shared-night-muted, #d1d5db);
  --aqi-panel-body-bg: rgba(15,23,42,0.36);
  --aqi-control-bg: rgba(15,23,42,0.72);
  --aqi-control-border: rgba(148,163,184,0.28);
  --ak-code-bg: #0f1116;
  --ak-code-fg: #e6edf3;
  --ak-code-border: #2d333b;
  --ak-code-label: #e6edf3;
  --sqv-question-fg: #f3f4f6;
  --sqv-question-muted: #d1d5db;
  --sqv-question-shadow: 0 1px 2px rgba(0,0,0,0.35);
  --sqv-chip-bg: rgba(255, 255, 255, 0.14);
  --sqv-chip-border: rgba(255, 255, 255, 0.16);
  --sqv-input-bg: #111827;
  --sqv-input-fg: #f9fafb;
  --sqv-input-border: #374151;
  --aqi-score-na-bg: rgba(107,114,128,0.22);
  --aqi-score-na-color: #cbd5e1;
  --aqi-score-low-bg: rgba(239,68,68,0.18);
  --aqi-score-low-color: #fca5a5;
  --aqi-score-mid-bg: rgba(245,158,11,0.18);
  --aqi-score-mid-color: #fcd34d;
  --aqi-score-high-bg: rgba(34,197,94,0.18);
  --aqi-score-high-color: #86efac;
  --aqi-score-excellent-bg: rgba(59,130,246,0.18);
  --aqi-score-excellent-color: #93c5fd;
}

/* Fallback pour systèmes qui annoncent le thème via le média */
@media (prefers-color-scheme: dark) {
  :root {
    --aqi-surface-bg: rgba(255,255,255,0.06);
    --aqi-surface-border: #64748b;
    --aqi-copy-strong: var(--shared-night-text, #f5f5f5);
    --aqi-copy-body: var(--shared-night-muted, #d1d5db);
    --aqi-panel-body-bg: rgba(15,23,42,0.36);
    --aqi-control-bg: rgba(15,23,42,0.72);
    --aqi-control-border: rgba(148,163,184,0.28);
    --ak-code-bg: #0f1116;
    --ak-code-fg: #e6edf3;
    --ak-code-border: #2d333b;
    --ak-code-label: #e6edf3;
    --sqv-question-fg: #f3f4f6;
    --sqv-question-muted: #d1d5db;
    --sqv-question-shadow: 0 1px 2px rgba(0,0,0,0.35);
    --sqv-chip-bg: rgba(255, 255, 255, 0.14);
    --sqv-chip-border: rgba(255, 255, 255, 0.16);
    --sqv-input-bg: #111827;
    --sqv-input-fg: #f9fafb;
    --sqv-input-border: #374151;
    --aqi-score-na-bg: rgba(107,114,128,0.22);
    --aqi-score-na-color: #cbd5e1;
    --aqi-score-low-bg: rgba(239,68,68,0.18);
    --aqi-score-low-color: #fca5a5;
    --aqi-score-mid-bg: rgba(245,158,11,0.18);
    --aqi-score-mid-color: #fcd34d;
    --aqi-score-high-bg: rgba(34,197,94,0.18);
    --aqi-score-high-color: #86efac;
    --aqi-score-excellent-bg: rgba(59,130,246,0.18);
    --aqi-score-excellent-color: #93c5fd;
  }
}

.aqi-shell {
  font-family: var(--aqi-font-body) !important;
  max-width: 800px;
  margin: 0 auto;
}

.aqi-anki-compare {
  background: var(--aqi-surface-bg);
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
  border-left: 4px solid var(--aqi-surface-border);
}

.aqi-loading-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 16px;
  padding: 25px;
  margin: 20px 0;
  text-align: center;
  color: white;
  position: relative;
  overflow: hidden;
}

.aqi-loading-head {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.aqi-loading-spinner {
  width: 26px;
  height: 26px;
  border: 3px solid rgba(255,255,255,0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: aki_spin 0.9s linear infinite;
}

.aqi-loading-title {
  font-size: 18px;
  font-weight: 600;
}

.aqi-loading-copy {
  color: rgba(255,255,255,0.9);
  margin: 0;
  font-size: 14px;
}

.aqi-loading-note {
  color: rgba(255,255,255,0.7);
  margin-top: 10px;
  font-size: 12px;
  font-style: italic;
}

.sqv-question-block {
  margin: 0 auto 18px auto;
  max-width: 780px;
}

.sqv-active-question {
  margin-bottom: 10px;
}

.sqv-choice-list {
  text-align: center;
  font-size: 13px;
  line-height: 1.5;
  color: var(--sqv-question-muted) !important;
}

.sqv-choice-chip {
  display: inline-block;
  margin: 4px 6px;
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--sqv-chip-bg) !important;
  border: 1px solid var(--sqv-chip-border) !important;
  color: inherit;
}

input#typeans,
textarea#typeans,
.sqv-type-input {
  background: var(--sqv-input-bg) !important;
  color: var(--sqv-input-fg) !important;
  border: 1px solid var(--sqv-input-border) !important;
  border-radius: 12px;
  padding: 12px;
  box-sizing: border-box;
}

input#typeans:focus,
textarea#typeans:focus,
.sqv-type-input:focus {
  outline: 2px solid rgba(59, 130, 246, 0.45);
  outline-offset: 1px;
}

/* Styles des blocs de comparaison */
.ak-compare .ak-label {
  font-weight: 700;
  margin-bottom: 6px;
  color: var(--ak-code-label) !important;
}
.ak-compare .ak-pre {
  white-space: pre-wrap !important;
  padding: 10px;
  border: 1px solid var(--ak-code-border) !important;
  border-radius: 8px;
  background: var(--ak-code-bg) !important;
  color: var(--ak-code-fg) !important;
  overflow: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace !important;
}

.aqi-panel-card {
  --aqi-score-bg: var(--aqi-score-na-bg);
  --aqi-score-color: var(--aqi-score-na-color);
  border-radius: 16px;
  padding: 16px;
  margin: 16px 0;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  background: var(--aqi-score-bg);
  border: 2px solid var(--aqi-score-color);
}

.aqi-panel-card[data-score-tier="low"] {
  --aqi-score-bg: var(--aqi-score-low-bg);
  --aqi-score-color: var(--aqi-score-low-color);
}

.aqi-panel-card[data-score-tier="mid"] {
  --aqi-score-bg: var(--aqi-score-mid-bg);
  --aqi-score-color: var(--aqi-score-mid-color);
}

.aqi-panel-card[data-score-tier="high"] {
  --aqi-score-bg: var(--aqi-score-high-bg);
  --aqi-score-color: var(--aqi-score-high-color);
}

.aqi-panel-card[data-score-tier="excellent"] {
  --aqi-score-bg: var(--aqi-score-excellent-bg);
  --aqi-score-color: var(--aqi-score-excellent-color);
}

.aqi-panel-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.aqi-panel-title-wrap {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.aqi-panel-title {
  color: var(--aqi-score-color);
  margin: 0;
  font-size: 18px;
  font-weight: 650;
  font-family: var(--aqi-font-body) !important;
}

.aqi-ai-action-btn {
  background: var(--aqi-control-bg);
  color: var(--aqi-score-color);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid var(--aqi-control-border);
  font-weight: 700;
  font-size: 16px;
  line-height: 1;
  box-shadow: 0 3px 10px rgba(0,0,0,0.10);
  cursor: pointer;
  font-family: var(--aqi-font-body) !important;
}

.aqi-ai-action-btn[disabled] {
  opacity: 0.6;
  cursor: not-allowed;
}

.aqi-ai-action-icon {
  font-size: 18px;
  line-height: 1;
}

.aqi-ai-action-label {
  line-height: 1.2;
}

.aqi-regenerate-btn {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.aqi-score-badge {
  background: var(--aqi-score-color);
  color: white;
  padding: 8px 14px;
  border-radius: 999px;
  font-weight: 700;
  font-size: 16px;
  box-shadow: 0 4px 15px rgba(0,0,0,0.18);
}

.aqi-panel-body {
  padding: 14px 16px;
  background: var(--aqi-panel-body-bg);
  border-radius: 12px;
  border-left: 4px solid var(--aqi-score-color);
}

.aqi-front-hint-wrap {
  font-family: var(--aqi-font-body) !important;
  max-width: 800px;
  margin: 16px auto 0 auto;
  text-align: center;
}

.aqi-front-hint-toggle {
  appearance: none;
  border: 1px solid var(--sqv-chip-border) !important;
  background: var(--sqv-chip-bg) !important;
  color: var(--sqv-question-fg) !important;
  border-radius: 999px;
  padding: 8px 14px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.aqi-front-hint-toggle {
  margin-bottom: 12px;
}

.aqi-front-hint-card {
  margin-top: 0;
}

.aqi-front-hint-panel.is-hidden {
  display: none;
}

.aqi-front-hint-manual,
.aqi-front-hint-ai {
  margin: 0;
}

.aqi-front-hint-manual + .aqi-front-hint-ai {
  margin-top: 12px;
}

.aqi-front-hint-actions {
  margin-top: 14px;
}

.aqi-section-copy {
  color: var(--aqi-copy-body);
  margin: 0;
  line-height: 1.45;
  font-size: clamp(14px, 4vw, 16px);
  text-wrap: pretty;
}

.aqi-rich-copy > :first-child {
  margin-top: 0;
}

.aqi-rich-copy > :last-child {
  margin-bottom: 0;
}

.aqi-rich-copy p,
.aqi-rich-copy ul,
.aqi-rich-copy ol,
.aqi-rich-copy pre {
  margin: 0 0 10px 0;
}

.aqi-rich-copy ul,
.aqi-rich-copy ol {
  padding-left: 22px;
}

.aqi-rich-copy code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.aqi-rich-copy pre {
  overflow-x: auto;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.08);
}
</style>
<script>
(function(){
  function upgradeTypeAnswer(){
    var inp = document.getElementById('typeans');
    if (!inp || inp.tagName.toLowerCase() === 'textarea') return;

    // Cloner les attributs de l’input vers un textarea
    var ta = document.createElement('textarea');
    for (var i=0; i<inp.attributes.length; i++){
      var a = inp.attributes[i];
      try { ta.setAttribute(a.name, a.value); } catch(e){}
    }
    ta.value = inp.value || '';
    ta.rows = 10;
    ta.spellcheck = false;

    inp.parentNode.replaceChild(ta, inp);

    try {
      ta.focus();
      ta.setSelectionRange(ta.value.length, ta.value.length);
    } catch(e){}

    // Ctrl/Cmd+Entrée => montrer la réponse
    ta.addEventListener('keydown', function(e){
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        if (typeof pycmd === 'function') pycmd('ans');
        e.preventDefault();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', upgradeTypeAnswer);
  } else {
    upgradeTypeAnswer();
  }
})();
</script>
"""

# Activer l’injection au chargement
from aqt import gui_hooks
gui_hooks.webview_will_set_content.append(inject_multiline_type_input)

def _build_compare_variant_chip_list(variants: list[str]) -> str:
    if not variants:
        return ""
    chips = "".join(
        f'<span class="sqv-choice-chip">{html.escape(variant)}</span>'
        for variant in variants
        if variant
    )
    if not chips:
        return ""
    return f'<div class="sqv-choice-list">{chips}</div>'

def _code_compare_block(expected: str, provided: str, lang_hint: str, labels: dict, expected_alternatives: list[str] | None = None) -> str:
    exp_text = expected or ""
    prov_text = extract_code_text(provided)
    le = labels.get("expected", "Expected")
    lp = labels.get("provided", "Your answer")
    expected_variant_list = _build_compare_variant_chip_list(expected_alternatives or [])
    return f"""
    <div class="ak-compare" style="display:flex; gap:12px; margin:12px 0;">
      <div style="flex:1; min-width:0;">
        <div class="ak-label">{html.escape(le)}</div>
        <pre class="ak-pre"><code class="language-{lang_hint}">{html.escape(exp_text)}</code></pre>
        {expected_variant_list}
      </div>
      <div style="flex:1; min-width:0;">
        <div class="ak-label">{html.escape(lp)}</div>
        <pre class="ak-pre"><code class="language-{lang_hint}">{html.escape(prov_text)}</code></pre>
      </div>
    </div>
    """

def make_analysis_unavailable(reason: str, language: str = "english") -> dict:
    texts = get_ui_texts(language)
    base = texts.get("ai_not_available", "AI analysis not available")
    reason = (reason or "").strip()
    tips = f"{base}: {reason}" if reason else base
    return {
        "scored": False,
        "score": None,
        "tips": tips,
    }

def make_variant_mismatch_result(reason: str, language: str = "english") -> dict:
    texts = get_ui_texts(language)
    base = texts.get("ai_not_available", "AI analysis not available")
    details = (reason or "Question variant does not match canonical answer.").strip()
    return {
        "scored": False,
        "score": None,
        "tips": f"{base}: {details}",
        "status": "variant_mismatch",
    }

def build_analysis_prompt_payload(card, user_answer: str) -> dict:
    canonical_answer, accepted_answers = build_accepted_answer_pool(card)
    question_text = get_active_question_variant(card) or (get_note_field(card, QUESTION_FIELD) or "").strip()
    return {
        "question_text": question_text,
        "canonical_answer": canonical_answer,
        "accepted_answers": accepted_answers,
        "user_answer": user_answer or "",
    }


def build_analysis_cache_key(question_text: str, true_answer: str, user_answer: str) -> str:
    return f"{hash(question_text or '')}_{hash(true_answer or '')}_{hash(user_answer or '')}"


def invalidate_analysis_state(cache_key: str) -> None:
    ai_analysis_cache.pop(cache_key, None)
    analysis_results.pop(cache_key, None)
    is_analyzing.pop(cache_key, None)

def store_ai_analysis(expected_provided_tuple, type_pattern):
    """
    Lance l'analyse IA en arrière-plan pour ne pas bloquer l'UI,
    afin que le verso s'affiche tout de suite avec un spinner.
    """
    user_answer = expected_provided_tuple[1] or ""
    card = mw.reviewer.card if hasattr(mw, 'reviewer') and mw.reviewer else None
    if not should_score_card(card):
        return expected_provided_tuple
    payload = build_analysis_prompt_payload(card, user_answer)
    cache_key = build_analysis_cache_key(payload["question_text"], payload["canonical_answer"], user_answer)
    current_analysis_context.update(
        {
            "card_id": getattr(card, "id", None),
            "expected_provided_tuple": (payload["canonical_answer"], user_answer),
            "type_pattern": type_pattern,
            "cache_key": cache_key,
        }
    )

    # Déjà en cache
    if cache_key in ai_analysis_cache:
        print(f"Using cached analysis for {cache_key}")
        return expected_provided_tuple

    # Analyse déjà en cours
    if is_analyzing.get(cache_key, False):
        print(f"Analysis already in progress for {cache_key}")
        return expected_provided_tuple

    # Marquer en cours
    is_analyzing[cache_key] = True
    analysis_results[cache_key] = None
    print(f"Starting background AI analysis for key: {cache_key}")

    # Tâche de fond
    def task():
        try:
            print("Calling AI API for analysis (background)...")
            mismatch_reason = get_question_variant_mismatch_reason(card)
            if mismatch_reason:
                cfg = get_config()
                return make_variant_mismatch_result(mismatch_reason, cfg.get("language", "english"))
            return analyze_answer_with_ai(
                payload["question_text"],
                payload["canonical_answer"],
                payload["accepted_answers"],
                payload["user_answer"],
            )
        except Exception as e:
            print(f"AI Analysis Error (bg): {e}")
            cfg = get_config()
            return make_analysis_unavailable(str(e), cfg.get("language", "english"))

    # Callback: reçoit un Future
    def on_done(fut):
        try:
            result = fut.result()
        except Exception as e:
            print(f"Background task failed: {e}")
            cfg = get_config()
            result = make_analysis_unavailable(str(e), cfg.get("language", "english"))
        finally:
            # Toujours dé-marquer l'état d'analyse
            is_analyzing[cache_key] = False

        # Stocker le résultat (un dict, pas un Future)
        ai_analysis_cache[cache_key] = result
        analysis_results[cache_key] = result
        print(f"AI analysis completed (bg) for {cache_key}")

        # Rafraîchir l'affichage
        try:
            refresh_ai_analysis({"card_id": getattr(card, "id", None), "cache_key": cache_key})
        except Exception as e:
            print(f"Refresh error after AI analysis: {e}")

    # Lancer en arrière-plan
    mw.taskman.run_in_background(task, on_done)

    # Laisser l'UI afficher le verso avec spinner
    return expected_provided_tuple

def clean_html_content(html_content):
    """
    Nettoie le contenu HTML pour extraire le texte brut, 
    en supprimant les balises HTML, le CSS et le JavaScript.
    """
    if not html_content:
        return ""
    
    # 1. Supprimer les blocs de script et de style
    # L'option re.DOTALL permet au '.' de correspondre aussi aux sauts de ligne
    text = re.sub(r'<script.*?</script>', '', html_content, flags=re.DOTALL)
    text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL)
    
    # 2. Supprimer les balises HTML restantes
    text = re.sub(r'<[^>]+>', '', text)
    
    # 3. Remplacer les entités HTML communes
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&amp;', '&')
    text = text.replace('&quot;', '"')
    
    # 4. Nettoyer les espaces multiples et les sauts de ligne
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def get_note_field(card, field_name: str) -> str:
    if not card:
        return ""
    try:
        note_attr = getattr(card, "note", None)
        note = note_attr() if callable(note_attr) else note_attr
        if note is None:
            return ""
        try:
            value = note[field_name]
        except Exception:
            value = getattr(note, field_name, "")
        return value if isinstance(value, str) else str(value or "")
    except Exception as e:
        print(f"Error getting note field {field_name}: {e}")
        return ""


def get_card_template_name(card) -> str:
    if not card:
        return ""
    try:
        note_attr = getattr(card, "note", None)
        note = note_attr() if callable(note_attr) else note_attr
        if note is None:
            return ""
        model_attr = getattr(note, "model", None)
        model = model_attr() if callable(model_attr) else model_attr
        if not isinstance(model, dict):
            return ""
        template_ord = getattr(card, "ord", 0)
        templates = model.get("tmpls") or []
        if not isinstance(template_ord, int) or template_ord < 0 or template_ord >= len(templates):
            return ""
        template = templates[template_ord] or {}
        name = template.get("name", "") if isinstance(template, dict) else ""
        return name if isinstance(name, str) else str(name or "")
    except Exception as e:
        print(f"Error getting card template name: {e}")
        return ""


def should_score_card(card) -> bool:
    template_name = get_card_template_name(card).strip().lower()
    return template_name.endswith("_score")


def resolve_prompt_profile(config) -> str:
    merged_config = merge_config_with_defaults(config)
    return normalize_prompt_profile(merged_config.get("prompt_profile")) or PROMPT_PROFILE_DEFAULT


def get_manual_hint_html(card) -> str:
    return (get_note_field(card, "Hint") or "").strip()


def is_supported_typed_answer_card(card, rendered_text: str = "", kind: str = "") -> bool:
    if not card:
        return False
    if kind and "Question" not in kind:
        return False
    card_question = ""
    try:
        card_question = card.question() or ""
    except Exception:
        card_question = ""
    rendered_text = rendered_text or ""
    return "[[type:" in card_question or 'id="typeans"' in rendered_text or "id='typeans'" in rendered_text


def is_front_hint_eligible(card, rendered_text: str = "", kind: str = "Question") -> bool:
    return bool(card) and should_score_card(card) and is_supported_typed_answer_card(card, rendered_text, kind)


def build_hint_cache_key(*, card_id, card_ord, question_text: str, canonical_answer: str, manual_hint: str, language: str, prompt_profile: str, hint_prompt_version: str) -> str:
    return "_".join(
        [
            str(card_id),
            str(card_ord),
            str(hash(question_text or "")),
            str(hash(canonical_answer or "")),
            str(hash(manual_hint or "")),
            str(hash(language or "")),
            str(hash(prompt_profile or "")),
            str(hash(hint_prompt_version or "")),
        ]
    )


def invalidate_hint_state(cache_key: str) -> None:
    hint_cache.pop(cache_key, None)
    is_generating_hint.pop(cache_key, None)
    if current_hint_context.get("cache_key") == cache_key:
        current_hint_context.clear()
    if front_hint_panel_state.get("cache_key") == cache_key:
        front_hint_panel_state.clear()


def reset_hint_state() -> None:
    hint_cache.clear()
    is_generating_hint.clear()
    current_hint_context.clear()
    front_hint_panel_state.clear()


def build_front_hint_context(card, rendered_text: str = "", kind: str = "Question") -> dict[str, str | int | None]:
    canonical_answer, _accepted_answers = build_accepted_answer_pool(card)
    question_text = get_active_visible_question(card)
    manual_hint = get_manual_hint_html(card)
    config = get_config()
    prompt_profile = resolve_prompt_profile(config)
    return {
        "card_id": getattr(card, "id", None),
        "card_ord": getattr(card, "ord", None),
        "question_text": question_text,
        "canonical_answer": canonical_answer,
        "manual_hint": manual_hint,
        "language": config.get("language", "english"),
        "prompt_profile": prompt_profile,
        "hint_prompt_version": HINT_PROMPT_VERSION,
        "cache_key": build_hint_cache_key(
            card_id=getattr(card, "id", None),
            card_ord=getattr(card, "ord", None),
            question_text=question_text,
            canonical_answer=canonical_answer,
            manual_hint=manual_hint,
            language=config.get("language", "english"),
            prompt_profile=prompt_profile,
            hint_prompt_version=HINT_PROMPT_VERSION,
        ),
    }


def get_hint_availability_reason(config=None, language: str = "english") -> str:
    merged_config = merge_config_with_defaults(config)
    if not merged_config.get("enabled", True):
        return "AI disabled"
    provider = merged_config.get("provider", "openai")
    model = (merged_config.get(f"{provider}_model", get_provider_default_model(provider)) or "").strip()
    api_key = (merged_config.get(f"{provider}_api_key", "") or "").strip()
    if provider == CUSTOM_OPENAI_PROVIDER:
        base_url = (merged_config.get(f"{provider}_base_url", "") or "").strip()
        if not base_url:
            return "Custom OpenAI base URL not configured"
        if not model:
            return "Custom OpenAI model not configured"
        return ""
    if not api_key:
        provider_name = PROVIDERS.get(provider, {}).get("name", provider)
        return f"{provider_name} API key not configured"
    return ""

def make_hint_unavailable(reason: str, language: str = "english") -> dict:
    texts = get_hint_ui_texts(language)
    base = texts.get("hint_unavailable", "AI hint not available")
    reason = (reason or "").strip()
    error_text = f"{base}: {reason}" if reason else base
    return {
        "status": "unavailable",
        "hint_text": "",
        "error_text": error_text,
    }

def normalize_hint_result(result, language: str = "english") -> dict:
    if isinstance(result, dict):
        status = result.get("status") or "ready"
        hint_text = (result.get("hint_text", "") or "").strip()
        error_text = (result.get("error_text", "") or "").strip()
        if status == "loading":
            return {"status": "loading", "hint_text": "", "error_text": ""}
        if status == "unavailable":
            return {"status": "unavailable", "hint_text": "", "error_text": error_text or make_hint_unavailable("", language)["error_text"]}
        if hint_text:
            return {"status": "ready", "hint_text": hint_text, "error_text": ""}
        return make_hint_unavailable(error_text or "Empty AI response", language)
    hint_text = str(result or "").strip()
    if hint_text.startswith("```"):
        hint_text = hint_text.strip("`").strip()
        if hint_text.lower().startswith("json"):
            hint_text = hint_text[4:].strip()
    if not hint_text:
        return make_hint_unavailable("Empty AI response", language)
    return {"status": "ready", "hint_text": hint_text, "error_text": ""}

def build_hint_prompt(context_data: dict, config=None) -> tuple[str, str]:
    merged_config = merge_config_with_defaults(config)
    language = context_data.get("language", merged_config.get("language", "english"))
    resolved = resolve_prompt_profile_content(merged_config, language, context_data.get("prompt_profile", PROMPT_PROFILE_DEFAULT))
    prompt = render_prompt_template(
        resolved["hint_prompt_template"],
        language,
        context_data.get("question_text", ""),
        context_data.get("canonical_answer", ""),
        [],
        "",
        clean_html_content(context_data.get("manual_hint", "")),
    )
    prompt += f"\n\nReturn only one concise hint in {get_language_name(language)}. Do not reveal the full answer."
    return resolved["system_prompt"], prompt

def escape_ai_source_text(text) -> str:
    return html.escape(str(text or ""), quote=False)


def _restore_ai_tokens(text: str, tokens: list[str], marker: str) -> str:
    for idx, value in enumerate(tokens):
        text = text.replace(marker.format(idx), value)
    return text


def render_ai_inline_markup(text: str) -> str:
    if not text:
        return ""
    code_tokens: list[str] = []
    marker = "@@AQI_CODE_{}@@"

    def capture_code(match):
        code_tokens.append(f"<code>{match.group(1)}</code>")
        return marker.format(len(code_tokens) - 1)

    rendered = re.sub(r'`([^`\n]+)`', capture_code, text)
    rendered = re.sub(r'\*\*([^*\n][\s\S]*?[^*\n]|[^*\n])\*\*', r'<strong>\1</strong>', rendered)
    rendered = re.sub(r'(?<!\*)\*([^\s*](?:[^*\n]*?[^\s*])?)\*(?!\*)', r'<em>\1</em>', rendered)
    rendered = _restore_ai_tokens(rendered, code_tokens, marker)
    return rendered


def render_ai_markdown_subset(text: str) -> str:
    escaped = escape_ai_source_text(text).replace("\r\n", "\n").replace("\r", "\n")
    if not escaped.strip():
        return ""
    lines = escaped.split("\n")
    parts: list[str] = []
    idx = 0

    def is_unordered(line: str) -> bool:
        return bool(re.match(r'^\s*[-*]\s+.+$', line))

    def is_ordered(line: str) -> bool:
        return bool(re.match(r'^\s*\d+\.\s+.+$', line))

    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        if not stripped:
            idx += 1
            continue
        if stripped.startswith("```"):
            idx += 1
            code_lines: list[str] = []
            while idx < len(lines) and not lines[idx].strip().startswith("```"):
                code_lines.append(lines[idx])
                idx += 1
            if idx < len(lines) and lines[idx].strip().startswith("```"):
                idx += 1
            code_text = "\n".join(code_lines).strip("\n")
            parts.append(f'<pre class="aqi-rich-pre"><code>{code_text}</code></pre>')
            continue
        if is_unordered(line):
            items: list[str] = []
            while idx < len(lines) and is_unordered(lines[idx]):
                item = re.sub(r'^\s*[-*]\s+', '', lines[idx]).strip()
                items.append(f'<li>{render_ai_inline_markup(item)}</li>')
                idx += 1
            parts.append('<ul>' + ''.join(items) + '</ul>')
            continue
        if is_ordered(line):
            items: list[str] = []
            while idx < len(lines) and is_ordered(lines[idx]):
                item = re.sub(r'^\s*\d+\.\s+', '', lines[idx]).strip()
                items.append(f'<li>{render_ai_inline_markup(item)}</li>')
                idx += 1
            parts.append('<ol>' + ''.join(items) + '</ol>')
            continue
        para_lines: list[str] = []
        while idx < len(lines):
            current = lines[idx]
            if not current.strip():
                break
            if current.strip().startswith("```") or is_unordered(current) or is_ordered(current):
                break
            para_lines.append(render_ai_inline_markup(current.strip()))
            idx += 1
        if para_lines:
            parts.append('<p>' + '<br>'.join(para_lines) + '</p>')
        else:
            idx += 1
    return ''.join(parts)


def sanitize_ai_rendered_html(html_text: str) -> str:
    if not html_text:
        return ""
    allowed = {"div", "p", "br", "strong", "em", "code", "pre", "ul", "ol", "li"}

    def replace_tag(match):
        tag = (match.group(1) or "").lower()
        return match.group(0) if tag in allowed else html.escape(match.group(0), quote=False)

    return re.sub(r'</?([a-zA-Z0-9]+)(?:\s[^<>]*)?>', replace_tag, html_text)


def render_ai_rich_text(text) -> str:
    try:
        return sanitize_ai_rendered_html(render_ai_markdown_subset(text))
    except Exception:
        return escape_ai_source_text(text)


def build_ai_analysis_sections(ai_analysis: dict) -> list[dict]:
    return [
        {"key": "tips", "title_key": None, "kind": "rich_text", "value": ai_analysis.get("tips", "")},
        {"key": "sample_answers", "title_key": "ai_analysis_sample_answers", "kind": "string_list", "value": ai_analysis.get("sample_answers", [])},
        {"key": "question_variants", "title_key": "ai_analysis_question_variants", "kind": "string_list", "value": ai_analysis.get("question_variants", [])},
    ]


def render_ai_analysis_section(section: dict, texts: dict) -> str:
    if section.get("kind") == "rich_text":
        rendered = render_ai_rich_text(section.get("value", ""))
        return f'<div class="aqi-section-copy aqi-rich-copy">{rendered}</div>' if rendered else ""

    items = section.get("value") or []
    if not items:
        return ""

    title_key = section.get("title_key")
    title = html.escape(texts.get(title_key, ""), quote=False) if title_key else ""
    rendered_items = [f'<li>{render_ai_rich_text(item)}</li>' for item in items]
    heading = f'<div class="aqi-section-label">{title}</div>' if title else ""
    return heading + '<div class="aqi-section-copy aqi-rich-copy"><ul>' + ''.join(rendered_items) + '</ul></div>'

def build_post_refresh_typeset_js() -> str:
    return (
        "try{"
        "if(window.MathJax){"
        "if(typeof window.MathJax.typesetPromise==='function'){window.MathJax.typesetPromise();}"
        "else if(typeof window.MathJax.typeset==='function'){window.MathJax.typeset();}"
        "}"
        "}catch(e){}"
    )


def build_ai_loading_fragment(language: str = "english", title: str | None = None, body: str | None = None, note: str | None = None) -> str:
    texts = get_ai_ui_texts(language)
    resolved_title = html.escape((title or texts.get("loading_title", "AI in progress...")).strip())
    resolved_body = html.escape((body or texts.get("loading_body", "Please wait while AI works")).strip())
    resolved_note = html.escape((note or texts.get("loading_note", "Automatic refresh...")).strip())
    return f"""
    <div class="aqi-loading-card">
        <div class="aqi-loading-head">
            <div class="aqi-loading-spinner"></div>
            <div class="aqi-loading-title">{resolved_title}</div>
        </div>
        <p class="aqi-loading-copy">{resolved_body}</p>
        <p class="aqi-loading-note">{resolved_note}</p>
    </div>
    """

def build_ai_action_button(action_message: str, label: str, icon: str = "", disabled: bool = False, title: str | None = None, extra_classes: str = "") -> str:
    button_title = html.escape((title or label or "").strip())
    button_label = html.escape((label or "").strip())
    button_attrs = ' disabled aria-disabled="true"' if disabled else ""
    class_suffix = f" {extra_classes.strip()}" if extra_classes.strip() else ""
    icon_html = f'<span class="aqi-ai-action-icon">{html.escape(icon)}</span>' if icon else ""
    label_html = f'<span class="aqi-ai-action-label">{button_label}</span>' if button_label else ""
    return (
        f'<button class="aqi-ai-action-btn{class_suffix}" type="button" title="{button_title}" aria-label="{button_title}"{button_attrs} '
        f'onclick="if (typeof pycmd === \'function\') pycmd(\'{action_message}\'); return false;">'
        f'{icon_html}{label_html}'
        '</button>'
    )

def refresh_dom_fragment(selector: str, fragment_html: str) -> bool:
    reviewer = getattr(mw, "reviewer", None)
    web = getattr(reviewer, "web", None)
    if not web or not hasattr(web, "eval"):
        return False
    escaped_selector = json.dumps(selector)
    escaped_html = json.dumps(fragment_html)
    command = (
        "(function(){"
        "var wrap=document.querySelector(" + escaped_selector + ");"
        "if(wrap){wrap.outerHTML=" + escaped_html + ";}"
        + build_post_refresh_typeset_js()
        + "})();"
    )
    web.eval(command)
    return True

def build_front_hint_panel_html(card, rendered_text: str = "", kind: str = "Question") -> str:
    if not kind or "Question" not in kind:
        return ""
    if not is_front_hint_eligible(card, rendered_text, kind):
        return ""

    context = build_front_hint_context(card, rendered_text, kind)
    cache_key = context["cache_key"]
    current_hint_context.update(context)
    is_open = bool(front_hint_panel_state.get("is_open")) and front_hint_panel_state.get("cache_key") == cache_key
    front_hint_panel_state.update({"cache_key": cache_key, "is_open": is_open})

    config = get_config()
    language = context.get("language", config.get("language", "english"))
    texts = get_hint_ui_texts(language)
    ai_texts = get_ai_ui_texts(language)
    availability_reason = get_hint_availability_reason(config, language)
    manual_hint_html = context["manual_hint"]
    ai_state = dict(hint_cache.get(cache_key, {}) or {})
    if not ai_state and availability_reason:
        ai_state = make_hint_unavailable(availability_reason, language)

    status = ai_state.get("status", "idle")
    ai_hint_text = (ai_state.get("hint_text", "") or "").strip()
    ai_error_text = (ai_state.get("error_text", "") or "").strip()
    ai_body = ""
    ai_block = ""
    if status == "loading":
        ai_block = build_ai_loading_fragment(language)
    elif ai_hint_text or ai_error_text:
        ai_body = render_ai_rich_text(ai_hint_text or ai_error_text)
    if ai_body:
        ai_block = (
            f'<div class="aqi-front-hint-ai"><strong>{html.escape(texts.get("ai_hint_label", "AI Hint"))}:</strong>'
            f'<div id="aqi-front-hint-body" class="aqi-section-copy aqi-rich-copy">{ai_body}</div></div>'
        )

    if status == "ready":
        button_html = build_ai_action_button(
            "regenerate_ai_hint",
            ai_texts.get("regenerate", "Regenerate"),
            icon="⟳",
            extra_classes="aqi-front-hint-action",
        )
    else:
        button_title = ""
        if availability_reason:
            button_title = make_hint_unavailable(availability_reason, language)["error_text"]
        button_html = build_ai_action_button(
            "suggest_ai_hint",
            texts.get("suggest_hint", "Suggest Hint"),
            disabled=bool(availability_reason) or status == "loading",
            title=button_title or texts.get("suggest_hint", "Suggest Hint"),
            extra_classes="aqi-front-hint-action",
        )
    panel_class = "aqi-front-hint-panel" if is_open else "aqi-front-hint-panel is-hidden"
    manual_block = ""
    if manual_hint_html:
        manual_block = f'<div class="aqi-section-copy aqi-front-hint-manual">{manual_hint_html}</div>'
    return (
        '<div class="aqi-front-hint-wrap">'
        f'<button class="aqi-front-hint-toggle" type="button" onclick="if (typeof pycmd === \'function\') pycmd(\'toggle_hint_panel\'); return false;">{html.escape(texts.get("hint_toggle", "Hint"))}</button>'
        f'<div id="aqi-front-hint-panel" class="{panel_class}">'
        '<div class="aqi-panel-card aqi-front-hint-card" data-score-tier="na">'
        '<div class="aqi-panel-body">'
        f'{manual_block}'
        f'{ai_block}'
        '<div class="aqi-front-hint-actions">'
        f'{button_html}'
        '</div>'
        '</div>'
        '</div>'
        '</div>'
        '</div>'
    )

def refresh_current_front_hint_panel(cache_key: str | None = None) -> None:
    reviewer = getattr(mw, "reviewer", None)
    card = getattr(reviewer, "card", None)
    if not card:
        return
    rendered_text = ""
    try:
        rendered_text = card.question() or ""
    except Exception:
        rendered_text = ""
    panel_html = build_front_hint_panel_html(card, rendered_text, "Question")
    if not panel_html:
        return
    if cache_key and current_hint_context.get("cache_key") != cache_key:
        return
    refresh_front_hint_panel_dom(panel_html)

def refresh_front_hint_panel_dom(panel_html: str) -> None:
    refresh_dom_fragment('.aqi-front-hint-wrap', panel_html)

def build_ai_analysis_panel_html(cache_key: str, language: str = "english") -> str:
    texts = get_ui_texts(language)
    ai_texts = get_ai_ui_texts(language)
    if is_analyzing.get(cache_key, False) and cache_key not in ai_analysis_cache:
        return (
            '<div class="aqi-analysis-panel-wrap">'
            f'{build_ai_loading_fragment(language)}'
            '</div>'
        )

    ai_analysis = analysis_results.get(cache_key) or ai_analysis_cache.get(cache_key)
    if not ai_analysis:
        ai_analysis = make_analysis_unavailable("", language)

    is_scored = bool(ai_analysis.get("scored", True)) and isinstance(ai_analysis.get("score"), int)
    score = ai_analysis.get('score', 5) if is_scored else None
    score_tier = get_score_tier(score, is_scored)
    score_badge = f"{score}/10" if is_scored else "N/A"
    regenerate_button = build_ai_action_button(
        "regenerate_ai_analysis",
        ai_texts.get("regenerate", "Regenerate"),
        icon="⟳",
    )
    tips = ai_analysis.get('tips', texts.get('no_tips_available', 'No tips available'))
    if not isinstance(tips, str) or not tips.strip():
        tips = texts.get('no_tips_available', 'No tips available')

    if is_scored:
        section_payload = dict(ai_analysis)
        section_payload['tips'] = tips
        rendered_body = ''.join(
            render_ai_analysis_section(section, ai_texts)
            for section in build_ai_analysis_sections(section_payload)
        )
    else:
        rendered_body = f'<div class="aqi-section-copy aqi-rich-copy">{render_ai_rich_text(tips)}</div>'

    return f"""
    <div class="aqi-analysis-panel-wrap">
        <div class="aqi-panel-card" data-score-tier="{score_tier}">
            <div class="aqi-panel-head">
                <div class="aqi-panel-title-wrap">
                    <h3 class="aqi-panel-title">
                        {texts.get('ai_analysis', 'AI Analysis')}
                    </h3>
                </div>
                {regenerate_button}
                <div class="aqi-score-badge">
                    {score_badge}
                </div>
            </div>
            <div class="aqi-panel-body">
                {rendered_body}
            </div>
        </div>
    </div>
    """

def refresh_ai_analysis_panel_dom(panel_html: str) -> bool:
    return refresh_dom_fragment('.aqi-analysis-panel-wrap', panel_html)

def refresh_current_ai_analysis_panel(request_identity: dict | None = None) -> bool:
    reviewer = getattr(mw, "reviewer", None)
    card = getattr(reviewer, "card", None)
    if not card:
        return False
    context = dict(current_analysis_context)
    identity = dict(request_identity or context)
    cache_key = identity.get("cache_key")
    if not cache_key:
        return False
    if identity.get("card_id") is not None and identity.get("card_id") != getattr(card, "id", None):
        return False
    if context.get("cache_key") != cache_key:
        return False
    if context.get("card_id") is not None and context.get("card_id") != getattr(card, "id", None):
        return False
    language = get_config().get("language", "english")
    return refresh_ai_analysis_panel_dom(build_ai_analysis_panel_html(cache_key, language))

def suggest_ai_hint() -> dict:
    reviewer = getattr(mw, "reviewer", None)
    card = getattr(reviewer, "card", None)
    config = get_config()
    language = config.get("language", "english")
    if not is_front_hint_eligible(card, "", "Question"):
        return make_hint_unavailable("Hint unavailable for this card", language)

    context_data = build_front_hint_context(card)
    cache_key = context_data["cache_key"]
    current_hint_context.update(context_data)
    front_hint_panel_state.update({"cache_key": cache_key, "is_open": True})

    cached = hint_cache.get(cache_key)
    if cached and cached.get("status") == "ready":
        refresh_current_front_hint_panel(cache_key)
        return cached

    if is_generating_hint.get(cache_key, False):
        refresh_current_front_hint_panel(cache_key)
        return hint_cache.get(cache_key, {"status": "loading", "hint_text": "", "error_text": ""})

    availability_reason = get_hint_availability_reason(config, language)
    if availability_reason:
        result = make_hint_unavailable(availability_reason, language)
        hint_cache[cache_key] = result
        refresh_current_front_hint_panel(cache_key)
        return result

    provider = config.get("provider", "openai")
    model = (config.get(f"{provider}_model", get_provider_default_model(provider)) or "").strip()
    api_key = (config.get(f"{provider}_api_key", "") or "").strip()
    base_url = (config.get(f"{provider}_base_url", "") or "").strip()
    system_message, prompt = build_hint_prompt(context_data, config)
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt},
    ]

    hint_cache[cache_key] = {"status": "loading", "hint_text": "", "error_text": ""}
    is_generating_hint[cache_key] = True
    refresh_current_front_hint_panel(cache_key)

    def task():
        return normalize_hint_result(
            call_ai_api(
                messages=messages,
                provider=provider,
                model=model,
                max_tokens=config.get("max_tokens", 200),
                temperature=config.get("temperature", 0.7),
                api_key=api_key,
                base_url=base_url,
            ),
            language,
        )

    def on_done(fut):
        try:
            result = normalize_hint_result(fut.result(), language)
        except Exception as exc:
            provider_name = PROVIDERS.get(provider, {}).get("name", provider)
            result = make_hint_unavailable(f"{provider_name}: {exc}", language)
        finally:
            is_generating_hint[cache_key] = False
        hint_cache[cache_key] = result
        refresh_current_front_hint_panel(cache_key)

    mw.taskman.run_in_background(task, on_done)
    return hint_cache[cache_key]

def regenerate_ai_hint() -> dict:
    reviewer = getattr(mw, "reviewer", None)
    card = getattr(reviewer, "card", None)
    if not card:
        return make_hint_unavailable("Hint unavailable for this card", get_config().get("language", "english"))
    context_data = build_front_hint_context(card)
    invalidate_hint_state(context_data["cache_key"])
    current_hint_context.update(context_data)
    front_hint_panel_state.update({"cache_key": context_data["cache_key"], "is_open": True})
    return suggest_ai_hint()

def render_front_hint_panel(text: str, card, kind: str) -> str:
    panel_html = build_front_hint_panel_html(card, text, kind)
    if not panel_html:
        return text
    return text + panel_html

def get_raw_front_field(card) -> str:
    return get_note_field(card, QUESTION_FIELD)

def parse_variant_field(raw_value: str) -> list[str]:
    if not raw_value:
        return []
    return [segment.strip() for segment in raw_value.split(QUESTION_VARIANT_SEPARATOR) if segment.strip()]

def _ordered_unique(values: list[str]) -> list[str]:
    unique_values = []
    seen = set()
    for value in values:
        normalized = (value or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_values.append(normalized)
    return unique_values

def build_visible_question_pool(card) -> list[str]:
    return _ordered_unique([
        get_note_field(card, QUESTION_FIELD),
        *parse_variant_field(get_note_field(card, QUESTION_VARIANTS_FIELD)),
    ])

def build_accepted_answer_pool(card) -> tuple[str, list[str]]:
    canonical_answer = (get_note_field(card, ANSWER_FIELD) or "").strip()
    accepted_answers = _ordered_unique([
        canonical_answer,
        *parse_variant_field(get_note_field(card, ANSWER_VARIANTS_FIELD)),
    ])
    return canonical_answer, accepted_answers

def _normalize_expected_compare_text(value: str) -> str:
    return extract_code_text(value).strip()

def build_expected_display_model(card, expected_text: str) -> dict:
    primary_expected = _normalize_expected_compare_text(expected_text)
    if not card:
        return {
            "primary_expected": primary_expected,
            "alternative_expected_answers": [],
        }

    canonical_answer, accepted_answers = build_accepted_answer_pool(card)
    primary_expected = _normalize_expected_compare_text(canonical_answer or expected_text)
    seen = {primary_expected} if primary_expected else set()
    alternatives = []
    for answer in accepted_answers:
        normalized = _normalize_expected_compare_text(answer)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        alternatives.append(normalized)

    return {
        "primary_expected": primary_expected,
        "alternative_expected_answers": alternatives,
    }

def _is_plain_text_variant(value: str) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    if re.search(r'<[^>]+>', value):
        return False
    lowered = value.lower()
    return not any(marker in lowered for marker in QUESTION_VARIANT_MEDIA_MARKERS)

def _parse_numeric_text(value: str) -> float | None:
    text = (value or "").strip()
    if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", text):
        return None
    try:
        return float(text)
    except Exception:
        return None

def _safe_eval_arithmetic(expression: str) -> float:
    tree = ast.parse(expression, mode="eval")

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = evaluate(node.operand)
            return operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)):
            left = evaluate(node.left)
            right = evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.FloorDiv):
                return left // right
            if isinstance(node.op, ast.Mod):
                return left % right
            return left ** right
        raise ValueError("Unsupported arithmetic expression")

    return float(evaluate(tree))

def _evaluate_equation_with_answer(question_variant: str, answer_value: float | None) -> str:
    if answer_value is None:
        return "unsupported"
    if not isinstance(question_variant, str) or question_variant.count("?") != 1 or question_variant.count("=") != 1:
        return "unsupported"
    left_raw, right_raw = [segment.strip() for segment in question_variant.split("=", 1)]
    if "?" not in left_raw and "?" not in right_raw:
        return "unsupported"
    substituted = str(int(answer_value)) if float(answer_value).is_integer() else str(answer_value)
    left_expr = left_raw.replace("?", substituted)
    right_expr = right_raw.replace("?", substituted)
    try:
        left_value = _safe_eval_arithmetic(left_expr)
        right_value = _safe_eval_arithmetic(right_expr)
    except Exception:
        return "unsupported"
    return "compatible" if abs(left_value - right_value) < 1e-9 else "incompatible"

def evaluate_question_variant_compatibility(question_variant: str, canonical_answer: str, answer_pool: list[str]) -> str:
    canonical_status = _evaluate_equation_with_answer(question_variant, _parse_numeric_text(canonical_answer))
    if canonical_status != "unsupported":
        return canonical_status
    for answer in answer_pool or []:
        fallback_status = _evaluate_equation_with_answer(question_variant, _parse_numeric_text(answer))
        if fallback_status == "compatible":
            return "compatible"
    return canonical_status

def get_eligible_question_variants(card) -> list[str]:
    canonical_answer, accepted_answers = build_accepted_answer_pool(card)
    eligible_variants = []
    for question_variant in build_visible_question_pool(card):
        compatibility = evaluate_question_variant_compatibility(question_variant, canonical_answer, accepted_answers)
        if compatibility != "incompatible":
            eligible_variants.append(question_variant)
    return eligible_variants

def get_question_variant_mismatch_reason(card) -> str | None:
    question_pool = build_visible_question_pool(card)
    if not question_pool:
        return None
    canonical_answer, accepted_answers = build_accepted_answer_pool(card)
    canonical_question = question_pool[0]
    compatibility = evaluate_question_variant_compatibility(canonical_question, canonical_answer, accepted_answers)
    if compatibility == "incompatible":
        return f'Canonical Front question is incompatible with canonical Back answer: "{canonical_question}" vs "{canonical_answer}"'
    return None

def choose_question_variant(candidates: list[str], rng=None) -> str:
    if not candidates:
        return ""
    if rng is None:
        return random.choice(candidates)
    if hasattr(rng, "choice") and callable(rng.choice):
        return rng.choice(candidates)
    return rng(candidates)

def reset_active_question_state() -> None:
    active_question_state.clear()

def _build_active_question_signature(card) -> tuple[object, int, int]:
    card_id = getattr(card, "id", None)
    question_pool_hash = hash(tuple(build_visible_question_pool(card)))
    _canonical_answer, accepted_answers = build_accepted_answer_pool(card)
    answer_pool_hash = hash(tuple(accepted_answers))
    return card_id, question_pool_hash, answer_pool_hash

def get_active_question_variant(card) -> str | None:
    if not card:
        return None
    card_id, question_pool_hash, answer_pool_hash = _build_active_question_signature(card)
    chosen_variant = active_question_state.get("chosen_variant")
    if (
        active_question_state.get("card_id") == card_id
        and active_question_state.get("question_pool_hash") == question_pool_hash
        and active_question_state.get("answer_pool_hash") == answer_pool_hash
        and chosen_variant in get_eligible_question_variants(card)
    ):
        return chosen_variant
    return None

def _prepare_active_question_state_for_render(card, kind: str) -> None:
    if not card or not kind or ("Question" not in kind and "Answer" not in kind):
        return
    render_phase = "Question" if "Question" in kind else "Answer"
    card_id = getattr(card, "id", None)
    if render_phase == "Question":
        last_render_phase = active_question_state.get("last_render_phase")
        last_render_card_id = active_question_state.get("last_render_card_id")
        if last_render_phase != "Question" or last_render_card_id != card_id:
            reset_active_question_state()
    active_question_state["last_render_phase"] = render_phase
    active_question_state["last_render_card_id"] = card_id

def get_or_choose_active_question_variant(card, rng=None) -> str | None:
    eligible_variants = get_eligible_question_variants(card)
    if len(eligible_variants) <= 1:
        return eligible_variants[0] if eligible_variants else None

    existing_variant = get_active_question_variant(card)
    if existing_variant:
        return existing_variant

    raw_front = get_raw_front_field(card)
    if not _is_plain_text_variant(raw_front):
        return None
    if any(not _is_plain_text_variant(variant) for variant in eligible_variants):
        return None

    card_id, question_pool_hash, answer_pool_hash = _build_active_question_signature(card)
    chosen_variant = choose_question_variant(eligible_variants, rng=rng)
    active_question_state.update(
        {
            "card_id": card_id,
            "question_pool_hash": question_pool_hash,
            "answer_pool_hash": answer_pool_hash,
            "chosen_variant": chosen_variant,
        }
    )
    return chosen_variant

def get_active_visible_question(card) -> str:
    chosen_variant = get_active_question_variant(card)
    if chosen_variant:
        return chosen_variant
    canonical_question = get_note_field(card, QUESTION_FIELD)
    if canonical_question:
        return canonical_question.strip()
    return clean_html_content(card.question()) if card else ""

def build_question_variant_markup(card) -> str:
    raw_front = get_raw_front_field(card)
    candidates = get_eligible_question_variants(card)
    chosen_variant = get_or_choose_active_question_variant(card)
    if not chosen_variant or len(candidates) <= 1:
        return ""

    other_variants = [variant for variant in candidates if variant != chosen_variant]
    choice_html = "".join(
        f'<span class="sqv-choice-chip">{html.escape(variant)}</span>'
        for variant in other_variants
    )
    if not choice_html:
        choice_html = f'<span class="sqv-choice-chip">{html.escape(chosen_variant)}</span>'

    return f"""
    <div class="sqv-question-block">
        <div class="sqv-active-question">
            {html.escape(chosen_variant)}
        </div>
        <div class="sqv-choice-list">
            {choice_html}
        </div>
    </div>
    """

def apply_question_variant_to_rendered_question(text: str, card, kind: str) -> str:
    if not kind or ("Question" not in kind and "Answer" not in kind):
        return text

    _prepare_active_question_state_for_render(card, kind)

    chosen_variant = get_or_choose_active_question_variant(card)
    if not chosen_variant:
        return text

    raw_front = get_raw_front_field(card)
    variant_markup = build_question_variant_markup(card)
    if not variant_markup:
        return text
    if raw_front and raw_front in text:
        return text.replace(raw_front, variant_markup, 1)
    return text

def get_current_question():
    """
    **NOUVELLE FONCTION: Récupère le contenu de la question de la carte actuelle**
    """
    try:
        if hasattr(mw, 'reviewer') and mw.reviewer and hasattr(mw.reviewer, 'card') and mw.reviewer.card:
            card = mw.reviewer.card
            question_text = get_active_visible_question(card)

            print(f"Current question extracted: {question_text[:100]}...")
            return question_text
        else:
            print("No current card available")
            return ""
    except Exception as e:
        print(f"Error getting current question: {e}")
        return ""



def render_enhanced_comparison(output, initial_expected, initial_provided, type_pattern):
    """
    Améliore l'affichage de la comparaison avec l'analyse IA
    """
    config = get_config()
    language = config.get("language", "english")
    texts = get_ui_texts(language)
    ai_texts = get_ai_ui_texts(language)
    labels = get_compare_labels(config)
    show_anki = config.get("show_anki_compare", True)
    show_code = config.get("show_code_compare", True)
    
    # Skip if AI is disabled
    if not config.get("enabled", True):
        return output
    card = mw.reviewer.card if hasattr(mw, 'reviewer') and mw.reviewer else None
    if not should_score_card(card):
        return output
    
    # **MODIFIÉ: Inclure la question dans la clé de cache**
    question_text = get_current_question()
    cache_key = build_analysis_cache_key(question_text, initial_expected, initial_provided)
    current_analysis_context.update(
        {
            "card_id": getattr(card, "id", None),
            "expected_provided_tuple": (initial_expected or "", initial_provided or ""),
            "type_pattern": type_pattern,
            "cache_key": cache_key,
        }
    )
    print(f"Rendering comparison for key: {cache_key}")
    
    # Affichage alternatif fidèle pour le code (en plus du diff Anki)
    anki_section = f"""
    <div class="aqi-anki-compare">
    {output}
    </div>
    """ if show_anki else ""

    expected_display = build_expected_display_model(card, initial_expected)
    code_block = _code_compare_block(
        expected_display["primary_expected"],
        initial_provided,
        lang_hint="",
        labels=labels,
        expected_alternatives=expected_display["alternative_expected_answers"],
    ) if show_code else ""
        
    # Affichage simplifié des résultats
    enhanced_output = f"""
    <div class="aqi-shell">
        {anki_section}
        {code_block}
        
        {build_ai_analysis_panel_html(cache_key, language)}
    </div>
    """
    
    # Nettoyer les caches plus prudemment
    cleanup_old_cache_entries()
    
    return enhanced_output

def cleanup_old_cache_entries():
    """Nettoie les anciennes entrées de cache"""
    try:
        if len(ai_analysis_cache) > 10:
            # Garder seulement les 5 plus récents
            keys_to_remove = list(ai_analysis_cache.keys())[:-5]
            for key in keys_to_remove:
                ai_analysis_cache.pop(key, None)
                is_analyzing.pop(key, None)
                analysis_results.pop(key, None)
            print(f"Cleaned up {len(keys_to_remove)} old cache entries")
    except Exception as e:
        print(f"Error during cache cleanup: {e}")

def debug_cache_state():
    """Debug la situation actuelle des caches"""
    print("=== CACHE STATE DEBUG ===")
    print(f"ai_analysis_cache: {len(ai_analysis_cache)} entries")
    print(f"is_analyzing: {len(is_analyzing)} entries")
    print(f"analysis_results: {len(analysis_results)} entries")
    print(f"Currently analyzing: {[k for k, v in is_analyzing.items() if v]}")
    print("========================")

def reset_ai_caches():
    """Réinitialise tous les caches"""
    global ai_analysis_cache, is_analyzing, analysis_results
    ai_analysis_cache.clear()
    is_analyzing.clear()
    analysis_results.clear()
    print("AI caches reset")

# import the necessary hooks
from aqt import gui_hooks, mw
from aqt.utils import showInfo, showWarning
import json
import urllib.request
import urllib.error

# Configuration par défaut
DEFAULT_CONFIG = {
    "provider": "openai",
    "language": "english",
    "openai_api_key": "",
    "openai_model": "gpt-4.1-mini",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-flash",
    "claude_api_key": "",
    "claude_model": "claude-3-5-haiku-latest",
    "deepseek_api_key": "",
    "deepseek_model": "deepseek-chat",
    "groq_api_key": "",
    "groq_model": "llama-3.3-70b-versatile",
    "openrouter_api_key": "",
    "openrouter_model": "openrouter/free",
    "custom_openai_base_url": "",
    "custom_openai_api_key": "",
    "custom_openai_model": "",
    "custom_openai_custom_models": [],
    "enabled": True,
    "max_tokens": 200,
    "temperature": 0.7,
    "show_anki_compare": True,
    "show_code_compare": True,
    "ui_language": "auto",  # 'auto' | 'en' | 'fr' | 'es' | 'de' | 'pt' | 'it' | 'ru' | 'ja' | 'zh' | 'ko'
    "prompt_profile": "default",
    "use_custom_prompt": False,
    "custom_system_prompt": "",
    "custom_analysis_prompt_template": "",
    "custom_hint_prompt_template": ""
}

PROMPT_PROFILE_DEFAULT = "default"
PROMPT_PROFILE_STRICT_STEM = "strict_stem"
PROMPT_PROFILE_SPEAKING_FLEXIBLE = "speaking_flexible"
PROMPT_PROFILE_CUSTOM = "custom"
PROMPT_PROFILE_CHOICES = (
    PROMPT_PROFILE_DEFAULT,
    PROMPT_PROFILE_STRICT_STEM,
    PROMPT_PROFILE_SPEAKING_FLEXIBLE,
    PROMPT_PROFILE_CUSTOM,
)


def normalize_prompt_profile(value) -> str | None:
    profile = str(value or "").strip()
    return profile if profile in PROMPT_PROFILE_CHOICES else None


def should_show_custom_prompt_fields(profile: str) -> bool:
    return normalize_prompt_profile(profile) == PROMPT_PROFILE_CUSTOM


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

# **MODIFIÉ: Langues supportées avec nouveau texte pour le contexte de question**
LANGUAGES = {
    "english": {
        "name": "English",
        "ai_analysis": "AI Analysis",
        "improvement_tips": "Improvement Tips",
        "review_suggestion": "Review Suggestion",
        "question_context": "Question Context",
        "analyzing": "AI Analysis in progress...",
        "please_wait": "Please wait while the AI evaluates your answer",
        "processing_response": "Processing your response...",
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
        "improvement_tips": "Conseils d'amélioration",
        "review_suggestion": "Suggestion de révision",
        "question_context": "Contexte de la question",
        "analyzing": "Analyse IA en cours...",
        "please_wait": "Veuillez patienter pendant que l'IA évalue votre réponse",
        "processing_response": "Traitement de votre réponse...",
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
        "improvement_tips": "Consejos de mejora",
        "review_suggestion": "Sugerencia de revisión",
        "question_context": "Contexto de la pregunta",
        "analyzing": "Análisis IA en progreso...",
        "please_wait": "Por favor espera mientras la IA evalúa tu respuesta",
        "processing_response": "Procesando tu respuesta...",
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
        "improvement_tips": "Verbesserungstipps",
        "review_suggestion": "Wiederholungsvorschlag",
        "question_context": "Fragenkontext",
        "analyzing": "KI-Analyse läuft...",
        "please_wait": "Bitte warten Sie, während die KI Ihre Antwort bewertet",
        "processing_response": "Ihre Antwort wird verarbeitet...",
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
        "improvement_tips": "Советы по улучшению",
        "review_suggestion": "Рекомендация по повторению",
        "question_context": "Контекст вопроса",
        "analyzing": "Идет анализ ИИ...",
        "please_wait": "Подождите, пока ИИ оценивает ваш ответ",
        "processing_response": "Обрабатывается ваш ответ...",
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
        "improvement_tips": "改善のヒント",
        "review_suggestion": "復習の提案",
        "question_context": "問題の文脈",
        "analyzing": "AI分析中...",
        "please_wait": "AIが回答を評価するまでお待ちください",
        "processing_response": "回答を処理中...",
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
        "improvement_tips": "改进建议",
        "review_suggestion": "复习建议",
        "question_context": "问题上下文",
        "analyzing": "AI 正在分析...",
        "please_wait": "请稍候，AI 正在评估你的答案",
        "processing_response": "正在处理你的回答...",
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
        "improvement_tips": "개선 팁",
        "review_suggestion": "복습 제안",
        "question_context": "질문 맥락",
        "analyzing": "AI 분석 진행 중...",
        "please_wait": "AI가 답변을 평가하는 동안 잠시만 기다려 주세요",
        "processing_response": "답변 처리 중...",
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

DEFAULT_CUSTOM_SYSTEM_PROMPT = (
    "You are an educational assistant. Evaluate the student's answer kindly and constructively."
)

DEFAULT_CUSTOM_ANALYSIS_PROMPT_TEMPLATE = """Analyze the student's answer and return strict JSON.

Question: "{question}"
Expected answer: "{expected_answer}"
Accepted answers: "{accepted_answers}"
Student answer: "{user_answer}"
Language: "{language}"

Return ONLY valid JSON with this schema:
{
  "score": 0,
  "tips": "short constructive feedback"
}

Rules:
- score is an integer from 0 to 10
- tips should be concise and actionable
"""

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
    return LANGUAGES.get(language, LANGUAGES["english"])

def get_hint_ui_texts(language="english"):
    return HINT_UI_TEXTS.get(language, HINT_UI_TEXTS["english"])

def get_ai_ui_texts(language="english"):
    return AI_UI_TEXTS.get(language, AI_UI_TEXTS["english"])

def get_config_ui_texts(config=None):
    cfg = config or {}
    sel = str(cfg.get("ui_language", "auto")).lower()
    code = _detect_ui_lang_code() if sel == "auto" else sel[:2]
    return CONFIG_UI_TEXTS.get(code, CONFIG_UI_TEXTS["en"])


CUSTOM_OPENAI_PROVIDER = "custom_openai"


def merge_config_with_defaults(config):
    merged = dict(DEFAULT_CONFIG)
    source_config = config or {}
    if source_config:
        merged.update(source_config)
    merged_prompt_profile = normalize_prompt_profile(source_config.get("prompt_profile"))
    if merged_prompt_profile is None:
        merged_prompt_profile = PROMPT_PROFILE_CUSTOM if bool(source_config.get("use_custom_prompt", False)) else PROMPT_PROFILE_DEFAULT
    merged["prompt_profile"] = merged_prompt_profile
    merged["use_custom_prompt"] = False
    merged.pop("template_prompt_profile_overrides", None)
    return merged


def build_persisted_config(config):
    persisted = merge_config_with_defaults(config)
    persisted.pop("template_prompt_profile_overrides", None)
    return persisted


def get_provider_default_model(provider):
    models = PROVIDERS.get(provider, {}).get("models", [])
    return models[0] if models else ""


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

# Configuration des fournisseurs
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

def get_config():
    """Récupère la configuration depuis les métadonnées d'Anki"""
    try:
        saved_config = mw.addonManager.getConfig(__name__) or {}
        config = merge_config_with_defaults(saved_config)
        if config != saved_config:
            save_config(config)
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return merge_config_with_defaults(None)

def save_config(config):
    """Sauvegarde la configuration dans les métadonnées d'Anki"""
    try:
        mw.addonManager.writeConfig(__name__, build_persisted_config(config))
        reset_hint_state()
    except Exception as e:
        print(f"Error saving config: {e}")

def format_messages_for_provider(messages, provider):
    """Formate les messages selon le fournisseur"""
    if provider == "gemini":
        # Gemini utilise un format différent
        formatted_messages = []
        for msg in messages:
            if msg["role"] == "system":
                # Gemini n'a pas de role system, on l'ajoute au premier message user
                continue
            elif msg["role"] == "user":
                system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
                content = f"{system_msg}\n\n{msg['content']}" if system_msg else msg["content"]
                formatted_messages.append({
                    "parts": [{"text": content}]
                })
        return {"contents": formatted_messages}
    
    elif provider == "claude":
        # Claude utilise un format spécifique
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_messages = [m for m in messages if m["role"] != "system"]
        
        formatted_data = {
            "model": "",  # Sera ajouté plus tard
            "max_tokens": 350,  # Sera ajouté plus tard
            "messages": user_messages
        }
        
        if system_msg:
            formatted_data["system"] = system_msg
            
        return formatted_data
    
    else:
        # Format OpenAI (compatible avec OpenAI, DeepSeek, Groq)
        return {
            "messages": messages,
            "max_tokens": 350,  # Sera ajouté plus tard
            "temperature": 0.7  # Sera ajouté plus tard
        }

def call_ai_api(messages, provider="openai", model="gpt-4.1-mini", max_tokens=200, temperature=0.7, api_key="", base_url=""):
    """
    Appelle l'API du fournisseur choisi
    """
    if provider not in PROVIDERS:
        raise Exception(f"Fournisseur non supporté: {provider}")
    
    provider_config = PROVIDERS[provider]

    # Construire l'URL
    if provider == "gemini":
        url = provider_config["url"].format(model=model) + f"?key={api_key}"
        headers = {"Content-Type": "application/json"}
    elif provider == CUSTOM_OPENAI_PROVIDER:
        request_config = resolve_custom_openai_request(base_url, api_key)
        url = request_config["url"]
        headers = request_config["headers"]
    else:
        url = provider_config["url"]
        headers = provider_config["headers_func"](api_key)
    
    # Formater les données selon le fournisseur
    data = format_messages_for_provider(messages, provider)
    
    # Ajouter les paramètres spécifiques au modèle
    if provider == "gemini":
        data["generationConfig"] = {
            "maxOutputTokens": max_tokens,
            "temperature": temperature
        }
    elif provider == "claude":
        data["model"] = model
        data["max_tokens"] = max_tokens
        data["temperature"] = temperature
    else:
        # OpenAI, DeepSeek, Groq
        data["model"] = model
        data["max_tokens"] = max_tokens
        data["temperature"] = temperature
    
    try:
        # Préparer la requête
        json_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
        
        # Faire la requête
        with urllib.request.urlopen(req, timeout=30) as response:
            response_data = json.loads(response.read().decode('utf-8'))
            print(f'--AI response-- {response_data}')
        
        # Extraire la réponse selon le fournisseur
        if provider == "gemini":
            candidates = response_data.get("candidates") or []
            if candidates:
                c0 = candidates[0] or {}
                content = c0.get("content") or {}
                parts = content.get("parts") or []
                if parts:
                    p0 = parts[0] or {}
                    text = p0.get("text")
                    if isinstance(text, str) and text.strip():
                        return text
        elif provider == "claude":
            content = response_data.get("content") or []
            if content:
                c0 = content[0] or {}
                text = c0.get("text")
                if isinstance(text, str) and text.strip():
                    return text
        else:
            # OpenAI-compatible: OpenAI, DeepSeek, Groq, OpenRouter
            choices = response_data.get("choices") or []
            if choices:
                first = choices[0] or {}
                message = first.get("message") or {}
                content = message.get("content")
                # Standard content string
                if isinstance(content, str) and content.strip():
                    return content
                # Some providers return content as blocks
                if isinstance(content, list):
                    txt_parts = []
                    for block in content:
                        if isinstance(block, dict):
                            t = block.get("text")
                            if isinstance(t, str) and t:
                                txt_parts.append(t)
                    if txt_parts:
                        return "\n".join(txt_parts)
                # Fallbacks used by some implementations
                text = first.get("text")
                if isinstance(text, str) and text.strip():
                    return text
                delta = first.get("delta") or {}
                dcontent = delta.get("content")
                if isinstance(dcontent, str) and dcontent.strip():
                    return dcontent
        
        raise Exception(f"Réponse API invalide ({provider}) - structure inattendue")
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            error_data = json.loads(error_body)
            if provider == "gemini":
                error_message = error_data.get('error', {}).get('message', str(e))
            elif provider == "claude":
                error_message = error_data.get('error', {}).get('message', str(e))
            else:
                error_message = error_data.get('error', {}).get('message', str(e))
        except:
            error_message = f"Erreur HTTP {e.code}: {error_body[:100]}"
        raise Exception(f"Erreur API {provider_config['name']}: {error_message}")
    
    except urllib.error.URLError as e:
        raise Exception(f"Erreur de connexion: {str(e)}")
    
    except json.JSONDecodeError as e:
        raise Exception(f"Erreur de parsing JSON: {str(e)}")
    
    except Exception as e:
        raise Exception(f"Erreur inattendue: {str(e)}")

def _format_accepted_answers_for_prompt(accepted_answers) -> str:
    if isinstance(accepted_answers, str):
        return accepted_answers
    if not accepted_answers:
        return ""
    return "; ".join(str(answer) for answer in accepted_answers if str(answer).strip())

def get_language_specific_prompt(language, question_text, true_answer, accepted_answers, user_answer):
    """
    **MODIFIÉ: Génère un prompt selon la langue configurée avec contexte de question**
    """
    accepted_answers_text = _format_accepted_answers_for_prompt(accepted_answers)
    
    prompts = {
        "english": f"""
        Analyze the student's answer in the context of the given question and provide a structured evaluation.

        Question: "{question_text}"
        Expected answer: "{true_answer}"
        Accepted answers: "{accepted_answers_text}"
        Student's answer: "{user_answer}"

        Please provide your evaluation in the following JSON format:
        {{
            "score": [number from 0 to 10],
            "tips": "[constructive feedback in English, maximum 100 words, considering the question context]"
        }}

        Evaluation criteria:
        - Score 0-3: Incorrect or very incomplete answer
        - Score 4-5: Partially correct but with significant errors
        - Score 6-8: Correct answer with minor imperfections
        - Score 9-10: Excellent and complete answer
        
        Consider the question context when evaluating the relevance and completeness of the student's response.
        """,
        
        "french": f"""
        Analysez la réponse de l'étudiant dans le contexte de la question donnée et fournissez une évaluation structurée.

        Question: "{question_text}"
        Réponse attendue: "{true_answer}"
        Réponses acceptées: "{accepted_answers_text}"
        Réponse de l'étudiant: "{user_answer}"

        Veuillez fournir votre évaluation au format JSON suivant:
        {{
            "score": [nombre de 0 à 10],
            "tips": "[conseils constructifs en français, maximum 100 mots, en tenant compte du contexte de la question]"
        }}

        Critères d'évaluation:
        - Score 0-3: Réponse incorrecte ou très incomplète → "Again"
        - Score 4-5: Réponse partiellement correcte mais avec des erreurs importantes → "Hard"  
        - Score 6-8: Réponse correcte avec quelques imperfections mineures → "Good"
        - Score 9-10: Réponse excellente et complète → "Easy"
        
        Considérez le contexte de la question lors de l'évaluation de la pertinence et de la complétude de la réponse de l'étudiant.
        """,
        
        "spanish": f"""
        Analiza la respuesta del estudiante en el contexto de la pregunta dada y proporciona una evaluación estructurada.

        Pregunta: "{question_text}"
        Respuesta esperada: "{true_answer}"
        Respuestas aceptadas: "{accepted_answers_text}"
        Respuesta del estudiante: "{user_answer}"

        Por favor proporciona tu evaluación en el siguiente formato JSON:
        {{
            "score": [número del 0 al 10],
            "tips": "[comentarios constructivos en español, máximo 100 palabras, considerando el contexto de la pregunta]"
        }}

        Criterios de evaluación:
        - Puntuación 0-3: Respuesta incorrecta o muy incompleta → "Again"
        - Puntuación 4-5: Respuesta parcialmente correcta pero con errores significativos → "Hard"
        - Puntuación 6-8: Respuesta correcta con imperfecciones menores → "Good"
        - Puntuación 9-10: Respuesta excelente y completa → "Easy"
        
        Considera el contexto de la pregunta al evaluar la relevancia y completitud de la respuesta del estudiante.
        """,
        
        "german": f"""
        Analysieren Sie die Antwort des Studenten im Kontext der gegebenen Frage und geben Sie eine strukturierte Bewertung ab.

        Frage: "{question_text}"
        Erwartete Antwort: "{true_answer}"
        Akzeptierte Antworten: "{accepted_answers_text}"
        Antwort des Studenten: "{user_answer}"

        Bitte geben Sie Ihre Bewertung im folgenden JSON-Format an:
        {{
            "score": [Zahl von 0 bis 10],
            "tips": "[konstruktives Feedback auf Deutsch, maximal 100 Wörter, unter Berücksichtigung des Fragenkontexts]"
        }}

        Bewertungskriterien:
        - Punktzahl 0-3: Falsche oder sehr unvollständige Antwort → "Again"
        - Punktzahl 4-5: Teilweise richtige Antwort, aber mit erheblichen Fehlern → "Hard"
        - Punktzahl 6-8: Richtige Antwort mit kleineren Unvollkommenheiten → "Good"
        - Punktzahl 9-10: Ausgezeichnete und vollständige Antwort → "Easy"
        
        Berücksichtigen Sie den Fragenkontext bei der Bewertung der Relevanz und Vollständigkeit der studentischen Antwort.
        """,

        "russian": f"""
        Проанализируйте ответ студента в контексте заданного вопроса и предоставьте структурированную оценку.

        Вопрос: "{question_text}"
        Ожидаемый ответ: "{true_answer}"
        Допустимые ответы: "{accepted_answers_text}"
        Ответ студента: "{user_answer}"

        Предоставьте оценку в формате JSON:
        {{
            "score": [число от 0 до 10],
            "tips": "[конструктивная обратная связь на русском, максимум 100 слов, учитывая контекст вопроса]"
        }}

        Критерии:
        - 0-3: Неверный или очень неполный ответ → "Again"
        - 4-5: Частично верный ответ с существенными ошибками → "Hard"
        - 6-8: Верный ответ с небольшими недочетами → "Good"
        - 9-10: Отличный и полный ответ → "Easy"
        """,

        "japanese": f"""
        与えられた問題文の文脈に基づいて、学習者の回答を分析し、構造化された評価を返してください。

        問題: "{question_text}"
        期待される回答: "{true_answer}"
        許容される回答: "{accepted_answers_text}"
        学習者の回答: "{user_answer}"

        次のJSON形式で返してください:
        {{
            "score": [0から10の数値],
            "tips": "[日本語で建設的なフィードバック。100語以内。問題文の文脈を考慮すること]"
        }}

        評価基準:
        - 0-3: 不正解、または大きく不十分 → "Again"
        - 4-5: 部分的に正しいが重要な誤りあり → "Hard"
        - 6-8: ほぼ正しいが軽微な不備あり → "Good"
        - 9-10: 非常に良く、完全な回答 → "Easy"
        """,

        "chinese": f"""
        请结合题目上下文分析学生回答，并给出结构化评估。

        题目: "{question_text}"
        期望答案: "{true_answer}"
        可接受答案: "{accepted_answers_text}"
        学生答案: "{user_answer}"

        请使用以下 JSON 格式输出:
        {{
            "score": [0 到 10 的数字],
            "tips": "[中文的建设性反馈，最多100词，并结合题目上下文]"
        }}

        评分标准:
        - 0-3: 错误或非常不完整 → "Again"
        - 4-5: 部分正确但有明显错误 → "Hard"
        - 6-8: 基本正确，有轻微不足 → "Good"
        - 9-10: 非常优秀且完整 → "Easy"
        """,

        "korean": f"""
        주어진 질문의 맥락에서 학생의 답변을 분석하고 구조화된 평가를 제공하세요.

        질문: "{question_text}"
        정답: "{true_answer}"
        허용 답변: "{accepted_answers_text}"
        학생 답변: "{user_answer}"

        다음 JSON 형식으로 답변하세요:
        {{
            "score": [0에서 10 사이 숫자],
            "tips": "[한국어로 된 건설적인 피드백, 최대 100단어, 질문 맥락 반영]"
        }}

        평가 기준:
        - 0-3: 오답 또는 매우 불완전 → "Again"
        - 4-5: 부분적으로 정답이나 중요한 오류 존재 → "Hard"
        - 6-8: 전반적으로 정답이나 사소한 미흡함 → "Good"
        - 9-10: 매우 우수하고 완전한 답변 → "Easy"
        """
    }
    
    return prompts.get(language, prompts["english"])

def get_system_message_for_language(language):
    system_messages = {
        "english": "You are an educational assistant that evaluates student responses constructively and kindly. Use the question context to provide more accurate and relevant feedback.",
        "french": "Vous êtes un assistant pédagogique qui évalue les réponses des étudiants de manière constructive et bienveillante. Utilisez le contexte de la question pour fournir des commentaires plus précis et pertinents.",
        "spanish": "Eres un asistente educativo que evalúa las respuestas de los estudiantes de manera constructiva y amable. Usa el contexto de la pregunta para proporcionar comentarios más precisos y relevantes.",
        "german": "Sie sind ein pädagogischer Assistent, der die Antworten der Studenten konstruktiv und freundlich bewertet. Nutzen Sie den Fragenkontext, um genauere und relevantere Rückmeldungen zu geben.",
        "russian": "Вы образовательный ассистент. Оценивайте ответы конструктивно, доброжелательно и с учетом контекста вопроса.",
        "japanese": "あなたは学習支援アシスタントです。問題の文脈を踏まえ、建設的で丁寧なフィードバックを返してください。",
        "chinese": "你是一名教育助手。请结合题目上下文，以建设性且友好的方式评估学生回答。",
        "korean": "당신은 교육용 어시스턴트입니다. 질문 맥락을 반영해 학생 답변을 친절하고 건설적으로 평가하세요.",
    }
    return system_messages.get(language, system_messages["english"])


def render_prompt_template(template: str, language: str, question_text: str, true_answer: str, accepted_answers: list[str], user_answer: str, hint: str = "") -> str:
    rendered = template
    replacements = {
        "{question}": question_text or "",
        "{expected_answer}": true_answer or "",
        "{accepted_answers}": _format_accepted_answers_for_prompt(accepted_answers),
        "{user_answer}": user_answer or "",
        "{language}": language or "english",
        "{hint}": hint or "",
    }
    for token, value in replacements.items():
        rendered = rendered.replace(token, value)
    return rendered



def resolve_prompt_profile_content(config, language: str, profile_name: str) -> dict[str, str]:
    merged_config = merge_config_with_defaults(config)
    normalized_profile = normalize_prompt_profile(profile_name) or PROMPT_PROFILE_DEFAULT
    base_system = get_system_message_for_language(language)
    base_analysis_prompt = get_language_specific_prompt(language, "{question}", "{expected_answer}", ["{accepted_answers}"], "{user_answer}")

    default_hint_template = (
        "Give one concise study hint for the question without revealing the full answer. "
        "Question: {question}\nExpected answer: {expected_answer}\n"
        "Existing hint: {hint}\nLanguage: {language}"
    )
    strict_stem_hint_template = (
        "Give one concise STEM-oriented study hint without revealing the full answer. "
        "Focus on units, sign, setup, or first step. "
        "Question: {question}\nExpected answer: {expected_answer}\n"
        "Existing hint: {hint}\nLanguage: {language}"
    )
    speaking_flexible_hint_template = (
        "Give one concise speaking-oriented hint without revealing a full model answer. "
        "Focus on communicative intent, topic framing, or useful direction. "
        "Question: {question}\nExpected answer: {expected_answer}\n"
        "Existing hint: {hint}\nLanguage: {language}"
    )

    built_in_profiles = {
        PROMPT_PROFILE_DEFAULT: {
            "system_prompt": base_system,
            "analysis_prompt_template": base_analysis_prompt,
            "hint_prompt_template": default_hint_template,
        },
        PROMPT_PROFILE_STRICT_STEM: {
            "system_prompt": base_system,
            "analysis_prompt_template": base_analysis_prompt + (
                "\n\nProfile-specific evaluation rules:\n"
                "- Treat this as a strict STEM response.\n"
                "- Require precision for numeric result, sign, and unit.\n"
                "- Treat materially incomplete answers as wrong.\n"
                "- Do not accept vague semantic similarity when the factual result is wrong.\n"
                "- Accept mathematically or scientifically equivalent answers."
            ),
            "hint_prompt_template": strict_stem_hint_template,
        },
        PROMPT_PROFILE_SPEAKING_FLEXIBLE: {
            "system_prompt": base_system,
            "analysis_prompt_template": base_analysis_prompt + (
                "\n\nProfile-specific evaluation rules:\n"
                "- Treat the expected answer as an anchor example, not exclusive truth.\n"
                "- Score communicative adequacy, relevance, grammar, and completeness.\n"
                "- Allow alternative valid responses that satisfy prompt intent.\n"
                "- Accept alternative valid responses when meaning is preserved.\n"
                "- Return JSON fields `sample_answers` and `question_variants`.\n"
                "- `sample_answers` must contain 2-3 strings.\n"
                "- `question_variants` must contain 2-3 strings.\n"
                "- At least one sample answer must build from learner answer.\n"
                "- If learner answer is incomplete, low-scoring, or unnatural, sample answer built from learner answer must correct and expand it into clearly better, higher-scoring full answer.\n"
                "- Do not repeat learner answer unchanged as sample answer unless it would already score high."
            ),
            "hint_prompt_template": speaking_flexible_hint_template,
        },
    }

    if normalized_profile == PROMPT_PROFILE_CUSTOM:
        custom_system = (merged_config.get("custom_system_prompt", "") or "").strip() or base_system
        custom_analysis_template = (merged_config.get("custom_analysis_prompt_template", "") or "").strip() or base_analysis_prompt
        custom_hint_template = (merged_config.get("custom_hint_prompt_template", "") or "").strip() or default_hint_template
        return {
            "system_prompt": custom_system,
            "analysis_prompt_template": custom_analysis_template,
            "hint_prompt_template": custom_hint_template,
        }

    return built_in_profiles.get(normalized_profile, built_in_profiles[PROMPT_PROFILE_DEFAULT])
def build_prompt_profile_content(config, language: str, profile: str, question_text: str, true_answer: str, accepted_answers: list[str], user_answer: str) -> tuple[str, str]:
    resolved = resolve_prompt_profile_content(config, language, profile)
    rendered_prompt = render_prompt_template(
        resolved["analysis_prompt_template"],
        language,
        question_text,
        true_answer,
        accepted_answers,
        user_answer,
    )
    return resolved["system_prompt"], rendered_prompt

def build_analysis_prompt(config, language, question_text, true_answer, accepted_answers, user_answer):
    card = mw.reviewer.card if hasattr(mw, 'reviewer') and mw.reviewer else None
    profile = resolve_prompt_profile(config)
    _system, prompt = build_prompt_profile_content(config, language, profile, question_text, true_answer, accepted_answers, user_answer)
    return prompt

def get_language_name(language_key: str) -> str:
    mapping = {
        "english": "English",
        "french": "French",
        "spanish": "Spanish",
        "german": "German",
        "russian": "Russian",
        "japanese": "Japanese",
        "chinese": "Chinese",
        "korean": "Korean",
    }
    return mapping.get(language_key, "English")

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


def normalize_ai_json_math_delimiters(text: str) -> str:
    return re.sub(r'(?<!\\)\\([()\[\]])', lambda match: '\\' + match.group(0), text)


def normalize_ai_analysis_string_list(value, min_items=2, max_items=3) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if len(cleaned) > max_items:
        cleaned = cleaned[:max_items]
    if len(cleaned) < min_items:
        return []
    return cleaned

def analyze_answer_with_ai(question_text: str, true_answer: str, accepted_answers: list[str], user_answer: str) -> dict:
    """
    **MODIFIÉ: Analyse la réponse de l'utilisateur avec l'IA en incluant le contexte de la question**
    Retourne un dictionnaire avec le score, les conseils et la suggestion de révision
    """
    config = get_config()
    
    if not config.get("enabled", True):
        return make_analysis_unavailable("AI disabled", config.get("language", "english"))
    
    provider = config.get("provider", "openai")
    language = config.get("language", "english")
    api_key_field = f"{provider}_api_key"
    model_field = f"{provider}_model"

    api_key = config.get(api_key_field, "").strip()
    base_url = (config.get(f"{provider}_base_url", "") or "").strip()
    model = (config.get(model_field, get_provider_default_model(provider)) or "").strip()

    if provider == CUSTOM_OPENAI_PROVIDER:
        if not base_url:
            return make_analysis_unavailable("Custom OpenAI base URL not configured", language)
        if not model:
            return make_analysis_unavailable("Custom OpenAI model not configured", language)
    elif not api_key:
        return make_analysis_unavailable(f"{PROVIDERS[provider]['name']} API key not configured", language)
    
    card = mw.reviewer.card if hasattr(mw, 'reviewer') and mw.reviewer else None
    profile = resolve_prompt_profile(config)
    system_message, prompt = build_prompt_profile_content(
        config,
        language,
        profile,
        question_text,
        true_answer,
        accepted_answers,
        user_answer,
    )
    prompt += get_language_lock_instruction(language)

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]

    try:
        ai_response = call_ai_api(
            messages=messages,
            provider=provider,
            model=model,
            max_tokens=config.get("max_tokens", 200),
            temperature=config.get("temperature", 0.7),
            api_key=api_key,
            base_url=base_url
        )
        
        # Tenter de parser la réponse JSON
        try:
            # Nettoyer la réponse (enlever les balises markdown si présentes)
            clean_response = ai_response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            parse_candidates = [clean_response]
            normalized_response = normalize_ai_json_math_delimiters(clean_response)
            if normalized_response != clean_response:
                parse_candidates.append(normalized_response)

            result = None
            for candidate in parse_candidates:
                try:
                    result = json.loads(candidate)
                    break
                except json.JSONDecodeError:
                    continue

            if result is None:
                raise json.JSONDecodeError("Invalid AI JSON response", clean_response, 0)
            # Valider les champs requis
            if all(key in result for key in ["score", "tips"]):
                # Valider le score
                result["score"] = max(0, min(10, int(result["score"])))
                result["scored"] = True
                result["sample_answers"] = normalize_ai_analysis_string_list(result.get("sample_answers"))
                result["question_variants"] = normalize_ai_analysis_string_list(result.get("question_variants"))
                return result
        except (json.JSONDecodeError, ValueError, KeyError):
            pass
        
        # Si le parsing JSON échoue, essayer d'extraire les informations
        lines = ai_response.split('\n')
        score = 5
        tips = "Analyse disponible dans la réponse complète"
        
        for line in lines:
            if 'score' in line.lower():
                try:
                    import re
                    score_match = re.search(r'(\d+)', line)
                    if score_match:
                        score = max(0, min(10, int(score_match.group(1))))
                except:
                    pass
        
        return {"scored": True, "score": score, "tips": ai_response[:300] + "..."}
        
    except Exception as e:
        print(f"AI Analysis Error: {str(e)}")  # Pour debugging
        return make_analysis_unavailable(f"{PROVIDERS[provider]['name']}: {str(e)}", language)

def setup_config_menu():
    """Configure le menu de configuration"""
    def open_config():
        config = get_config()
        ui = get_config_ui_texts(config)
        
        # Interface simple pour la configuration
        from aqt.qt import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton, QSpinBox, QDoubleSpinBox, QTabWidget, QWidget, QTextEdit, QApplication, QScrollArea, QAbstractSpinBox
        
        dialog = QDialog(mw)
        dialog.setWindowTitle(ui["window_title"])
        dialog.setMinimumWidth(550)
        dialog.setMinimumHeight(700)

        root_layout = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        # Paramètres généraux en haut
        general_group = QVBoxLayout()
        
        # Display options
        compare_group = QVBoxLayout()
        show_anki_chk = QCheckBox(ui["show_anki_compare"])
        show_anki_chk.setChecked(config.get("show_anki_compare", True))
        compare_group.addWidget(show_anki_chk)

        show_code_chk = QCheckBox(ui["show_code_compare"])
        show_code_chk.setChecked(config.get("show_code_compare", True))
        compare_group.addWidget(show_code_chk)

        layout.addLayout(compare_group)
        
        # Sélecteur de fournisseur principal
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel(ui["ai_provider"]))
        provider_combo = QComboBox()
        provider_items = [(key, value["name"]) for key, value in PROVIDERS.items()]
        for key, name in provider_items:
            provider_combo.addItem(name, key)
        
        current_provider = config.get("provider", "openai")
        provider_index = next((i for i, (key, _) in enumerate(provider_items) if key == current_provider), 0)
        provider_combo.setCurrentIndex(provider_index)
        provider_layout.addWidget(provider_combo)
        general_group.addLayout(provider_layout)
        
        # Analysis language selector
        language_layout = QHBoxLayout()
        language_layout.addWidget(QLabel(ui["analysis_language"]))
        language_combo = QComboBox()
        for lang_key, lang_info in LANGUAGES.items():
            language_combo.addItem(lang_info["name"], lang_key)
        
        current_language = config.get("language", "english")
        language_index = next((i for i, (key, _) in enumerate(LANGUAGES.items()) if key == current_language), 0)
        language_combo.setCurrentIndex(language_index)
        language_layout.addWidget(language_combo)
        general_group.addLayout(language_layout)
        
        # Activation
        enabled_checkbox = QCheckBox(ui["enable_ai"])
        enabled_checkbox.setChecked(config.get("enabled", True))
        general_group.addWidget(enabled_checkbox)
        
        # Max tokens
        tokens_layout = QHBoxLayout()
        tokens_layout.addWidget(QLabel(ui["max_tokens"]))
        tokens_spin = QSpinBox()
        tokens_spin.setRange(100, 16000)
        tokens_spin.setSingleStep(100)
        tokens_spin.setAccelerated(True)
        tokens_spin.setKeyboardTracking(False)
        tokens_spin.setReadOnly(False)
        tokens_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        tokens_spin.setCorrectionMode(QAbstractSpinBox.CorrectionMode.CorrectToNearestValue)
        try:
            tokens_spin.lineEdit().setReadOnly(False)
        except Exception:
            pass
        tokens_spin.setValue(min(max(config.get("max_tokens", 300), 100), 16000))
        tokens_layout.addWidget(tokens_spin)
        general_group.addLayout(tokens_layout)
        feedback_length_help = QLabel(ui.get("feedback_length_help", "Lower = shorter, faster feedback."))
        feedback_length_help.setStyleSheet("color: #666; font-size: 11px; margin-bottom: 6px;")
        feedback_length_help.setWordWrap(True)
        general_group.addWidget(feedback_length_help)
        
        # Temperature
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel(ui["temperature"]))
        temp_spin = QDoubleSpinBox()
        temp_spin.setRange(0.0, 1.0)
        temp_spin.setSingleStep(0.1)
        temp_spin.setValue(config.get("temperature", 0.7))
        temp_layout.addWidget(temp_spin)
        general_group.addLayout(temp_layout)

        prompt_profile_layout = QHBoxLayout()
        prompt_profile_layout.addWidget(QLabel(ui.get("prompt_profile", "Default prompt profile")))
        prompt_profile_combo = QComboBox()
        prompt_profile_options = [
            ("Default", PROMPT_PROFILE_DEFAULT),
            ("Strict STEM", PROMPT_PROFILE_STRICT_STEM),
            ("Speaking Flexible", PROMPT_PROFILE_SPEAKING_FLEXIBLE),
            ("Custom", PROMPT_PROFILE_CUSTOM),
        ]
        for label, value in prompt_profile_options:
            prompt_profile_combo.addItem(label, value)
        current_prompt_profile = normalize_prompt_profile(config.get("prompt_profile")) or PROMPT_PROFILE_DEFAULT
        prompt_profile_combo.setCurrentIndex(next((idx for idx, (_label, value) in enumerate(prompt_profile_options) if value == current_prompt_profile), 0))
        prompt_profile_layout.addWidget(prompt_profile_combo)
        general_group.addLayout(prompt_profile_layout)

        custom_system_label = QLabel(ui["custom_system_prompt"])
        general_group.addWidget(custom_system_label)
        custom_system_input = QTextEdit()
        custom_system_input.setPlainText(config.get("custom_system_prompt", ""))
        custom_system_input.setMinimumHeight(80)
        general_group.addWidget(custom_system_input)

        custom_template_label = QLabel(ui["custom_analysis_prompt"])
        general_group.addWidget(custom_template_label)
        custom_template_input = QTextEdit()
        custom_template_input.setPlainText(config.get("custom_analysis_prompt_template", ""))
        custom_template_input.setMinimumHeight(140)
        general_group.addWidget(custom_template_input)

        custom_hint_template_label = QLabel(ui.get("custom_hint_prompt", "Custom hint prompt template (supports {question}, {expected_answer}, {hint}, {language}):"))
        general_group.addWidget(custom_hint_template_label)
        custom_hint_template_input = QTextEdit()
        custom_hint_template_input.setPlainText(config.get("custom_hint_prompt_template", ""))
        custom_hint_template_input.setMinimumHeight(110)
        general_group.addWidget(custom_hint_template_input)

        reset_custom_prompt_btn = QPushButton(ui.get("reset_custom_prompt", "Reset prompts to defaults"))
        general_group.addWidget(reset_custom_prompt_btn)

        def update_default_prompt_placeholders():
            lang_key = language_combo.currentData() or "english"
            localized_template = get_language_specific_prompt(
                lang_key,
                "{question}",
                "{expected_answer}",
                "{accepted_answers}",
                "{user_answer}",
            )
            custom_system_input.setPlaceholderText(build_custom_system_placeholder(ui))
            custom_template_input.setPlaceholderText(localized_template or DEFAULT_CUSTOM_ANALYSIS_PROMPT_TEMPLATE)
            custom_hint_template_input.setPlaceholderText(resolve_prompt_profile_content({}, lang_key, PROMPT_PROFILE_DEFAULT)["hint_prompt_template"])

        def get_selected_prompt_profile() -> str:
            return prompt_profile_combo.currentData() or PROMPT_PROFILE_DEFAULT

        def reset_custom_prompts_to_defaults():
            if get_selected_prompt_profile() != PROMPT_PROFILE_CUSTOM:
                return
            lang_key = language_combo.currentData() or "english"
            resolved_defaults = resolve_prompt_profile_content({}, lang_key, PROMPT_PROFILE_DEFAULT)
            custom_system_input.setPlainText(resolved_defaults["system_prompt"])
            custom_template_input.setPlainText(resolved_defaults["analysis_prompt_template"])
            custom_hint_template_input.setPlainText(resolved_defaults["hint_prompt_template"])

        def update_custom_prompt_inputs():
            enabled = should_show_custom_prompt_fields(get_selected_prompt_profile())
            custom_system_label.setVisible(enabled)
            custom_system_input.setVisible(enabled)
            custom_template_label.setVisible(enabled)
            custom_template_input.setVisible(enabled)
            custom_hint_template_label.setVisible(enabled)
            custom_hint_template_input.setVisible(enabled)
            reset_custom_prompt_btn.setVisible(enabled)
            reset_custom_prompt_btn.setEnabled(enabled)
            custom_system_input.setReadOnly(not enabled)
            custom_template_input.setReadOnly(not enabled)
            custom_hint_template_input.setReadOnly(not enabled)
            if enabled:
                custom_system_input.setStyleSheet("")
                custom_template_input.setStyleSheet("")
                custom_hint_template_input.setStyleSheet("")
            else:
                custom_system_input.setStyleSheet("background: #f2f2f2; color: #6b6b6b;")
                custom_template_input.setStyleSheet("background: #f2f2f2; color: #6b6b6b;")
                custom_hint_template_input.setStyleSheet("background: #f2f2f2; color: #6b6b6b;")

        reset_custom_prompt_btn.clicked.connect(reset_custom_prompts_to_defaults)
        language_combo.currentTextChanged.connect(update_default_prompt_placeholders)
        update_default_prompt_placeholders()
        prompt_profile_combo.currentIndexChanged.connect(update_custom_prompt_inputs)
        update_custom_prompt_inputs()
        
        layout.addLayout(general_group)
        
        # Onglets pour chaque fournisseur
        tabs = QTabWidget()
        
        # Stockage des widgets pour récupérer les valeurs
        api_inputs = {}
        base_url_inputs = {}
        model_combos = {}
        builtin_models_by_provider = {}
        tab_widgets = {}
        
        for provider_key, provider_info in PROVIDERS.items():
            tab = QWidget()
            tab_layout = QVBoxLayout()

            if provider_key == CUSTOM_OPENAI_PROVIDER:
                base_url_layout = QHBoxLayout()
                base_url_layout.addWidget(QLabel(ui.get("base_url", "Base URL:")))
                base_url_input = QLineEdit(config.get(f"{provider_key}_base_url", ""))
                base_url_input.setPlaceholderText(ui.get("base_url_placeholder", "http://127.0.0.1:20128/v1"))
                base_url_layout.addWidget(base_url_input)
                tab_layout.addLayout(base_url_layout)
                base_url_inputs[provider_key] = base_url_input

            # Clé API
            api_key_layout = QHBoxLayout()
            api_key_label = ui.get("api_key_optional", "API Key (optional):") if provider_key == CUSTOM_OPENAI_PROVIDER else f"{provider_info['name']} API Key:"
            api_key_layout.addWidget(QLabel(api_key_label))
            api_key_input = QLineEdit(config.get(f"{provider_key}_api_key", ""))
            
            # Compatible avec PyQt5 et PyQt6 pour le mode password
            try:
                api_key_input.setEchoMode(QLineEdit.EchoMode.Password)  # PyQt6
            except AttributeError:
                try:
                    api_key_input.setEchoMode(QLineEdit.Password)  # PyQt5
                except AttributeError:
                    api_key_input.setEchoMode(2)  # Fallback numérique
            
            api_key_layout.addWidget(api_key_input)
            tab_layout.addLayout(api_key_layout)
            api_inputs[provider_key] = api_key_input
            
            # Modèle
            model_layout = QHBoxLayout()
            model_layout.addWidget(QLabel("Model:"))
            model_combo = QComboBox()
            builtin_models = list(provider_info["models"])
            builtin_models_by_provider[provider_key] = set(builtin_models)
            custom_models = config.get(f"{provider_key}_custom_models", [])
            if not isinstance(custom_models, list):
                custom_models = []
            merged_models = list(builtin_models)
            for cm in custom_models:
                cm = str(cm).strip()
                if cm and cm not in merged_models:
                    merged_models.append(cm)
            model_combo.addItems(merged_models)
            model_combo.setEditable(True)
            current_model = config.get(f"{provider_key}_model", get_provider_default_model(provider_key))
            if current_model in merged_models:
                model_combo.setCurrentText(current_model)
            else:
                model_combo.setEditText(current_model)
            model_layout.addWidget(model_combo)
            tab_layout.addLayout(model_layout)
            model_combos[provider_key] = model_combo

            add_model_layout = QHBoxLayout()
            custom_model_input = QLineEdit()
            custom_model_input.setPlaceholderText(ui.get("model_id_placeholder", "provider/model-id"))
            add_model_btn = QPushButton(ui.get("add_model_id", "Add model ID"))
            add_model_layout.addWidget(custom_model_input)
            add_model_layout.addWidget(add_model_btn)
            tab_layout.addLayout(add_model_layout)

            def add_model_id_to_combo(_checked=False, pk=provider_key, inp=custom_model_input):
                model_id = inp.text().strip()
                if not model_id:
                    return
                combo = model_combos[pk]
                found = False
                for i in range(combo.count()):
                    if combo.itemText(i) == model_id:
                        found = True
                        combo.setCurrentIndex(i)
                        break
                if not found:
                    combo.addItem(model_id)
                    combo.setCurrentText(model_id)
                inp.clear()

            add_model_btn.clicked.connect(add_model_id_to_combo)
            
            # Instructions spécifiques au fournisseur
            instructions = {
                "openai": "Get your API key at: https://platform.openai.com/api-keys",
                "gemini": "Get your API key at: https://aistudio.google.com/app/apikey",
                "claude": "Get your API key at: https://console.anthropic.com/",
                "deepseek": "Get your API key at: https://platform.deepseek.com/api_keys",
                "groq": "Get your API key at: https://console.groq.com/keys",
                "openrouter": "Get your API key at: https://openrouter.ai/settings/keys\nTip: use openrouter/free for maximum compatibility.",
                CUSTOM_OPENAI_PROVIDER: "Enter base URL root, for example: http://127.0.0.1:20128/v1\nDo not enter the full /chat/completions endpoint. API key is optional for local routers."
            }
            
            info_label = QLabel(instructions.get(provider_key, ""))
            info_label.setWordWrap(True)
            info_label.setStyleSheet("color: #666; font-size: 11px; margin: 10px 0;")
            tab_layout.addWidget(info_label)
            
            tab.setLayout(tab_layout)
            tabs.addTab(tab, provider_info["name"])
            tab_widgets[provider_key] = tab
        
        layout.addWidget(tabs)
        
        # Fonction pour activer/désactiver les onglets selon le fournisseur sélectionné
        def update_tab_states():
            selected_provider = provider_combo.currentData()
            for i, (provider_key, _) in enumerate(PROVIDERS.items()):
                tab_enabled = (provider_key == selected_provider)
                tabs.setTabEnabled(i, tab_enabled)
                if tab_enabled:
                    tabs.setCurrentIndex(i)
        
        # Connecter le changement de fournisseur à la mise à jour des onglets
        provider_combo.currentTextChanged.connect(update_tab_states)
        
        # Initialiser l'état des onglets
        update_tab_states()
        
        # Test de connexion
        test_button = QPushButton(ui["test_api"])
        layout.addWidget(test_button)
        
        def test_api():
            current_provider_data = provider_combo.currentData()
            api_key = api_inputs[current_provider_data].text().strip()
            selected_model = model_combos[current_provider_data].currentText().strip()
            base_url = ""

            if current_provider_data == CUSTOM_OPENAI_PROVIDER:
                base_url = base_url_inputs[current_provider_data].text().strip()
                if not base_url:
                    showWarning(ui.get("enter_base_url", "Please enter a base URL to test the connection."))
                    return
                if base_url.rstrip("/").lower().endswith("/chat/completions"):
                    showWarning(ui.get("enter_base_url_root", "Please enter the base URL root, not the full /chat/completions endpoint."))
                    return
                if not selected_model:
                    showWarning(ui.get("enter_model", "Please enter a model ID to test the connection."))
                    return

            if current_provider_data != CUSTOM_OPENAI_PROVIDER and not api_key:
                showWarning(ui["enter_api_key"])
                return
            
            # Changer le texte du bouton pour indiquer le test en cours
            original_text = test_button.text()
            test_button.setText(ui["testing"])
            test_button.setEnabled(False)
            
            try:
                messages = [{"role": "user", "content": "Respond simply 'OK' to test the connection."}]
                response = call_ai_api(
                    messages=messages,
                    provider=current_provider_data,
                    model=selected_model,
                    max_tokens=10,
                    temperature=0.1,
                    api_key=api_key,
                    base_url=base_url
                )
                showInfo("✅ " + ui["connection_success"].format(provider=PROVIDERS[current_provider_data]["name"], response=response[:50] + "..."))
            except Exception as e:
                # OpenRouter models can be intermittently unavailable depending on providers.
                # Retry with the free router to avoid false-negative config tests.
                if current_provider_data == "openrouter":
                    try:
                        response = call_ai_api(
                            messages=messages,
                            provider=current_provider_data,
                            model="openrouter/free",
                            max_tokens=10,
                            temperature=0.1,
                            api_key=api_key
                        )
                        showInfo(
                            "✅ "
                            + ui["connection_success"].format(
                                provider=PROVIDERS[current_provider_data]["name"],
                                response=response[:50] + "...",
                            )
                            + f"\n\nSelected model failed, but fallback 'openrouter/free' worked.\nOriginal error: {str(e)}"
                        )
                        return
                    except Exception:
                        pass
                showWarning("❌ " + ui["connection_error"].format(provider=PROVIDERS[current_provider_data]["name"], error=str(e)))
            finally:
                # Restaurer le bouton
                test_button.setText(original_text)
                test_button.setEnabled(True)
        
        test_button.clicked.connect(test_api)
        
        # Boutons
        button_layout = QHBoxLayout()
        save_button = QPushButton(ui["save"])
        cancel_button = QPushButton(ui["cancel"])
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        scroll_area.setWidget(content_widget)
        root_layout.addWidget(scroll_area)
        root_layout.addLayout(button_layout)
        
        def save_and_close():
            new_config = {
                "provider": provider_combo.currentData(),
                "language": language_combo.currentData(),
                "enabled": enabled_checkbox.isChecked(),
                "max_tokens": tokens_spin.value(),
                "temperature": temp_spin.value(),
                "prompt_profile": get_selected_prompt_profile(),
                "use_custom_prompt": False,
                "custom_system_prompt": custom_system_input.toPlainText().strip(),
                "custom_analysis_prompt_template": custom_template_input.toPlainText().strip(),
                "custom_hint_prompt_template": custom_hint_template_input.toPlainText().strip(),
            }
            new_config["show_anki_compare"] = show_anki_chk.isChecked()
            new_config["show_code_compare"] = show_code_chk.isChecked()
            
            # Sauvegarder toutes les clés API et modèles
            for provider_key in PROVIDERS.keys():
                if provider_key in base_url_inputs:
                    new_config[f"{provider_key}_base_url"] = base_url_inputs[provider_key].text().strip()
                new_config[f"{provider_key}_api_key"] = api_inputs[provider_key].text()
                new_config[f"{provider_key}_model"] = model_combos[provider_key].currentText()
                custom_list = []
                combo = model_combos[provider_key]
                builtin = builtin_models_by_provider.get(provider_key, set())
                for i in range(combo.count()):
                    item = combo.itemText(i).strip()
                    if item and item not in builtin and item not in custom_list:
                        custom_list.append(item)
                new_config[f"{provider_key}_custom_models"] = custom_list
            
            save_config(new_config)
            showInfo(ui["saved"])
            dialog.accept()
        
        save_button.clicked.connect(save_and_close)
        cancel_button.clicked.connect(dialog.reject)
        
        dialog.setLayout(root_layout)
        
        # Compatible avec PyQt5 et PyQt6 pour l'exécution
        try:
            dialog.exec()  # PyQt6
        except AttributeError:
            dialog.exec_()  # PyQt5
    
    # Ajouter au menu Tools
    action = mw.form.menuTools.addAction(get_config_ui_texts(get_config())["menu_title"])
    action.triggered.connect(open_config)

# Commande pour rafraîchir l'analyse IA
def refresh_ai_analysis(request_identity=None):
    """Rafraîchit l'affichage de l'analyse IA"""
    if refresh_current_ai_analysis_panel(request_identity):
        return
    if hasattr(mw, 'reviewer') and mw.reviewer and hasattr(mw.reviewer, 'card') and mw.reviewer.card:
        if hasattr(mw.reviewer, '_showAnswer'):
            mw.reviewer._showAnswer()


def regenerate_ai_analysis():
    card = mw.reviewer.card if hasattr(mw, 'reviewer') and mw.reviewer else None
    if not should_score_card(card):
        return
    context = dict(current_analysis_context)
    cache_key = context.get("cache_key")
    expected_provided_tuple = context.get("expected_provided_tuple")
    type_pattern = context.get("type_pattern")
    if not cache_key or not expected_provided_tuple:
        return
    if is_analyzing.get(cache_key, False):
        refresh_ai_analysis()
        return
    invalidate_analysis_state(cache_key)
    store_ai_analysis(expected_provided_tuple, type_pattern)
    refresh_ai_analysis()

# Enregistrer la commande pour le JavaScript
def register_refresh_command():
    """Enregistre la commande de rafraîchissement pour le JavaScript"""
    try:
        from aqt import gui_hooks
        gui_hooks.webview_did_receive_js_message.append(handle_js_message)
    except ImportError:
        pass

def handle_js_message(handled, message, context):
    """Gère les messages JavaScript"""
    if message == "refresh_ai_analysis":
        refresh_ai_analysis()
        return True, None
    if message == "regenerate_ai_analysis":
        regenerate_ai_analysis()
        return True, None
    if message == "toggle_hint_panel":
        card = mw.reviewer.card if hasattr(mw, "reviewer") and mw.reviewer else None
        if is_front_hint_eligible(card, "", "Question"):
            context_data = build_front_hint_context(card)
            cache_key = context_data["cache_key"]
            is_open = not (front_hint_panel_state.get("cache_key") == cache_key and front_hint_panel_state.get("is_open"))
            front_hint_panel_state.update({"cache_key": cache_key, "is_open": is_open})
            current_hint_context.update(context_data)
            refresh_current_front_hint_panel(cache_key)
        return True, None
    if message == "suggest_ai_hint":
        suggest_ai_hint()
        return True, None
    if message == "regenerate_ai_hint":
        regenerate_ai_hint()
        return True, None
    return handled

# Initialisation
def init():
    """Initialise l'add-on"""
    setup_config_menu()
    register_refresh_command()
    
    # Nettoyer les caches au démarrage
    ai_analysis_cache.clear()
    is_analyzing.clear()
    analysis_results.clear()
    reset_active_question_state()
    reset_hint_state()
    
def _debug_dump_front(text, card, kind):
    if kind and "Question" in kind:
        print("=== FRONT HTML START ===")
        print(text[:4000])  # enough to see the input markup
        print("=== FRONT HTML END ===")
    return text

# Add the functions to the hooks
gui_hooks.card_will_show.append(_to_textarea_on_question)
gui_hooks.card_will_show.append(render_front_hint_panel)
gui_hooks.card_will_show.append(_code_friendly_diff_on_answer)
gui_hooks.reviewer_will_compare_answer.append(store_ai_analysis)
gui_hooks.reviewer_will_render_compared_answer.append(render_enhanced_comparison)

# Initialiser lors du chargement
init()





