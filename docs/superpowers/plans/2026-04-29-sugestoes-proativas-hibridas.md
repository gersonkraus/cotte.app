# Sugestoes Proativas Hibridas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar um sistema de sugestoes proativas hibridas (regras + IA) integrado ao assistente, com endpoint dedicado na abertura, injecao contextual durante conversa e feedback de utilidade.

**Architecture:** A implementacao cria um `InsightEngine` com geracao por regras, opcao de enriquecimento por IA e filtro por contexto de sessao. O backend expoe `GET /api/v1/ai/insights` e adiciona `insights` no retorno do `POST /api/v1/ai/assistente` sem quebrar contrato. O frontend consome e renderiza cards/chips com feedback e deduplicacao local por sessao.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, frontend HTML/CSS/JS vanilla existente (`assistente-ia.js`), SessionStore/ContextBuilder/SemanticMemoryStore.

---

## Mapa de arquivos (antes das tasks)

- Create: `sistema/app/services/insight_engine.py`
  - Responsabilidade: regras, ranking, cooldown e payload canonico de insights.
- Create: `sistema/tests/test_insight_engine.py`
  - Responsabilidade: testes unitarios do motor de insights.
- Modify: `sistema/app/routers/ai_hub.py`
  - Responsabilidade: endpoint `GET /ai/insights` + schema de resposta + feedback endpoint.
- Modify: `sistema/app/services/cotte_ai_hub.py`
  - Responsabilidade: anexar insights contextuais na resposta do `assistente_unificado_v2`.
- Modify: `sistema/tests/test_assistente_unificado_v2.py`
  - Responsabilidade: garantir contrato de `insights` no fluxo principal.
- Create: `sistema/cotte-frontend/js/assistente-ia-insights.js`
  - Responsabilidade: buscar/renderizar insights da abertura e feedback.
- Modify: `sistema/cotte-frontend/assistente-ia.html`
  - Responsabilidade: slot de renderizacao + include do script.
- Modify: `sistema/cotte-frontend/js/assistente-ia.js`
  - Responsabilidade: integrar insights durante conversa e pos-acao.
- Modify: `sistema/cotte-frontend/css/assistente-ia.css`
  - Responsabilidade: estilos de cards/chips de insight.

### Task 1: Insight Engine (core por regras)

**Files:**
- Create: `sistema/app/services/insight_engine.py`
- Test: `sistema/tests/test_insight_engine.py`

- [ ] **Step 1: Write failing tests for canonical insight payload and priority ordering**

```python
# sistema/tests/test_insight_engine.py
from app.services.insight_engine import InsightEngine


def test_build_returns_canonical_fields():
    engine = InsightEngine()
    out = engine.build_for_empresa(
        empresa_id=1,
        contexto={"dominio": "orcamentos"},
        snapshot={"orcamentos": [{"id": 10, "dias_pendente": 8, "status": "ENVIADO"}]},
    )
    assert isinstance(out, list)
    assert out
    item = out[0]
    for k in ("id", "tipo", "prioridade", "dominio", "titulo", "descricao", "acao", "contexto", "score", "fonte", "expira_em"):
        assert k in item


def test_high_priority_is_ranked_first():
    engine = InsightEngine()
    out = engine.build_for_empresa(
        empresa_id=1,
        contexto={"dominio": "financeiro"},
        snapshot={
            "financeiro": {"saldo_projetado": -100.0, "inadimplencia_pct": 25.0},
            "orcamentos": [{"id": 33, "dias_pendente": 6, "status": "ENVIADO"}],
        },
    )
    assert out[0]["prioridade"] in ("critica", "alta")
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `cd sistema && pytest tests/test_insight_engine.py -q`
Expected: FAIL com `ModuleNotFoundError` ou `AttributeError` para `InsightEngine`.

- [ ] **Step 3: Implement minimal InsightEngine with rule evaluation and ranking**

```python
# sistema/app/services/insight_engine.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha1
from typing import Any


_PRIORITY_WEIGHT = {"critica": 1.0, "alta": 0.8, "media": 0.5, "baixa": 0.2}


