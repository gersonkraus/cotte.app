# Copiloto Trace e Filtros Gerenciais Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** adicionar preview curto do histórico no `trace` do planner e ampliar o runtime autônomo para interpretar filtros gerenciais frequentes por status e período civil simples.

**Architecture:** a mudança fica concentrada em `internal_copilot_autonomy_runtime.py`, sem criar novo módulo. O runtime ganha helpers locais para preview de histórico, extração de status/período e composição de SQL fallback, preservando o planner LLM como caminho prioritário quando habilitado.

**Tech Stack:** Python, FastAPI, SQLAlchemy, pytest.

---

## Estrutura de arquivos

### Arquivos modificados

- `sistema/app/services/internal_copilot_autonomy_runtime.py` — enriquecer `trace`, interpretar status/período e montar fallback SQL com coluna de data correta.
- `sistema/tests/test_internal_copilot_autonomy_runtime.py` — testes de regressão para preview do histórico, novos filtros e SQL fallback.

### Dependências a consultar durante a execução

- `sistema/app/models/models.py` — confirmar valores reais do enum `StatusOrcamento`.
- `sistema/app/services/assistant_autonomy/llm_sql_planner.py` — preservar contrato de `historico` enviado ao planner.

---

### Task 1: Cobrir o preview de histórico no trace

**Files:**
- Modify: `sistema/tests/test_internal_copilot_autonomy_runtime.py`
- Modify: `sistema/app/services/internal_copilot_autonomy_runtime.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_runtime_exposes_history_preview_in_plan_trace(monkeypatch):
    from app.services.internal_copilot_autonomy_runtime import run_internal_copilot_autonomy
    from app.services.assistant_autonomy.llm_sql_planner import LLMSqlPlan

    def fake_enabled():
        return True

    async def fake_llm_plan(message, *, period_days, historico=""):
        return LLMSqlPlan(
            sql="SELECT COUNT(*) as total FROM orcamentos",
            rationale="Usou contexto da sessao",
            used=True,
        )

    def fake_validate(**kwargs):
        return SimpleNamespace(
            allowed=True,
            mode="read_only",
            needs_confirmation=False,
            reason=None,
            rewritten_sql="SELECT COUNT(*) as total FROM orcamentos WHERE orcamentos.empresa_id = 3 LIMIT 100",
        )

    async def fake_execute(**kwargs):
        return {"columns": ["total"], "rows": [[10]], "row_count": 1}

    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.llm_sql_planner_enabled", fake_enabled)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.try_generate_sql_from_llm", fake_llm_plan)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.validate_sql_query", fake_validate)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._execute_validated_query", fake_execute)
    monkeypatch.setattr(
        "app.services.internal_copilot_autonomy_runtime._load_session_history",
        lambda **kwargs: "usuario: liste os orcamentos em rascunho\nassistente: Encontrei 39 resultado(s).\nusuario: agora gere um resumo executivo com mais contexto e detalhes.",
    )

    result = await run_internal_copilot_autonomy(
        db=None,
        current_user=SimpleNamespace(id=7, empresa_id=3),
        mensagem="agora crie uma versao gerencial",
        sessao_id="sess-hist-trace-1",
        request_id="req-hist-trace-1",
    )

    plan_trace = next(step for step in result["trace"] if step["step"] == "plan")
    assert plan_trace["history_messages"] == 3
    assert plan_trace["history_truncated"] is True
    assert "liste os orcamentos em rascunho" in plan_trace["history_preview"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sistema && pytest tests/test_internal_copilot_autonomy_runtime.py -k history_preview_in_plan_trace -v`
Expected: FAIL because the `plan` trace step does not expose `history_preview`, `history_messages`, or `history_truncated` yet.

- [ ] **Step 3: Write minimal implementation**

```python
def _build_history_preview(history_text: str, *, max_lines: int = 3, max_chars: int = 220) -> dict[str, Any]:
    lines = [line.strip() for line in str(history_text or "").splitlines() if line.strip()]
    selected = lines[:max_lines]
    preview = "\n".join(selected)
    truncated = len(lines) > max_lines
    if len(preview) > max_chars:
        preview = preview[: max_chars - 3].rstrip() + "..."
        truncated = True
    return {
        "history_preview": preview,
        "history_messages": len(lines),
        "history_truncated": truncated,
    }
```

