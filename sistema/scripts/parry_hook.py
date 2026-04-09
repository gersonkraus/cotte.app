#!/usr/bin/env python3
"""
parry_hook.py — Detector de prompt injection para Claude Code (PreToolUse)

Escaneia o input de ferramentas Bash e Edit em busca de padrões de:
- Prompt injection (tentativas de sobrescrever instruções do Claude)
- Vazamento de credenciais (tokens, API keys, senhas)
- Comandos destrutivos de alto risco não esperados

Saída:
  exit 0 — permitir a ação
  exit 2 — bloquear e avisar o Claude (Claude verá a mensagem e pedirá confirmação)

Referência: https://docs.anthropic.com/en/docs/claude-code/hooks
"""
import json
import os
import re
import sys
from datetime import datetime


# ── Padrões de prompt injection ────────────────────────────────────────────

INJECTION_PATTERNS = [
    # Tentativas de sobrescrever system prompt
    (r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", "Possível prompt injection: 'ignore previous instructions'"),
    (r"(disregard|forget|override)\s+(your\s+)?(previous|prior|system|all)\s+(instructions?|rules?|constraints?)", "Possível prompt injection: override de instruções"),
    (r"you\s+are\s+now\s+(a\s+)?(?!COTTE|assistant)", "Possível role hijack: 'you are now...'"),
    (r"new\s+system\s+prompt\s*:", "Possível injeção de system prompt"),
    (r"(act|behave|pretend)\s+as\s+(if\s+you\s+are|a)\s+(?!helpful)", "Possível role manipulation"),
    (r"\[SYSTEM\]|\[INST\]|\[\/INST\]|<\|im_start\|>|<\|im_end\|>", "Token de controle de LLM detectado"),

    # Exfiltração de dados
    (r"(send|exfiltrate|leak|transmit)\s+(all\s+)?(credentials?|secrets?|env\s+vars?|api\s+keys?)", "Possível tentativa de exfiltração"),
    (r"curl\s+.*\$\{?(SECRET|TOKEN|KEY|PASSWORD|API_KEY)", "Possível exfiltração de credencial via curl"),
    (r"wget\s+.*\$\{?(SECRET|TOKEN|KEY|PASSWORD|API_KEY)", "Possível exfiltração de credencial via wget"),

    # Comandos destrutivos inesperados
    (r"\brm\s+-rf\s+/(?!tmp|var/tmp)", "Comando destrutivo rm -rf em diretório raiz"),
    (r"DROP\s+TABLE\s+\w+\s*;", "Comando SQL destrutivo: DROP TABLE"),
    (r"DELETE\s+FROM\s+\w+\s*;", "SQL DELETE sem WHERE detectado"),
    (r">\s*/etc/(passwd|shadow|hosts)", "Tentativa de escrita em arquivo de sistema"),
]

# ── Padrões de credenciais hardcoded ──────────────────────────────────────

CREDENTIAL_PATTERNS = [
    (r'(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*=\s*["\']?[A-Za-z0-9_\-]{20,}', "Possível API key hardcoded no código"),
    (r'(?i)password\s*=\s*["\'][^"\']{8,}["\']', "Possível senha hardcoded"),
    (r'sk-[A-Za-z0-9]{20,}', "Possível Anthropic/OpenAI API key no código"),
    (r'(?i)ANTHROPIC_API_KEY\s*=\s*["\']?sk-', "Anthropic API key exposta"),
]

# ── Arquivos sensíveis que não devem ser editados ─────────────────────────

SENSITIVE_FILES = [
    r"\.env$",
    r"\.env\.(local|prod|production|staging)$",
    r"settings\.secret\.",
    r"secrets?\.json$",
    r"credentials?\.json$",
    r"id_rsa$",
    r"\.pem$",
]


def log_alert(tool: str, pattern_desc: str, snippet: str):
    """Registra alertas em ~/.claude/parry_alerts.log."""
    log_dir = os.path.join(os.environ.get("USERPROFILE") or os.environ.get("HOME", ""), ".claude")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "parry_alerts.log")
    timestamp = datetime.now().isoformat()
    entry = f"{timestamp} | TOOL={tool} | {pattern_desc} | snippet={snippet[:100]!r}\n"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def scan_text(text: str, tool: str) -> list[str]:
    """Retorna lista de alertas encontrados no texto."""
    alerts = []
    text_lower = text.lower()

    for pattern, description in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            log_alert(tool, description, text[:200])
            alerts.append(description)

    for pattern, description in CREDENTIAL_PATTERNS:
        if re.search(pattern, text):
            log_alert(tool, description, "[REDACTED]")
            alerts.append(description)

    return alerts


def check_sensitive_file(path: str) -> str | None:
    """Retorna alerta se o arquivo é sensível."""
    for pattern in SENSITIVE_FILES:
        if re.search(pattern, path, re.IGNORECASE):
            return f"Tentativa de editar arquivo sensível: {path}"
    return None


def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    raw_input = os.environ.get("CLAUDE_TOOL_INPUT", "{}")

    try:
        tool_input = json.loads(raw_input)
    except json.JSONDecodeError:
        sys.exit(0)  # Input inválido, deixa o Claude lidar

    alerts = []

    # ── Bash: escaneia o comando ───────────────────────────────────────────
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if command:
            alerts.extend(scan_text(command, tool_name))

    # ── Edit/Write: escaneia conteúdo e verifica arquivo sensível ─────────
    elif tool_name in ("Edit", "Write"):
        file_path = tool_input.get("file_path", "")
        content = tool_input.get("new_string", "") or tool_input.get("content", "")

        if file_path:
            alert = check_sensitive_file(file_path)
            if alert:
                log_alert(tool_name, alert, file_path)
                alerts.append(alert)

        if content:
            alerts.extend(scan_text(content, tool_name))

    # ── WebFetch: escaneia URL ────────────────────────────────────────────
    elif tool_name == "WebFetch":
        url = tool_input.get("url", "")
        # Bloqueia exfiltração de dados para URLs externas suspeitas
        if re.search(r'\$\{?(SECRET|TOKEN|KEY|PASSWORD)', url, re.IGNORECASE):
            alerts.append(f"URL com possível vazamento de credencial: {url[:80]}")
            log_alert(tool_name, alerts[-1], url)

    # ── Resultado ─────────────────────────────────────────────────────────
    if alerts:
        print(f"⚠️  PARRY detectou padrão suspeito em {tool_name}:")
        for a in alerts:
            print(f"   • {a}")
        print("\nVerifique se esta ação é intencional antes de prosseguir.")
        sys.exit(2)  # Bloqueia e mostra mensagem ao Claude

    sys.exit(0)  # Permite


if __name__ == "__main__":
    main()
