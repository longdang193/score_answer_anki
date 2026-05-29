import html
import re
from aqt import gui_hooks


ai_analysis_cache = {}
is_analyzing = {}
analysis_results = {}

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
/* Couleurs thème-aware pour les blocs de comparaison */
:root {
  --ak-code-bg: #fafafa;
  --ak-code-fg: #1b1b1b;
  --ak-code-border: #ddd;
  --ak-code-label: #222;
}

/* Détection du sombre dans Anki + fallback */
body.nightMode, body.night-mode, .nightMode, .night-mode, .isDark, [data-theme="dark"] {
  --ak-code-bg: #0f1116;
  --ak-code-fg: #e6edf3;
  --ak-code-border: #2d333b;
  --ak-code-label: #e6edf3;
}

/* Fallback pour systèmes qui annoncent le thème via le média */
@media (prefers-color-scheme: dark) {
  :root {
    --ak-code-bg: #0f1116;
    --ak-code-fg: #e6edf3;
    --ak-code-border: #2d333b;
    --ak-code-label: #e6edf3;
  }
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

def _code_compare_block(expected: str, provided: str, lang_hint: str, labels: dict) -> str:
    exp_text = extract_code_text(expected)
    prov_text = extract_code_text(provided)
    le = labels.get("expected", "Expected")
    lp = labels.get("provided", "Your answer")
    return f"""
    <div class="ak-compare" style="display:flex; gap:12px; margin:12px 0;">
      <div style="flex:1; min-width:0;">
        <div class="ak-label">{html.escape(le)}</div>
        <pre class="ak-pre"><code class="language-{lang_hint}">{html.escape(exp_text)}</code></pre>
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
        "review_suggestion": None,
    }

def store_ai_analysis(expected_provided_tuple, type_pattern):
    """
    Lance l'analyse IA en arrière-plan pour ne pas bloquer l'UI,
    afin que le verso s'affiche tout de suite avec un spinner.
    """
    true_answer = expected_provided_tuple[0] or ""
    user_answer = expected_provided_tuple[1] or ""

    question_text = get_current_question()
    cache_key = f"{hash(question_text)}_{hash(true_answer)}_{hash(user_answer)}"

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
            return analyze_answer_with_ai(question_text, true_answer, user_answer)
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
            refresh_ai_analysis()
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

def get_current_question():
    """
    **NOUVELLE FONCTION: Récupère le contenu de la question de la carte actuelle**
    """
    try:
        if hasattr(mw, 'reviewer') and mw.reviewer and hasattr(mw.reviewer, 'card') and mw.reviewer.card:
            card = mw.reviewer.card
            
            # Récupérer le contenu de la question (front de la carte)
            question_html = card.question()
            
            # Nettoyer le HTML pour extraire le texte
            question_text = clean_html_content(question_html)
            
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
    labels = get_compare_labels(config)
    show_anki = config.get("show_anki_compare", True)
    show_code = config.get("show_code_compare", True)
    
    # Skip if AI is disabled
    if not config.get("enabled", True):
        return output
    
    # **MODIFIÉ: Inclure la question dans la clé de cache**
    question_text = get_current_question()
    cache_key = f"{hash(question_text)}_{hash(initial_expected)}_{hash(initial_provided)}"
    print(f"Rendering comparison for key: {cache_key}")
    
    # Vérification simplifiée - si l'analyse est en cours, afficher un message simple
    if is_analyzing.get(cache_key, False) and cache_key not in ai_analysis_cache:
        print(f"Analysis in progress for {cache_key}, showing simple loading message")
        # Message de chargement simple sans JavaScript compliqué
        # Dans render_enhanced_comparison, remplacer le spinner_output par :
        spinner_output = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto;">

            <!-- Comparaison par défaut d'Anki -->
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #6c757d;">
                {output}
            </div>

            <!-- Bloc chargement -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; border-radius: 16px; padding: 25px; margin: 20px 0; text-align: center; color: white; position: relative; overflow: hidden;">
                <div style="display: inline-flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                    <div style="width: 26px; height: 26px; border: 3px solid rgba(255,255,255,0.35); border-top-color: #fff; border-radius: 50%; animation: aki_spin 0.9s linear infinite;"></div>
                    <div style="font-size: 18px; font-weight: 600;">{texts['analyzing']}</div>
                </div>
                <p style="color: rgba(255,255,255,0.9); margin: 0; font-size: 14px;">
                    {texts['please_wait']}
                </p>
                <p style="color: rgba(255,255,255,0.7); margin-top: 10px; font-size: 12px; font-style: italic;">
                    Actualisation automatique...
                </p>
            </div>

            <!-- Style + auto-refresh doux -->
            <style>
            @keyframes aki_spin {{ to {{ transform: rotate(360deg); }} }}
            </style>
            <script>
            // Relance un rafraîchissement du verso pendant l'analyse.
            // Sans boucle infinie: on appelle 1 fois à T+1.2s; si encore en cours, le même bloc se ré-affichera et relancera ce timeout.
            setTimeout(function() {{
                if (typeof pycmd === 'function') {{
                pycmd('refresh_ai_analysis');
                }}
            }}, 1200);
            </script>
        </div>
        """
        return spinner_output
    
    # Récupérer l'analyse IA stockée avec debug
    ai_analysis = analysis_results.get(cache_key) or ai_analysis_cache.get(cache_key)
    print(f"Retrieved analysis for {cache_key}: {ai_analysis is not None}")
    
    # Si l'analyse n'est pas disponible, utiliser des valeurs par défaut
    if not ai_analysis:
        print(f"No analysis available for {cache_key}, using defaults")
        ai_analysis = make_analysis_unavailable("", language)
    
    is_scored = bool(ai_analysis.get("scored", True)) and isinstance(ai_analysis.get("score"), int)

    # Déterminer les couleurs selon le score
    score = ai_analysis.get('score', 5) if is_scored else None
    if not is_scored:
        score_color = "#6c757d"
        score_bg = "#f3f4f6"
        score_icon = "ℹ️"
    elif score <= 3:
        score_color = "#f44336"  # Rouge
        score_bg = "#ffebee"
        score_icon = "❌"
    elif score <= 5:
        score_color = "#ff9800"  # Orange
        score_bg = "#fff3e0"
        score_icon = "⚠️"
    elif score <= 8:
        score_color = "#4caf50"  # Vert
        score_bg = "#e8f5e8"
        score_icon = "✅"
    else:
        score_color = "#2196f3"  # Bleu
        score_bg = "#e3f2fd"
        score_icon = "🌟"
    
    # Déterminer la couleur de la suggestion
    suggestion = ai_analysis.get('review_suggestion', 'Good') if is_scored else None
    suggestion_colors = {
        "Again": ("#f44336", "#ffebee", "🔄"),
        "Hard": ("#ff9800", "#fff3e0", "🔥"), 
        "Good": ("#4caf50", "#e8f5e8", "👍"),
        "Easy": ("#2196f3", "#e3f2fd", "😎")
    }
    suggestion_color, suggestion_bg, suggestion_icon = suggestion_colors.get(suggestion, ("#4caf50", "#e8f5e8", "👍"))
    score_badge = f"{score_icon} {score}/10" if is_scored else f"{score_icon} N/A"
    suggestion_section = f"""
            <div style="background: linear-gradient(135deg, {suggestion_bg}, {suggestion_bg}dd); border: 2px solid {suggestion_color}; border-radius: 12px; padding: 16px;">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <span style="color: #2c3e50; font-weight: 700; font-size: 16px; display: flex; align-items: center;">
                        🎯 {texts.get('review_suggestion', 'Review Suggestion')}:
                    </span>
                    <span style="background: linear-gradient(135deg, {suggestion_color}, {suggestion_color}dd); color: white; padding: 10px 18px; border-radius: 20px; font-weight: bold; font-size: 15px; box-shadow: 0 3px 10px rgba(0,0,0,0.2);">
                        {suggestion_icon} {texts.get('suggestions', {}).get(suggestion, suggestion)}
                    </span>
                </div>
            </div>
    """ if is_scored else ""
    
    # **NOUVEAU: Afficher la question pour plus de contexte si elle existe**
    question_display = ""
    if question_text and len(question_text.strip()) > 0:
        # Limiter la longueur de la question affichée
        display_question = question_text[:200] + "..." if len(question_text) > 200 else question_text
        question_display = f"""
        <div style="background: rgba(255,255,255,0.9); border: 2px solid #e0e0e0; border-radius: 12px; padding: 15px; margin-bottom: 15px;">
            <h4 style="color: #2c3e50; margin: 0 0 8px 0; font-size: 16px; font-weight: 700; display: flex; align-items: center;">
                ❓ {texts.get('question_context', 'Question Context')}:
            </h4>
            <p style="color: #34495e; margin: 0; line-height: 1.4; font-size: 14px; font-style: italic;">
                {display_question}
            </p>
        </div>
        """
    
    # Affichage alternatif fidèle pour le code (en plus du diff Anki)
    anki_section = f"""
    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #6c757d;">
    {output}
    </div>
    """ if show_anki else ""

    code_block = _code_compare_block(initial_expected, initial_provided, lang_hint="", labels=labels) if show_code else ""
        
    # Affichage simplifié des résultats
    enhanced_output = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto;">
        {anki_section}
        {code_block}
        
        <!-- Analyse IA avec animation d'apparition -->
        <div style="background: {score_bg}; border: 2px solid {score_color}; border-radius: 16px; padding: 25px; margin: 20px 0; box-shadow: 0 8px 32px rgba(0,0,0,0.1);">
            
            <div style="display: flex; align-items: center; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; flex: 1;">
                    <div style="background: {score_color}; width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                        <span style="font-size: 20px;">🤖</span>
                    </div>
                    <h3 style="color: {score_color}; margin: 0; font-size: 22px; font-weight: 700;">
                        {texts.get('ai_analysis', 'AI Analysis')}
                    </h3>
                </div>
                <div style="background: linear-gradient(135deg, {score_color}, {score_color}dd); color: white; padding: 12px 20px; border-radius: 25px; font-weight: bold; font-size: 18px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
                    {score_badge}
                </div>
            </div>
            
            {question_display}
            
            <div style="margin-bottom: 20px; padding: 15px; background: rgba(255,255,255,0.7); border-radius: 12px; border-left: 4px solid {score_color};">
                <h4 style="color: #2c3e50; margin: 0 0 10px 0; font-size: clamp(15px, 4vw, 17px); font-weight: 700; text-transform: uppercase; letter-spacing: 1px; display: flex; align-items: center;">
                    💡 {texts.get('improvement_tips', 'Improvement Tips')}
                </h4>
                <p style="color: #34495e; margin: 0; line-height: 1.6; font-size: clamp(14px, 4vw, 16px);">
                    {ai_analysis.get('tips', texts.get('no_tips_available', 'No tips available'))}
                </p>
            </div>
            
            {suggestion_section}
        </div>
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
    "enabled": True,
    "max_tokens": 200,
    "temperature": 0.7,
    "show_anki_compare": True,
    "show_code_compare": True,
    "ui_language": "auto",  # 'auto' | 'en' | 'fr' | 'es' | 'de' | 'pt' | 'it' | 'ru' | 'ja' | 'zh' | 'ko'
    "use_custom_prompt": False,
    "custom_system_prompt": "",
    "custom_analysis_prompt_template": ""
}

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
Student answer: "{user_answer}"
Language: "{language}"

