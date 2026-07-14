from __future__ import annotations

import ast
import hashlib
import html
import os
import pathlib
import random
import re
import time

from aqt import gui_hooks, mw
from aqt.utils import showInfo, showWarning

from locales import *
from locales import _detect_ui_lang_code, _get_language_bundle
from config_model import *
from config_model import get_config as _config_get_config, save_config as _config_save_config
from ai_runtime import *

ADDON_EXPORTS = None


def _addon_attr(name: str, fallback):
    if isinstance(ADDON_EXPORTS, dict) and name in ADDON_EXPORTS:
        return ADDON_EXPORTS[name]
    return fallback

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

ANALYSIS_PROMPT_VERSION = "v1"

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

def _to_textarea_on_question(text: str, card, kind: str) -> str:
    text = apply_question_variant_to_rendered_question(text, card, kind)

    if not kind or "Question" not in kind:
        return text
    if not should_score_card(card):
        return text

    # robust: quoted/unquoted id=typeans
    pat = re.compile(r'(?is)<input(?P<attrs>[^>]*\bid\s*=\s*(?:"|\')?typeans(?:"|\')?[^>]*)>')
    textarea_rows = 6
    textarea_min_height = "132px"

    def build_shared_js() -> str:
        return """
function insertTabIntoTextarea(ta){
  if(!ta) return;
  var start=ta.selectionStart||0,end=ta.selectionEnd||0,value=ta.value||'';
  ta.value=value.slice(0,start)+'	'+value.slice(end);
  ta.focus();
  ta.selectionStart=ta.selectionEnd=start+1;
}
function getReviewerScrollRoot(){
  return document.scrollingElement || document.documentElement || document.body || null;
}
function getTypedAnswerFooter(){
  return document.getElementById('aqi-review-footer');
}
function ensureTypedAnswerFooter(){
  var footer=getTypedAnswerFooter();
  if(!footer){
    footer=document.createElement('div');
    footer.id='aqi-review-footer';
    footer.setAttribute('data-aqi-review-footer','1');
    footer.innerHTML='<div class="aqi-review-footer__content"><div class="aqi-review-footer__input"></div><div class="aqi-review-footer__hint"></div></div>';
    (document.body||document.documentElement).appendChild(footer);
  }
  if(!footer.querySelector('.aqi-review-footer__content')){
    footer.innerHTML='<div class="aqi-review-footer__content"><div class="aqi-review-footer__input"></div><div class="aqi-review-footer__hint"></div></div>';
  }
  return footer;
}
function disconnectTypedAnswerFooterObserver(){
  if(window.__aqiTypedAnswerFooterResizeObserver&&typeof window.__aqiTypedAnswerFooterResizeObserver.disconnect==='function'){
    window.__aqiTypedAnswerFooterResizeObserver.disconnect();
  }
  window.__aqiTypedAnswerFooterResizeObserver=null;
  window.__aqiTypedAnswerFooterResizeTarget=null;
}
function clearTypedAnswerFooter(){
  disconnectTypedAnswerFooterObserver();
  var footer=getTypedAnswerFooter();
  if(footer&&footer.parentNode){ footer.parentNode.removeChild(footer); }
  var root=getReviewerScrollRoot();
  if(root&&root.classList){ root.classList.remove('aqi-review-footer-active'); }
  try{ document.documentElement.style.setProperty('--aqi-review-footer-offset','0px'); }catch(_){ }
}
function syncTypedAnswerFooterOffset(){
  var footer=getTypedAnswerFooter();
  var root=getReviewerScrollRoot();
  var height=footer?Math.ceil(footer.getBoundingClientRect().height):0;
  try{ document.documentElement.style.setProperty('--aqi-review-footer-offset', height+'px'); }catch(_){ }
  if(root&&root.classList){
    if(height>0){ root.classList.add('aqi-review-footer-active'); }
    else { root.classList.remove('aqi-review-footer-active'); }
  }
  return height;
}
function measureTypedAnswerFooterGeometry(){
  var footer=getTypedAnswerFooter();
  if(!footer) return null;
  var candidates=Array.prototype.slice.call(document.body.querySelectorAll('.aqi-active-question,.sqv-active-question,.aqi-question-block,.sqv-question-block,body>*'));
  var lastNode=null;
  for(var i=0;i<candidates.length;i++){
    var node=candidates[i];
    if(!node||node===footer||footer.contains(node)) continue;
    var tag=(node.tagName||'').toLowerCase();
    if(tag==='script'||tag==='style') continue;
    if(((node.innerText||node.textContent||'').trim())) lastNode=node;
  }
  if(!lastNode) return null;
  var footerRect=footer.getBoundingClientRect();
  var questionRect=lastNode.getBoundingClientRect();
  var geometry={
    footerTop: Math.round(footerRect.top),
    questionBottom: Math.round(questionRect.bottom),
    ok: questionRect.bottom<=footerRect.top
  };
  window.__aqiTypedAnswerFooterGeometry=geometry;
  return geometry;
}
function ensureTypedAnswerFooterResizeObserver(){
  var footer=getTypedAnswerFooter();
  if(!footer) return;
  if(window.__aqiTypedAnswerFooterResizeTarget===footer) return;
  disconnectTypedAnswerFooterObserver();
  if(typeof ResizeObserver!=='function') return;
  window.__aqiTypedAnswerFooterResizeTarget=footer;
  window.__aqiTypedAnswerFooterResizeObserver=new ResizeObserver(function(){
    syncTypedAnswerFooterOffset();
    measureTypedAnswerFooterGeometry();
  });
  window.__aqiTypedAnswerFooterResizeObserver.observe(footer);
}
function ensureTypedAnswerFooterMutationObserver(){
  if(window.__aqiTypedAnswerFooterMutationObserver||typeof MutationObserver!=='function') return;
  window.__aqiTypedAnswerFooterMutationObserver=new MutationObserver(function(){ syncTypedAnswerFooter(); });
  window.__aqiTypedAnswerFooterMutationObserver.observe(document.documentElement||document.body,{childList:true,subtree:true});
}
function syncTypedAnswerFooter(){
  var ta=document.getElementById('typeans');
  var wrap=ta&&typeof ta.closest==='function'?ta.closest('.aqi-type-input-wrap'):null;
  if(!wrap){
    clearTypedAnswerFooter();
    return null;
  }
  var footer=ensureTypedAnswerFooter();
  var inputHost=footer.querySelector('.aqi-review-footer__input');
  var hintHost=footer.querySelector('.aqi-review-footer__hint');
  if(inputHost){
    Array.prototype.slice.call(inputHost.children).forEach(function(child){
      if(child!==wrap&&child&&child.parentNode===inputHost){ inputHost.removeChild(child); }
    });
  }
  if(inputHost&&wrap.parentNode!==inputHost){ inputHost.appendChild(wrap); }
  var hint=document.querySelector('.aqi-front-hint-wrap');
  if(hintHost){
    Array.prototype.slice.call(hintHost.children).forEach(function(child){
      if(child!==hint&&child&&child.parentNode===hintHost){ hintHost.removeChild(child); }
    });
  }
  if(hintHost&&hint&&hint.parentNode!==hintHost){ hintHost.appendChild(hint); }
  ensureTypedAnswerFooterResizeObserver();
  syncTypedAnswerFooterOffset();
  measureTypedAnswerFooterGeometry();
  return footer;
}
function ensureTypeToolbar(ta){
  if(!ta||!ta.parentNode) return null;
  var wrap=ta.parentNode;
  if(!wrap.classList||!wrap.classList.contains('aqi-type-input-wrap')){
    wrap=document.createElement('div');
    wrap.className='aqi-type-input-wrap';
    wrap.setAttribute('data-aqi-type-toolbar','1');
    ta.parentNode.insertBefore(wrap,ta);
    wrap.appendChild(ta);
  } else {
    wrap.setAttribute('data-aqi-type-toolbar','1');
  }
  var btn=wrap.querySelector('.aqi-insert-tab-btn');
  if(!btn){
    btn=document.createElement('button');
    btn.type='button';
    btn.className='aqi-ai-action-btn aqi-insert-tab-btn';
    btn.textContent='Insert Tab';
    btn.setAttribute('aria-label','Insert Tab');
    btn.setAttribute('title','Insert Tab');
    wrap.insertBefore(btn,ta);
  }
  if(!btn.dataset.aqiBound){
    btn.dataset.aqiBound='1';
    btn.addEventListener('click', function(e){ e.preventDefault(); insertTabIntoTextarea(ta); syncTypedAnswerFooterOffset(); measureTypedAnswerFooterGeometry(); });
  }
  return wrap;
}
function wireTypeAnswerTextarea(ta){
  if(!ta||ta.dataset.mlReady) return;
  ta.dataset.mlReady='1';
  ensureTypeToolbar(ta);
  function onEnter(e){
    if(e.key==='Tab'&&!e.ctrlKey&&!e.metaKey&&!e.altKey&&!e.shiftKey){ e.preventDefault(); insertTabIntoTextarea(ta); syncTypedAnswerFooterOffset(); measureTypedAnswerFooterGeometry(); return; }
    if(e.key==="Enter"){
      if(e.shiftKey){ e.stopImmediatePropagation(); e.stopPropagation(); e.preventDefault();
        if(typeof pycmd==="function") pycmd("ans");
      } else { e.stopImmediatePropagation(); e.stopPropagation(); }
    }
  }
  ta.addEventListener('keydown',onEnter,true);
  syncTypedAnswerFooter();
  ensureTypedAnswerFooterMutationObserver();
}
""".replace("__AQI_TYPE_ROWS__", str(textarea_rows)).replace("__AQI_TYPE_MIN_HEIGHT__", textarea_min_height)

    def build_textarea(attrs: str, value_text: str = "") -> str:
        return (
            '<div class="aqi-type-input-wrap" data-aqi-type-toolbar="1">'
            '<button class="aqi-ai-action-btn aqi-insert-tab-btn" type="button" aria-label="Insert Tab" title="Insert Tab">Insert Tab</button>'
            f'<textarea{attrs} rows="{textarea_rows}" spellcheck="false" '
            f'style="width:100%;min-height:{textarea_min_height};'
            "font-family: var(--aqi-font-body);"
            f'font-size:16px; line-height:1.4; tab-size:2;">{html.escape(value_text)}</textarea>'
            '</div>'
        )

    def repl(m):
        attrs = m.group('attrs')
        value_text = ""
        value_match = re.search(r'\svalue\s*=\s*"(?P<value>[^"]*)"', attrs, flags=re.I|re.S)
        if not value_match:
            value_match = re.search(r"\svalue\s*=\s*'(?P<value>[^']*)'", attrs, flags=re.I|re.S)
        if value_match:
            value_text = html.unescape(value_match.group('value'))
        # strip type= and value= on textarea
        attrs = re.sub(r'\stype\s*=\s*(?:"|\')?[^"\'>\s]+(?:"|\')?', '', attrs, flags=re.I)
        attrs = re.sub(r'\svalue\s*=\s*(?:"|\').*?(?:"|\')', '', attrs, flags=re.I|re.S)
        attrs = re.sub(r'\son(?:key(?:down|press|up))\s*=\s*(?:"|\').*?(?:"|\')', '', attrs, flags=re.I|re.S)
        return (
            build_textarea(attrs, value_text)
            + '<script>(function(){'
            + build_shared_js()
            + 'var ta=document.getElementById("typeans"); if(ta) wireTypeAnswerTextarea(ta);'
            + '})();</script>'
        )

    new_text, replaced = pat.subn(repl, text)

    # Fallback if no match (timing/DOM variants)
    if replaced == 0:
        new_text += (
            "<script>\n(function(){\n"
            + build_shared_js()
            + """
  function swap(){
    var e=document.getElementById('typeans');
    if(!e){ syncTypedAnswerFooter(); return; }
    if(e.tagName.toLowerCase()!=='textarea'){
      var ta=document.createElement('textarea');
      for(var i=0;i<e.attributes.length;i++){ var a=e.attributes[i]; if(/^onkey(?:down|press|up)$/i.test(a.name)) continue; try{ ta.setAttribute(a.name,a.value);}catch(_){} }
      ta.value=e.value||''; ta.rows=__AQI_TYPE_ROWS__; ta.spellcheck=false;
      ta.style.width='100%'; ta.style.minHeight='__AQI_TYPE_MIN_HEIGHT__';
      ta.style.fontFamily='var(--aqi-font-body)';
      ta.style.fontSize='16px'; ta.style.lineHeight='1.4'; ta.style.tabSize='2';
      e.parentNode.replaceChild(ta,e); e=ta;
    }
    wireTypeAnswerTextarea(e);
    syncTypedAnswerFooter();
    ensureTypedAnswerFooterMutationObserver();
  }
  swap();
})();
</script>
""".replace("__AQI_TYPE_ROWS__", str(textarea_rows)).replace("__AQI_TYPE_MIN_HEIGHT__", textarea_min_height)
        )
    return new_text

