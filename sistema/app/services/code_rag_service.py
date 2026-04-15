"""Code RAG técnico simplificado para copiloto interno."""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Optional


_DEFAULT_CODE_RAG_PATHS = (
    "sistema/app",
    "sistema/cotte-frontend",
)
_ALLOWED_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".html", ".md", ".css", ".json", ".yaml", ".yml"}
_SKIP_PARTS = {
    ".git",
    "node_modules",
    "__pycache__",
    "graphify-out",
    ".pytest_cache",
}


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_code_rag_paths() -> tuple[str, ...]:
    raw = os.getenv("CODE_RAG_PATHS", "")
    if not raw.strip():
        return _DEFAULT_CODE_RAG_PATHS
    paths = tuple(part.strip() for part in raw.split(",") if part and part.strip())
    return paths or _DEFAULT_CODE_RAG_PATHS


def _index_enabled() -> bool:
    return str(os.getenv("CODE_RAG_USE_INDEX", "true")).strip().lower() in {"1", "true", "yes", "on"}


def _index_file_path() -> Path:
    custom = (os.getenv("CODE_RAG_INDEX_FILE", "") or "").strip()
    if custom:
        p = Path(custom)
        if not p.is_absolute():
            p = _workspace_root() / p
        return p
    return _workspace_root() / ".cache" / "code_rag_index.json"


def _read_content(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _fingerprint(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return int(stat.st_mtime_ns), int(stat.st_size)


def _load_index() -> dict[str, Any]:
    idx_path = _index_file_path()
    try:
        if not idx_path.exists():
            return {"version": 1, "files": {}}
        payload = json.loads(idx_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {"version": 1, "files": {}}
        files = payload.get("files")
        if not isinstance(files, dict):
            return {"version": 1, "files": {}}
        return {"version": 1, "files": files}
    except Exception:
        return {"version": 1, "files": {}}


def _save_index(index: dict[str, Any]) -> None:
    idx_path = _index_file_path()
    try:
        idx_path.parent.mkdir(parents=True, exist_ok=True)
        idx_path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    except Exception:
        # fallback silencioso para não quebrar o fluxo principal do assistente
        return


def _iter_candidate_files(max_files: int) -> list[Path]:
    root = _workspace_root()
    files: list[Path] = []
    for rel in _resolve_code_rag_paths():
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


def _match_score(text: str, terms: list[str]) -> int:
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
    root = _workspace_root()
    use_index = _index_enabled()
    ranked: list[tuple[int, Path, str]] = []
    indexed_records: dict[str, Any] = {}
    index_dirty = False
    if use_index:
        index_payload = _load_index()
        indexed_records = dict(index_payload.get("files") or {})
        valid_keys = set()
        for path in candidates:
            rel = str(path.relative_to(root))
            valid_keys.add(rel)
            try:
                mtime_ns, size = _fingerprint(path)
            except Exception:
                continue
            cached = indexed_records.get(rel)
            if (
                isinstance(cached, dict)
                and int(cached.get("mtime_ns", 0)) == mtime_ns
                and int(cached.get("size", -1)) == size
                and isinstance(cached.get("content"), str)
            ):
                continue
            content = _read_content(path)
            indexed_records[rel] = {"mtime_ns": mtime_ns, "size": size, "content": content}
            index_dirty = True
        stale = [key for key in indexed_records.keys() if key not in valid_keys]
        for key in stale:
            indexed_records.pop(key, None)
            index_dirty = True
        if index_dirty:
            _save_index({"version": 1, "files": indexed_records})

    for path in candidates:
        rel = str(path.relative_to(root))
        if use_index:
            cached = indexed_records.get(rel) or {}
            content = str(cached.get("content") or "")
        else:
            content = _read_content(path)
        if not content:
            continue
        score = _match_score(content.lower(), terms)
        if score <= 0:
            continue
        snippet = _extract_snippet(content, terms)
        ranked.append((score, path, snippet))

    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = ranked[: max(1, top_k)]
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
