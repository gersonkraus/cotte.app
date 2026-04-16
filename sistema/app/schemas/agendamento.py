from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.models import (
    StatusAgendamento,
    TipoAgendamento,
    OrigemAgendamento,
)


# ── AGENDAMENTO ────────────────────────────────────────────────────────────


class AgendamentoCreate(BaseModel):
    cliente_id: int
    orcamento_id: Optional[int] = None
    responsavel_id: Optional[int] = None
    tipo: TipoAgendamento = TipoAgendamento.SERVICO
    data_agendada: datetime
    data_fim: Optional[datetime] = None
    duracao_estimada_min: int = Field(default=60, ge=15, le=480)
    endereco: Optional[str] = None
    observacoes: Optional[str] = None


class AgendamentoUpdate(BaseModel):
    cliente_id: Optional[int] = None
    orcamento_id: Optional[int] = None
    responsavel_id: Optional[int] = None
    tipo: Optional[TipoAgendamento] = None
    data_agendada: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    duracao_estimada_min: Optional[int] = Field(default=None, ge=15, le=480)
    endereco: Optional[str] = None
    observacoes: Optional[str] = None


class AgendamentoReagendar(BaseModel):
    nova_data: datetime
    nova_data_fim: Optional[datetime] = None
    motivo: Optional[str] = None


class AgendamentoStatusUpdate(BaseModel):
    status: StatusAgendamento
    motivo: Optional[str] = None


class AgendamentoOut(BaseModel):
    id: int
    empresa_id: int
    cliente_id: int
    orcamento_id: Optional[int] = None
    criado_por_id: int
    responsavel_id: Optional[int] = None
    numero: Optional[str] = None
    status: StatusAgendamento
    tipo: TipoAgendamento
    origem: OrigemAgendamento
    data_agendada: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    duracao_estimada_min: Optional[int] = None
    endereco: Optional[str] = None
    observacoes: Optional[str] = None
    motivo_cancelamento: Optional[str] = None
    confirmado_em: Optional[datetime] = None
    cancelado_em: Optional[datetime] = None
    concluido_em: Optional[datetime] = None
    reagendamento_anterior_id: Optional[int] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None

    # Dados enriquecidos
    cliente_nome: Optional[str] = None
    responsavel_nome: Optional[str] = None
    orcamento_numero: Optional[str] = None
    # Primeira opção de data (status aguardando_escolha); para exibir no calendário
    primeira_opcao_data_hora: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgendamentoCalendario(BaseModel):
    """Versão simplificada para renderização em calendário."""

    id: int
    numero: Optional[str] = None
    status: StatusAgendamento
    tipo: TipoAgendamento
    data_agendada: datetime
    data_fim: Optional[datetime] = None
    duracao_estimada_min: Optional[int] = None
    cliente_nome: Optional[str] = None
    responsavel_nome: Optional[str] = None

    class Config:
        from_attributes = True


class AgendamentoDashboard(BaseModel):
    total_hoje: int = 0
    pendentes_confirmacao: int = 0
    confirmados_hoje: int = 0
    em_andamento: int = 0
    proximos_7_dias: int = 0
    cancelados_semana: int = 0


class SlotDisponivel(BaseModel):
    inicio: datetime
    fim: datetime
    duracao_min: int


# ── CONFIG AGENDAMENTO ─────────────────────────────────────────────────────


class ConfigAgendamentoCreate(BaseModel):
    horario_inicio: str = "08:00"
    horario_fim: str = "18:00"
    dias_trabalho: List[int] = [0, 1, 2, 3, 4]
    duracao_padrao_min: int = Field(default=60, ge=15, le=480)
    intervalo_minimo_min: int = Field(default=30, ge=0, le=120)
    antecedencia_minima_horas: int = Field(default=24, ge=0, le=720)
    permite_agendamento_cliente: bool = False
    requer_confirmacao: bool = True
    lembrete_antecedencia_horas: List[int] = [24, 2]
    mensagem_confirmacao: Optional[str] = None
    mensagem_lembrete: Optional[str] = None
    mensagem_reagendamento: Optional[str] = None
    usa_agendamento: bool = False


class ConfigAgendamentoUpdate(BaseModel):
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None
    dias_trabalho: Optional[List[int]] = None
    duracao_padrao_min: Optional[int] = Field(default=None, ge=15, le=480)
    intervalo_minimo_min: Optional[int] = Field(default=None, ge=0, le=120)
    antecedencia_minima_horas: Optional[int] = Field(default=None, ge=0, le=720)
    permite_agendamento_cliente: Optional[bool] = None
    requer_confirmacao: Optional[bool] = None
    lembrete_antecedencia_horas: Optional[List[int]] = None
    mensagem_confirmacao: Optional[str] = None
    mensagem_lembrete: Optional[str] = None
    mensagem_reagendamento: Optional[str] = None
    usa_agendamento: Optional[bool] = None


class ConfigAgendamentoOut(BaseModel):
    id: int
    empresa_id: int
    horario_inicio: str
    horario_fim: str
    dias_trabalho: List[int]
    duracao_padrao_min: int
    intervalo_minimo_min: int
    antecedencia_minima_horas: int
    permite_agendamento_cliente: bool
    requer_confirmacao: bool
    lembrete_antecedencia_horas: List[int]
    mensagem_confirmacao: Optional[str] = None
    mensagem_lembrete: Optional[str] = None
    mensagem_reagendamento: Optional[str] = None
    usa_agendamento: bool = False
    ativo: bool

    class Config:
        from_attributes = True