Atualizar o append do step `plan` para incluir o dicionário retornado por `_build_history_preview(history_text)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sistema && pytest tests/test_internal_copilot_autonomy_runtime.py -k history_preview_in_plan_trace -v`
Expected: PASS.

### Task 2: Cobrir interpretação de períodos civis e status gerenciais

**Files:**
- Modify: `sistema/tests/test_internal_copilot_autonomy_runtime.py`
- Modify: `sistema/app/services/internal_copilot_autonomy_runtime.py`

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_runtime_interpret_recognizes_aprovados_em_abril():
    from app.services.internal_copilot_autonomy_runtime import _interpret_message

    result = await _interpret_message(
        mensagem="relatorio gerencial de orcamentos aprovados em abril",
        current_user=SimpleNamespace(id=7, empresa_id=3),
        sessao_id=None,
        request_id=None,
    )

    assert result["intent"] == "listar_orcamentos_aprovados"
    assert result["preferred_output"] == "table"


@pytest.mark.asyncio
async def test_runtime_interpret_recognizes_recusados_ontem():
    from app.services.internal_copilot_autonomy_runtime import _interpret_message

    result = await _interpret_message(
        mensagem="orcamentos recusados ontem",
        current_user=SimpleNamespace(id=7, empresa_id=3),
        sessao_id=None,
        request_id=None,
    )

    assert result["intent"] == "listar_orcamentos_recusados"
    assert result["preferred_output"] == "table"


@pytest.mark.asyncio
async def test_runtime_interpret_recognizes_rascunho_este_mes():
    from app.services.internal_copilot_autonomy_runtime import _interpret_message

    result = await _interpret_message(
        mensagem="orcamentos em rascunho este mes",
        current_user=SimpleNamespace(id=7, empresa_id=3),
        sessao_id=None,
        request_id=None,
    )

    assert result["intent"] == "listar_orcamentos_rascunho"
    assert result["preferred_output"] == "table"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sistema && pytest tests/test_internal_copilot_autonomy_runtime.py -k "aprovados_em_abril or recusados_ontem or rascunho_este_mes" -v`
Expected: FAIL because the interpreter still routes these phrases to generic intents.

- [ ] **Step 3: Write minimal implementation**

```python
asks_for_approved = any(k in lowered for k in ("aprovado", "aprovada", "aprovados", "aprovadas"))
asks_for_rejected = any(k in lowered for k in ("recusado", "recusada", "recusados", "recusadas"))
asks_for_draft = any(k in lowered for k in ("rascunho", "rascunhos"))

if refers_to_sales and asks_for_non_approved:
    intent.intent = "listar_orcamentos_nao_aprovados"
    intent.preferred_output = "table"
elif refers_to_sales and asks_for_approved and asks_for_list:
    intent.intent = "listar_orcamentos_aprovados"
    intent.preferred_output = "table"
elif refers_to_sales and asks_for_rejected and asks_for_list:
    intent.intent = "listar_orcamentos_recusados"
    intent.preferred_output = "table"
elif refers_to_sales and asks_for_draft and asks_for_list:
    intent.intent = "listar_orcamentos_rascunho"
    intent.preferred_output = "table"
```

Manter a normalização por `_normalize_text(...)` para cobrir `mês` e `não` sem acento.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sistema && pytest tests/test_internal_copilot_autonomy_runtime.py -k "aprovados_em_abril or recusados_ontem or rascunho_este_mes" -v`
Expected: PASS.

### Task 3: Cobrir SQL fallback com data por status e período civil

**Files:**
- Modify: `sistema/tests/test_internal_copilot_autonomy_runtime.py`
- Modify: `sistema/app/services/internal_copilot_autonomy_runtime.py`

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_build_plan_uses_aprovado_em_for_aprovados_with_named_month(monkeypatch):
    from app.services import internal_copilot_autonomy_runtime as runtime

    monkeypatch.setattr(runtime, "llm_sql_planner_enabled", lambda: False)

    plan = await runtime._build_plan(
        intent={"intent": "listar_orcamentos_aprovados", "raw_message": "orcamentos aprovados em abril"},
        raw_message="orcamentos aprovados em abril",
        history_text="",
        current_user=None,
        sessao_id=None,
        request_id=None,
    )

    assert "status = 'APROVADO'" in plan["sql_candidate"]
    assert "aprovado_em" in plan["sql_candidate"]