@dataclass
class InsightEngine:
    ttl_minutes: int = 5

    def _id(self, dominio: str, raw: str) -> str:
        return sha1(f"{dominio}:{raw}".encode("utf-8")).hexdigest()[:16]

    def _expira_em(self) -> str:
        return (datetime.now(timezone.utc) + timedelta(minutes=self.ttl_minutes)).isoformat()

    def _mk(self, *, dominio: str, prioridade: str, titulo: str, descricao: str, acao: dict, contexto: dict, fonte: str = "regra") -> dict:
        rid = self._id(dominio, f"{titulo}|{descricao}|{contexto}")
        return {
            "id": rid,
            "tipo": "acao_sugerida",
            "prioridade": prioridade,
            "dominio": dominio,
            "titulo": titulo,
            "descricao": descricao,
            "acao": acao,
            "contexto": contexto,
            "score": _PRIORITY_WEIGHT.get(prioridade, 0.2),
            "fonte": fonte,
            "expira_em": self._expira_em(),
        }

    def build_for_empresa(self, *, empresa_id: int, contexto: dict[str, Any], snapshot: dict[str, Any]) -> list[dict]:
        insights: list[dict] = []

        for o in snapshot.get("orcamentos", []) or []:
            if (o.get("status") in ("ENVIADO", "RASCUNHO")) and (o.get("dias_pendente", 0) > 5):
                insights.append(
                    self._mk(
                        dominio="orcamentos",
                        prioridade="alta",
                        titulo=f"Follow-up no orçamento #{o.get('id')}",
                        descricao=f"Orçamento pendente há {o.get('dias_pendente')} dias.",
                        acao={"tipo": "executar_prompt", "label": "Gerar follow-up", "prompt": f"Gerar follow-up do orçamento {o.get('id')}"},
                        contexto={"orcamento_id": o.get("id")},
                    )
                )

        fin = snapshot.get("financeiro") or {}
        if (fin.get("saldo_projetado") or 0) < 0:
            insights.append(
                self._mk(
                    dominio="financeiro",
                    prioridade="critica",
                    titulo="Alerta de saldo projetado negativo",
                    descricao="A projeção de caixa está negativa no curto prazo.",
                    acao={"tipo": "executar_prompt", "label": "Ver plano de contingência", "prompt": "Como corrigir caixa negativo nos próximos 7 dias?"},
                    contexto={"saldo_projetado": fin.get("saldo_projetado")},
                )
            )

        if (fin.get("inadimplencia_pct") or 0) >= 20:
            insights.append(
                self._mk(
                    dominio="financeiro",
                    prioridade="alta",
                    titulo="Inadimplência acima do limite",
                    descricao="Clientes em atraso acima de 20%.",
                    acao={"tipo": "executar_prompt", "label": "Sugerir cobrança", "prompt": "Sugerir ação de cobrança por faixa de atraso"},
                    contexto={"inadimplencia_pct": fin.get("inadimplencia_pct")},
                )
            )

        insights.sort(key=lambda x: x.get("score", 0), reverse=True)
        return insights
```

- [ ] **Step 4: Re-run tests to verify pass**

Run: `cd sistema && pytest tests/test_insight_engine.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sistema/app/services/insight_engine.py sistema/tests/test_insight_engine.py
git commit -m "feat(ai): adicionar insight engine base com regras e ranking"
```

### Task 2: Endpoint de insights + feedback

**Files:**
- Modify: `sistema/app/routers/ai_hub.py`
- Test: `sistema/tests/test_ai_assistente_contract.py`

- [ ] **Step 1: Write failing tests for `GET /api/v1/ai/insights` and feedback endpoint**

```python
# sistema/tests/test_ai_assistente_contract.py
def test_get_insights_retorna_lista(client, token_headers):
    r = client.get("/api/v1/ai/insights", headers=token_headers)
    assert r.status_code == 200
    payload = r.json()
    assert "insights" in payload
    assert "total" in payload


def test_post_insights_feedback_aceita_payload(client, token_headers):
    r = client.post(
        "/api/v1/ai/insights/feedback",
        headers=token_headers,
        json={"insight_id": "abc123", "acao": "dispensou", "sessao_id": "sess-1"},
    )
    assert r.status_code == 200
    assert r.json().get("ok") is True
