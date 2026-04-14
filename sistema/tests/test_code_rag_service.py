from __future__ import annotations

from pathlib import Path

from app.services import code_rag_service as svc


def test_build_code_context_encontra_snippets(monkeypatch, tmp_path: Path):
    code_file = tmp_path / "module.py"
    code_file.write_text(
        "def calcular_total(valor):\n    return valor * 2\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(svc, "_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(svc, "_DEFAULT_CODE_RAG_PATHS", ("",))

    out = svc.build_code_context(query="calcular total", top_k=2, max_files=20)
    assert out.get("matches", 0) >= 1
    assert out.get("sources")
    assert "calcular_total" in (out.get("context") or "")