def _code_friendly_diff_on_answer(text: str, card, kind: str) -> str:
    if not kind or "Answer" not in kind:
        return text
    return """
<style>
.typeGood, .typeBad, .typeMissed {
  white-space: pre-wrap !important;
}
</style>
""" + text

REVIEWER_THEME_TOKENS_BASE = """
  --aqi-font-body: var(--shared-font-body, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
  --aqi-font-heading: var(--shared-font-heading, 'Segoe UI', sans-serif);
  --aqi-surface-bg: #f8f9fa;
  --aqi-overlay-surface-bg: #f8f9fa;
  --aqi-overlay-panel-bg: #ffffff;
  --aqi-overlay-control-bg: #ffffff;
  --aqi-surface-border: #6c757d;
  --aqi-copy-strong: #2c3e50;
  --aqi-copy-body: #34495e;
  --aqi-panel-body-bg: rgba(255,255,255,0.7);
  --aqi-control-bg: rgba(255,255,255,0.78);
  --aqi-control-border: rgba(0,0,0,0.08);
  --aqi-code-bg: #fafafa;
  --aqi-code-fg: #1b1b1b;
  --aqi-code-border: #ddd;
  --aqi-code-label: #222;
  --ak-code-bg: var(--aqi-code-bg);
  --ak-code-fg: var(--aqi-code-fg);
  --ak-code-border: var(--aqi-code-border);
  --ak-code-label: var(--aqi-code-label);
  --aqi-question-fg: #1f2937;
  --aqi-question-muted: #4b5563;
  --aqi-question-shadow: none;
  --aqi-variant-chip-bg: rgba(15, 23, 42, 0.08);
  --aqi-variant-chip-border: rgba(15, 23, 42, 0.12);
  --aqi-input-bg: #ffffff;
  --aqi-input-fg: #111827;
  --aqi-input-border: #cbd5e1;
  --sqv-question-fg: var(--aqi-question-fg);
  --sqv-question-muted: var(--aqi-question-muted);
  --sqv-question-shadow: var(--aqi-question-shadow);
  --sqv-chip-bg: var(--aqi-variant-chip-bg);
  --sqv-chip-border: var(--aqi-variant-chip-border);
  --sqv-input-bg: var(--aqi-input-bg);
  --sqv-input-fg: var(--aqi-input-fg);
  --sqv-input-border: var(--aqi-input-border);
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
  --aqi-gap-sm: 8px;
  --aqi-gap-md: 12px;
  --aqi-gap-lg: 14px;
  --aqi-pill-radius: 999px;
  --aqi-pill-padding: 8px 14px;
  --aqi-title-size: 18px;
  --aqi-score-size: 16px;
  --aqi-panel-body-padding: 14px 16px;
  --aqi-panel-shadow: 0 8px 32px rgba(0,0,0,0.1);
  --aqi-action-shadow: 0 3px 10px rgba(0,0,0,0.10);
  --aqi-badge-shadow: 0 4px 15px rgba(0,0,0,0.18);
  --aqi-icon-button-size: 38px;
""".strip()

REVIEWER_THEME_TOKENS_DARK = """
  --aqi-surface-bg: rgba(255,255,255,0.06);
  --aqi-overlay-surface-bg: #1f2937;
  --aqi-overlay-panel-bg: #111827;
  --aqi-overlay-control-bg: #111827;
  --aqi-surface-border: #64748b;
  --aqi-copy-strong: var(--shared-night-text, #f5f5f5);
  --aqi-copy-body: var(--shared-night-muted, #d1d5db);
  --aqi-panel-body-bg: rgba(15,23,42,0.36);
  --aqi-control-bg: rgba(15,23,42,0.72);
  --aqi-control-border: rgba(148,163,184,0.28);
  --aqi-code-bg: #0f1116;
  --aqi-code-fg: #e6edf3;
  --aqi-code-border: #2d333b;
  --aqi-code-label: #e6edf3;
  --ak-code-bg: var(--aqi-code-bg);
  --ak-code-fg: var(--aqi-code-fg);
  --ak-code-border: var(--aqi-code-border);
  --ak-code-label: var(--aqi-code-label);
  --aqi-question-fg: #f3f4f6;
  --aqi-question-muted: #d1d5db;
  --aqi-question-shadow: 0 1px 2px rgba(0,0,0,0.35);
  --aqi-variant-chip-bg: rgba(255, 255, 255, 0.14);
  --aqi-variant-chip-border: rgba(255, 255, 255, 0.16);
  --aqi-input-bg: #111827;
  --aqi-input-fg: #f9fafb;
  --aqi-input-border: #374151;
  --sqv-question-fg: var(--aqi-question-fg);
  --sqv-question-muted: var(--aqi-question-muted);
  --sqv-question-shadow: var(--aqi-question-shadow);
  --sqv-chip-bg: var(--aqi-variant-chip-bg);
  --sqv-chip-border: var(--aqi-variant-chip-border);
  --sqv-input-bg: var(--aqi-input-bg);
  --sqv-input-fg: var(--aqi-input-fg);
  --sqv-input-border: var(--aqi-input-border);
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
""".strip()

REVIEWER_SHARED_CSS = (
    "<style>\n"
    '@import url("_card-base-shared.css");\n\n'
    "/* Shared theme tokens */\n:root {\n"
    + REVIEWER_THEME_TOKENS_BASE
    + "\n}\n\n"
    "/* Dark-mode overrides */\nbody.nightMode, body.night-mode, .nightMode, .night-mode, .isDark, [data-theme='dark'] {\n"
    + REVIEWER_THEME_TOKENS_DARK
    + "\n}\n\n"
    "/* Fallback pour systèmes qui annoncent le thème via le média */\n@media (prefers-color-scheme: dark) {\n  :root {\n"
    + REVIEWER_THEME_TOKENS_DARK
    + "\n  }\n}\n\n"
    + """.aqi-shell,
.aqi-front-hint-wrap {
  font-family: var(--aqi-font-body) !important;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
}

/* Shared typography for addon-owned compare and panel surfaces */
.aqi-anki-compare,
.aqi-anki-compare *,
.aqi-compare .aqi-compare-pre,
.ak-compare .ak-pre,
.aqi-panel-title,
.aqi-ai-action-btn,
.aqi-panel-body,
.aqi-section-label {
  font-family: var(--aqi-font-body) !important;
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
  gap: var(--aqi-gap-md);
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

.aqi-question-block,
.sqv-question-block {
  margin: 0 auto 18px auto;
  max-width: 780px;
}

.aqi-active-question,
.sqv-active-question {
  font-family: inherit;
  margin-bottom: 10px;
}

.aqi-choice-list,
.sqv-choice-list {
  font-family: inherit;
  text-align: center;
  font-size: 13px;
  line-height: 1.5;
  color: var(--aqi-question-muted) !important;
}

.aqi-compare .aqi-compare-pre + .aqi-choice-list,
.aqi-compare .aqi-compare-pre + .sqv-choice-list,
.ak-compare .ak-pre + .aqi-choice-list,
.ak-compare .ak-pre + .sqv-choice-list {
  margin-top: 6px;
}

.aqi-choice-chip,
.sqv-choice-chip {
  font-family: inherit;
  display: inline-block;
  margin: 4px 6px;
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--aqi-variant-chip-bg) !important;
  border: 1px solid var(--aqi-variant-chip-border) !important;
  color: inherit;
}

input#typeans,
textarea#typeans,
.aqi-type-input,
.sqv-type-input {
  font-family: var(--aqi-font-body) !important;
  background: var(--aqi-input-bg) !important;
  color: var(--aqi-input-fg) !important;
  border: 1px solid var(--aqi-input-border) !important;
  border-radius: 12px;
  padding: 12px;
  box-sizing: border-box;
}

.aqi-type-input-wrap {
  width: 96%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
}

.aqi-type-input-wrap > .aqi-ai-action-btn {
  align-self: flex-start;
}

.aqi-type-input-wrap > #typeans,
.aqi-type-input-wrap > textarea#typeans {
  width: 100% !important;
}

:root {
  --aqi-review-footer-offset: 0px;
  --aqi-review-footer-gap: 16px;
}

html.aqi-review-footer-active,
body.aqi-review-footer-active {
  padding-bottom: calc(var(--aqi-review-footer-offset) + var(--aqi-review-footer-gap));
}

#aqi-review-footer {
  position: fixed;
  left: 50%;
  bottom: 0;
  transform: translateX(-50%);
  width: min(800px, calc(100vw - 24px));
  z-index: 2147483000;
  padding: 0 0 12px 0;
  pointer-events: none;
}

#aqi-review-footer::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 18px 18px 0 0;
  background: var(--aqi-overlay-surface-bg, var(--aqi-surface-bg));
  border: 1px solid var(--aqi-surface-border);
  box-shadow: var(--aqi-panel-shadow);
}

#aqi-review-footer .aqi-front-hint-card[data-score-tier="na"] {
  background: var(--aqi-overlay-panel-bg, var(--aqi-score-na-bg));
  border-color: var(--aqi-surface-border);
}

#aqi-review-footer .aqi-panel-body {
  background: var(--aqi-overlay-panel-bg, var(--aqi-panel-body-bg));
  border-left-color: var(--aqi-surface-border);
}

#aqi-review-footer .aqi-front-hint-toggle,
#aqi-review-footer .aqi-ai-action-btn {
  background: var(--aqi-overlay-control-bg, var(--aqi-control-bg)) !important;
}

.aqi-review-footer__content {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  pointer-events: auto;
}

.aqi-review-footer__input,
.aqi-review-footer__hint {
  width: 100%;
}

.aqi-review-footer__input > .aqi-type-input-wrap,
.aqi-review-footer__hint > .aqi-front-hint-wrap {
  width: 100%;
  max-width: none;
  margin: 0;
}

.aqi-review-footer__hint .aqi-front-hint-wrap {
  text-align: left;
}

.aqi-review-footer__hint .aqi-front-hint-toggle {
  margin-bottom: 8px;
}

input#typeans:focus,
textarea#typeans:focus,
.aqi-type-input:focus,
.sqv-type-input:focus {
  outline: 2px solid rgba(59, 130, 246, 0.45);
  outline-offset: 1px;
}

/* Styles des blocs de comparaison */
.aqi-compare .aqi-compare-label,
.ak-compare .ak-label {
  font-weight: 700;
  margin-bottom: 6px;
  color: var(--ak-code-label) !important;
}
.aqi-compare .aqi-compare-pre,
.ak-compare .ak-pre {
  white-space: pre-wrap !important;
  padding: 10px;
  border: 1px solid var(--ak-code-border) !important;
  border-radius: 8px;
  background: var(--ak-code-bg) !important;
  color: var(--ak-code-fg) !important;
  overflow: auto;
}

.aqi-panel-card {
  --aqi-score-bg: var(--aqi-score-na-bg);
  --aqi-score-color: var(--aqi-score-na-color);
  border-radius: 16px;
  padding: 16px;
  margin: 16px 0;
  box-shadow: var(--aqi-panel-shadow);
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
  gap: var(--aqi-gap-sm);
  margin-bottom: 8px;
}

.aqi-panel-title-wrap {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
  gap: var(--aqi-gap-sm);
  flex-wrap: wrap;
}

.aqi-mode-badge {
  background: var(--aqi-control-bg);
  color: var(--aqi-score-color);
  border: 1px solid var(--aqi-control-border);
  border-radius: var(--aqi-pill-radius);
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
}

.aqi-panel-actions {
  display: flex;
  align-items: center;
  gap: var(--aqi-gap-sm);
  flex-wrap: wrap;
  margin-left: auto;
}

.aqi-panel-title {
  color: var(--aqi-score-color);
  margin: 0;
  font-size: var(--aqi-title-size);
  font-weight: 650;
}

.aqi-ai-action-btn {
  background: var(--aqi-control-bg);
  color: var(--aqi-score-color);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--aqi-gap-sm);
  padding: var(--aqi-pill-padding);
  border-radius: var(--aqi-pill-radius);
  border: 1px solid var(--aqi-control-border);
  font-weight: 700;
  font-size: var(--aqi-score-size);
  line-height: 1;
  box-shadow: var(--aqi-action-shadow);
  cursor: pointer;
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
  width: var(--aqi-icon-button-size);
  height: var(--aqi-icon-button-size);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.aqi-score-badge {
  background: var(--aqi-score-color);
  color: white;
  padding: var(--aqi-pill-padding);
  border-radius: var(--aqi-pill-radius);
  font-weight: 700;
  font-size: var(--aqi-score-size);
  box-shadow: var(--aqi-badge-shadow);
}

.aqi-panel-body {
  padding: var(--aqi-panel-body-padding);
  background: var(--aqi-panel-body-bg);
  border-radius: 12px;
  border-left: 4px solid var(--aqi-score-color);
}

.aqi-front-hint-wrap {
  margin-top: 16px;
  text-align: center;
}

.aqi-front-hint-toggle {
  appearance: none;
  border: 1px solid var(--aqi-variant-chip-border) !important;
  background: var(--aqi-variant-chip-bg) !important;
  color: var(--aqi-question-fg) !important;
  border-radius: var(--aqi-pill-radius);
  padding: var(--aqi-pill-padding);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
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
  margin-top: var(--aqi-gap-md);
}

.aqi-front-hint-actions {
  margin-top: var(--aqi-gap-lg);
}

.aqi-section-label {
  color: var(--aqi-copy-strong);
  margin: 0 0 6px 0;
  font-weight: 700;
}

.aqi-section-copy + .aqi-section-label {
  margin-top: var(--aqi-gap-md);
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
  font-family: inherit;
}

.aqi-rich-copy pre {
  overflow-x: auto;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.08);
}
</style>
"""
)

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

    web_content.head += REVIEWER_SHARED_CSS

