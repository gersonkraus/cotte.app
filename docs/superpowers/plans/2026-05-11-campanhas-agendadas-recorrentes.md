# Campanhas Agendadas e Recorrentes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que operadores programem campanhas para enviar automaticamente em data/hora definida, com opção de recorrência diária ou semanal (ex: restaurante enviando cardápio todo dia às 8h).

**Architecture:** Três campos são adicionados ao modelo `TenantCommercialCampaign` (`data_agendamento`, `recorrencia`, `ultima_execucao`). Um loop asyncio em `main.py` verifica a cada 60 segundos se há campanhas "agendadas" com `data_agendamento <= now()` e as dispara automaticamente. Para campanhas recorrentes, após a conclusão do disparo o sistema reinicia a campanha com a próxima data calculada — a entrada na tabela permanece única e se auto-renova.

**Tech Stack:** FastAPI BackgroundTasks + asyncio.create_task (mesmo padrão do ML sync), SQLAlchemy sync sessions, Alembic migration, HTML datetime-local input + Vanilla JS.

---

## Contexto

O módulo de campanhas em `tenant-comercial.html` já tem UI premium e disparo manual funcional. Falta apenas:
1. Campos de agendamento no modelo/schema
2. Loop de verificação periódica no backend
3. Lógica de reinício para recorrência (reset dos CampaignLeads + nova data)
4. UI de programação no modal de criação

---

## Arquivos Envolvidos

| Ação | Arquivo |
|------|---------|
| Modificar | `sistema/app/models/models.py:1528-1546` — TenantCommercialCampaign |
| Criar | `sistema/alembic/versions/z028_campanha_agendamento.py` |
| Modificar | `sistema/app/schemas/schemas.py:1758-1793` — CampaignCreate, CampaignOut |
| Modificar | `sistema/app/routers/tenant/comercial_campaigns.py:218-367` — _executar_disparo_background |
| Modificar | `sistema/app/main.py` — startup_event, adicionar loop |
| Modificar | `sistema/cotte-frontend/tenant-comercial.html:742-757` — modal campanha |
| Modificar | `sistema/cotte-frontend/js/tenant-comercial.js:2771-2799, 3042-3087` — render + salvar |

---

## Task 1: Modelo DB + Migration

**Files:**
- Modify: `sistema/app/models/models.py:1528-1546`
- Create: `sistema/alembic/versions/z028_campanha_agendamento.py`

- [ ] **Step 1: Adicionar campos ao modelo TenantCommercialCampaign**

Em `models.py`, após a linha `atualizado_em = Column(...)` (linha ~1546) e antes de `empresa = relationship(...)`:

