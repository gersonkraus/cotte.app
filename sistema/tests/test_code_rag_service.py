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


def test_build_code_context_gera_indice_incremental(monkeypatch, tmp_path: Path):
    code_file = tmp_path / "service.py"
    code_file.write_text("def gerar_relatorio():\n    return 'ok'\n", encoding="utf-8")
    index_file = tmp_path / ".cache" / "code_rag_index.json"

    monkeypatch.setattr(svc, "_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(svc, "_DEFAULT_CODE_RAG_PATHS", ("",))
    monkeypatch.setenv("CODE_RAG_USE_INDEX", "true")
    monkeypatch.setenv("CODE_RAG_INDEX_FILE", str(index_file))

    first = svc.build_code_context(query="gerar relatorio", top_k=1, max_files=20)
    assert first.get("matches", 0) >= 1
    assert index_file.exists()

    code_file.write_text("def gerar_relatorio():\n    return 'ok atualizado'\n", encoding="utf-8")
    second = svc.build_code_context(query="atualizado", top_k=1, max_files=20)
    assert second.get("matches", 0) >= 1
    assert "ok atualizado" in (second.get("context") or "")
