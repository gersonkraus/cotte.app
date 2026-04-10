"""
Router unificado para COTTE AI Hub
Exposto em /api/v1/ai/{modulo}
"""

import uuid as _uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Literal
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.services.cotte_ai_hub import ai_hub, AIResponse
from app.core.auth import get_usuario_atual as get_current_user, exigir_permissao, exigir_modulo
from app.models.models import Usuario, HistoricoEdicao, Empresa

router = APIRouter(prefix="/ai", tags=["AI"], dependencies=[Depends(exigir_modulo("ia"))])


# ── Schemas de Requisição ───────────────────────────────────────────────────


class AIProcessRequest(BaseModel):
    """Requisição para processamento de IA"""

    mensagem: str = Field(
        ..., min_length=1, max_length=1000, description="Mensagem em linguagem natural"
    )
    contexto: Optional[dict] = Field(
        default=None, description="Dados adicionais para contextualização"
    )
    usar_cache: bool = Field(
        default=True, description="Se deve usar cache de resultados"
    )
    confianca_minima: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confiança mínima aceitável"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "mensagem": "Orçamento de pintura 800 reais para João da Silva",
                "contexto": {"empresa_id": 1},
                "usar_cache": True,
                "confianca_minima": 0.5,
            }
        }


class AIConversarRequest(BaseModel):
    """Requisição para conversação com IA"""

    mensagem: str = Field(..., min_length=1, max_length=500)
    historico: Optional[list] = Field(
        default=None, description="Histórico de mensagens (opcional)"
    )


class AIMensagemRequest(BaseModel):
    """Requisição simples com mensagem para endpoints de análise"""

    mensagem: str = Field(
        ..., min_length=1, max_length=1000, description="Mensagem em linguagem natural"
    )

    class Config:
        json_schema_extra = {"example": {"mensagem": "Qual o saldo futuro do caixa?"}}


class AIAssistenteRequest(BaseModel):
    """Requisição para o assistente universal com suporte a histórico de sessão."""

    mensagem: str = Field(
        ..., min_length=1, max_length=1000, description="Mensagem em linguagem natural"
    )
    sessao_id: str = Field(
        default_factory=lambda: str(_uuid.uuid4()),
        description="UUID de sessão para manter histórico. Gerado automaticamente se omitido.",
    )
    confirmation_token: Optional[str] = Field(
        default=None,
        description="Token de confirmação para executar uma ação destrutiva pendente (Tool Use v2).",
    )
    override_args: Optional[dict] = Field(
        default=None,
        description="Overrides opcionais aplicados sobre os args do pending (allowlisted por tool).",
    )


class AIConfirmarOrcamentoRequest(BaseModel):
    """Dados extraídos pela IA para criação do orçamento após confirmação do usuário."""

    cliente_id: Optional[int] = None
    cliente_nome: str = "A definir"
    servico: str
    valor: float
    desconto: float = 0.0
    desconto_tipo: str = "percentual"
    observacoes: Optional[str] = None


class AIStatusResponse(BaseModel):
    """Status do sistema de IA"""

    status: str
    modulos_disponiveis: list[str]
    cache_stats: dict
    versoes_modelos: dict


# ── Endpoints Principais ────────────────────────────────────────────────────

# NOTA: Endpoints específicos devem vir ANTES de /{modulo} para evitar conflito
# no FastAPI. A ordem de definição determina a ordem de matching das rotas.