```python
# Scheduling
data_agendamento = Column(DateTime(timezone=True), nullable=True)
recorrencia = Column(String(20), nullable=False, default="nenhuma")  # nenhuma/diario/semanal
ultima_execucao = Column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 2: Criar migration Alembic**

Criar `sistema/alembic/versions/z028_campanha_agendamento.py`:

```python
"""add scheduling fields to tenant_commercial_campaigns

Revision ID: z028
Revises: z027_forma_pagamento_exibir_no_whatsapp
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa

revision = "z028"
down_revision = "z027_forma_pagamento_exibir_no_whatsapp"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "tenant_commercial_campaigns",
        sa.Column("data_agendamento", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tenant_commercial_campaigns",
        sa.Column("recorrencia", sa.String(20), nullable=False, server_default="nenhuma"),
    )
    op.add_column(
        "tenant_commercial_campaigns",
        sa.Column("ultima_execucao", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("tenant_commercial_campaigns", "ultima_execucao")
    op.drop_column("tenant_commercial_campaigns", "recorrencia")
    op.drop_column("tenant_commercial_campaigns", "data_agendamento")
```

- [ ] **Step 3: Verificar o down_revision correto**

```bash
cd /home/gk/Projeto-izi/sistema
python -c "from alembic.config import Config; from alembic import command; c=Config('alembic.ini'); command.current(c, verbose=True)"
```

Confirmar que o `down_revision` no arquivo bate com o head atual. Ajustar se necessário.

- [ ] **Step 4: Commit parcial**

```bash
git add sistema/app/models/models.py sistema/alembic/versions/z028_campanha_agendamento.py
git commit -m "feat(campanhas): adiciona campos data_agendamento, recorrencia e ultima_execucao ao modelo TenantCommercialCampaign"
```

---

## Task 2: Schemas Pydantic

**Files:**
- Modify: `sistema/app/schemas/schemas.py:1758-1793`

- [ ] **Step 1: Atualizar CampaignCreate para aceitar campos de agendamento**

Substituir o bloco `CampaignCreate` (linha ~1758):

```python
class CampaignCreate(BaseModel):
    """Criação de campanha de disparo."""

    nome: str
    template_id: int
    canal: str = Field(..., description="Canal: whatsapp, email ou ambos")
    lead_ids: List[int] = Field(..., description="IDs dos leads para disparo")
    data_agendamento: Optional[datetime] = Field(None, description="Data/hora UTC do envio agendado")
    recorrencia: str = Field("nenhuma", description="nenhuma | diario | semanal")
```

- [ ] **Step 2: Atualizar CampaignOut para expor campos de agendamento**

Adicionar aos campos de `CampaignOut` (após `respondidos`):

```python
data_agendamento: Optional[datetime] = None
recorrencia: str = "nenhuma"
ultima_execucao: Optional[datetime] = None
```

- [ ] **Step 3: Commit**

```bash
git add sistema/app/schemas/schemas.py
git commit -m "feat(campanhas): schema CampaignCreate e CampaignOut agora suportam data_agendamento e recorrencia"
```

---

## Task 3: Router — Criar campanha com agendamento + lógica de recorrência no disparo

**Files:**
- Modify: `sistema/app/routers/tenant/comercial_campaigns.py`

- [ ] **Step 1: Aplicar data_agendamento e recorrencia ao criar campanha**

Na função `create_campaign` (linha ~86), ao criar o objeto `TenantCommercialCampaign`, adicionar:

```python
campaign = TenantCommercialCampaign(
    empresa_id=current_user.empresa_id,
    nome=request.nome,
    template_id=request.template_id,
    canal=request.canal,
    status="agendada",
    total_leads=len(request.lead_ids),
    data_agendamento=request.data_agendamento,
    recorrencia=request.recorrencia or "nenhuma",
)
```

- [ ] **Step 2: Adicionar helper de cálculo de próxima data**

Logo após os imports e dicts `_running_campaigns`/`_campaign_start_times` (linha ~10), adicionar:

```python
from datetime import timedelta

def _proximo_agendamento(data_atual: datetime, recorrencia: str) -> datetime | None:
    if recorrencia == "diario":
        return data_atual + timedelta(days=1)
    if recorrencia == "semanal":
        return data_atual + timedelta(weeks=1)
    return None
```

- [ ] **Step 3: Adicionar lógica de recorrência ao final de _executar_disparo_background**

Localizar o bloco (linha ~355-360):
```python
if _running_campaigns.get(campaign_id) is False:
    campaign.status = "cancelada"
else:
    campaign.status = "concluida"
campaign.atualizado_em = datetime.now()
db.commit()
```

Substituir por:
```python
if _running_campaigns.get(campaign_id) is False:
    campaign.status = "cancelada"
    campaign.atualizado_em = datetime.now()
    db.commit()
else:
    # Recorrência: reiniciar campanha se configurada
    proxima = None
    if campaign.recorrencia and campaign.recorrencia != "nenhuma" and campaign.data_agendamento:
        proxima = _proximo_agendamento(campaign.data_agendamento, campaign.recorrencia)

    if proxima:
        # Resetar leads para próxima execução
        db.query(TenantCampaignLead).filter(
            TenantCampaignLead.campaign_id == campaign.id
        ).update({"status": "pendente", "data_envio": None, "data_entrega": None, "data_resposta": None})
        campaign.ultima_execucao = datetime.now()
        campaign.data_agendamento = proxima
        campaign.enviados = 0
        campaign.entregues = 0
        campaign.respondidos = 0
        campaign.status = "agendada"
        campaign.atualizado_em = datetime.now()
        db.commit()
        logger.info(f"Campanha recorrente {campaign_id} reagendada para {proxima}")
    else:
        campaign.status = "concluida"
        campaign.atualizado_em = datetime.now()
        db.commit()
```

- [ ] **Step 4: Commit**

```bash
git add sistema/app/routers/tenant/comercial_campaigns.py
git commit -m "feat(campanhas): suporte a agendamento no create + lógica de auto-renovação para recorrência diária/semanal"
```

---

## Task 4: Loop de Verificação Periódica em main.py

**Files:**
- Modify: `sistema/app/main.py`

- [ ] **Step 1: Adicionar função _start_scheduled_campaigns_loop em main.py**

Após a função `_start_ml_periodic_sync_loop` (linha ~520), adicionar:

```python
async def _start_scheduled_campaigns_loop():
    """Verifica a cada 60s se há campanhas agendadas para disparar."""

    async def _runner():
        import asyncio
        from app.core.database import SessionLocal
        from app.models.models import TenantCommercialCampaign
        from app.routers.tenant.comercial_campaigns import (
            _executar_disparo_background,
            _running_campaigns,
        )

        while True:
            await asyncio.sleep(60)
            db = SessionLocal()
            try:
                now = datetime.utcnow()
                campanhas_devidas = (
                    db.query(TenantCommercialCampaign)
                    .filter(
                        TenantCommercialCampaign.status == "agendada",
                        TenantCommercialCampaign.data_agendamento.isnot(None),
                        TenantCommercialCampaign.data_agendamento <= now,
                    )
                    .all()
                )
                for campaign in campanhas_devidas:
                    if campaign.id not in _running_campaigns:
                        asyncio.create_task(
                            _executar_disparo_background(
                                campaign.id,
                                [],   # lista vazia = todos os leads da campanha
                                None,  # canal do próprio registro
                                campaign.empresa_id,
                            )
                        )
                        logging.info(
                            "Disparo automático iniciado para campanha %s (%s)",
                            campaign.id,
                            campaign.nome,
                        )
            except Exception as exc:
                logging.error("Loop de campanhas agendadas falhou: %s", exc)
            finally:
                db.close()

    asyncio.create_task(_runner())
    logging.info("Loop de campanhas agendadas iniciado (intervalo=60s).")
```

- [ ] **Step 2: Chamar a função no startup_event de main.py**

Localizar o bloco de startup (onde `_start_ml_periodic_sync_loop()` é chamado) e adicionar logo abaixo:

```python
await _start_scheduled_campaigns_loop()
```

- [ ] **Step 3: Garantir import de datetime no topo de main.py**

Verificar se `from datetime import datetime` já existe. Se não, adicionar.

- [ ] **Step 4: Commit**

```bash
git add sistema/app/main.py
git commit -m "feat(campanhas): loop asyncio para disparo automático de campanhas agendadas (intervalo 60s)"
```

---

## Task 5: Frontend HTML — Seção de Agendamento no Modal

**Files:**
- Modify: `sistema/cotte-frontend/tenant-comercial.html:742-757`

- [ ] **Step 1: Adicionar seção de agendamento entre config-bar e audience-builder**

Localizar o fechamento da `camp-config-bar` (linha ~757, `</div>`) e ANTES da div `camp-audience` (linha ~759), inserir:

```html
<!-- Agendamento Automático -->
<div class="camp-config-bar camp-schedule-section" style="border-top:1px solid rgba(255,255,255,.1);padding-top:12px;gap:10px;flex-wrap:wrap;align-items:flex-start">
  <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;color:rgba(255,255,255,.85);white-space:nowrap;padding-top:4px">
    <input type="checkbox" id="camp-agendar" style="width:16px;height:16px;cursor:pointer">
    📅 Programar envio automático
  </label>
  <div id="camp-agendamento-opts" style="display:none;display:flex;gap:12px;flex:1;flex-wrap:wrap">
    <div class="camp-config-group" style="flex:1;min-width:180px">
      <label class="camp-config-label">Data e hora *</label>
      <input type="datetime-local" class="camp-config-select" id="camp-data-agendamento" style="padding:7px 10px">
    </div>
    <div class="camp-config-group" style="min-width:160px">
      <label class="camp-config-label">🔁 Repetir</label>
      <select class="camp-config-select" id="camp-recorrencia">
        <option value="nenhuma">Não repetir</option>
        <option value="diario">Todo dia (mesmo horário)</option>
        <option value="semanal">Toda semana</option>
      </select>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Verificar que o HTML está bem formado (sem tags abertas)**

```bash
python3 -c "
from html.parser import HTMLParser
class V(HTMLParser): pass
v=V()
with open('sistema/cotte-frontend/tenant-comercial.html') as f: v.feed(f.read())
print('OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add sistema/cotte-frontend/tenant-comercial.html
git commit -m "feat(campanhas): adiciona seção de agendamento automático no modal de criação de campanha"
```

---

## Task 6: Frontend JS — salvarCampanha + render com dados de agendamento

**Files:**
- Modify: `sistema/cotte-frontend/js/tenant-comercial.js:2771-2799, 3042-3087, 2836-2841`

- [ ] **Step 1: Adicionar toggle do painel de agendamento**

No DOMContentLoaded (procurar onde `btn-nova-campanha` é bound, linha ~3189), adicionar listener para o checkbox:

```javascript
document.getElementById('camp-agendar')?.addEventListener('change', function() {
  var opts = document.getElementById('camp-agendamento-opts');
  if (opts) opts.style.display = this.checked ? 'flex' : 'none';
  if (!this.checked) {
    var dtInput = document.getElementById('camp-data-agendamento');
    if (dtInput) dtInput.value = '';
    var recInput = document.getElementById('camp-recorrencia');
    if (recInput) recInput.value = 'nenhuma';
  }
});
```

- [ ] **Step 2: Atualizar salvarCampanha para enviar campos de agendamento**

Na função `salvarCampanha()` (linha ~3042), localizar onde `body` é montado (linha ~3072):

```javascript
var body = { nome: nome, template_id: parseInt(templateId), canal: canal, lead_ids: leadIds };
```

Substituir por:

```javascript
var body = { nome: nome, template_id: parseInt(templateId), canal: canal, lead_ids: leadIds, recorrencia: 'nenhuma', data_agendamento: null };

var agendarChecked = document.getElementById('camp-agendar')?.checked;
if (agendarChecked) {
  var dtVal = document.getElementById('camp-data-agendamento')?.value;
  if (!dtVal) {
    _showCampError('Informe a data e hora do envio agendado.');
    if (btnSalvar) { btnSalvar.disabled = false; btnSalvar.innerHTML = btnOrigHtml; }
    return;
  }
  // Converter datetime-local (hora local) para ISO UTC
  body.data_agendamento = new Date(dtVal).toISOString();
  body.recorrencia = document.getElementById('camp-recorrencia')?.value || 'nenhuma';
}
```

- [ ] **Step 3: Resetar campos de agendamento ao abrir modal de nova campanha**

Localizar o bloco de reset do modal (linha ~2836):

```javascript
document.getElementById('camp-id').value = '';
document.getElementById('camp-nome').value = '';
// ...
```

Adicionar ao final desse bloco:

```javascript
var agendarEl = document.getElementById('camp-agendar');
if (agendarEl) { agendarEl.checked = false; }
var agOpts = document.getElementById('camp-agendamento-opts');
if (agOpts) { agOpts.style.display = 'none'; }
var dtAgend = document.getElementById('camp-data-agendamento');
if (dtAgend) { dtAgend.value = ''; }
var recEl = document.getElementById('camp-recorrencia');
if (recEl) { recEl.value = 'nenhuma'; }
```

- [ ] **Step 4: Exibir informação de agendamento na listagem de campanhas**

Na função `renderCampanhasTable` (linha ~2779), substituir a linha onde o nome é renderizado:

De:
```javascript
'<td>' + escapeHtml(c.nome) + '</td>' +
```

Para:
```javascript
'<td>' + escapeHtml(c.nome) +
  (c.recorrencia && c.recorrencia !== 'nenhuma' ? ' <span style="font-size:11px;color:var(--muted)">🔁 ' + (c.recorrencia === 'diario' ? 'Diária' : 'Semanal') + '</span>' : '') +
  (c.data_agendamento && c.status === 'agendada' ? '<br><small style="color:var(--muted)">📅 ' + new Date(c.data_agendamento).toLocaleString('pt-BR', {day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}) + '</small>' : '') +
'</td>' +
```

- [ ] **Step 5: Fazer o mesmo para a versão mobile (renderCampanhasMobile, linha ~2812)**

Localizar:
```javascript
'<div class="crud-mobile-card-title">' + escapeHtml(c.nome) + '</div>' +
```

Substituir por:
```javascript
'<div class="crud-mobile-card-title">' + escapeHtml(c.nome) +
  (c.recorrencia && c.recorrencia !== 'nenhuma' ? ' <span style="font-size:11px">🔁</span>' : '') +
'</div>' +
(c.data_agendamento && c.status === 'agendada' ? '<div style="font-size:12px;color:var(--muted)">📅 ' + new Date(c.data_agendamento).toLocaleString('pt-BR', {day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}) + '</div>' : '') +
```

- [ ] **Step 6: Commit**

```bash
git add sistema/cotte-frontend/js/tenant-comercial.js
git commit -m "feat(campanhas): UI de agendamento — toggle, envio com data/recorrência, exibição na lista"
```

---

## Task 7: Deploy e Verificação End-to-End

- [ ] **Step 1: Rodar migration localmente (se ambiente disponível)**

```bash
cd /home/gk/Projeto-izi/sistema
alembic upgrade head
```

Esperado: `Running upgrade ... -> z028, add scheduling fields to tenant_commercial_campaigns`

- [ ] **Step 2: Fazer deploy no Railway**

```bash
git push origin main
```

Verificar no Railway dashboard que o build passa e a migration roda automaticamente (via `release.sh`).

- [ ] **Step 3: Teste manual — campanha agendada para +2 minutos**

1. Abrir `tenant-comercial.html` → aba Campanhas → "Nova Campanha"
2. Preencher: nome, template, canal WhatsApp, selecionar 1 lead de teste
3. Marcar "📅 Programar envio automático"
4. Definir data/hora = agora + 2 minutos
5. Recorrência = "Não repetir"
6. Clicar "Criar Campanha"
7. Verificar: campanha aparece na lista com status "Agendada" e a data informada
8. Aguardar o loop (máx 60s após o horário definido)
9. Verificar: status muda para "Em Andamento" → "Concluída" sem clique manual
10. Verificar que a mensagem chegou no WhatsApp do lead de teste

- [ ] **Step 4: Teste de recorrência diária**

1. Criar campanha agendada para +2 minutos com recorrência = "Todo dia"
2. Aguardar disparo automático
3. Após conclusão, verificar: status volta a "Agendada", `data_agendamento` = +24h, `ultima_execucao` = agora
4. Verificar que todos os `TenantCampaignLead.status` voltaram para "pendente"

- [ ] **Step 5: Verificar via Railway logs**

```bash
railway logs --tail
```

Procurar por:
```
INFO: Loop de campanhas agendadas iniciado (intervalo=60s).
INFO: Disparo automático iniciado para campanha X (Nome da Campanha)
INFO: Campanha recorrente X reagendada para YYYY-MM-DD HH:MM:SS
```

---

## Notas de Implementação

- **Timezone**: O campo `data_agendamento` é `DateTime(timezone=True)` no Postgres. O frontend converte `datetime-local` → `new Date(val).toISOString()` (UTC). O loop em `main.py` compara com `datetime.utcnow()`. Consistência garantida.
- **Anti-colisão**: O dict `_running_campaigns` (já existente) garante que o loop não dispara uma campanha que já está sendo processada.
- **Campanha manual**: O botão "🚀 Disparar" continua funcionando para disparar imediatamente campanhas agendadas (útil se o operador quiser antecipar).
- **Sem novo arquivo JS**: Todo o código vai em `tenant-comercial.js` (já carregado) — o arquivo `tenant-comercial-campanhas.js` existe mas não está no HTML e não deve ser tocado nesta tarefa.
- **down_revision**: Verificar o valor correto na Task 1 Step 3 antes de usar a migration — o valor no plano é baseado no último arquivo encontrado (`z027_*`).