@pytest.mark.asyncio
async def test_build_plan_uses_criado_em_for_recusados_with_relative_day(monkeypatch):
    from app.services import internal_copilot_autonomy_runtime as runtime

    monkeypatch.setattr(runtime, "llm_sql_planner_enabled", lambda: False)

    plan = await runtime._build_plan(
        intent={"intent": "listar_orcamentos_recusados", "raw_message": "orcamentos recusados ontem"},
        raw_message="orcamentos recusados ontem",
        history_text="",
        current_user=None,
        sessao_id=None,
        request_id=None,
    )

    assert "status = 'RECUSADO'" in plan["sql_candidate"]
    assert "criado_em" in plan["sql_candidate"]


@pytest.mark.asyncio
async def test_build_plan_keeps_non_approved_with_status_not_equal(monkeypatch):
    from app.services import internal_copilot_autonomy_runtime as runtime

    monkeypatch.setattr(runtime, "llm_sql_planner_enabled", lambda: False)

    plan = await runtime._build_plan(
        intent={"intent": "listar_orcamentos_nao_aprovados", "raw_message": "propostas nao aprovadas em abril"},
        raw_message="propostas nao aprovadas em abril",
        history_text="",
        current_user=None,
        sessao_id=None,
        request_id=None,
    )

    assert "status <> 'APROVADO'" in plan["sql_candidate"]
    assert "criado_em" in plan["sql_candidate"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sistema && pytest tests/test_internal_copilot_autonomy_runtime.py -k "uses_aprovado_em or uses_criado_em or keeps_non_approved" -v`
Expected: FAIL because `_build_plan(...)` still returns SQL fixo sem filtro temporal nem coluna de data por status.

- [ ] **Step 3: Write minimal implementation**

```python
def _extract_civil_period(value: str) -> tuple[str, str] | None:
    normalized = _normalize_text(value)
    if "ontem" in normalized:
        return ("<yesterday_start>", "<today_start>")
    if "este mes" in normalized:
        return ("<month_start>", "<now>")
    if "abril" in normalized:
        return ("<april_start>", "<may_start>")
    return None


def _resolve_date_column_for_intent(intent_name: str) -> str | None:
    if intent_name == "listar_orcamentos_aprovados":
        return "aprovado_em"
    if intent_name in {"listar_orcamentos_recusados", "listar_orcamentos_rascunho", "listar_orcamentos_nao_aprovados"}:
        return "criado_em"
    return None
```

Montar o SQL com base em um helper que anexa `status` e janela temporal simples usando a coluna correta, por exemplo:

```python
if intent_name == "listar_orcamentos_aprovados":
    return {"sql_candidate": _build_orcamentos_status_query("APROVADO", "aprovado_em", raw_message)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sistema && pytest tests/test_internal_copilot_autonomy_runtime.py -k "uses_aprovado_em or uses_criado_em or keeps_non_approved" -v`
Expected: PASS.

### Task 4: Rodar a suíte alvo de regressão

**Files:**
- Modify: `sistema/tests/test_internal_copilot_autonomy_runtime.py`
- Modify: `sistema/app/services/internal_copilot_autonomy_runtime.py`

- [ ] **Step 1: Run the focused runtime suite**

Run: `cd sistema && pytest tests/test_internal_copilot_autonomy_runtime.py -v`
Expected: PASS with all existing and new runtime tests green.

- [ ] **Step 2: Inspect the diff before finishing**

Run: `git diff -- sistema/app/services/internal_copilot_autonomy_runtime.py sistema/tests/test_internal_copilot_autonomy_runtime.py docs/superpowers/specs/2026-04-30-copiloto-trace-filtros-gerenciais-design.md docs/superpowers/plans/2026-04-30-copiloto-trace-filtros-gerenciais.md`
Expected: diff restrito ao runtime, testes e documentação já criada.