gui_hooks.webview_will_set_content.append(inject_multiline_type_input)

def _build_variant_chip_list(variants: list[str]) -> str:
    if not variants:
        return ""
    chips = "".join(
        f'<span class="aqi-choice-chip sqv-choice-chip">{html.escape(variant)}</span>'
        for variant in variants
        if variant
    )
    if not chips:
        return ""
    return f'<div class="aqi-choice-list sqv-choice-list">{chips}</div>'

def _code_compare_block(expected: str, provided: str, lang_hint: str, labels: dict, expected_alternatives: list[str] | None = None) -> str:
    exp_text = expected or ""
    prov_text = extract_code_text(provided)
    le = labels.get("expected", "Expected")
    lp = labels.get("provided", "Your answer")
    expected_variant_list = _build_variant_chip_list(expected_alternatives or [])
    return f"""
    <div class="aqi-compare ak-compare" style="display:flex; gap:12px; margin:12px 0;">
      <div style="flex:1; min-width:0;">
        <div class="aqi-compare-label ak-label">{html.escape(le)}</div>
        <div class="aqi-compare-pre ak-pre">{html.escape(exp_text)}</div>
        {expected_variant_list}
      </div>
      <div style="flex:1; min-width:0;">
        <div class="aqi-compare-label ak-label">{html.escape(lp)}</div>
        <div class="aqi-compare-pre ak-pre">{html.escape(prov_text)}</div>
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
        "warnings": [],
        "sources_used": [],
        "context_sources": [],
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
        "warnings": [],
        "sources_used": [],
        "context_sources": [],
    }

def merge_analysis_warnings(tips: str, warnings: list[str]) -> str:
    clean_warnings = [str(item or "").strip() for item in (warnings or []) if str(item or "").strip()]
    tips_text = str(tips or "").strip()
    if not clean_warnings:
        return tips_text
    warning_block = "Warnings:\n- " + "\n- ".join(clean_warnings)
    return f"{tips_text}\n\n{warning_block}" if tips_text else warning_block

def build_analysis_prompt_payload(card, user_answer: str) -> dict:
    contract = build_answer_contract(card)
    question_text = get_active_visible_question(card) if card else ""
    expected_answer = contract["canonical_joined_answer"]
    return {
        "question_text": question_text,
        "canonical_answer": expected_answer,
        "expected_answer": expected_answer,
        "accepted_answers": contract["accepted_joined_answers"],
        "front_text_raw": contract["front_text_raw"],
        "active_cloze_index": contract.get("active_cloze_index"),
        "cloze_targets": contract["cloze_targets"],
        "user_answer": user_answer or "",
        "is_valid": contract["is_valid"],
        "invalid_reason": contract["invalid_reason"],
        "mode": contract["mode"],
    }

def _cache_hash(value) -> str:
    if isinstance(value, tuple):
        value = list(value)
    if value is None:
        value = ""
    try:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except TypeError:
        payload = json.dumps(str(value), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def _build_ai_cache_base_parts(*, card_id=None, card_ord=None, question_text: str = "", canonical_answer: str = "", language: str = "", provider: str = "", model: str = "", analysis_mode: str = "standard", resolved_prompt_contract: str = "") -> list[str]:
    return [
        str(card_id),
        str(card_ord),
        _cache_hash(question_text),
        _cache_hash(canonical_answer),
        _cache_hash(language),
        _cache_hash(provider),
        _cache_hash(model),
        _cache_hash(normalize_analysis_mode(analysis_mode)),
        _cache_hash(resolved_prompt_contract),
    ]

def build_analysis_cache_key(
    question_text: str,
    true_answer: str,
    user_answer: str,
    *,
    card_id=None,
    card_ord=None,
    language: str = "",
    provider: str = "",
    model: str = "",
    analysis_mode: str = "standard",
    max_tokens: int = 0,
    temperature: float = 0.0,
    accepted_answers: list[str] | None = None,
    resolved_prompt_contract: str = "",
    analysis_prompt_version: str = ANALYSIS_PROMPT_VERSION,
    use_notebooklm: bool = False,
    notebook_id: str = "",
) -> str:
    return "_".join(
        _build_ai_cache_base_parts(
            card_id=card_id,
            card_ord=card_ord,
            question_text=question_text,
            canonical_answer=true_answer,
            language=language,
            provider=provider,
            model=model,
            analysis_mode=analysis_mode,
            resolved_prompt_contract=resolved_prompt_contract,
        ) + [
            _cache_hash(max_tokens),
            _cache_hash(temperature),
            _cache_hash(user_answer),
            _cache_hash(accepted_answers or []),
            _cache_hash(analysis_prompt_version),
            _cache_hash(bool(use_notebooklm)),
            _cache_hash(str(notebook_id or "")),
        ]
    )

def invalidate_analysis_state(cache_key: str) -> None:
    ai_analysis_cache.pop(cache_key, None)
    analysis_results.pop(cache_key, None)
    is_analyzing.pop(cache_key, None)

def store_ai_analysis(expected_provided_tuple, type_pattern, analysis_mode: str = "standard"):
    """
    Lance l'analyse IA en arrière-plan pour ne pas bloquer l'UI,
    afin que le verso s'affiche tout de suite avec un spinner.
    """
    user_answer = expected_provided_tuple[1] or ""
    card = mw.reviewer.card if hasattr(mw, 'reviewer') and mw.reviewer else None
    if not should_score_card(card):
        return expected_provided_tuple
    request = build_analysis_request(card, user_answer, analysis_mode)
    cache_key = build_analysis_request_cache_key(card, request)
    standard_request = request if request["analysis_mode"] == "standard" else build_analysis_request(card, user_answer, "standard")
    standard_cache_key = build_analysis_request_cache_key(card, standard_request)
    current_analysis_context.update(
        {
            "card_id": getattr(card, "id", None),
            "expected_provided_tuple": (request["canonical_answer"], user_answer),
            "type_pattern": type_pattern,
            "cache_key": cache_key,
            "analysis_mode": request["analysis_mode"],
            "analysis_request": dict(request),
            "standard_cache_key": standard_cache_key,
        }
    )

    persist_cache = not (request["analysis_mode"] == "deep" and bool(request.get("use_notebooklm", False)))

    if persist_cache and cache_key in ai_analysis_cache:
        print(f"Using cached analysis for {cache_key}")
        return expected_provided_tuple

    if is_analyzing.get(cache_key, False):
        print(f"Analysis already in progress for {cache_key}")
        return expected_provided_tuple

    is_analyzing[cache_key] = True
    analysis_results[cache_key] = None
    print(f"Starting background AI analysis for key: {cache_key}")

    def task():
        try:
            print("Calling AI API for analysis (background)...")
            mismatch_reason = get_question_variant_mismatch_reason(card)
            if mismatch_reason:
                cfg = get_config()
                return make_variant_mismatch_result(mismatch_reason, cfg.get("language", "english"))
            return analyze_answer_request(request, card=card)
        except Exception as e:
            print(f"AI Analysis Error (bg): {e}")
            cfg = get_config()
            return make_analysis_unavailable(str(e), cfg.get("language", "english"))

    def on_done(fut):
        try:
            result = fut.result()
        except Exception as e:
            print(f"Background task failed: {e}")
            cfg = get_config()
            result = make_analysis_unavailable(str(e), cfg.get("language", "english"))
        finally:
            is_analyzing[cache_key] = False

        if isinstance(result, dict):
            result = dict(result)
            result["analysis_mode"] = request["analysis_mode"]
            result["standard_cache_key"] = standard_cache_key
        if persist_cache:
            ai_analysis_cache[cache_key] = result
        else:
            ai_analysis_cache.pop(cache_key, None)
        analysis_results[cache_key] = result
        print(f"AI analysis completed (bg) for {cache_key}")

        try:
            refresh_ai_analysis({"card_id": getattr(card, "id", None), "cache_key": cache_key})
        except Exception as e:
            print(f"Refresh error after AI analysis: {e}")

    mw.taskman.run_in_background(task, on_done)

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

def get_note_model_name(card) -> str:
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
        name = model.get("name", "")
        return name if isinstance(name, str) else str(name or "")
    except Exception as e:
        print(f"Error getting note model name: {e}")
        return ""

def get_card_capabilities(card, rendered_text: str = "", kind: str = "") -> dict[str, bool]:
    template_name = get_card_template_name(card).strip().lower() if card else ""
    scoreable = "_score" in template_name
    typed_question_input = bool(card) and is_supported_typed_answer_card(card, rendered_text, kind)
    is_answer_phase = bool(kind) and "Answer" in kind
    return {
        "scoreable": scoreable,
        "typed_question_input": typed_question_input,
        "front_hint": scoreable and typed_question_input,
        "answer_compare": bool(card) and scoreable and is_answer_phase,
    }

def should_score_card(card) -> bool:
    return get_card_capabilities(card).get("scoreable", False)

def resolve_prompt_profile(config) -> str:
    merged_config = merge_config_with_defaults(config)
    return normalize_prompt_profile(merged_config.get("prompt_profile")) or PROMPT_PROFILE_DEFAULT

def get_manual_hint_html(card) -> str:
    if not card:
        return ""
    slot_index = 1
    if is_clozeanything_score_template(card):
        slot_index = get_active_cloze_index(card) or 0
        if slot_index <= 0:
            return ""
    hint_field_name = resolve_slot_field_names(slot_index)["hint_field"]
    if not _note_has_field(card, hint_field_name):
        return ""
    return (get_note_field(card, hint_field_name) or "").strip()

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
    return get_card_capabilities(card, rendered_text, kind).get("front_hint", False)

def build_hint_cache_key(*, card_id, card_ord, question_text: str, canonical_answer: str, manual_hint: str, language: str, prompt_profile: str, hint_prompt_version: str, provider: str = "", model: str = "", resolved_prompt_contract: str = "") -> str:
    return "_".join(
        _build_ai_cache_base_parts(
            card_id=card_id,
            card_ord=card_ord,
            question_text=question_text,
            canonical_answer=canonical_answer,
            language=language,
            provider=provider,
            model=model,
            resolved_prompt_contract=resolved_prompt_contract,
        ) + [
            _cache_hash(manual_hint),
            _cache_hash(prompt_profile),
            _cache_hash(hint_prompt_version),
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

def build_analysis_request(card, user_answer: str, analysis_mode: str = "standard") -> dict:
    payload = build_analysis_prompt_payload(card, user_answer)
    runtime = resolve_ai_runtime_config(get_config(), analysis_mode=analysis_mode)
    use_notebooklm = bool(runtime["mode_settings"].get("use_notebooklm", False)) if runtime["analysis_mode"] == "deep" else False
    notebook_id = str(runtime["mode_settings"].get("notebook_id", "") or "").strip() if use_notebooklm else ""
    notebook_title = str(runtime["mode_settings"].get("notebook_title", "") or "").strip() if use_notebooklm else ""
    return {
        "analysis_mode": runtime["analysis_mode"],
        "question_text": payload["question_text"],
        "canonical_answer": payload["canonical_answer"],
        "accepted_answers": payload["accepted_answers"],
        "user_answer": payload["user_answer"],
        "language": runtime["language"],
        "provider": runtime["provider"],
        "model": runtime["model"],
        "api_key": runtime["api_key"],
        "base_url": runtime["base_url"],
        "prompt_profile": runtime["prompt_profile"],
        "max_tokens": runtime["max_tokens"],
        "temperature": runtime["temperature"],
        "availability_reason": runtime["availability_reason"],
        "use_notebooklm": use_notebooklm,
        "notebook_id": notebook_id,
        "notebook_title": notebook_title,
        "context_sources": [],
    }

def build_analysis_request_cache_key(card, request: dict, config=None) -> str:
    merged_config = merge_config_with_defaults(config or get_config())
    general_settings = merged_config.get("general", {}) if isinstance(merged_config.get("general"), dict) else {}
    language = (request.get("language") or general_settings.get("language", merged_config.get("language", "english")) or "english").strip() or "english"
    prompt_profile = request.get("prompt_profile") or PROMPT_PROFILE_DEFAULT
    return build_analysis_cache_key(
        request.get("question_text", ""),
        request.get("canonical_answer", ""),
        request.get("user_answer", ""),
        card_id=getattr(card, "id", None),
        card_ord=getattr(card, "ord", None),
        language=language,
        provider=request.get("provider", ""),
        model=request.get("model", ""),
        analysis_mode=request.get("analysis_mode", "standard"),
        max_tokens=request.get("max_tokens", 0),
        temperature=request.get("temperature", 0.0),
        accepted_answers=request.get("accepted_answers") or [],
        resolved_prompt_contract=build_prompt_contract_hash(merged_config, language, prompt_profile, "analysis"),
        analysis_prompt_version=ANALYSIS_PROMPT_VERSION,
        use_notebooklm=bool(request.get("use_notebooklm", False)),
        notebook_id=str(request.get("notebook_id", "") or "").strip(),
    )

def build_prompt_contract_hash(config, language: str, prompt_profile: str, surface: str = "analysis") -> str:
    resolved = resolve_prompt_profile_content(config, language, prompt_profile)
    template_key = "hint_prompt_template" if surface == "hint" else "analysis_prompt_template"
    return _cache_hash([resolved.get("system_prompt", ""), resolved.get(template_key, "")])

def build_front_hint_context(card, rendered_text: str = "", kind: str = "Question") -> dict[str, str | int | None]:
    canonical_answer, _accepted_answers = build_accepted_answer_pool(card)
    question_text = get_active_visible_question(card)
    manual_hint = get_manual_hint_html(card)
    runtime = resolve_ai_runtime_config(get_config())
    prompt_profile = runtime["prompt_profile"]
    resolved_prompt_contract = build_prompt_contract_hash(runtime["config"], runtime["language"], prompt_profile, "hint")
    return {
        "card_id": getattr(card, "id", None),
        "card_ord": getattr(card, "ord", None),
        "question_text": question_text,
        "canonical_answer": canonical_answer,
        "manual_hint": manual_hint,
        "language": runtime["language"],
        "provider": runtime["provider"],
        "model": runtime["model"],
        "prompt_profile": prompt_profile,
        "resolved_prompt_contract": resolved_prompt_contract,
        "hint_prompt_version": HINT_PROMPT_VERSION,
        "cache_key": build_hint_cache_key(
            card_id=getattr(card, "id", None),
            card_ord=getattr(card, "ord", None),
            question_text=question_text,
            canonical_answer=canonical_answer,
            manual_hint=manual_hint,
            language=runtime["language"],
            prompt_profile=prompt_profile,
            provider=runtime["provider"],
            model=runtime["model"],
            resolved_prompt_contract=resolved_prompt_contract,
            hint_prompt_version=HINT_PROMPT_VERSION,
        ),
    }

def get_hint_availability_reason(config=None, language: str = "english") -> str:
    return resolve_ai_runtime_config(config, language).get("availability_reason", "")

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
        hint_text = (result.get("hint_text") or result.get("hint") or "").strip()
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
    try:
        parsed_hint = json.loads(hint_text)
    except (TypeError, ValueError):
        parsed_hint = None
    if isinstance(parsed_hint, dict):
        return normalize_hint_result(parsed_hint, language)
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
    prompt += f'\n\nReturn exactly one JSON object with key "hint" containing one concise hint in {get_language_name(language)}. No markdown, no code fences, no extra text. Do not reveal the full answer.'
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
    normalized_text = re.sub(r'(?i)<br\s*/?>', "\n", str(text or ""))
    escaped = escape_ai_source_text(normalized_text).replace("\r\n", "\n").replace("\r", "\n")
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
        {"key": "tips", "title_key": "review_suggestion", "kind": "rich_text", "value": ai_analysis.get("tips", "")},
        {"key": "sample_answers", "title_key": "ai_analysis_sample_answers", "kind": "string_list", "value": ai_analysis.get("sample_answers", [])},
        {"key": "question_variants", "title_key": "ai_analysis_question_variants", "kind": "string_list", "value": ai_analysis.get("question_variants", [])},
    ]

def render_section_label(title: str) -> str:
    resolved_title = html.escape((title or "").strip(), quote=False)
    return f'<div class="aqi-section-label">{resolved_title}</div>' if resolved_title else ""

def render_ai_analysis_section(section: dict, texts: dict) -> str:
    title_key = section.get("title_key")
    heading = render_section_label(texts.get(title_key, "")) if title_key else ""

    if section.get("kind") == "rich_text":
        rendered = render_ai_rich_text(section.get("value", ""))
        return heading + f'<div class="aqi-section-copy aqi-rich-copy">{rendered}</div>' if rendered else ""

    items = section.get("value") or []
    if not items:
        return ""

    rendered_items = [f'<li>{render_ai_rich_text(item)}</li>' for item in items]
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

def build_footer_post_refresh_js() -> str:
    return (
        "try{"
        "if(typeof syncTypedAnswerFooter==='function'){syncTypedAnswerFooter();}"
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
    manual_hint_html = render_ai_rich_text(clean_html_content(context["manual_hint"])) if context["manual_hint"] else ""
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
            '<div class="aqi-front-hint-ai">'
            f'{render_section_label(texts.get("ai_hint_label", "AI Hint"))}'
            f'<div id="aqi-front-hint-body" class="aqi-section-copy aqi-rich-copy">{ai_body}</div>'
            '</div>'
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
    if cache_key and current_hint_context.get("cache_key") != cache_key:
        return
    if current_hint_context.get("card_id") is not None and current_hint_context.get("card_id") != getattr(card, "id", None):
        return
    rendered_text = ""
    try:
        rendered_text = card.question() or ""
    except Exception:
        rendered_text = ""
    panel_html = build_front_hint_panel_html(card, rendered_text, "Question")
    if not panel_html:
        return
    refresh_front_hint_panel_dom(panel_html)

def refresh_open_review_surfaces_after_config_save() -> None:
    try:
        _addon_attr("refresh_ai_analysis", refresh_ai_analysis)()
    except Exception:
        pass
    try:
        _addon_attr("refresh_current_front_hint_panel", refresh_current_front_hint_panel)()
    except Exception:
        pass

def refresh_front_hint_panel_dom(panel_html: str) -> None:
    if not refresh_dom_fragment('.aqi-front-hint-wrap', panel_html):
        return
    reviewer = getattr(mw, "reviewer", None)
    web = getattr(reviewer, "web", None)
    if web and hasattr(web, "eval"):
        web.eval("(function(){" + build_footer_post_refresh_js() + "})();")

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

    context = dict(current_analysis_context)
    is_current_context = context.get("cache_key") == cache_key
    analysis_mode = normalize_analysis_mode(
        ai_analysis.get("analysis_mode")
        or (context.get("analysis_mode") if is_current_context else "standard")
    )
    standard_cache_key = (
        ai_analysis.get("standard_cache_key")
        or (context.get("standard_cache_key") if is_current_context else "")
        or cache_key
    )

    is_scored = bool(ai_analysis.get("scored", True)) and isinstance(ai_analysis.get("score"), int)
    score = ai_analysis.get('score', 5) if is_scored else None
    score_tier = get_score_tier(score, is_scored)
    score_badge = f"{score}/10" if is_scored else "N/A"
    regenerate_button = build_ai_action_button(
        "regenerate_ai_analysis",
        ai_texts.get("regenerate", "Regenerate"),
        icon="⟳",
    )
    deep_runtime = resolve_ai_runtime_config(get_config(), language=language, analysis_mode="deep")
    deep_button = ""
    if analysis_mode == "standard" and not deep_runtime.get("availability_reason"):
        deep_button = build_ai_action_button(
            "run_deep_analysis",
            ai_texts.get("deep_analysis", "Deep Analysis"),
        )
    standard_result_exists = bool(standard_cache_key) and standard_cache_key != cache_key and bool(
        analysis_results.get(standard_cache_key) or ai_analysis_cache.get(standard_cache_key)
    )
    show_standard_button = ""
    if analysis_mode == "deep" and standard_result_exists:
        show_standard_button = build_ai_action_button(
            "show_standard_ai_analysis",
            ai_texts.get("show_standard", "Show standard"),
        )
    mode_label = ai_texts.get(
        "deep_mode_badge" if analysis_mode == "deep" else "standard_mode_badge",
        "Deep" if analysis_mode == "deep" else "Standard",
    )
    mode_badge = f'<div class="aqi-mode-badge" data-analysis-mode="{analysis_mode}">{html.escape(mode_label)}</div>'
    tips = ai_analysis.get('tips', texts.get('no_tips_available', 'No tips available'))
    if not isinstance(tips, str) or not tips.strip():
        tips = texts.get('no_tips_available', 'No tips available')

    if is_scored:
        section_payload = dict(ai_analysis)
        section_payload['tips'] = tips
        section_texts = dict(ai_texts)
        section_texts.update(texts)
        rendered_body = ''.join(
            render_ai_analysis_section(section, section_texts)
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
                    {mode_badge}
                </div>
                <div class="aqi-panel-actions">
                    {deep_button}
                    {show_standard_button}
                    {regenerate_button}
                </div>
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
    runtime = resolve_ai_runtime_config(get_config())
    config = runtime["config"]
    language = runtime["language"]
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

    availability_reason = runtime["availability_reason"]
    if availability_reason:
        result = make_hint_unavailable(availability_reason, language)
        hint_cache[cache_key] = result
        refresh_current_front_hint_panel(cache_key)
        return result

    provider = runtime["provider"]
    model = runtime["model"]
    api_key = runtime["api_key"]
    base_url = runtime["base_url"]
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
            _addon_attr("call_ai_api", call_ai_api)(
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

def is_clozeanything_score_template(card) -> bool:
    template_name = get_card_template_name(card).strip().lower() if card else ""
    if "_score" in template_name and bool(re.search(r"_clozeanything[1-9]", template_name)):
        return True
    model_name = get_note_model_name(card).strip().lower() if card else ""
    return "_score" in model_name and bool(re.search(r"_clozeanything[1-9]", model_name))

CLOZEANYTHING_TARGET_PATTERN = re.compile(
    r"\(\(c(?P<paren_index>\d+)::(?P<paren_target>[\s\S]*?)\)\)|\|\(c(?P<pipe_index>\d+)::(?P<pipe_target>[\s\S]*?)\|\)"
)

def _iter_clozeanything_targets(front_text: str):
    if not isinstance(front_text, str) or not front_text.strip():
        return
    for match in CLOZEANYTHING_TARGET_PATTERN.finditer(front_text):
        group_index_text = match.group("paren_index") or match.group("pipe_index")
        raw_target = match.group("paren_target") or match.group("pipe_target") or ""
        target = raw_target.split("::", 1)[0].strip()
        if not target:
            continue
        yield int(group_index_text), target

def extract_grouped_cloze_targets_from_front(front_text: str) -> dict[int, list[str]]:
    grouped_targets: dict[int, list[str]] = {}
    for group_index, target in _iter_clozeanything_targets(front_text):
        grouped_targets.setdefault(group_index, []).append(target)
    return grouped_targets

def extract_cloze_targets_from_front(front_text: str) -> list[str]:
    grouped_targets = extract_grouped_cloze_targets_from_front(front_text)
    flattened_targets = [target for group_targets in grouped_targets.values() for target in group_targets]
    return _ordered_unique(flattened_targets)

def _normalize_answer_match_key(value: str) -> str:
    return _normalize_full_answer_text(value).casefold()

def _normalize_answer_segment(value: str) -> str:
    return _normalize_full_answer_text(value)

def _normalize_full_answer_text(value: str) -> str:
    return re.sub(r"\s+", " ", extract_code_text(value or "")).strip()

def _normalize_display_answer_text(value: str) -> str:
    return extract_code_text(value or "").strip()

def _join_answer_segments(segments: list[str]) -> str:
    return " ".join(segment.strip() for segment in segments if isinstance(segment, str) and segment.strip()).strip()

def _join_answer_segments_for_display(segments: list[str]) -> str:
    return "\n".join(segment.strip() for segment in segments if isinstance(segment, str) and segment.strip()).strip()

def get_active_cloze_index(card) -> int | None:
    card_ord = getattr(card, "ord", None) if card else None
    return card_ord + 1 if isinstance(card_ord, int) and card_ord >= 0 else None

def resolve_slot_field_names(slot_index: int) -> dict[str, str]:
    suffix = "" if slot_index <= 1 else str(slot_index)
    return {
        "answer_field": f"Back{suffix}",
        "answer_variants_field": f"Back{suffix}_variants",
        "hint_field": f"Hint{suffix}",
    }

def resolve_answer_field_names(cloze_index: int) -> tuple[str, str]:
    slot_fields = resolve_slot_field_names(cloze_index)
    return slot_fields["answer_field"], slot_fields["answer_variants_field"]

def _note_has_field(card, field_name: str) -> bool:
    if not card or not field_name:
        return False
    note_attr = getattr(card, "note", None)
    note = note_attr() if callable(note_attr) else note_attr
    if note is None:
        return False
    try:
        if field_name in note:
            return True
    except Exception:
        pass
    model_attr = getattr(note, "model", None)
    model = model_attr() if callable(model_attr) else model_attr
    fields = model.get("flds") if isinstance(model, dict) else None
    if not isinstance(fields, list):
        return False
    return any(isinstance(field, dict) and field.get("name") == field_name for field in fields)

def _build_invalid_cloze_contract(front_text_raw: str, active_cloze_index: int | None, mode: str, reason: str) -> dict:
    return {
        "mode": mode,
        "source_kind": "cloze",
        "active_cloze_index": active_cloze_index,
        "canonical_segments": [],
        "canonical_joined_answer": "",
        "accepted_joined_answers": [],
        "front_text_raw": front_text_raw,
        "cloze_targets": [],
        "is_valid": False,
        "invalid_reason": reason,
    }

def build_answer_contract(card) -> dict:
    front_text_raw = (get_note_field(card, QUESTION_FIELD) or "").strip() if card else ""
    canonical_answer = (get_note_field(card, ANSWER_FIELD) or "").strip() if card else ""
    answer_variants = parse_variant_field(get_note_field(card, ANSWER_VARIANTS_FIELD)) if card else []
    if not is_clozeanything_score_template(card):
        accepted_answers = _ordered_unique([canonical_answer, *answer_variants])
        return {
            "mode": "single",
            "source_kind": "plain_back",
            "active_cloze_index": None,
            "canonical_segments": [canonical_answer] if canonical_answer else [],
            "canonical_joined_answer": canonical_answer,
            "canonical_display_answer": canonical_answer,
            "accepted_joined_answers": accepted_answers,
            "front_text_raw": front_text_raw,
            "cloze_targets": [],
            "is_valid": True,
            "invalid_reason": "",
        }

    active_cloze_index = get_active_cloze_index(card)
    if active_cloze_index is None:
        return _build_invalid_cloze_contract(front_text_raw, None, "single", "Active cloze index unavailable.")

    slot_fields = resolve_slot_field_names(active_cloze_index)
    answer_field_name = slot_fields["answer_field"]
    answer_variants_field_name = slot_fields["answer_variants_field"]
    if not _note_has_field(card, answer_field_name) or not _note_has_field(card, answer_variants_field_name):
        return _build_invalid_cloze_contract(
            front_text_raw,
            active_cloze_index,
            "single",
            f"Missing mapped answer fields for c{active_cloze_index}: {answer_field_name} / {answer_variants_field_name}.",
        )

    grouped_targets = extract_grouped_cloze_targets_from_front(front_text_raw)
    active_targets = grouped_targets.get(active_cloze_index) or []
    mode = "multi_segment" if len(active_targets) > 1 else "single"
    if not active_targets:
        return _build_invalid_cloze_contract(
            front_text_raw,
            active_cloze_index,
            mode,
            f"Missing active cloze group c{active_cloze_index} in Front.",
        )

    canonical_answer = (get_note_field(card, answer_field_name) or "").strip()
    answer_variants = parse_variant_field(get_note_field(card, answer_variants_field_name))
    if len(active_targets) <= 1:
        resolved_canonical = canonical_answer or active_targets[0]
        accepted_values = [resolved_canonical, *answer_variants]
        if resolved_canonical:
            canonical_key = _normalize_answer_match_key(resolved_canonical)
            accepted_values.extend(
                target for target in active_targets if _normalize_answer_match_key(target) == canonical_key
            )
        accepted_answers = _ordered_unique(accepted_values)
        return {
            "mode": "single",
            "source_kind": "cloze",
            "active_cloze_index": active_cloze_index,
            "canonical_segments": [resolved_canonical] if resolved_canonical else [],
            "canonical_joined_answer": resolved_canonical,
            "canonical_display_answer": resolved_canonical,
            "accepted_joined_answers": accepted_answers,
            "front_text_raw": front_text_raw,
            "cloze_targets": active_targets,
            "is_valid": True,
            "invalid_reason": "",
        }

    canonical_segments = [_normalize_answer_segment(target) for target in active_targets if _normalize_answer_segment(target)]
    canonical_joined_answer = _join_answer_segments(canonical_segments)
    derived_display_answer = _join_answer_segments_for_display(active_targets)
    normalized_canonical = _normalize_full_answer_text(canonical_joined_answer)
    normalized_back = _normalize_full_answer_text(canonical_answer)
    canonical_display_answer = canonical_answer if canonical_answer and normalized_back == normalized_canonical else derived_display_answer
    is_valid = True
    invalid_reason = ""
    if normalized_back and normalized_back != normalized_canonical:
        is_valid = False
        invalid_reason = f"Invalid multi-cloze Back for c{active_cloze_index} does not match derived full answer."
    accepted_values = []
    if canonical_answer and normalized_back == normalized_canonical:
        accepted_values.append(canonical_answer)
    elif canonical_joined_answer:
        accepted_values.append(canonical_joined_answer)
    accepted_values.extend(answer_variants)
    accepted_answers = _ordered_unique(accepted_values)
    return {
        "mode": "multi_segment",
        "source_kind": "cloze",
        "active_cloze_index": active_cloze_index,
        "canonical_segments": canonical_segments,
        "canonical_joined_answer": canonical_joined_answer,
        "canonical_display_answer": canonical_display_answer,
        "accepted_joined_answers": accepted_answers,
        "front_text_raw": front_text_raw,
        "cloze_targets": canonical_segments,
        "is_valid": is_valid,
        "invalid_reason": invalid_reason,
    }

def is_accepted_answer_match(user_answer: str, accepted_answers: list[str], card=None) -> bool:
    if card is not None:
        contract = build_answer_contract(card)
        accepted_answers = contract.get("accepted_joined_answers", accepted_answers)
    user_key = _normalize_answer_match_key(user_answer)
    if not user_key:
        return False
    return any(user_key == _normalize_answer_match_key(answer) for answer in accepted_answers or [])

def build_accepted_answer_pool(card) -> tuple[str, list[str]]:
    contract = build_answer_contract(card)
    return contract["canonical_joined_answer"], contract["accepted_joined_answers"]

def _normalize_expected_compare_text(value: str) -> str:
    return extract_code_text(value).strip()

def _contains_variant_media_marker(value: str) -> bool:
    lowered = (value or "").lower()
    return any(marker in lowered for marker in QUESTION_VARIANT_MEDIA_MARKERS)

def build_visible_expected_alternatives(raw_answers: list[str], primary_expected: str) -> list[str]:
    visible_answers = []
    seen = {_normalize_answer_match_key(primary_expected)} if primary_expected else set()
    for raw_answer in raw_answers or []:
        if not isinstance(raw_answer, str) or _contains_variant_media_marker(raw_answer):
            continue
        normalized = _normalize_expected_compare_text(raw_answer)
        match_key = _normalize_answer_match_key(raw_answer)
        if not normalized or not match_key or match_key in seen:
            continue
        seen.add(match_key)
        visible_answers.append(normalized)
    return visible_answers

def build_expected_display_model(card, expected_text: str) -> dict:
    primary_expected = _normalize_display_answer_text(expected_text)
    if not card:
        return {
            "primary_expected": primary_expected,
            "alternative_expected_answers": [],
        }

    contract = build_answer_contract(card)
    primary_expected = _normalize_display_answer_text(contract.get("canonical_display_answer") or expected_text)

    return {
        "primary_expected": primary_expected,
        "alternative_expected_answers": build_visible_expected_alternatives(contract["accepted_joined_answers"], primary_expected),
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
            if right < 0 or not float(right).is_integer() or right > 8:
                raise ValueError('Exponent out of bounds')
            return left ** int(right)
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
    question_pool_hash = _cache_hash(build_visible_question_pool(card))
    _canonical_answer, accepted_answers = build_accepted_answer_pool(card)
    answer_pool_hash = _cache_hash(accepted_answers)
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
    chosen_variant = _addon_attr("choose_question_variant", choose_question_variant)(eligible_variants, rng=rng)
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
    candidates = get_eligible_question_variants(card)
    chosen_variant = get_or_choose_active_question_variant(card)
    if not chosen_variant or len(candidates) <= 1:
        return ""

    other_variants = [variant for variant in candidates if variant != chosen_variant]
    choice_html = _build_variant_chip_list(other_variants)
    if not choice_html:
        choice_html = _build_variant_chip_list([chosen_variant])

    return f"""
    <div class="aqi-question-block sqv-question-block">
        <div class="aqi-active-question sqv-active-question">
            {html.escape(chosen_variant)}
        </div>
        {choice_html}
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