# ── CONFIG AGENDAMENTO USUÁRIO ─────────────────────────────────────────────


class ConfigAgendamentoUsuarioCreate(BaseModel):
    usuario_id: int
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None
    dias_trabalho: Optional[List[int]] = None
    duracao_padrao_min: Optional[int] = Field(default=None, ge=15, le=480)


class ConfigAgendamentoUsuarioUpdate(BaseModel):
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None
    dias_trabalho: Optional[List[int]] = None
    duracao_padrao_min: Optional[int] = Field(default=None, ge=15, le=480)


class ConfigAgendamentoUsuarioOut(BaseModel):
    id: int
    empresa_id: int
    usuario_id: int
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None
    dias_trabalho: Optional[List[int]] = None
    duracao_padrao_min: Optional[int] = None
    ativo: bool
    usuario_nome: Optional[str] = None

    class Config:
        from_attributes = True


# ── SLOT BLOQUEADO ─────────────────────────────────────────────────────────


class SlotBloqueadoCreate(BaseModel):
    usuario_id: Optional[int] = None  # NULL = empresa toda
    data_inicio: datetime
    data_fim: datetime
    motivo: Optional[str] = None
    recorrente: bool = False
    recorrencia_tipo: Optional[str] = None


class SlotBloqueadoOut(BaseModel):
    id: int
    empresa_id: int
    usuario_id: Optional[int] = None
    data_inicio: datetime
    data_fim: datetime
    motivo: Optional[str] = None
    recorrente: bool
    recorrencia_tipo: Optional[str] = None
    criado_em: Optional[datetime] = None
    usuario_nome: Optional[str] = None

    class Config:
        from_attributes = True


# ── HISTÓRICO ──────────────────────────────────────────────────────────────


class HistoricoAgendamentoOut(BaseModel):
    id: int
    agendamento_id: int
    status_anterior: Optional[str] = None
    status_novo: str
    descricao: Optional[str] = None
    editado_por_id: Optional[int] = None
    criado_em: Optional[datetime] = None
    editado_por_nome: Optional[str] = None

    class Config:
        from_attributes = True


# ── CRIAR DO ORÇAMENTO ─────────────────────────────────────────────────────


class CriarDoOrcamento(BaseModel):
    responsavel_id: Optional[int] = None
    tipo: TipoAgendamento = TipoAgendamento.SERVICO
    data_agendada: datetime
    data_fim: Optional[datetime] = None
    duracao_estimada_min: int = Field(default=60, ge=15, le=480)
    observacoes: Optional[str] = None


# ── OPÇÕES DE DATA/HORA ──────────────────────────────────────────────────


class AgendamentoOpcaoCreate(BaseModel):
    data_hora: datetime


class AgendamentoOpcaoOut(BaseModel):
    id: int
    agendamento_id: int
    data_hora: datetime
    disponivel: bool
    escolhida: bool = False
    criado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgendamentoComOpcoes(AgendamentoOut):
    """Agendamento com opções de data/hora para o cliente escolher."""

    opcoes: List[AgendamentoOpcaoOut] = []
    # Derivado de agendamento_opcoes.escolhida (compatível com clientes antigos)
    opcao_escolhida_id: Optional[int] = None


class EscolherOpcaoRequest(BaseModel):
    opcao_id: int


# ── CRIAR COM OPÇÕES ─────────────────────────────────────────────────────


class AgendamentoCreateComOpcoes(BaseModel):
    """Criar agendamento com opções de data/hora (operador define)."""

    cliente_id: int
    orcamento_id: Optional[int] = None
    responsavel_id: Optional[int] = None
    tipo: TipoAgendamento = TipoAgendamento.SERVICO
    duracao_estimada_min: int = Field(default=60, ge=15, le=480)
    endereco: Optional[str] = None
    observacoes: Optional[str] = None
    opcoes: List[AgendamentoOpcaoCreate] = Field(min_length=1, max_length=10)


# ── PRÉ-AGENDAMENTO (fila pós-aprovação) ────────────────────────────────────


class PreAgendamentoFilaItem(BaseModel):
    orcamento_id: int
    numero: Optional[str] = None
    cliente_nome: Optional[str] = None
    cliente_telefone: Optional[str] = None
    aprovado_canal: Optional[str] = None
    aprovado_em: Optional[datetime] = None
    aceite_mensagem: Optional[str] = None
    total: Optional[float] = None
    percentual_pago: float = 0.0
    pagamento_ok_para_liberar: bool = True
    agendamento_modo: Optional[str] = None

    class Config:
        from_attributes = True


class PreAgendamentoLiberarRequest(BaseModel):
    orcamento_ids: List[int] = Field(..., min_length=1)
    observacao: Optional[str] = None


class PreAgendamentoLiberarResultado(BaseModel):
    orcamento_id: int
    ok: bool
    detalhe: Optional[str] = None
    agendamento_id: Optional[int] = None


class PreAgendamentoLiberarResponse(BaseModel):
    resultados: List[PreAgendamentoLiberarResultado]