```

- [ ] **Step 2: Run tests and confirm fail (404 endpoints)**

Run: `cd sistema && pytest tests/test_ai_assistente_contract.py -q`
Expected: FAIL com status `404` nos endpoints novos.

- [ ] **Step 3: Implement schemas and routes in ai_hub router**

```python
# trecho em sistema/app/routers/ai_hub.py
from app.services.insight_engine import InsightEngine


class AIInsightsFeedbackRequest(BaseModel):
    insight_id: str = Field(min_length=4, max_length=120)
    acao: Literal["clicou", "executou", "dispensou", "ignorado"]
    sessao_id: str = Field(min_length=3, max_length=120)


@router.get("/insights")
async def listar_insights(
    limit: int = Query(default=5, ge=1, le=10),
    dominio: Optional[Literal["orcamentos", "financeiro", "clientes", "comercial", "agendamentos"]] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    engine = InsightEngine()
    snapshot = {"orcamentos": [], "financeiro": {}}
    contexto = {"dominio": dominio} if dominio else {}
    insights = engine.build_for_empresa(
        empresa_id=current_user.empresa_id,
        contexto=contexto,
        snapshot=snapshot,
    )
    if dominio:
        insights = [i for i in insights if i.get("dominio") == dominio]
    return {
        "insights": insights[:limit],
        "total": len(insights),
        "cache": {"hit": False},
    }


@router.post("/insights/feedback")
async def registrar_feedback_insight(
    request: AIInsightsFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    logger.info(
        "[ai_insights_feedback] empresa=%s usuario=%s insight=%s acao=%s sessao=%s",
        current_user.empresa_id,
        current_user.id,
        request.insight_id,
        request.acao,
        request.sessao_id,
    )
    return {"ok": True}
```

- [ ] **Step 4: Re-run tests**

Run: `cd sistema && pytest tests/test_ai_assistente_contract.py -q`
Expected: PASS nos dois cenarios novos.

- [ ] **Step 5: Commit**

```bash
git add sistema/app/routers/ai_hub.py sistema/tests/test_ai_assistente_contract.py
git commit -m "feat(ai): expor endpoint de insights e feedback"
```

### Task 3: Injecao de insights no assistente durante conversa

**Files:**
- Modify: `sistema/app/services/cotte_ai_hub.py`
- Modify: `sistema/tests/test_assistente_unificado_v2.py`

- [ ] **Step 1: Add failing test for `insights` in assistente response**

```python
# trecho em sistema/tests/test_assistente_unificado_v2.py
def test_v2_retorna_insights_contextuais(db, monkeypatch):
    from app.services.insight_engine import InsightEngine

    emp = make_empresa(db)
    user = make_usuario(db, emp)

    async def fake_chat(messages, tools=None, **kw):
        return _fake_response(content="Resposta com contexto de orçamento", finish="stop")

    def fake_build_for_empresa(self, *, empresa_id, contexto, snapshot):
        return [
            {
                "id": "i-1",
                "tipo": "acao_sugerida",
                "prioridade": "alta",
                "dominio": "orcamentos",
                "titulo": "Follow-up",
                "descricao": "Teste",
                "acao": {"tipo": "executar_prompt", "prompt": "fazer follow-up"},
                "contexto": {},
                "score": 0.8,
                "fonte": "regra",
                "expira_em": "2099-01-01T00:00:00+00:00",
            }
        ]

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)
    monkeypatch.setattr(InsightEngine, "build_for_empresa", fake_build_for_empresa)

    out = _run(
        cotte_ai_hub.assistente_unificado_v2(
            mensagem="ver orçamento pendente",
            sessao_id="sess-insights-1",
            db=db,
            current_user=user,
        )
    )

    assert out.sucesso is True
    assert isinstance(out.dados, dict)
    assert isinstance(out.dados.get("insights"), list)
    assert out.dados["insights"][0]["dominio"] == "orcamentos"
```

- [ ] **Step 2: Run test and confirm fail**

Run: `cd sistema && pytest tests/test_assistente_unificado_v2.py::test_v2_retorna_insights_contextuais -q`
Expected: FAIL porque `dados.insights` ainda nao existe.

- [ ] **Step 3: Implement insight injection in assistente_unificado_v2**

```python
# trecho em sistema/app/services/cotte_ai_hub.py (perto da montagem de AIResponse final)
from app.services.insight_engine import InsightEngine


def _infer_domain_from_message(mensagem: str) -> str:
    low = (mensagem or "").lower()
    if "orc" in low or "orçamento" in low or "orcamento" in low:
        return "orcamentos"
    if "finance" in low or "caixa" in low or "inadimpl" in low:
        return "financeiro"
    if "cliente" in low:
        return "clientes"
    if "lead" in low or "pipeline" in low or "comercial" in low:
        return "comercial"
    if "agenda" in low or "agendamento" in low:
        return "agendamentos"
    return "orcamentos"


# na finalizacao da resposta
dominio = _infer_domain_from_message(mensagem)
engine = InsightEngine()
insights_ctx = engine.build_for_empresa(
    empresa_id=getattr(current_user, "empresa_id", 0),
    contexto={"dominio": dominio},
    snapshot={"orcamentos": [], "financeiro": {}},
)
resp_dados = {**(resp_dados or {}), "insights": insights_ctx[:3]}
```

- [ ] **Step 4: Re-run targeted and broader tests**

Run: `cd sistema && pytest tests/test_assistente_unificado_v2.py::test_v2_retorna_insights_contextuais -q`
Expected: PASS.

Run: `cd sistema && pytest tests/test_assistente_unificado_v2.py -q`
Expected: PASS sem regressao.

- [ ] **Step 5: Commit**

```bash
git add sistema/app/services/cotte_ai_hub.py sistema/tests/test_assistente_unificado_v2.py
git commit -m "feat(ai): injetar insights contextuais no fluxo assistente v2"
```

### Task 4: Frontend de insights na abertura e durante conversa

**Files:**
- Create: `sistema/cotte-frontend/js/assistente-ia-insights.js`
- Modify: `sistema/cotte-frontend/assistente-ia.html`
- Modify: `sistema/cotte-frontend/js/assistente-ia.js`
- Modify: `sistema/cotte-frontend/css/assistente-ia.css`

- [ ] **Step 1: Add failing frontend integration test stub (or manual checklist file) before implementation**

```markdown
<!-- criar checklist em docs de QA rapido -->
# sistema/cotte-frontend/docs/qa-insights-manual.md
- [ ] Abrir assistente exibe até 5 insights no topo
- [ ] Clique em insight preenche input com prompt
- [ ] Dismiss remove card e envia feedback
- [ ] Resposta do chat com insights mostra quick replies
```

- [ ] **Step 2: Implement insights loader/render module**

```javascript
// sistema/cotte-frontend/js/assistente-ia-insights.js
(function () {
  const state = { loaded: false, dismissed: new Set() };

  async function fetchInsights(limit = 5) {
    const api = window.ApiService || window.api;
    if (!api || typeof api.get !== "function") return [];
    const res = await api.get(`/ai/insights?limit=${limit}`);
    return Array.isArray(res?.insights) ? res.insights : [];
  }

  function renderInsights(container, insights) {
    if (!container) return;
    container.innerHTML = "";
    insights.forEach((i) => {
      if (state.dismissed.has(i.id)) return;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "assistente-insight-chip";
      btn.textContent = i.titulo || "Sugestão";
      btn.addEventListener("click", () => {
        const input = document.getElementById("messageInput");
        if (input && i?.acao?.prompt) input.value = i.acao.prompt;
      });
      container.appendChild(btn);
    });
  }

  async function initInsights() {
    if (state.loaded) return;
    state.loaded = true;
    const host = document.getElementById("assistenteInsightsHost");
    if (!host) return;
    const insights = await fetchInsights(5);
    renderInsights(host, insights);
  }

  window.AssistenteInsights = { initInsights, renderInsights };
})();
```

- [ ] **Step 3: Wire HTML slot + script include + chat hook**

```html
<!-- trecho em sistema/cotte-frontend/assistente-ia.html -->
<div id="assistenteInsightsHost" class="assistente-insights-host" aria-live="polite"></div>
<script src="js/assistente-ia-insights.js?v=1"></script>
```

```javascript
// trecho em sistema/cotte-frontend/js/assistente-ia.js
document.addEventListener("DOMContentLoaded", function () {
  if (window.AssistenteInsights?.initInsights) {
    window.AssistenteInsights.initInsights();
  }
});

function renderInsightsFromResponse(payload) {
  const host = document.getElementById("assistenteInsightsHost");
  if (!host || !window.AssistenteInsights?.renderInsights) return;
  const insights = Array.isArray(payload?.insights) ? payload.insights : [];
  if (insights.length) window.AssistenteInsights.renderInsights(host, insights.slice(0, 3));
}
```

```css
/* trecho em sistema/cotte-frontend/css/assistente-ia.css */
.assistente-insights-host { display:flex; flex-wrap:wrap; gap:8px; margin:8px 0 10px; }
.assistente-insight-chip { border:1px solid var(--line); background:var(--bg-panel); color:var(--text); border-radius:999px; padding:6px 10px; font-size:12px; cursor:pointer; }
.assistente-insight-chip:hover { border-color: var(--primary); }
```

- [ ] **Step 4: Manual validation**

Run app local e validar checklist:
- abertura carrega insights
- clique injeta prompt no textarea
- insights durante conversa atualizam lista

Expected: fluxo sem quebra visual no desktop e mobile.

- [ ] **Step 5: Commit**

```bash
git add sistema/cotte-frontend/assistente-ia.html sistema/cotte-frontend/js/assistente-ia.js sistema/cotte-frontend/js/assistente-ia-insights.js sistema/cotte-frontend/css/assistente-ia.css sistema/cotte-frontend/docs/qa-insights-manual.md
git commit -m "feat(frontend): renderizar insights proativos no assistente"
```

### Task 5: Observabilidade, hardening e regressao final

**Files:**
- Modify: `sistema/app/services/insight_engine.py`
- Modify: `sistema/app/routers/ai_hub.py`
- Test: `sistema/tests/test_insight_engine.py`

- [ ] **Step 1: Add failing tests for dedupe/cooldown behavior**

```python
def test_dedupe_by_id_keeps_single_item():
    engine = InsightEngine()
    items = [
        {"id": "x", "score": 0.8, "prioridade": "alta"},
        {"id": "x", "score": 0.9, "prioridade": "critica"},
    ]
    out = engine.dedupe(items)
    assert len(out) == 1
    assert out[0]["id"] == "x"


def test_limit_is_applied_after_sorting():
    engine = InsightEngine()
    out = engine.limit([
        {"id": "a", "score": 0.2},
        {"id": "b", "score": 0.9},
        {"id": "c", "score": 0.6},
    ], 2)
    assert [x["id"] for x in out] == ["b", "c"]
```

- [ ] **Step 2: Run tests and confirm fail**

Run: `cd sistema && pytest tests/test_insight_engine.py -q`
Expected: FAIL por metodos ausentes `dedupe`/`limit`.

- [ ] **Step 3: Implement dedupe/limit and structured logging**

```python
# trecho em sistema/app/services/insight_engine.py
def dedupe(self, insights: list[dict]) -> list[dict]:
    best = {}
    for i in insights:
        k = i.get("id")
        if not k:
            continue
        cur = best.get(k)
        if (cur is None) or (i.get("score", 0) > cur.get("score", 0)):
            best[k] = i
    return list(best.values())


def limit(self, insights: list[dict], n: int) -> list[dict]:
    return sorted(insights, key=lambda x: x.get("score", 0), reverse=True)[:n]
```

```python
# trecho em sistema/app/routers/ai_hub.py dentro de listar_insights
logger.info(
    "[ai_insights] empresa=%s total=%s retornados=%s dominio=%s",
    current_user.empresa_id,
    len(insights),
    min(limit, len(insights)),
    dominio,
)
```

- [ ] **Step 4: Run full regression set for changed scope**

Run: `cd sistema && pytest tests/test_insight_engine.py tests/test_assistente_unificado_v2.py tests/test_ai_assistente_contract.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sistema/app/services/insight_engine.py sistema/app/routers/ai_hub.py sistema/tests/test_insight_engine.py
git commit -m "chore(ai): hardening de insights com dedupe, limite e telemetria"
```

## Checklist final de rollout tecnico

- [ ] Garantir que `insights` e opcional no contrato e nao quebra consumidores atuais.
- [ ] Validar desktop/mobile na tela `sistema/cotte-frontend/assistente-ia.html`.
- [ ] Revisar logs para confirmar volume de sugestoes aceitavel.
- [ ] Habilitar gradualmente por flag se necessario (empresa piloto).