def render_enhanced_comparison(output, initial_expected, initial_provided, type_pattern):
    """
    Améliore l'affichage de la comparaison avec l'analyse IA
    """
    config = get_config()
    language = config.get("language", "english")
    labels = get_compare_labels(config)
    show_anki = config.get("show_anki_compare", True)
    show_code = config.get("show_code_compare", True)
    
    # Skip if AI is disabled
    if not config.get("enabled", True):
        return output
    card = mw.reviewer.card if hasattr(mw, 'reviewer') and mw.reviewer else None
    if not get_card_capabilities(card, output, "Answer").get("answer_compare"):
        return output

    payload = build_analysis_prompt_payload(card, initial_provided)
    runtime = resolve_ai_runtime_config(config)
    cache_key = build_analysis_cache_key(
        payload["question_text"],
        payload["canonical_answer"],
        initial_provided,
        card_id=getattr(card, "id", None),
        card_ord=getattr(card, "ord", None),
        language=runtime["language"],
        provider=runtime["provider"],
        model=runtime["model"],
        analysis_mode=runtime["analysis_mode"],
        max_tokens=runtime["max_tokens"],
        temperature=runtime["temperature"],
        accepted_answers=payload["accepted_answers"],
        resolved_prompt_contract=build_prompt_contract_hash(runtime["config"], runtime["language"], runtime["prompt_profile"], "analysis"),
        analysis_prompt_version=ANALYSIS_PROMPT_VERSION,
    )
    current_analysis_context.update(
        {
            "card_id": getattr(card, "id", None),
            "expected_provided_tuple": (payload["canonical_answer"] or "", initial_provided or ""),
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

def get_config():
    return _config_get_config()


def save_config(config):
    _config_save_config(config)

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

def _decode_ai_analysis_text_value(value: str) -> str:
    return (
        str(value or "")
        .replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
        .replace('\\\"', '\"')
        .strip()
    )

def _normalize_ai_analysis_text_payload(text: str, profile: str, active_profile: str, force_exact_match_perfect_score: bool) -> dict | None:
    if not isinstance(text, str):
        return None
    score_match = re.search(r'(?is)"score"\s*:\s*(-?\d+)', text)
    tips_match = re.search(r'(?is)"tips"\s*:\s*"(.*)"\s*[}\]]+\s*$', text)
    if not score_match or not tips_match:
        return None

    answer_match = re.search(r'(?is)"answer"\s*:\s*"(.*?)"\s*,\s*"score"', text)
    question_variant_matches = re.findall(r'(?is)"question_variants"\s*:\s*\[(.*?)\]', text)
    question_variants = []
    if question_variant_matches:
        question_variants = [
            _decode_ai_analysis_text_value(match)
            for match in re.findall(r'"((?:\\.|[^"\\])*)"', question_variant_matches[0])
        ]

    normalized = {
        "score": score_match.group(1),
        "tips": _decode_ai_analysis_text_value(tips_match.group(1)),
        "sample_answers": [_decode_ai_analysis_text_value(answer_match.group(1))] if answer_match else [],
        "question_variants": question_variants,
        "_allow_single_sample_answer": bool(answer_match),
    }
    return _normalize_ai_analysis_payload(normalized, profile, active_profile, force_exact_match_perfect_score)

def _normalize_ai_analysis_payload(result, profile: str, active_profile: str, force_exact_match_perfect_score: bool) -> dict | None:
    if not isinstance(result, dict):
        return None

    normalized = dict(result)
    allow_single_sample_answer = bool(normalized.pop("_allow_single_sample_answer", False))
    if not all(key in normalized for key in ["score", "tips"]):
        sample_answers = normalized.get("sample_answers")
        if isinstance(sample_answers, list):
            for item in sample_answers:
                if not isinstance(item, dict):
                    continue
                if "score" not in item or "tips" not in item:
                    continue
                answer_text = str(item.get("answer", "") or "").strip()
                normalized = {
                    "score": item.get("score"),
                    "tips": item.get("tips", ""),
                    "sample_answers": [answer_text] if answer_text else [],
                    "question_variants": [],
                }
                allow_single_sample_answer = bool(answer_text)
                break
        if not all(key in normalized for key in ["score", "tips"]):
            return None

    normalized["score"] = max(0, min(10, int(normalized["score"])))
    if force_exact_match_perfect_score:
        normalized["score"] = 10
    normalized["scored"] = True
    if profile == PROMPT_PROFILE_CLOZE_RECALL and active_profile == PROMPT_PROFILE_CLOZE_RECALL:
        normalized["sample_answers"] = normalize_ai_analysis_string_list(normalized.get("sample_answers"), min_items=0)
        normalized["question_variants"] = []
    else:
        normalized["sample_answers"] = normalize_ai_analysis_string_list(
            normalized.get("sample_answers"),
            min_items=0 if allow_single_sample_answer else 2,
        )
        normalized["question_variants"] = normalize_ai_analysis_string_list(normalized.get("question_variants"))
    return normalized

def analyze_answer_request(request: dict, card=None) -> dict:
    """
    Analyse une requête d'analyse déjà résolue pour garder un SSOT unique.
    """
    config = merge_config_with_defaults(get_config())
    general_settings = config.get("general", {}) if isinstance(config.get("general"), dict) else {}
    language = (request.get("language") or general_settings.get("language", config.get("language", "english")) or "english").strip() or "english"
    provider = request.get("provider") or config.get("provider", "openai")
    model = (request.get("model", "") or "").strip()
    api_key = (request.get("api_key") or get_provider_settings(config, provider).get("api_key", config.get(f"{provider}_api_key", "")) or "").strip()
    base_url = (request.get("base_url") or get_provider_settings(config, provider).get("base_url", config.get(f"{provider}_base_url", "")) or "").strip()
    if request.get("availability_reason"):
        return make_analysis_unavailable(request.get("availability_reason") or "", language)

    card = card or (mw.reviewer.card if hasattr(mw, 'reviewer') and mw.reviewer else None)
    question_text = request.get("question_text", "")
    true_answer = request.get("canonical_answer", "")
    accepted_answers = request.get("accepted_answers") or []
    user_answer = request.get("user_answer", "")
    profile = request.get("prompt_profile") or PROMPT_PROFILE_DEFAULT
    active_profile = profile
    front_text_raw = ""
    cloze_targets = []
    if profile == PROMPT_PROFILE_CLOZE_RECALL:
        if not is_clozeanything_score_template(card):
            active_profile = PROMPT_PROFILE_DEFAULT
        else:
            payload = build_analysis_prompt_payload(card, user_answer)
            question_text = payload["question_text"]
            true_answer = payload["canonical_answer"]
            accepted_answers = payload["accepted_answers"]
            front_text_raw = payload["front_text_raw"]
            cloze_targets = payload["cloze_targets"]
            if not payload.get("is_valid", True):
                return make_analysis_unavailable(payload.get("invalid_reason") or "Invalid cloze contract", language)

    force_exact_match_perfect_score = is_accepted_answer_match(user_answer, accepted_answers, card=card if is_clozeanything_score_template(card) else None)
    warnings = []
    context_sources = []

    def finalize_result(result: dict) -> dict:
        final = dict(result or {})
        final_warnings = []
        for item in list(warnings) + list(final.get("warnings") or []):
            clean_item = str(item or "").strip()
            if clean_item and clean_item not in final_warnings:
                final_warnings.append(clean_item)
        final_sources = []
        for item in list(context_sources) + list(final.get("sources_used") or []) + list(final.get("context_sources") or []):
            clean_item = str(item or "").strip()
            if clean_item and clean_item not in final_sources:
                final_sources.append(clean_item)
        final["warnings"] = final_warnings
        final["sources_used"] = list(final_sources)
        final["context_sources"] = list(final_sources)
        final["tips"] = merge_analysis_warnings(final.get("tips", ""), final_warnings)
        return final

    system_message, prompt = build_prompt_profile_content(
        config,
        language,
        active_profile,
        question_text,
        true_answer,
        accepted_answers,
        user_answer,
        front_text_raw=front_text_raw,
        cloze_targets=cloze_targets,
    )
    use_notebooklm = normalize_analysis_mode(request.get("analysis_mode", "standard")) == "deep" and bool(request.get("use_notebooklm", False))
    if use_notebooklm:
        notebook_id = str(request.get("notebook_id", "") or "").strip()
        if not notebook_id:
            warnings.append("No target notebook selected for NotebookLM MCP.")
        else:
            try:
                notebook_context = _addon_attr("query_notebooklm_context", query_notebooklm_context)(
                    notebook_id,
                    build_notebooklm_query_text(
                        {
                            "question_text": question_text,
                            "canonical_answer": true_answer,
                            "accepted_answers": accepted_answers,
                            "user_answer": user_answer,
                            "language": language,
                        }
                    ),
                    timeout_s=NOTEBOOKLM_QUERY_TIMEOUT_SECONDS,
                )
                normalized_context, was_trimmed = normalize_notebooklm_context_text(notebook_context)
                if normalized_context:
                    context_sources.append("notebooklm")
                    prompt += "\n\nNotebookLM context (retrieval-only; supporting reference, not scoring authority):\n" + normalized_context
                    if was_trimmed:
                        warnings.append(f"NotebookLM context trimmed to first {NOTEBOOKLM_CONTEXT_CHAR_LIMIT} characters.")
                else:
                    warnings.append("NotebookLM returned empty context.")
            except Exception as exc:
                warnings.append(f"NotebookLM MCP unavailable: {str(exc or '').strip()}")

    prompt += get_language_lock_instruction(language)

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]

    try:
        ai_response = _addon_attr("call_ai_api", call_ai_api)(
            messages=messages,
            provider=provider,
            model=model,
            max_tokens=int(request.get("max_tokens", config.get("max_tokens", 200)) or config.get("max_tokens", 200)),
            temperature=float(request.get("temperature", config.get("temperature", 0.7)) or config.get("temperature", 0.7)),
            api_key=api_key,
            base_url=base_url
        )

        try:
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
                    while isinstance(result, str):
                        nested_candidate = result.strip()
                        if not nested_candidate:
                            break
                        try:
                            result = json.loads(nested_candidate)
                        except json.JSONDecodeError:
                            break
                    break
                except json.JSONDecodeError:
                    continue

            if result is None:
                raise json.JSONDecodeError("Invalid AI JSON response", clean_response, 0)
            normalized_result = _normalize_ai_analysis_payload(result, profile, active_profile, force_exact_match_perfect_score)
            if normalized_result is not None:
                return finalize_result(normalized_result)
            return finalize_result(make_analysis_unavailable("AI returned unsupported JSON schema", language))
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

        normalized_result = _normalize_ai_analysis_text_payload(clean_response, profile, active_profile, force_exact_match_perfect_score)
        if normalized_result is not None:
            return finalize_result(normalized_result)

        lines = ai_response.split('\n')
        score = 5
        tips = "Analyse disponible dans la réponse complète"

        for line in lines:
            if 'score' in line.lower():
                try:
                    score_match = re.search(r'(?i)\bscore\b[^0-9-]*(-?\d+)', line)
                    if score_match:
                        score = max(0, min(10, int(score_match.group(1))))
                except Exception:
                    pass

        if force_exact_match_perfect_score:
            score = 10
        return finalize_result({"scored": True, "score": score, "tips": ai_response[:300] + "..."})

    except Exception as e:
        print(f"AI Analysis Error: {str(e)}")
        return finalize_result(make_analysis_unavailable(f"{PROVIDERS[provider]['name']}: {str(e)}", language))

def analyze_answer_with_ai(question_text: str, true_answer: str, accepted_answers: list[str], user_answer: str, analysis_mode: str = "standard") -> dict:
    """
    **MODIFIÉ: Analyse la réponse de l'utilisateur avec l'IA en incluant le contexte de la question**
    Retourne un dictionnaire avec le score, les conseils et la suggestion de révision
    """
    runtime = resolve_ai_runtime_config(get_config(), analysis_mode=analysis_mode)
    return analyze_answer_request(
        {
            "analysis_mode": runtime["analysis_mode"],
            "question_text": question_text,
            "canonical_answer": true_answer,
            "accepted_answers": accepted_answers,
            "user_answer": user_answer,
            "language": runtime["language"],
            "provider": runtime["provider"],
            "model": runtime["model"],
            "api_key": runtime["api_key"],
            "base_url": runtime["base_url"],
            "prompt_profile": runtime["prompt_profile"],
            "availability_reason": runtime["availability_reason"],
            "use_notebooklm": False,
            "notebook_id": "",
            "notebook_title": "",
            "context_sources": [],
        },
        card=card if (card := (mw.reviewer.card if hasattr(mw, 'reviewer') and mw.reviewer else None)) else None,
    )

def setup_config_menu():
    """Configure le menu de configuration"""
    def open_config():
        config = merge_config_with_defaults(get_config())
        ui = get_config_ui_texts(config)

        from aqt.qt import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton, QSpinBox, QTabWidget, QWidget, QTextEdit, QScrollArea, QAbstractSpinBox

        dialog = QDialog(mw)
        dialog.setWindowTitle(ui["window_title"])
        dialog.setMinimumWidth(550)
        dialog.setMinimumHeight(700)

        root_layout = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)

        general_settings = dict(config.get("general", {}))
        standard_mode = get_mode_settings(config, "standard")
        deep_mode = get_mode_settings(config, "deep")
        provider_settings = config.get("providers", {}) if isinstance(config.get("providers"), dict) else {}

        prompt_profile_options = [
            ("Default", PROMPT_PROFILE_DEFAULT),
            ("Strict STEM", PROMPT_PROFILE_STRICT_STEM),
            ("Speaking Flexible", PROMPT_PROFILE_SPEAKING_FLEXIBLE),
            ("Cloze Recall", PROMPT_PROFILE_CLOZE_RECALL),
            ("Custom", PROMPT_PROFILE_CUSTOM),
        ]

        provider_api_inputs = {}
        provider_base_url_inputs = {}
        provider_custom_models_inputs = {}
        mode_widgets = {}

        tabs = QTabWidget()
        layout.addWidget(tabs)

        def configure_numeric_spinbox(spinbox):
            spinbox.setKeyboardTracking(False)
            try:
                spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
            except Exception:
                pass
            try:
                spinbox.setCorrectionMode(QAbstractSpinBox.CorrectionMode.CorrectToNearestValue)
            except Exception:
                pass
            try:
                spinbox.lineEdit().setReadOnly(False)
            except Exception:
                pass
            return spinbox

        class TemperatureSpinBox(QSpinBox):
            def textFromValue(self, value):
                return f"{int(value) / 100:.2f}"

            def valueFromText(self, text):
                try:
                    return int(round(float(str(text).strip()) * 100))
                except Exception:
                    return 0

        def parse_provider_custom_models(provider_key: str) -> list[str]:
            raw_value = ""
            widget = provider_custom_models_inputs.get(provider_key)
            if widget is not None:
                raw_value = widget.toPlainText()
            else:
                raw_value = "\n".join(provider_settings.get(provider_key, {}).get("custom_models", []) or [])
            values = []
            for line in str(raw_value).replace(",", "\n").splitlines():
                item = line.strip()
                if item and item not in values:
                    values.append(item)
            return values

        def get_provider_model_choices(provider_key: str) -> list[str]:
            choices = []
            for item in PROVIDERS.get(provider_key, {}).get("models", []):
                model_id = str(item or "").strip()
                if model_id and model_id not in choices:
                    choices.append(model_id)
            for model_id in parse_provider_custom_models(provider_key):
                if model_id not in choices:
                    choices.append(model_id)
            return choices

        def set_combo_values(combo, values: list[str], current_text: str = ""):
            combo.blockSignals(True)
            combo.clear()
            if values:
                combo.addItems(values)
            current_text = str(current_text or "").strip()
            if current_text:
                if current_text in values:
                    combo.setCurrentText(current_text)
                else:
                    combo.setEditText(current_text)
            combo.blockSignals(False)

        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)

        language_layout = QHBoxLayout()
        language_layout.addWidget(QLabel(ui["analysis_language"]))
        language_combo = QComboBox()
        supported_languages = get_supported_language_options()
        for lang_key, display_name in supported_languages:
            language_combo.addItem(display_name, lang_key)
        current_language = general_settings.get("language", "english")
        current_language_index = next((index for index, (lang_key, _name) in enumerate(supported_languages) if lang_key == current_language), 0)
        language_combo.setCurrentIndex(current_language_index)
        language_layout.addWidget(language_combo)
        general_layout.addLayout(language_layout)

        show_anki_chk = QCheckBox(ui["show_anki_compare"])
        show_anki_chk.setChecked(bool(general_settings.get("show_anki_compare", True)))
        general_layout.addWidget(show_anki_chk)

        show_code_chk = QCheckBox(ui["show_code_compare"])
        show_code_chk.setChecked(bool(general_settings.get("show_code_compare", True)))
        general_layout.addWidget(show_code_chk)

        custom_system_label = QLabel(ui["custom_system_prompt"])
        general_layout.addWidget(custom_system_label)
        custom_system_input = QTextEdit()
        custom_system_input.setPlainText(config.get("custom_system_prompt", ""))
        custom_system_input.setMinimumHeight(80)
        general_layout.addWidget(custom_system_input)

        custom_template_label = QLabel(ui["custom_analysis_prompt"])
        general_layout.addWidget(custom_template_label)
        custom_template_input = QTextEdit()
        custom_template_input.setPlainText(config.get("custom_analysis_prompt_template", ""))
        custom_template_input.setMinimumHeight(140)
        general_layout.addWidget(custom_template_input)

        custom_hint_template_label = QLabel(ui.get("custom_hint_prompt", "Custom hint prompt template (supports {question}, {expected_answer}, {hint}, {language}):"))
        general_layout.addWidget(custom_hint_template_label)
        custom_hint_template_input = QTextEdit()
        custom_hint_template_input.setPlainText(config.get("custom_hint_prompt_template", ""))
        custom_hint_template_input.setMinimumHeight(110)
        general_layout.addWidget(custom_hint_template_input)

        reset_custom_prompt_btn = QPushButton(ui.get("reset_custom_prompt", "Reset prompts to defaults"))
        general_layout.addWidget(reset_custom_prompt_btn)
        general_layout.addStretch(1)
        tabs.addTab(general_tab, "General")

        def create_mode_tab(mode_key: str, title: str, enabled_label: str, mode_config: dict):
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)

            enabled_checkbox = QCheckBox(enabled_label)
            enabled_checkbox.setChecked(bool(mode_config.get("enabled", mode_key == "standard")))
            tab_layout.addWidget(enabled_checkbox)

            provider_layout = QHBoxLayout()
            provider_layout.addWidget(QLabel(ui["ai_provider"]))
            provider_combo = QComboBox()
            for provider_key, provider_info in PROVIDERS.items():
                provider_combo.addItem(provider_info["name"], provider_key)
            selected_provider = str(mode_config.get("provider", DEFAULT_CONFIG.get("provider", "openai")) or DEFAULT_CONFIG.get("provider", "openai")).strip() or DEFAULT_CONFIG.get("provider", "openai")
            provider_index = next((index for index in range(provider_combo.count()) if provider_combo.itemData(index) == selected_provider), 0)
            provider_combo.setCurrentIndex(provider_index)
            provider_layout.addWidget(provider_combo)
            tab_layout.addLayout(provider_layout)

            model_layout = QHBoxLayout()
            model_layout.addWidget(QLabel("Model:"))
            model_combo = QComboBox()
            model_combo.setEditable(True)
            model_layout.addWidget(model_combo)
            tab_layout.addLayout(model_layout)

            prompt_layout = QHBoxLayout()
            prompt_label = ui.get("standard_prompt_profile", "Standard prompt profile") if mode_key == "standard" else ui.get("deep_prompt_profile", "Deep prompt profile")
            prompt_layout.addWidget(QLabel(prompt_label))
            prompt_combo = QComboBox()
            for label, value in prompt_profile_options:
                prompt_combo.addItem(label, value)
            current_prompt_profile = normalize_prompt_profile(mode_config.get("prompt_profile")) or PROMPT_PROFILE_DEFAULT
            prompt_index = next((index for index, (_label, value) in enumerate(prompt_profile_options) if value == current_prompt_profile), 0)
            prompt_combo.setCurrentIndex(prompt_index)
            prompt_layout.addWidget(prompt_combo)
            tab_layout.addLayout(prompt_layout)

            tokens_layout = QHBoxLayout()
            tokens_layout.addWidget(QLabel(ui["max_tokens"]))
            tokens_spin = QSpinBox()
            tokens_spin.setRange(100, 16000)
            tokens_spin.setSingleStep(100)
            tokens_spin.setAccelerated(True)
            tokens_spin.setReadOnly(False)
            configure_numeric_spinbox(tokens_spin)
            tokens_spin.setValue(min(max(int(mode_config.get("max_tokens", 200) or 200), 100), 16000))
            tokens_layout.addWidget(tokens_spin)
            tab_layout.addLayout(tokens_layout)

            feedback_length_help = QLabel(ui.get("feedback_length_help", "Lower = shorter, faster feedback."))
            feedback_length_help.setStyleSheet("color: #666; font-size: 11px; margin-bottom: 6px;")
            feedback_length_help.setWordWrap(True)
            tab_layout.addWidget(feedback_length_help)

            temp_layout = QHBoxLayout()
            temp_layout.addWidget(QLabel(ui["temperature"]))
            temp_spin = TemperatureSpinBox()
            temp_spin.setRange(0, 100)
            temp_spin.setSingleStep(10)
            configure_numeric_spinbox(temp_spin)
            temp_spin.setValue(int(round(float(mode_config.get("temperature", 0.7) or 0.7) * 100)))
            temp_layout.addWidget(temp_spin)
            tab_layout.addLayout(temp_layout)

            notebooklm_checkbox = None
            notebooklm_combo = None
            notebooklm_controlled_widgets = []

            if mode_key == "deep":
                notebooklm_checkbox = QCheckBox("Use NotebookLM MCP")
                notebooklm_checkbox.setChecked(bool(mode_config.get("use_notebooklm", False)))
                tab_layout.addWidget(notebooklm_checkbox)

                notebooklm_status = QLabel()
                notebooklm_status.setWordWrap(True)
                tab_layout.addWidget(notebooklm_status)
                notebooklm_buttons = QHBoxLayout()
                notebooklm_session_button = QPushButton("Refresh NotebookLM Session")
                notebooklm_auth_button = QPushButton("Re-auth NotebookLM")
                notebooklm_list_button = QPushButton("Refresh Notebook List")
                notebooklm_buttons.addWidget(notebooklm_session_button)
                notebooklm_buttons.addWidget(notebooklm_auth_button)
                notebooklm_buttons.addWidget(notebooklm_list_button)
                tab_layout.addLayout(notebooklm_buttons)

                notebooklm_layout = QHBoxLayout()
                notebooklm_layout.addWidget(QLabel("Target Notebook"))
                notebooklm_combo = QComboBox()
                notebooklm_layout.addWidget(notebooklm_combo)
                tab_layout.addLayout(notebooklm_layout)
                notebooklm_controlled_widgets = [notebooklm_session_button, notebooklm_auth_button, notebooklm_list_button, notebooklm_combo]

                def update_notebooklm_status_label():
                    status_text = str(notebooklm_runtime_state.get("status", "Not checked") or "Not checked").strip() or "Not checked"
                    message = str(notebooklm_runtime_state.get("message", "") or "").strip()
                    notebooklm_status.setText(f"NotebookLM status: {status_text}" + (f" — {message}" if message else ""))

                def set_notebooklm_choices(notebooks=None):
                    values = notebooks if isinstance(notebooks, list) else list(notebooklm_runtime_state.get("notebooks", []) or [])
                    saved_id = str(mode_config.get("notebook_id", "") or "").strip()
                    saved_title = str(mode_config.get("notebook_title", "") or "").strip()
                    notebooklm_combo.blockSignals(True)
                    notebooklm_combo.clear()
                    notebooklm_combo.addItem("", "")
                    current_index = 0
                    for item in values:
                        if not isinstance(item, dict):
                            continue
                        notebook_id = str(item.get("id", "") or "").strip()
                        title_text = str(item.get("title", "") or notebook_id).strip()
                        if not notebook_id:
                            continue
                        notebooklm_combo.addItem(title_text, notebook_id)
                        if saved_id and notebook_id == saved_id:
                            current_index = notebooklm_combo.count() - 1
                    if saved_id and current_index == 0:
                        notebooklm_combo.addItem(f"Saved notebook not found ({saved_title or saved_id})", saved_id)
                        current_index = notebooklm_combo.count() - 1
                    notebooklm_combo.setCurrentIndex(current_index)
                    notebooklm_combo.blockSignals(False)

                def refresh_notebooklm_session_action():
                    state = refresh_notebooklm_session()
                    set_notebooklm_choices(state.get("notebooks", []))
                    update_notebooklm_status_label()
                    if state.get("status") == "Ready":
                        showInfo("NotebookLM session ready.")
                    else:
                        showWarning(f"NotebookLM session: {state.get('status')}" + (f" — {state.get('message')}" if state.get('message') else ""))

                def reauth_notebooklm_session_action():
                    state = reauth_notebooklm_session()
                    set_notebooklm_choices(state.get("notebooks", []))
                    update_notebooklm_status_label()
                    if state.get("status") == "Ready":
                        showInfo("NotebookLM re-auth complete.")
                    else:
                        showWarning(f"NotebookLM re-auth: {state.get('status')}" + (f" — {state.get('message')}" if state.get('message') else ""))

                def refresh_notebooklm_list_action():
                    try:
                        notebooks = list_notebooklm_notebooks()
                        set_notebooklm_choices(notebooks)
                        update_notebooklm_status_label()
                    except Exception as exc:
                        notebooklm_runtime_state.update({"status": _notebooklm_status_from_error(str(exc or "").strip()), "message": str(exc or "").strip(), "notebooks": []})
                        set_notebooklm_choices([])
                        update_notebooklm_status_label()
                        showWarning(f"NotebookLM list refresh failed: {str(exc)}")

                notebooklm_session_button.clicked.connect(refresh_notebooklm_session_action)
                notebooklm_auth_button.clicked.connect(reauth_notebooklm_session_action)
                notebooklm_list_button.clicked.connect(refresh_notebooklm_list_action)
                set_notebooklm_choices()
                update_notebooklm_status_label()

            tab_layout.addStretch(1)

            def refresh_model_choices():
                provider_key = provider_combo.currentData() or DEFAULT_CONFIG.get("provider", "openai")
                current_text = model_combo.currentText().strip()
                fallback_text = get_provider_default_model(provider_key) if mode_key == "standard" else ""
                next_text = current_text or str(mode_config.get("model", "") or fallback_text).strip()
                set_combo_values(model_combo, get_provider_model_choices(provider_key), next_text)

            controlled_widgets = [provider_combo, model_combo, prompt_combo, tokens_spin, temp_spin]
            if notebooklm_checkbox is not None:
                controlled_widgets.append(notebooklm_checkbox)

            def update_mode_enabled_state():
                enabled = enabled_checkbox.isChecked()
                for widget in controlled_widgets:
                    widget.setEnabled(enabled)
                if notebooklm_checkbox is not None:
                    notebooklm_enabled = enabled and notebooklm_checkbox.isChecked()
                    for widget in notebooklm_controlled_widgets:
                        widget.setEnabled(notebooklm_enabled)

            provider_combo.currentIndexChanged.connect(refresh_model_choices)
            enabled_checkbox.toggled.connect(update_mode_enabled_state)
            if notebooklm_checkbox is not None:
                notebooklm_checkbox.toggled.connect(update_mode_enabled_state)
            refresh_model_choices()
            update_mode_enabled_state()

            mode_widgets[mode_key] = {
                "enabled": enabled_checkbox,
                "provider": provider_combo,
                "model": model_combo,
                "prompt_profile": prompt_combo,
                "max_tokens": tokens_spin,
                "temperature": temp_spin,
                "refresh_models": refresh_model_choices,
            }
            if mode_key == "deep":
                mode_widgets[mode_key].update({
                    "use_notebooklm": notebooklm_checkbox,
                    "notebook_id": notebooklm_combo,
                })
            tabs.addTab(tab, title)

        create_mode_tab("standard", "Standard", "Use Standard Analysis", standard_mode)
        create_mode_tab("deep", "Deep", "Use Deep Analysis", deep_mode)

        providers_tab = QWidget()
        providers_layout = QVBoxLayout(providers_tab)
        provider_tabs = QTabWidget()

        provider_instructions = {
            "openai": "Get your API key at: https://platform.openai.com/api-keys",
            "gemini": "Get your API key at: https://aistudio.google.com/app/apikey",
            "claude": "Get your API key at: https://console.anthropic.com/",
            "deepseek": "Get your API key at: https://platform.deepseek.com/api_keys",
            "groq": "Get your API key at: https://console.groq.com/keys",
            "openrouter": "Get your API key at: https://openrouter.ai/settings/keys\nTip: use openrouter/free for maximum compatibility.",
            CUSTOM_OPENAI_PROVIDER: "Enter base URL root, for example: http://127.0.0.1:20128/v1\nDo not enter the full /chat/completions endpoint. API key is optional for local routers.",
        }

        for provider_key, provider_info in PROVIDERS.items():
            provider_tab = QWidget()
            provider_tab_layout = QVBoxLayout(provider_tab)
            current_provider_settings = provider_settings.get(provider_key, {}) if isinstance(provider_settings.get(provider_key), dict) else {}

            if provider_key == CUSTOM_OPENAI_PROVIDER:
                base_url_layout = QHBoxLayout()
                base_url_layout.addWidget(QLabel(ui.get("base_url", "Base URL:")))
                base_url_input = QLineEdit(str(current_provider_settings.get("base_url", "") or ""))
                base_url_input.setPlaceholderText(ui.get("base_url_placeholder", "http://127.0.0.1:20128/v1"))
                base_url_layout.addWidget(base_url_input)
                provider_tab_layout.addLayout(base_url_layout)
                provider_base_url_inputs[provider_key] = base_url_input

            api_key_layout = QHBoxLayout()
            api_key_label = ui.get("api_key_optional", "API Key (optional):") if provider_key == CUSTOM_OPENAI_PROVIDER else f"{provider_info['name']} API Key:"
            api_key_layout.addWidget(QLabel(api_key_label))
            api_key_input = QLineEdit(str(current_provider_settings.get("api_key", "") or ""))
            try:
                api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            except AttributeError:
                try:
                    api_key_input.setEchoMode(QLineEdit.Password)
                except AttributeError:
                    api_key_input.setEchoMode(2)
            api_key_layout.addWidget(api_key_input)
            provider_tab_layout.addLayout(api_key_layout)
            provider_api_inputs[provider_key] = api_key_input

            custom_models_label = QLabel(ui.get("provider_custom_models", "Extra model IDs (one per line):"))
            provider_tab_layout.addWidget(custom_models_label)
            custom_models_input = QTextEdit()
            custom_models_input.setMinimumHeight(90)
            custom_models_input.setPlainText("\n".join(current_provider_settings.get("custom_models", []) or []))
            provider_tab_layout.addWidget(custom_models_input)
            provider_custom_models_inputs[provider_key] = custom_models_input

            info_label = QLabel(provider_instructions.get(provider_key, ""))
            info_label.setWordWrap(True)
            info_label.setStyleSheet("color: #666; font-size: 11px;")
            provider_tab_layout.addWidget(info_label)
            provider_tab_layout.addStretch(1)
            provider_tabs.addTab(provider_tab, provider_info["name"])

        providers_layout.addWidget(provider_tabs)
        tabs.addTab(providers_tab, "Providers")

        def update_default_prompt_placeholders():
            lang_key = language_combo.currentData() or "english"
            resolved_defaults = resolve_prompt_default_content(lang_key, PROMPT_PROFILE_DEFAULT)
            custom_system_input.setPlaceholderText(build_custom_system_placeholder(ui))
            custom_template_input.setPlaceholderText(resolved_defaults["analysis_prompt_template"])
            custom_hint_template_input.setPlaceholderText(resolved_defaults["hint_prompt_template"])

        def get_selected_standard_prompt_profile() -> str:
            return mode_widgets["standard"]["prompt_profile"].currentData() or PROMPT_PROFILE_DEFAULT

        def get_selected_deep_prompt_profile() -> str:
            return mode_widgets["deep"]["prompt_profile"].currentData() or PROMPT_PROFILE_DEFAULT

        def reset_custom_prompts_to_defaults():
            if not should_show_custom_prompt_fields(get_selected_standard_prompt_profile(), get_selected_deep_prompt_profile()):
                return
            lang_key = language_combo.currentData() or "english"
            resolved_defaults = resolve_prompt_default_content(lang_key, PROMPT_PROFILE_DEFAULT)
            custom_system_input.setPlainText(resolved_defaults["system_prompt"])
            custom_template_input.setPlainText(resolved_defaults["analysis_prompt_template"])
            custom_hint_template_input.setPlainText(resolved_defaults["hint_prompt_template"])

        def update_custom_prompt_inputs():
            enabled = should_show_custom_prompt_fields(get_selected_standard_prompt_profile(), get_selected_deep_prompt_profile())
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
        mode_widgets["standard"]["prompt_profile"].currentIndexChanged.connect(update_custom_prompt_inputs)
        mode_widgets["deep"]["prompt_profile"].currentIndexChanged.connect(update_custom_prompt_inputs)
        update_default_prompt_placeholders()
        update_custom_prompt_inputs()

        test_button = QPushButton(ui["test_api"])
        providers_layout.addWidget(test_button)

        def test_api():
            targets = []
            for mode_key in ("standard", "deep"):
                provider_key = mode_widgets[mode_key]["provider"].currentData()
                model_id = mode_widgets[mode_key]["model"].currentText().strip()
                if provider_key and model_id:
                    targets.append((mode_key, provider_key, model_id))
            if not targets:
                showInfo(ui.get("no_models_selected", "No model selected. Skipping API test."))
                return

            original_text = test_button.text()
            test_button.setText(ui["testing"])
            test_button.setEnabled(False)

            try:
                messages = [{"role": "user", "content": "Respond simply 'OK' to test the connection."}]
                tested_models = []
                for mode_key, provider_key, model_id in targets:
                    api_key = provider_api_inputs.get(provider_key).text().strip() if provider_key in provider_api_inputs else ""
                    base_url = provider_base_url_inputs.get(provider_key).text().strip() if provider_key in provider_base_url_inputs else ""
                    if provider_key == CUSTOM_OPENAI_PROVIDER and not base_url:
                        showWarning(ui.get("enter_base_url", "Please enter a base URL to test the connection."))
                        return
                    response = _addon_attr("call_ai_api", call_ai_api)(
                        messages=messages,
                        provider=provider_key,
                        model=model_id,
                        max_tokens=10,
                        temperature=0.1,
                        api_key=api_key,
                        base_url=base_url,
                    )
                    tested_models.append(f"{mode_key}: {provider_key} / {model_id} ({response[:20].strip()})")
                showInfo("✅ " + ui["connection_success"].format(provider="multiple providers", response="; ".join(tested_models)))
            except Exception as e:
                showWarning("❌ " + str(e))
            finally:
                test_button.setText(original_text)
                test_button.setEnabled(True)

        test_button.clicked.connect(test_api)

        button_layout = QHBoxLayout()
        save_button = QPushButton(ui["save"])
        cancel_button = QPushButton(ui["cancel"])
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        scroll_area.setWidget(content_widget)
        root_layout.addWidget(scroll_area)
        root_layout.addLayout(button_layout)

        def save_and_close():
            providers_block = {}
            for provider_key in PROVIDERS.keys():
                provider_block = {
                    "api_key": provider_api_inputs.get(provider_key).text() if provider_key in provider_api_inputs else "",
                    "custom_models": parse_provider_custom_models(provider_key),
                }
                if provider_key in provider_base_url_inputs:
                    provider_block["base_url"] = provider_base_url_inputs[provider_key].text().strip()
                providers_block[provider_key] = provider_block

            new_config = {
                "general": {
                    "language": language_combo.currentData(),
                    "show_anki_compare": show_anki_chk.isChecked(),
                    "show_code_compare": show_code_chk.isChecked(),
                },
                "modes": {
                    "standard": {
                        "enabled": mode_widgets["standard"]["enabled"].isChecked(),
                        "provider": mode_widgets["standard"]["provider"].currentData(),
                        "model": mode_widgets["standard"]["model"].currentText().strip(),
                        "prompt_profile": get_selected_standard_prompt_profile(),
                        "max_tokens": mode_widgets["standard"]["max_tokens"].value(),
                        "temperature": mode_widgets["standard"]["temperature"].value() / 100.0,
                    },
                    "deep": {
                        "enabled": mode_widgets["deep"]["enabled"].isChecked(),
                        "provider": mode_widgets["deep"]["provider"].currentData(),
                        "model": mode_widgets["deep"]["model"].currentText().strip(),
                        "prompt_profile": get_selected_deep_prompt_profile(),
                        "max_tokens": mode_widgets["deep"]["max_tokens"].value(),
                        "temperature": mode_widgets["deep"]["temperature"].value() / 100.0,
                        "use_notebooklm": bool(mode_widgets["deep"].get("use_notebooklm") and mode_widgets["deep"]["use_notebooklm"].isChecked()),
                        "notebook_id": str(mode_widgets["deep"]["notebook_id"].currentData() or "").strip() if bool(mode_widgets["deep"].get("use_notebooklm") and mode_widgets["deep"]["use_notebooklm"].isChecked()) else "",
                        "notebook_title": str(mode_widgets["deep"]["notebook_id"].currentText() or "").strip() if bool(mode_widgets["deep"].get("use_notebooklm") and mode_widgets["deep"]["use_notebooklm"].isChecked()) else "",
                    },
                },
                "providers": providers_block,
                "ui_language": config.get("ui_language", DEFAULT_CONFIG.get("ui_language", "auto")),
                "prompt_profile": get_selected_standard_prompt_profile(),
                "use_custom_prompt": False,
                "custom_system_prompt": custom_system_input.toPlainText().strip(),
                "custom_analysis_prompt_template": custom_template_input.toPlainText().strip(),
                "custom_hint_prompt_template": custom_hint_template_input.toPlainText().strip(),
            }

            save_config(new_config)
            refresh_open_review_surfaces_after_config_save()
            showInfo(ui["saved"])
            dialog.accept()

        save_button.clicked.connect(save_and_close)
        cancel_button.clicked.connect(dialog.reject)

        dialog.setLayout(root_layout)

        try:
            dialog.exec()
        except AttributeError:
            dialog.exec_()
    # Ajouter au menu Tools
    action = mw.form.menuTools.addAction(get_config_ui_texts(get_config())["menu_title"])
    action.triggered.connect(open_config)

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
    analysis_mode = normalize_analysis_mode(context.get("analysis_mode"))
    if not cache_key or not expected_provided_tuple:
        return
    if is_analyzing.get(cache_key, False):
        _addon_attr("refresh_ai_analysis", refresh_ai_analysis)()
        return
    invalidate_analysis_state(cache_key)
    store_ai_analysis(expected_provided_tuple, type_pattern, analysis_mode=analysis_mode)
    refresh_ai_analysis()

