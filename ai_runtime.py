from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request

from config_model import *

ADDON_EXPORTS = None


def _addon_attr(name: str, fallback):
    if isinstance(ADDON_EXPORTS, dict) and name in ADDON_EXPORTS:
        return ADDON_EXPORTS[name]
    return fallback

NOTEBOOKLM_CONTEXT_CHAR_LIMIT = 4000

NOTEBOOKLM_QUERY_TIMEOUT_SECONDS = 45.0

NOTEBOOKLM_TOOL_TIMEOUT_SECONDS = 30.0

NOTEBOOKLM_CLIENT_INFO = {"name": "score_answer_anki", "version": "0.1"}

notebooklm_runtime_state = {"status": "Not checked", "message": "", "notebooks": []}

NOTEBOOKLM_AUTH_ERROR_MARKERS = (
    "authentication expired",
    "rpc error 16",
    "client error '400 bad request'",
    "https://notebooklm.google.com/_/labstailwindui/data/batchexecute",
)

NOTEBOOKLM_NETWORK_ERROR_MARKERS = (
    "handshake operation timed out",
    "read operation timed out",
    "getaddrinfo failed",
    "forcibly closed by the remote host",
    "server disconnected without sending a response",
    "connection reset by peer",
    "peer closed connection",
    "incomplete chunked read",
    "incomplete message body",
    "remote end closed connection",
)

def normalize_notebooklm_context_text(text: str, limit: int = NOTEBOOKLM_CONTEXT_CHAR_LIMIT) -> tuple[str, bool]:
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if not normalized:
        return "", False
    if len(normalized) <= limit:
        return normalized, False
    return normalized[:limit].rstrip(), True

def build_notebooklm_query_text(request: dict) -> str:
    accepted_answers = request.get("accepted_answers") or []
    return (
        "Review this learner answer with concise source-grounded context only.\n\n"
        f"Question: {request.get('question_text', '')}\n"
        f"Expected answer: {request.get('canonical_answer', '')}\n"
        f"Accepted answers: {accepted_answers}\n"
        f"Student answer: {request.get('user_answer', '')}\n"
        f"Language: {request.get('language', '')}\n\n"
        "Return short reference context that helps judge correctness, acceptable variants, and major omissions. Do not score the answer."
    )

def _notebooklm_send(proc, msg: dict) -> None:
    if not proc.stdin:
        raise RuntimeError("NotebookLM MCP stdin unavailable")
    proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
    proc.stdin.flush()

def _notebooklm_recv(proc, timeout_s: float) -> dict:
    if not proc.stdout:
        raise RuntimeError("NotebookLM MCP stdout unavailable")
    started = time.time()
    while time.time() - started < timeout_s:
        line = proc.stdout.readline()
        if not line:
            continue
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            return payload
    raise TimeoutError("NotebookLM MCP response timeout")

def _notebooklm_subprocess_kwargs(hide_window: bool = True) -> dict:
    kwargs = {}
    if hide_window and os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return kwargs