@router.post("/conversar")
async def conversar_ia(
    request: AIConversarRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """
    Conversação livre com o assistente COTTE.
    Retorna texto simples (não estruturado).
    """
    from app.services.cotte_ai_hub import ai_hub

    # Incrementar contador de mensagens IA da empresa
    if current_user.empresa:
        current_user.empresa.total_mensagens_ia = (
            current_user.empresa.total_mensagens_ia or 0
        ) + 1
        db.commit()

    resposta = await ai_hub.conversar(
        mensagem=request.mensagem, contexto_conversa=request.historico
    )

    return {"resposta": resposta}


@router.get("/status", response_model=AIStatusResponse)
async def status_ia(current_user: Usuario = Depends(get_current_user)):
    """
    Retorna status do sistema de IA e estatísticas.
    """
    return AIStatusResponse(
        status="operacional",
        modulos_disponiveis=[
            "orcamentos",
            "clientes",
            "financeiro",
            "comercial",
            "operador",
            "conversacao",
        ],
        cache_stats={
            "ttl_segundos": 300,
            "nota": "Cache em memória - reinicia com o servidor",
        },
        versoes_modelos={
            "sonnet": "claude-sonnet-4-20250514",
            "haiku": "claude-haiku-4-5-20251001",
        },
    )


# ── Endpoint de Confirmação de Orçamento via IA ──────────────────────────


@router.post("/orcamento/confirmar", response_model=AIResponse)
async def confirmar_orcamento_ia(
    request: AIConfirmarOrcamentoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """
    Confirma e cria o orçamento no banco a partir dos dados extraídos pela IA.
    Chamado pelo frontend após o usuário revisar a prévia do orçamento.
    """
    from fastapi import BackgroundTasks
    from app.models.models import Cliente, Orcamento, ItemOrcamento, Empresa, ModoAgendamentoOrcamento
    from app.schemas.schemas import OrcamentoCreate, ItemOrcamentoCreate
    from app.routers.orcamentos import criar_orcamento as _criar_orcamento

    # Resolver cliente
    cliente_id = request.cliente_id
    if not cliente_id:
        nome_cliente = (request.cliente_nome or "").strip() or "A definir"
        cliente = (
            db.query(Cliente)
            .filter(
                Cliente.empresa_id == current_user.empresa_id,
                Cliente.nome == nome_cliente,
            )
            .first()
        )
        if not cliente:
            cliente = Cliente(empresa_id=current_user.empresa_id, nome=nome_cliente)
            db.add(cliente)
            db.flush()
        cliente_id = cliente.id

    empresa_ia = (
        db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    )
    agendamento_modo_ia: Optional[ModoAgendamentoOrcamento] = None
    if empresa_ia and getattr(empresa_ia, "agendamento_escolha_obrigatoria", False):
        # Fluxo automático por IA não passa pelo modal: assume sem agendamento até o operador ajustar.
        agendamento_modo_ia = ModoAgendamentoOrcamento.NAO_USA

    orc_data = OrcamentoCreate(
        cliente_id=cliente_id,
        itens=[
            ItemOrcamentoCreate(
                descricao=request.servico or "Serviço",
                quantidade=1.0,
                valor_unit=request.valor,
            )
        ],
        desconto=request.desconto,
        desconto_tipo=request.desconto_tipo,
        observacoes=request.observacoes,
        agendamento_modo=agendamento_modo_ia,
    )

    try:
        orc = await _criar_orcamento(
            dados=orc_data,
            background_tasks=BackgroundTasks(),
            db=db,
            usuario=current_user,
        )
        
        # Registro extra indicando origem IA
        db.add(
            HistoricoEdicao(
                orcamento_id=orc.id,
                editado_por_id=current_user.id,
                descricao="Orçamento rascunhado por IA e confirmado via Assistente.",
            )
        )
        db.commit()

        return AIResponse(
            sucesso=True,
            resposta=f"Orçamento {orc.numero} criado com sucesso!",
            tipo_resposta="orcamento_criado",
            dados={
                "numero": orc.numero, 
                "id": orc.id, 
                "total": float(orc.total or 0),
                "cliente_nome": orc.cliente.nome if getattr(orc, "cliente", None) else None,
                "servico": orc.itens[0].descricao if getattr(orc, "itens", None) and len(orc.itens) > 0 else "Serviços gerais",
                "desconto": float(orc.desconto or 0),
                "validade_dias": orc.validade_dias,
                "link_publico": orc.link_publico
            },
            confianca=1.0,
            modulo_origem="confirmar_orcamento",
        )
    except Exception as e:
        logger.error(f"[confirmar_orcamento_ia] Erro: {e}")
        return AIResponse(
            sucesso=False,
            resposta=f"Não foi possível criar o orçamento: {str(e)}",
            tipo_resposta="erro",
            confianca=0.0,
            erros=[str(e)],
            modulo_origem="confirmar_orcamento",
        )


# ── Endpoints Especializados (conveniência) ───────────────────────────────


@router.post("/orcamento/interpretar", response_model=AIResponse)
async def interpretar_orcamento_rapido(
    mensagem: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """
    Endpoint rápido para interpretar orçamentos (compatibilidade com frontend existente).
    """
    return await ai_hub.processar(
        modulo="orcamentos",
        mensagem=mensagem,
        db=db,
        usar_cache=True,
        confianca_minima=0.5,
    )


@router.post("/cliente/extrair", response_model=AIResponse)
async def extrair_cliente_ia(
    mensagem: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """
    Extrai dados de cliente de mensagem em linguagem natural.

    Exemplo: "Cadastrar João, telefone 11999999999, email joao@email.com"
    """
    return await ai_hub.processar(
        modulo="clientes",
        mensagem=mensagem,
        db=db,
        usar_cache=True,
        confianca_minima=0.6,
    )


@router.post("/financeiro/categorizar", response_model=AIResponse)
async def categorizar_transacao_ia(
    mensagem: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """
    Categoriza transação financeira de descrição em linguagem natural.

    Exemplo: "Gastei 500 com material de pintura ontem"
    """
    return await ai_hub.processar(
        modulo="financeiro",
        mensagem=mensagem,
        db=db,
        usar_cache=True,
        confianca_minima=0.5,
    )


@router.post("/comercial/qualificar", response_model=AIResponse)
async def qualificar_lead_ia(
    mensagem: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """
    Qualifica lead com base em descrição.

    Exemplo: "Cliente interessado em reforma completa, orçamento de 50 mil, quer começar mês que vem"
    """
    return await ai_hub.processar(
        modulo="comercial",
        mensagem=mensagem,
        db=db,
        usar_cache=True,
        confianca_minima=0.5,
    )


@router.post("/operador/comando", response_model=AIResponse)
async def interpretar_comando_ia(
    mensagem: str, current_user: Usuario = Depends(exigir_permissao("ia", "leitura"))
):
    """
    Interpreta comando de operador do sistema.

    Exemplo: "ver orçamento 5", "aprovar 3", "10% de desconto no 7"
    """
    return await ai_hub.processar(
        modulo="operador", mensagem=mensagem, usar_cache=True, confianca_minima=0.6
    )


# ── Endpoints Fase 1: Financeiro Inteligente ─────────────────────────────────


@router.post("/financeiro/analise", response_model=AIResponse)
async def analisar_financeiro_endpoint(
    request: AIMensagemRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """
    Analisa dados financeiros e fornece insights.

    Exemplos:
    - "Como estão as finanças deste mês?"
    - "Quanto recebi e paguei nos últimos 30 dias?"
    - "Qual meu saldo atual?"
    - "Análise do fluxo de caixa"
    """
    from app.services.cotte_ai_hub import analisar_financeiro_ia

    return await analisar_financeiro_ia(
        request.mensagem, db=db, empresa_id=current_user.empresa_id
    )


@router.post("/financeiro/dashboard", response_model=AIResponse)
async def dashboard_financeiro_endpoint(
    db: Session = Depends(get_db), current_user: Usuario = Depends(exigir_permissao("ia", "leitura"))
):
    """
    Gera dashboard financeiro completo com KPIs e insights.

    Responde automaticamente a: "Como estão as finanças?"
    """
    from app.services.cotte_ai_hub import dashboard_financeiro_ia

    return await dashboard_financeiro_ia(db=db, empresa_id=current_user.empresa_id)


@router.post("/financeiro/clientes-devendo", response_model=AIResponse)
async def clientes_devendo_endpoint(
    db: Session = Depends(get_db), current_user: Usuario = Depends(exigir_permissao("ia", "leitura"))
):
    """
    Lista clientes com contas em atraso.

    Responde automaticamente a: "Quais clientes estão devendo?"
    """
    from app.services.cotte_ai_hub import clientes_devendo_ia

    return await clientes_devendo_ia(db=db, empresa_id=current_user.empresa_id)


@router.post("/financeiro/previsao-caixa", response_model=AIResponse)
async def previsao_caixa_endpoint(
    dias: Optional[int] = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """
    Gera previsão de fluxo de caixa.

    Exemplos:
    - "Previsão de caixa para próximos 30 dias"
    - "Quanto vou receber/pagar?"
    - "Projeção financeira"
    """
    from app.services.cotte_ai_hub import previsao_caixa_ia

    return await previsao_caixa_ia(db=db, empresa_id=current_user.empresa_id)


@router.post("/financeiro/saldo", response_model=AIResponse)
async def saldo_rapido_endpoint(
    db: Session = Depends(get_db), current_user: Usuario = Depends(exigir_permissao("ia", "leitura"))
):
    """
    Retorna saldo atual de forma rápida e objetiva.

    Exemplos:
    - "caixa"
    - "saldo"
    - "quanto tenho"
    - "meu saldo"
    """
    from app.services.ai_intention_classifier import saldo_rapido_ia

    return await saldo_rapido_ia(db=db, empresa_id=current_user.empresa_id)


# ── Endpoints Fase 1: Análise de Conversão ───────────────────────────────────


@router.post("/conversao/analise", response_model=AIResponse)
async def analisar_conversao_endpoint(
    request: AIMensagemRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """
    Analisa taxas de conversão de orçamentos.

    Exemplos:
    - "Qual minha taxa de aprovação?"
    - "Quantos orçamentos foram aprovados este mês?"
    - "Análise de conversão"
    """
    from app.services.cotte_ai_hub import analisar_conversao_ia

    return await analisar_conversao_ia(request.mensagem, db=db, empresa_id=current_user.empresa_id)


@router.post("/conversao/ticket-medio", response_model=AIResponse)
async def ticket_medio_endpoint(
    db: Session = Depends(get_db), current_user: Usuario = Depends(exigir_permissao("ia", "leitura"))
):
    """
    Calcula e analisa ticket médio.

    Responde automaticamente a: "Qual meu ticket médio?"
    """
    from app.services.cotte_ai_hub import ticket_medio_ia

    return await ticket_medio_ia(db=db)


@router.post("/conversao/servico-mais-vendido", response_model=AIResponse)
async def servico_mais_vendido_endpoint(
    db: Session = Depends(get_db), current_user: Usuario = Depends(exigir_permissao("ia", "leitura"))
):
    """
    Identifica serviço mais vendido/procurado.

    Responde automaticamente a: "Qual serviço mais vendido?"
    """
    from app.services.cotte_ai_hub import servico_mais_vendido_ia

    return await servico_mais_vendido_ia(db=db)


# ── Endpoints Fase 1: Sugestões de Negócio ─────────────────────────────────


@router.post("/negocio/sugestoes", response_model=AIResponse)
async def gerar_sugestoes_negocio_endpoint(
    request: AIMensagemRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """
    Gera sugestões estratégicas para o negócio.

    Exemplos:
    - "Como posso aumentar minhas vendas?"
    - "Sugestões para melhorar o negócio"
    - "O que fazer para crescer?"
    """
    from app.services.cotte_ai_hub import gerar_sugestoes_negocio_ia

    return await gerar_sugestoes_negocio_ia(request.mensagem, db=db, empresa_id=current_user.empresa_id)


@router.post("/negocio/cliente-mais-lucrativo", response_model=AIResponse)
async def cliente_mais_lucrativo_endpoint(
    db: Session = Depends(get_db), current_user: Usuario = Depends(exigir_permissao("ia", "leitura"))
):
    """
    Identifica cliente mais lucrativo.

    Responde automaticamente a: "Qual cliente mais lucrativo?"
    """
    from app.services.cotte_ai_hub import cliente_mais_lucrativo_ia

    return await cliente_mais_lucrativo_ia(db=db)


@router.post("/negocio/sugestao-precos", response_model=AIResponse)
async def sugestao_precos_endpoint(
    servico: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """
    Sugere ajustes de preços.

    Exemplos:
    - "Sugerir aumento de preços para pintura"
    - "Revisar tabela de preços"
    - "Precos muito baixos?"
    """
    from app.services.cotte_ai_hub import sugestao_precos_ia

    return await sugestao_precos_ia(servico=servico, db=db)


# ── Endpoint Universal Fase 1 ───────────────────────────────────────────────


@router.post("/assistente/stream")
async def assistente_universal_stream(
    request: AIAssistenteRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    from app.services.cotte_ai_hub import assistente_unificado_stream
    from fastapi.responses import StreamingResponse

    if current_user.empresa:
        current_user.empresa.total_mensagens_ia = (
            current_user.empresa.total_mensagens_ia or 0
        ) + 1
        db.commit()

    return StreamingResponse(
        assistente_unificado_stream(
            mensagem=request.mensagem,
            sessao_id=request.sessao_id,
            db=db,
            current_user=current_user,
            confirmation_token=getattr(request, "confirmation_token", None),
            override_args=getattr(request, "override_args", None),
        ),
        media_type="text/event-stream"
    )


@router.post("/assistente", response_model=AIResponse)
async def assistente_universal(
    request: AIAssistenteRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """
    Endpoint universal do assistente COTTE.

    Único ponto de entrada para todas as perguntas do chat:
    - Mantém histórico de conversa por sessao_id (in-memory, TTL 60min)
    - Classifica intenção automaticamente (regex + Haiku fallback)
    - Injeta contexto de dados relevante (financeiro, orçamentos, clientes, leads)
    - Retorna JSON estruturado com resposta, tipo, dados e sugestões de follow-up
    """
    import os

    # Incrementar contador de mensagens IA da empresa
    if current_user.empresa:
        current_user.empresa.total_mensagens_ia = (
            current_user.empresa.total_mensagens_ia or 0
        ) + 1
        db.commit()

    # Assistente Unificado V2 (Tool Use nativo) — engine padrão
    # USE_TOOL_CALLING=false desativa apenas em emerência; o normal é sempre V2.
    if os.getenv("USE_TOOL_CALLING", "true").lower() != "false":
        from app.services.cotte_ai_hub import assistente_unificado_v2

        return await assistente_unificado_v2(
            mensagem=request.mensagem,
            sessao_id=request.sessao_id,
            db=db,
            current_user=current_user,
            confirmation_token=request.confirmation_token,
            override_args=request.override_args,
        )

    # Fallback legado (apenas quando USE_TOOL_CALLING=false)
    from app.services.cotte_ai_hub import assistente_unificado

    return await assistente_unificado(
        mensagem=request.mensagem,
        sessao_id=request.sessao_id,
        db=db,
        empresa_id=current_user.empresa_id,
        usuario_id=current_user.id,
        permissoes=current_user.permissoes or {},
        is_gestor=current_user.is_gestor,
    )


# ── Feedback do Assistente ───────────────────────────────────────────────


class AIFeedbackRequest(BaseModel):
    sessao_id: Optional[str] = None
    pergunta: str = Field(..., min_length=1, max_length=2000)
    resposta: str = Field(..., min_length=1, max_length=5000)
    avaliacao: str = Field(..., pattern="^(positivo|negativo)$")
    comentario: Optional[str] = Field(default=None, max_length=1000)
    modulo_origem: Optional[str] = None


class AIPreferenciasAssistenteUpdateRequest(BaseModel):
    """Atualização de preferências do assistente."""

    instrucoes_empresa: Optional[str] = Field(
        default=None,
        max_length=4000,
        description="Guardrails/instruções gerais da empresa para o assistente.",
    )
    formato_preferido: Optional[str] = Field(
        default=None,
        pattern="^(auto|resumo|tabela)$",
        description="Preferência de visualização do usuário.",
    )
    dominio: Optional[str] = Field(
        default="geral",
        description="Domínio da preferência (geral, financeiro, orcamentos, etc.).",
    )


class AIPreferenciasAssistenteOut(BaseModel):
    """Resposta de preferências do assistente."""

    instrucoes_empresa: str = ""
    pode_editar_instrucoes: bool = False
    preferencia_visualizacao: dict = Field(default_factory=dict)
    playbook_setor: dict = Field(default_factory=dict)


@router.get("/assistente/preferencias", response_model=AIPreferenciasAssistenteOut)
async def obter_preferencias_assistente(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """Retorna instruções da empresa, preferência visual do usuário e playbook de setor."""
    from app.services.assistant_preferences_service import AssistantPreferencesService

    empresa = (
        db.query(Empresa.id, Empresa.assistente_instrucoes)
        .filter(Empresa.id == current_user.empresa_id)
        .first()
    )
    contexto = AssistantPreferencesService.get_context_for_prompt(
        db=db,
        empresa_id=current_user.empresa_id,
        usuario_id=current_user.id,
        mensagem="resumo geral",
    )
    return AIPreferenciasAssistenteOut(
        instrucoes_empresa=(empresa.assistente_instrucoes if empresa else "") or "",
        pode_editar_instrucoes=bool(
            getattr(current_user, "is_gestor", False)
            or getattr(current_user, "is_superadmin", False)
        ),
        preferencia_visualizacao=contexto.get("preferencia_visualizacao_usuario") or {},
        playbook_setor=contexto.get("playbook_setor") or {},
    )


@router.patch("/assistente/preferencias", response_model=AIPreferenciasAssistenteOut)
async def atualizar_preferencias_assistente(
    request: AIPreferenciasAssistenteUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """Atualiza instruções da empresa (gestor/admin) e preferência visual do usuário."""
    from app.services.assistant_preferences_service import AssistantPreferencesService

    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    pode_editar_instrucoes = bool(
        getattr(current_user, "is_gestor", False)
        or getattr(current_user, "is_superadmin", False)
    )

    if request.instrucoes_empresa is not None:
        if not pode_editar_instrucoes:
            raise HTTPException(
                status_code=403,
                detail="Somente gestor/admin pode editar instruções da empresa.",
            )
        empresa.assistente_instrucoes = request.instrucoes_empresa.strip() or None
        db.add(empresa)
        db.commit()
        db.refresh(empresa)

    if request.formato_preferido is not None:
        AssistantPreferencesService.upsert_preferencia_visualizacao(
            db,
            empresa_id=current_user.empresa_id,
            usuario_id=current_user.id,
            formato_preferido=request.formato_preferido,
            dominio=request.dominio or "geral",
        )

    contexto = AssistantPreferencesService.get_context_for_prompt(
        db=db,
        empresa_id=current_user.empresa_id,
        usuario_id=current_user.id,
        mensagem="resumo geral",
    )
    return AIPreferenciasAssistenteOut(
        instrucoes_empresa=(empresa.assistente_instrucoes or ""),
        pode_editar_instrucoes=pode_editar_instrucoes,
        preferencia_visualizacao=contexto.get("preferencia_visualizacao_usuario") or {},
        playbook_setor=contexto.get("playbook_setor") or {},
    )


@router.post("/feedback", status_code=201)
async def registrar_feedback(
    request: AIFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """Registra avaliação 👍/👎 de uma resposta do assistente."""
    from app.models.models import FeedbackAssistente

    fb = FeedbackAssistente(
        empresa_id=current_user.empresa_id,
        sessao_id=request.sessao_id,
        pergunta=request.pergunta,
        resposta=request.resposta,
        avaliacao=request.avaliacao,
        comentario=request.comentario,
        modulo_origem=request.modulo_origem,
    )
    db.add(fb)
    db.commit()
    return {"ok": True}


@router.get("/feedbacks")
async def listar_feedbacks(
    avaliacao: Optional[str] = None,  # 'positivo' | 'negativo' | None (todos)
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """Lista feedbacks do assistente (gestor vê da própria empresa, superadmin vê todos)."""
    from app.models.models import FeedbackAssistente
    from sqlalchemy import desc

    q = db.query(FeedbackAssistente)
    if not getattr(current_user, "is_superadmin", False):
        q = q.filter(FeedbackAssistente.empresa_id == current_user.empresa_id)
    if avaliacao:
        q = q.filter(FeedbackAssistente.avaliacao == avaliacao)
    items = q.order_by(desc(FeedbackAssistente.criado_em)).limit(limit).all()
    return [
        {
            "id": fb.id,
            "pergunta": fb.pergunta,
            "resposta": fb.resposta[:300] + ("..." if len(fb.resposta) > 300 else ""),
            "avaliacao": fb.avaliacao,
            "comentario": fb.comentario,
            "modulo_origem": fb.modulo_origem,
            "criado_em": fb.criado_em.isoformat() if fb.criado_em else None,
        }
        for fb in items
    ]


# ── Onboarding ───────────────────────────────────────────────────────────


@router.get("/onboarding", response_model=AIResponse)
async def onboarding_status(
    db: Session = Depends(get_db), current_user: Usuario = Depends(exigir_permissao("ia", "leitura"))
):
    """
    Retorna o status de onboarding da empresa autenticada.

    Calcula automaticamente:
    - Quais etapas de configuração já foram concluídas
    - Percentual de progresso
    - Próxima ação recomendada
    """
    from app.services.onboarding_service import (
        get_onboarding_status,
        formatar_resposta_onboarding,
    )

    status = get_onboarding_status(db=db, empresa_id=current_user.empresa_id)
    resposta = formatar_resposta_onboarding(status)
    return AIResponse(
        sucesso=True,
        resposta=resposta,
        tipo_resposta="onboarding",
        dados=status,
        confianca=1.0,
        modulo_origem="onboarding",
    )


# ── Endpoint Genérico com Path Parameter ─────────────────────────────────
# NOTA: Este endpoint DEVE vir DEPOIS de todos os endpoints específicos
# para evitar que o FastAPI faça match de rotas como /assistente aqui


@router.post("/{modulo}", response_model=AIResponse)
async def processar_ia(
    modulo: Literal[
        "orcamentos", "clientes", "financeiro", "comercial", "operador", "conversacao"
    ],
    request: AIProcessRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    """
    Processa mensagem usando IA do COTTE para qualquer módulo do sistema.
    """
    # Incrementar contador de mensagens IA da empresa
    if current_user.empresa:
        current_user.empresa.total_mensagens_ia = (
            current_user.empresa.total_mensagens_ia or 0
        ) + 1
        db.commit()

    # Adicionar contexto do usuário
    contexto = request.contexto or {}
    contexto["usuario_id"] = current_user.id
    contexto["empresa_id"] = current_user.empresa_id

    resultado = await ai_hub.processar(
        modulo=modulo,
        mensagem=request.mensagem,
        contexto=contexto,
        db=db,
        usar_cache=request.usar_cache,
        confianca_minima=request.confianca_minima,
    )

    if not resultado.sucesso and resultado.confianca < 0.3:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Não foi possível interpretar a mensagem com confiança suficiente",
                "erros": resultado.erros,
                "sugestao": "Tente reformular a mensagem com mais detalhes",
            },
        )

    return resultado


# ── Endpoints de Debug (apenas superadmin) ───────────────────────────────


@router.get("/debug/cache", include_in_schema=False)
async def debug_cache(current_user: Usuario = Depends(get_current_user)):
    """Retorna informações do cache (debug apenas)."""
    # Verificar se é superadmin
    if not getattr(current_user, "is_superadmin", False):
        raise HTTPException(status_code=403, detail="Acesso restrito")

    cache = ai_hub.cache
    return {
        "cache_size": len(cache._cache),
        "ttl_segundos": cache._ttl,
        "entradas": [
            {"key": k[:8] + "...", "expires": v["expires_at"].isoformat()}
            for k, v in list(cache._cache.items())[:10]
        ],
    }