def run_deep_analysis():
    card = mw.reviewer.card if hasattr(mw, 'reviewer') and mw.reviewer else None
    if not should_score_card(card):
        return
    context = dict(current_analysis_context)
    expected_provided_tuple = context.get("expected_provided_tuple")
    type_pattern = context.get("type_pattern")
    if not expected_provided_tuple:
        return
    store_ai_analysis(expected_provided_tuple, type_pattern, analysis_mode="deep")
    refresh_ai_analysis()

def show_standard_ai_analysis() -> bool:
    card = mw.reviewer.card if hasattr(mw, 'reviewer') and mw.reviewer else None
    context = dict(current_analysis_context)
    standard_cache_key = context.get("standard_cache_key")
    if not standard_cache_key:
        return False
    standard_result = analysis_results.get(standard_cache_key) or ai_analysis_cache.get(standard_cache_key)
    if not standard_result:
        return False
    current_analysis_context["cache_key"] = standard_cache_key
    current_analysis_context["analysis_mode"] = "standard"
    current_analysis_context["standard_cache_key"] = standard_cache_key
    expected_provided_tuple = context.get("expected_provided_tuple")
    if card and expected_provided_tuple:
        current_analysis_context["analysis_request"] = build_analysis_request(card, expected_provided_tuple[1] or "", "standard")
    refresh_ai_analysis({"card_id": context.get("card_id"), "cache_key": standard_cache_key})
    return True

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
        _addon_attr("refresh_ai_analysis", refresh_ai_analysis)()
        return True, None
    if message == "regenerate_ai_analysis":
        regenerate_ai_analysis()
        return True, None
    if message == "run_deep_analysis":
        run_deep_analysis()
        return True, None
    if message == "show_standard_ai_analysis":
        show_standard_ai_analysis()
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

gui_hooks.card_will_show.append(_to_textarea_on_question)
gui_hooks.card_will_show.append(render_front_hint_panel)
gui_hooks.card_will_show.append(_code_friendly_diff_on_answer)
gui_hooks.reviewer_will_compare_answer.append(store_ai_analysis)
gui_hooks.reviewer_will_render_compared_answer.append(render_enhanced_comparison)

init()