Return ONLY valid JSON with this schema:
{
  "score": 0,
  "tips": "short constructive feedback",
  "review_suggestion": "Again"
}

Rules:
- score is an integer from 0 to 10
- review_suggestion must be one of: Again, Hard, Good, Easy
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
        "max_tokens": "Max tokens:",
        "temperature": "Temperature (0-1):",
        "use_custom_prompt": "Use custom prompt template",
        "custom_system_prompt": "Custom system prompt (optional):",
        "custom_analysis_prompt": "Custom analysis prompt template (supports {question}, {expected_answer}, {user_answer}, {language}):",
        "custom_system_placeholder": "If empty, language default system prompt is used.",
        "reset_custom_prompt": "Reset prompts to defaults",
        "copy_default_prompts": "Copy default prompts",
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
        "max_tokens": "Max tokens :",
        "temperature": "Temperature (0-1) :",
        "use_custom_prompt": "Utiliser un prompt personnalise",
        "custom_system_prompt": "Prompt systeme personnalise (optionnel) :",
        "custom_analysis_prompt": "Template du prompt d'analyse (variables {question}, {expected_answer}, {user_answer}, {language}) :",
        "custom_system_placeholder": "Si vide, le prompt systeme par defaut de la langue est utilise.",
        "reset_custom_prompt": "Reinitialiser les prompts par defaut",
        "copy_default_prompts": "Copier les prompts par defaut",
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
        "max_tokens": "Max tokens:",
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
        "max_tokens": "Max Tokens:",
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
        "max_tokens": "Макс. токенов:",
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
        "max_tokens": "最大トークン:",
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
        "max_tokens": "最大 tokens：",
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
        "max_tokens": "최대 토큰:",
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

