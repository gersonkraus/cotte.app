"""Code RAG técnico simplificado para copiloto interno."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional


_DEFAULT_CODE_RAG_PATHS = (
    "sistema/app",
    "sistema/cotte-frontend/js",
)
_ALLOWED_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".html", ".md"}
_SKIP_PARTS = {
    ".git",
    "node_modules",
    "__pycache__",
    "graphify-out",
    ".pytest_cache",
}


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _iter_candidate_files(max_files: int) -> list[Path]:
    root = _workspace_root()
    files: list[Path] = []
    for rel in _DEFAULT_CODE_RAG_PATHS:
        base = root / rel
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if len(files) >= max_files:
                return files
            if not p.is_file():
                continue
            if p.suffix.lower() not in _ALLOWED_EXTENSIONS:
                continue
            if any(part in _SKIP_PARTS for part in p.parts):
                continue
            files.append(p)
    return files


def _match_score(content: str, terms: list[str]) -> int:
    text = content.lower()
    return sum(text.count(term) for term in terms if term)


def _extract_snippet(content: str, terms: list[str]) -> str:
    lines = content.splitlines()
    if not lines:
        return ""
    idx = 0
    lower_lines = [line.lower() for line in lines]
    for i, line in enumerate(lower_lines):
        if any(term in line for term in terms if term):
            idx = i
            break
    start = max(0, idx - 2)
    end = min(len(lines), idx + 3)
    return "\n".join(lines[start:end])


def build_code_context(
    *,
    query: str,
    top_k: int = 4,
    max_files: Optional[int] = None,
) -> dict[str, Any]:
    q = (query or "").strip()
    if not q:
        return {"context": "", "sources": [], "matches": 0}
    terms = [token.lower() for token in q.split() if len(token.strip()) >= 3][:6]
    if not terms:
        terms = [q.lower()]

    max_files = max_files or int(os.getenv("CODE_RAG_MAX_FILES", "700"))
    candidates = _iter_candidate_files(max_files=max_files)
    ranked: list[tuple[int, Path, str]] = []
    for path in candidates:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        score = _match_score(content, terms)
        if score <= 0:
            continue
        snippet = _extract_snippet(content, terms)
        ranked.append((score, path, snippet))

    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = ranked[: max(1, top_k)]
    root = _workspace_root()
    sources: list[str] = []
    snippets: list[str] = []
    for score, path, snippet in selected:
        rel = str(path.relative_to(root))
        sources.append(rel)
        snippets.append(f"[{rel}] (score={score})\n{snippet}")

    context = "\n\n".join(snippets)
    return {
        "context": context,
        "sources": sources,
        "matches": len(ranked),
    }