def _start_notebooklm_session():
    proc = subprocess.Popen(
        ["notebooklm-mcp", "--transport", "stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        **_notebooklm_subprocess_kwargs(),
    )
    _addon_attr("_notebooklm_send", _notebooklm_send)(
        proc,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                "clientInfo": NOTEBOOKLM_CLIENT_INFO,
            },
        },
    )
    _addon_attr("_notebooklm_recv", _notebooklm_recv)(proc, 20.0)
    _addon_attr("_notebooklm_send", _notebooklm_send)(proc, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
    return {"proc": proc, "next_id": 2}

def _stop_notebooklm_session(session) -> None:
    proc = (session or {}).get("proc") if isinstance(session, dict) else None
    if proc is None:
        return
    try:
        proc.terminate()
    except Exception:
        pass

def _notebooklm_tool_call(session, name: str, arguments: dict, timeout_s: float) -> dict:
    call_id = session["next_id"]
    session["next_id"] += 1
    _addon_attr("_notebooklm_send", _notebooklm_send)(
        session["proc"],
        {
            "jsonrpc": "2.0",
            "id": call_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )
    return _addon_attr("_notebooklm_recv", _notebooklm_recv)(session["proc"], timeout_s)

def _notebooklm_response_json(resp: dict) -> dict:
    result = resp.get("result", {}) if isinstance(resp, dict) else {}
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    content = result.get("content", []) if isinstance(result, dict) else []
    text_value = "".join(part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text")
    if not text_value.strip():
        return {}
    try:
        parsed = json.loads(text_value)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}

def _notebooklm_require_success_payload(resp: dict, tool_name: str) -> dict:
    payload = _notebooklm_response_json(resp)
    if not isinstance(payload, dict):
        return {}
    status_text = str(payload.get("status", "") or "").strip().lower()
    if not status_text or status_text == "success":
        return payload
    error_text = str(payload.get("error") or payload.get("message") or payload).strip() or "unknown NotebookLM error"
    raise RuntimeError(f"{tool_name} failed: {error_text}")

def _normalize_notebooklm_error_text(text: str) -> str:
    return " ".join(str(text or "").casefold().split())

def classify_notebooklm_error(text: str) -> str:
    normalized = _normalize_notebooklm_error_text(text)
    if any(marker in normalized for marker in NOTEBOOKLM_AUTH_ERROR_MARKERS):
        return "auth"
    if any(marker in normalized for marker in NOTEBOOKLM_NETWORK_ERROR_MARKERS):
        return "network"
    return "other"

def _notebooklm_status_from_error(text: str) -> str:
    return "Auth required" if classify_notebooklm_error(text) == "auth" else "Error"

def _normalize_notebooklm_notebooks(payload: dict) -> list[dict]:
    notebooks = payload.get("notebooks", []) if isinstance(payload, dict) else []
    normalized = []
    for item in notebooks if isinstance(notebooks, list) else []:
        if not isinstance(item, dict):
            continue
        notebook_id = str(item.get("id", "") or "").strip()
        title = str(item.get("title", "") or notebook_id).strip()
        if notebook_id:
            normalized.append({"id": notebook_id, "title": title})
    return normalized

def _build_notebooklm_auth_env() -> dict:
    env = os.environ.copy()
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        if env.get(key):
            env[key] = ""
    return env

def run_notebooklm_auth_command() -> int:
    proc = subprocess.run(["notebooklm-mcp-auth"], env=_build_notebooklm_auth_env())
    return int(proc.returncode)

def _notebooklm_response_text(resp: dict) -> str:
    result = resp.get("result", {}) if isinstance(resp, dict) else {}
    structured = result.get("structuredContent")
    if isinstance(structured, dict) and isinstance(structured.get("answer"), str):
        return structured.get("answer", "")
    content = result.get("content", []) if isinstance(result, dict) else []
    text_value = "".join(part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text")
    if not text_value.strip():
        return ""
    try:
        parsed = json.loads(text_value)
    except Exception:
        return text_value
    if isinstance(parsed, dict) and isinstance(parsed.get("answer"), str):
        return parsed.get("answer", "")
    return text_value

def refresh_notebooklm_session() -> dict:
    session = None
    try:
        session = _addon_attr("_start_notebooklm_session", _start_notebooklm_session)()
        resp = _addon_attr("_notebooklm_tool_call", _notebooklm_tool_call)(session, "refresh_auth", {}, NOTEBOOKLM_TOOL_TIMEOUT_SECONDS)
        payload = _notebooklm_require_success_payload(resp, "refresh_auth")
        list_resp = _addon_attr("_notebooklm_tool_call", _notebooklm_tool_call)(session, "notebook_list", {"max_results": 200}, 60.0)
        list_payload = _notebooklm_require_success_payload(list_resp, "notebook_list")
        notebooks = _normalize_notebooklm_notebooks(list_payload)
        notebooklm_runtime_state.update({
            "status": "Ready",
            "message": str(payload.get("message", "") or "").strip(),
            "notebooks": notebooks,
        })
    except FileNotFoundError:
        notebooklm_runtime_state.update({"status": "Error", "message": "notebooklm-mcp not found", "notebooks": []})
    except Exception as exc:
        message = str(exc or "").strip()
        notebooklm_runtime_state.update({"status": _notebooklm_status_from_error(message), "message": message, "notebooks": []})
    finally:
        _stop_notebooklm_session(session)
    return dict(notebooklm_runtime_state)

def reauth_notebooklm_session() -> dict:
    try:
        returncode = _addon_attr("run_notebooklm_auth_command", run_notebooklm_auth_command)()
    except FileNotFoundError:
        notebooklm_runtime_state.update({"status": "Error", "message": "notebooklm-mcp-auth not found", "notebooks": []})
        return dict(notebooklm_runtime_state)
    if returncode != 0:
        notebooklm_runtime_state.update({"status": "Auth required", "message": "NotebookLM re-auth canceled or failed.", "notebooks": []})
        return dict(notebooklm_runtime_state)
    return refresh_notebooklm_session()

def list_notebooklm_notebooks(max_results: int = 200) -> list[dict]:
    session = None
    try:
        session = _addon_attr("_start_notebooklm_session", _start_notebooklm_session)()
        resp = _addon_attr("_notebooklm_tool_call", _notebooklm_tool_call)(session, "notebook_list", {"max_results": max_results}, 60.0)
        payload = _notebooklm_require_success_payload(resp, "notebook_list")
        normalized = _normalize_notebooklm_notebooks(payload)
        notebooklm_runtime_state.update({"status": "Ready", "notebooks": normalized, "message": ""})
        return normalized
    except Exception as exc:
        message = str(exc or "").strip()
        notebooklm_runtime_state.update({"status": _notebooklm_status_from_error(message), "message": message, "notebooks": []})
        raise
    finally:
        _stop_notebooklm_session(session)

def query_notebooklm_context(notebook_id: str, query_text: str, timeout_s: float | None = None) -> str:
    notebook_id = str(notebook_id or "").strip()
    if not notebook_id:
        raise ValueError("NotebookLM notebook_id is required")
    session = None
    try:
        session = _addon_attr("_start_notebooklm_session", _start_notebooklm_session)()
        timeout_value = float(timeout_s or NOTEBOOKLM_QUERY_TIMEOUT_SECONDS)
        resp = _addon_attr("_notebooklm_tool_call", _notebooklm_tool_call)(
            session,
            "notebook_query",
            {"notebook_id": notebook_id, "query": query_text, "timeout": int(timeout_value)},
            timeout_value + 15.0,
        )
        _notebooklm_require_success_payload(resp, "notebook_query")
        answer = _notebooklm_response_text(resp).strip()
        if not answer:
            raise RuntimeError("NotebookLM returned empty context")
        return answer
    finally:
        _stop_notebooklm_session(session)

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