def get_config_ui_texts(config=None):
    cfg = config or {}
    sel = str(cfg.get("ui_language", "auto")).lower()
    code = _detect_ui_lang_code() if sel == "auto" else sel[:2]
    return CONFIG_UI_TEXTS.get(code, CONFIG_UI_TEXTS["en"])

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
    }
}

def get_config():
    """Récupère la configuration depuis les métadonnées d'Anki"""
    try:
        config = mw.addonManager.getConfig(__name__)
        if not config:
            config = DEFAULT_CONFIG
            save_config(config)
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return DEFAULT_CONFIG

def save_config(config):
    """Sauvegarde la configuration dans les métadonnées d'Anki"""
    try:
        mw.addonManager.writeConfig(__name__, config)
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

def call_ai_api(messages, provider="openai", model="gpt-4.1-mini", max_tokens=200, temperature=0.7, api_key=""):
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

def get_language_specific_prompt(language, question_text, true_answer, user_answer):
    """
    **MODIFIÉ: Génère un prompt selon la langue configurée avec contexte de question**
    """
    
    prompts = {
        "english": f"""
        Analyze the student's answer in the context of the given question and provide a structured evaluation.

        Question: "{question_text}"
        Expected answer: "{true_answer}"
        Student's answer: "{user_answer}"

        Please provide your evaluation in the following JSON format:
        {{
            "score": [number from 0 to 10],
            "tips": "[constructive feedback in English, maximum 100 words, considering the question context]",
            "review_suggestion": "[choose from: Again, Hard, Good, Easy]"
        }}

        Evaluation criteria:
        - Score 0-3: Incorrect or very incomplete answer → "Again"
        - Score 4-5: Partially correct but with significant errors → "Hard"  
        - Score 6-8: Correct answer with minor imperfections → "Good"
        - Score 9-10: Excellent and complete answer → "Easy"
        
        Consider the question context when evaluating the relevance and completeness of the student's response.
        """,
        
        "french": f"""
        Analysez la réponse de l'étudiant dans le contexte de la question donnée et fournissez une évaluation structurée.

        Question: "{question_text}"
        Réponse attendue: "{true_answer}"
        Réponse de l'étudiant: "{user_answer}"

        Veuillez fournir votre évaluation au format JSON suivant:
        {{
            "score": [nombre de 0 à 10],
            "tips": "[conseils constructifs en français, maximum 100 mots, en tenant compte du contexte de la question]",
            "review_suggestion": "[choisir parmi: Again, Hard, Good, Easy]"
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
        Respuesta del estudiante: "{user_answer}"

        Por favor proporciona tu evaluación en el siguiente formato JSON:
        {{
            "score": [número del 0 al 10],
            "tips": "[comentarios constructivos en español, máximo 100 palabras, considerando el contexto de la pregunta]",
            "review_suggestion": "[elegir entre: Again, Hard, Good, Easy]"
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
        Antwort des Studenten: "{user_answer}"

        Bitte geben Sie Ihre Bewertung im folgenden JSON-Format an:
        {{
            "score": [Zahl von 0 bis 10],
            "tips": "[konstruktives Feedback auf Deutsch, maximal 100 Wörter, unter Berücksichtigung des Fragenkontexts]",
            "review_suggestion": "[wählen Sie aus: Again, Hard, Good, Easy]"
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
        Ответ студента: "{user_answer}"

        Предоставьте оценку в формате JSON:
        {{
            "score": [число от 0 до 10],
            "tips": "[конструктивная обратная связь на русском, максимум 100 слов, учитывая контекст вопроса]",
            "review_suggestion": "[выберите из: Again, Hard, Good, Easy]"
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
        学習者の回答: "{user_answer}"

        次のJSON形式で返してください:
        {{
            "score": [0から10の数値],
            "tips": "[日本語で建設的なフィードバック。100語以内。問題文の文脈を考慮すること]",
            "review_suggestion": "[Again, Hard, Good, Easy から選択]"
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
        学生答案: "{user_answer}"

        请使用以下 JSON 格式输出:
        {{
            "score": [0 到 10 的数字],
            "tips": "[中文的建设性反馈，最多100词，并结合题目上下文]",
            "review_suggestion": "[从 Again, Hard, Good, Easy 中选择]"
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
        학생 답변: "{user_answer}"

        다음 JSON 형식으로 답변하세요:
        {{
            "score": [0에서 10 사이 숫자],
            "tips": "[한국어로 된 건설적인 피드백, 최대 100단어, 질문 맥락 반영]",
            "review_suggestion": "[Again, Hard, Good, Easy 중 하나]"
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

def build_analysis_prompt(config, language, question_text, true_answer, user_answer):
    use_custom_prompt = bool(config.get("use_custom_prompt", False))
    template = (config.get("custom_analysis_prompt_template", "") or "").strip()

    if use_custom_prompt and template:
        rendered = template
        replacements = {
            "{question}": question_text or "",
            "{expected_answer}": true_answer or "",
            "{user_answer}": user_answer or "",
            "{language}": language or "english",
        }
        for token, value in replacements.items():
            rendered = rendered.replace(token, value)
        return rendered

    return get_language_specific_prompt(language, question_text, true_answer, user_answer)

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
        f'- Keep "review_suggestion" in English enum values only: Again, Hard, Good, Easy.\n'
        f'- Do not use another language for "tips".\n'
        f'- Return valid JSON only.'
    )

def analyze_answer_with_ai(question_text: str, true_answer: str, user_answer: str) -> dict:
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
    if not api_key:
        return make_analysis_unavailable(f"{PROVIDERS[provider]['name']} API key not configured", language)
    
    prompt = build_analysis_prompt(config, language, question_text, true_answer, user_answer) + get_language_lock_instruction(language)
    custom_system_prompt = (config.get("custom_system_prompt", "") or "").strip()
    system_message = custom_system_prompt or get_system_message_for_language(language)

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]

    try:
        ai_response = call_ai_api(
            messages=messages,
            provider=provider,
            model=config.get(model_field, PROVIDERS[provider]["models"][0]),
            max_tokens=config.get("max_tokens", 200),
            temperature=config.get("temperature", 0.7),
            api_key=api_key
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
            
            result = json.loads(clean_response)
            # Valider les champs requis
            if all(key in result for key in ["score", "tips", "review_suggestion"]):
                # Valider le score
                result["score"] = max(0, min(10, int(result["score"])))
                # Valider la suggestion de révision
                if result["review_suggestion"] not in ["Again", "Hard", "Good", "Easy"]:
                    result["review_suggestion"] = "Good"
                result["scored"] = True
                return result
        except (json.JSONDecodeError, ValueError, KeyError):
            pass
        
        # Si le parsing JSON échoue, essayer d'extraire les informations
        lines = ai_response.split('\n')
        score = 5
        tips = "Analyse disponible dans la réponse complète"
        review_suggestion = "Good"
        
        for line in lines:
            if 'score' in line.lower():
                try:
                    import re
                    score_match = re.search(r'(\d+)', line)
                    if score_match:
                        score = max(0, min(10, int(score_match.group(1))))
                except:
                    pass
        
        return {"scored": True, "score": score, "tips": ai_response[:300] + "...", "review_suggestion": review_suggestion}
        
    except Exception as e:
        print(f"AI Analysis Error: {str(e)}")  # Pour debugging
        return make_analysis_unavailable(f"{PROVIDERS[provider]['name']}: {str(e)}", language)

def setup_config_menu():
    """Configure le menu de configuration"""
    def open_config():
        config = get_config()
        ui = get_config_ui_texts(config)
        
        # Interface simple pour la configuration
        from aqt.qt import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton, QSpinBox, QDoubleSpinBox, QTabWidget, QWidget, QTextEdit, QApplication
        
        dialog = QDialog(mw)
        dialog.setWindowTitle(ui["window_title"])
        dialog.setMinimumWidth(550)
        dialog.setMinimumHeight(700)
        
        layout = QVBoxLayout()
        
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
        tokens_spin.setRange(300, 4000)
        tokens_spin.setValue(max(config.get("max_tokens", 300), 300))
        tokens_layout.addWidget(tokens_spin)
        general_group.addLayout(tokens_layout)
        
        # Temperature
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel(ui["temperature"]))
        temp_spin = QDoubleSpinBox()
        temp_spin.setRange(0.0, 1.0)
        temp_spin.setSingleStep(0.1)
        temp_spin.setValue(config.get("temperature", 0.7))
        temp_layout.addWidget(temp_spin)
        general_group.addLayout(temp_layout)

        use_custom_prompt_chk = QCheckBox(ui["use_custom_prompt"])
        use_custom_prompt_chk.setChecked(config.get("use_custom_prompt", False))
        general_group.addWidget(use_custom_prompt_chk)

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

        reset_custom_prompt_btn = QPushButton(ui.get("reset_custom_prompt", "Reset prompts to defaults"))
        general_group.addWidget(reset_custom_prompt_btn)
        copy_default_prompt_btn = QPushButton(ui.get("copy_default_prompts", "Copy default prompts"))
        general_group.addWidget(copy_default_prompt_btn)

        def update_default_prompt_placeholders():
            lang_key = language_combo.currentData() or "english"
            localized_system = get_system_message_for_language(lang_key)
            localized_template = get_language_specific_prompt(
                lang_key,
                "{question}",
                "{expected_answer}",
                "{user_answer}",
            )
            custom_system_input.setPlaceholderText(ui["custom_system_placeholder"] + "\n\n" + localized_system)
            custom_template_input.setPlaceholderText(localized_template or DEFAULT_CUSTOM_ANALYSIS_PROMPT_TEMPLATE)

        def reset_custom_prompts_to_defaults():
            lang_key = language_combo.currentData() or "english"
            custom_system_input.setPlainText(get_system_message_for_language(lang_key))
            custom_template_input.setPlainText(
                get_language_specific_prompt(
                    lang_key,
                    "{question}",
                    "{expected_answer}",
                    "{user_answer}",
                )
            )

        def copy_default_prompts_to_clipboard():
            lang_key = language_combo.currentData() or "english"
            default_system = get_system_message_for_language(lang_key)
            default_template = get_language_specific_prompt(
                lang_key,
                "{question}",
                "{expected_answer}",
                "{user_answer}",
            )
            payload = (
                "=== Default system prompt ===\n"
                f"{default_system}\n\n"
                "=== Default analysis prompt template ===\n"
                f"{default_template}"
            )
            QApplication.clipboard().setText(payload)
            showInfo(ui.get("copied_default_prompts", "Default prompts copied to clipboard."))

        def update_custom_prompt_inputs():
            enabled = use_custom_prompt_chk.isChecked()
            custom_system_input.setReadOnly(not enabled)
            custom_template_input.setReadOnly(not enabled)
            reset_custom_prompt_btn.setEnabled(enabled)
            if enabled:
                custom_system_input.setStyleSheet("")
                custom_template_input.setStyleSheet("")
            else:
                custom_system_input.setStyleSheet("background: #f2f2f2; color: #6b6b6b;")
                custom_template_input.setStyleSheet("background: #f2f2f2; color: #6b6b6b;")

        reset_custom_prompt_btn.clicked.connect(reset_custom_prompts_to_defaults)
        copy_default_prompt_btn.clicked.connect(copy_default_prompts_to_clipboard)
        language_combo.currentTextChanged.connect(update_default_prompt_placeholders)
        update_default_prompt_placeholders()
        use_custom_prompt_chk.toggled.connect(update_custom_prompt_inputs)
        update_custom_prompt_inputs()
        
        layout.addLayout(general_group)
        
        # Onglets pour chaque fournisseur
        tabs = QTabWidget()
        
        # Stockage des widgets pour récupérer les valeurs
        api_inputs = {}
        model_combos = {}
        builtin_models_by_provider = {}
        tab_widgets = {}
        
        for provider_key, provider_info in PROVIDERS.items():
            tab = QWidget()
            tab_layout = QVBoxLayout()
            
            # Clé API
            api_key_layout = QHBoxLayout()
            api_key_layout.addWidget(QLabel(f"{provider_info['name']} API Key:"))
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
            current_model = config.get(f"{provider_key}_model", provider_info["models"][0])
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
                "openrouter": "Get your API key at: https://openrouter.ai/settings/keys\nTip: use openrouter/free for maximum compatibility."
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
            
            if not api_key:
                showWarning(ui["enter_api_key"])
                return
            
            # Changer le texte du bouton pour indiquer le test en cours
            original_text = test_button.text()
            test_button.setText(ui["testing"])
            test_button.setEnabled(False)
            
            try:
                messages = [{"role": "user", "content": "Respond simply 'OK' to test the connection."}]
                selected_model = model_combos[current_provider_data].currentText()
                response = call_ai_api(
                    messages=messages,
                    provider=current_provider_data,
                    model=selected_model,
                    max_tokens=10,
                    temperature=0.1,
                    api_key=api_key
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
        layout.addLayout(button_layout)
        
        def save_and_close():
            new_config = {
                "provider": provider_combo.currentData(),
                "language": language_combo.currentData(),
                "enabled": enabled_checkbox.isChecked(),
                "max_tokens": tokens_spin.value(),
                "temperature": temp_spin.value(),
                "use_custom_prompt": use_custom_prompt_chk.isChecked(),
                "custom_system_prompt": custom_system_input.toPlainText().strip(),
                "custom_analysis_prompt_template": custom_template_input.toPlainText().strip(),
            }
            new_config["show_anki_compare"] = show_anki_chk.isChecked()
            new_config["show_code_compare"] = show_code_chk.isChecked()
            
            # Sauvegarder toutes les clés API et modèles
            for provider_key in PROVIDERS.keys():
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
        
        dialog.setLayout(layout)
        
        # Compatible avec PyQt5 et PyQt6 pour l'exécution
        try:
            dialog.exec()  # PyQt6
        except AttributeError:
            dialog.exec_()  # PyQt5
    
    # Ajouter au menu Tools
    action = mw.form.menuTools.addAction(get_config_ui_texts(get_config())["menu_title"])
    action.triggered.connect(open_config)

# Commande pour rafraîchir l'analyse IA
def refresh_ai_analysis():
    """Rafraîchit l'affichage de l'analyse IA"""
    if hasattr(mw, 'reviewer') and mw.reviewer and hasattr(mw.reviewer, 'card') and mw.reviewer.card:
        if hasattr(mw.reviewer, '_showAnswer'):
            mw.reviewer._showAnswer()

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
    
def _debug_dump_front(text, card, kind):
    if kind and "Question" in kind:
        print("=== FRONT HTML START ===")
        print(text[:4000])  # enough to see the input markup
        print("=== FRONT HTML END ===")
    return text

# Add the functions to the hooks
gui_hooks.card_will_show.append(_to_textarea_on_question)
gui_hooks.card_will_show.append(_code_friendly_diff_on_answer)
gui_hooks.reviewer_will_compare_answer.append(store_ai_analysis)
gui_hooks.reviewer_will_render_compared_answer.append(render_enhanced_comparison)

# Initialiser lors du chargement
init()