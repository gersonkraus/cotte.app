"""Schemas Pydantic para o Módulo Financeiro COTTE."""

from pydantic import BaseModel, ConfigDict, Field, field_serializer
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from app.models.models import (
    TipoPagamento,
    StatusConta,
    TipoConta,
    OrigemRegistro,
    StatusPagamentoFinanceiro,
)


# ── FORMA DE PAGAMENTO CONFIG ───────────────────────────────────────────────

class FormaPagamentoConfigOut(BaseModel):
    id: int
    empresa_id: int
    nome: str
    slug: str
    icone: str
    cor: str
    ativo: bool
    aceita_parcelamento: bool
    max_parcelas: int
    taxa_percentual: Decimal
    gera_pix_qrcode: bool
    ordem: int
    created_at: datetime
    # Campos f002
    descricao: Optional[str] = None
    padrao: bool = False
    exigir_entrada_na_aprovacao: bool = False
    percentual_entrada: Decimal = Decimal("0")
    metodo_entrada: Optional[str] = None
    percentual_saldo: Decimal = Decimal("0")
    metodo_saldo: Optional[str] = None
    dias_vencimento_saldo: Optional[int] = None
    # Parcelamento do saldo (i001)
    numero_parcelas_saldo: int = 1
    intervalo_dias_parcela: int = 30
    class Config:
        from_attributes = True

    @field_serializer("taxa_percentual", "percentual_entrada", "percentual_saldo")
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v) if v is not None else 0.0


_METODOS_VALIDOS = {"pix", "dinheiro", "cartao", "boleto", "transferencia", "na_execucao", "na_entrega", "outro"}


class FormaPagamentoConfigCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=50)
    icone: str = Field(default="💳", max_length=10)
    cor: str = Field(default="#00e5a0", max_length=7)
    aceita_parcelamento: bool = False
    max_parcelas: int = Field(default=1, ge=1, le=24)
    taxa_percentual: Decimal = Field(default=Decimal("0"), ge=0)
    gera_pix_qrcode: bool = False
    ordem: int = 0
    # Campos f002
    descricao: Optional[str] = None
    padrao: bool = False
    exigir_entrada_na_aprovacao: bool = False
    percentual_entrada: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    metodo_entrada: Optional[str] = None
    percentual_saldo: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    metodo_saldo: Optional[str] = None
    dias_vencimento_saldo: Optional[int] = Field(None, ge=0)
    # Parcelamento do saldo (i001)
    numero_parcelas_saldo: int = Field(default=1, ge=1, le=60)
    intervalo_dias_parcela: int = Field(default=30, ge=1, le=365)


class FormaPagamentoConfigUpdate(BaseModel):
    nome: Optional[str] = None
    icone: Optional[str] = None
    cor: Optional[str] = None
    ativo: Optional[bool] = None
    aceita_parcelamento: Optional[bool] = None
    max_parcelas: Optional[int] = None
    taxa_percentual: Optional[Decimal] = None
    gera_pix_qrcode: Optional[bool] = None
    ordem: Optional[int] = None
    # Campos f002
    descricao: Optional[str] = None
    padrao: Optional[bool] = None
    exigir_entrada_na_aprovacao: Optional[bool] = None
    percentual_entrada: Optional[Decimal] = Field(None, ge=0, le=100)
    metodo_entrada: Optional[str] = None
    percentual_saldo: Optional[Decimal] = Field(None, ge=0, le=100)
    metodo_saldo: Optional[str] = None
    dias_vencimento_saldo: Optional[int] = Field(None, ge=0)
    # Parcelamento do saldo (i001)
    numero_parcelas_saldo: Optional[int] = Field(None, ge=1, le=60)
    intervalo_dias_parcela: Optional[int] = Field(None, ge=1, le=365)


# ── PAGAMENTO FINANCEIRO ────────────────────────────────────────────────────

class PagamentoCreate(BaseModel):
    orcamento_id: int
    valor: Decimal = Field(..., gt=0, description="Valor em R$ (Numeric 10,2)")
    tipo: TipoPagamento = TipoPagamento.QUITACAO
    forma_pagamento_id: Optional[int] = None
    data_pagamento: date
    observacao: Optional[str] = Field(None, max_length=500)
    comprovante_url: Optional[str] = Field(None, max_length=500)
    origem: OrigemRegistro = OrigemRegistro.MANUAL
    parcela_numero: Optional[int] = None
    txid_pix: Optional[str] = Field(None, max_length=35)
    idempotency_key: Optional[str] = Field(
        None,
        max_length=128,
        description="Chave opcional para deduplicar requisições repetidas (por empresa).",
    )


class PagamentoOut(BaseModel):
    id: int
    orcamento_id: Optional[int]
    conta_id: Optional[int]
    forma_pagamento_id: Optional[int]
    forma_pagamento_nome: Optional[str] = None   # campo calculado
    forma_pagamento_icone: Optional[str] = None  # campo calculado
    valor: Decimal
    tipo: TipoPagamento
    data_pagamento: date
    confirmado_em: datetime
    confirmado_por_id: Optional[int]
    confirmado_por_nome: Optional[str] = None    # campo calculado
    observacao: Optional[str]
    comprovante_url: Optional[str]
    origem: OrigemRegistro
    parcela_numero: Optional[int]
    status: StatusPagamentoFinanceiro
    txid_pix: Optional[str]
    idempotency_key: Optional[str] = None
    empresa_id: Optional[int] = None
    # Dados do orçamento (para tabelas)
    orcamento_numero: Optional[str] = None
    class Config:
        from_attributes = True

    @field_serializer("valor")
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v) if v is not None else 0.0


class EstornoRequest(BaseModel):
    motivo: Optional[str] = Field(None, max_length=500)


class ReceberContaRequest(BaseModel):
    """Body opcional para POST /financeiro/contas/{id}/receber."""

    valor: Optional[Decimal] = None
    forma_pagamento_id: Optional[int] = None
    observacao: Optional[str] = Field(None, max_length=500)
    data_pagamento: Optional[date] = None
    idempotency_key: Optional[str] = Field(
        None,
        max_length=128,
        description="Deduplica reenvios (combinar com header Idempotency-Key).",
    )


# ── CONTA FINANCEIRA ────────────────────────────────────────────────────────

class ContaFinanceiraCreate(BaseModel):
    orcamento_id: Optional[int] = None
    tipo: TipoConta = TipoConta.RECEBER
    descricao: str = Field(..., min_length=1, max_length=300)
    valor: Decimal = Field(..., gt=0)
    data_vencimento: Optional[date] = None
    categoria: Optional[str] = Field(None, max_length=100)
    origem: OrigemRegistro = OrigemRegistro.MANUAL
    # Parcelamento manual
    numero_parcela: Optional[int] = None
    total_parcelas: Optional[int] = None
    grupo_parcelas_id: Optional[str] = Field(None, max_length=36)
    metodo_previsto: Optional[str] = Field(None, max_length=50)
    tipo_lancamento: Optional[str] = Field(None, max_length=50)
    favorecido: Optional[str] = Field(None, max_length=200)
    categoria_slug: Optional[str] = Field(None, max_length=50)


class DespesaCreate(BaseModel):
    favorecido: Optional[str] = Field(None, max_length=200)
    descricao: str = Field(..., min_length=1, max_length=300)
    categoria_slug: Optional[str] = Field(None, max_length=50)
    valor: Decimal = Field(..., gt=0)
    data_vencimento: Optional[date] = None
    data_competencia: Optional[date] = None
    observacao: Optional[str] = Field(None, max_length=500)
    # Parcelamento manual
    numero_parcela: Optional[int] = None
    total_parcelas: Optional[int] = None
    grupo_parcelas_id: Optional[str] = Field(None, max_length=36)
    tipo_lancamento: Optional[str] = Field(None, max_length=50)


class ContaFinanceiraUpdate(BaseModel):
    descricao: Optional[str] = None
    valor: Optional[Decimal] = None
    data_vencimento: Optional[date] = None
    categoria: Optional[str] = None
    status: Optional[StatusConta] = None
    favorecido: Optional[str] = Field(None, max_length=200)
    categoria_slug: Optional[str] = Field(None, max_length=50)
    metodo_previsto: Optional[str] = Field(None, max_length=30)
    tipo_lancamento: Optional[str] = Field(None, max_length=20)
    data_competencia: Optional[date] = None


class ContaFinanceiraOut(BaseModel):
    id: int
    empresa_id: int
    orcamento_id: Optional[int]
    tipo: TipoConta
    descricao: str
    valor: Decimal
    valor_pago: Decimal
    saldo_devedor: Decimal = Decimal("0")   # calculado: valor - valor_pago
    status: StatusConta
    data_vencimento: Optional[date]
    data_criacao: datetime
    categoria: Optional[str]
    origem: OrigemRegistro
    ultima_cobranca_em: Optional[datetime]
    # Campos f002
    metodo_previsto: Optional[str] = None
    tipo_lancamento: Optional[str] = None   # 'entrada','saldo','integral'
    # Parcelamento (i001)
    numero_parcela: Optional[int] = None
    total_parcelas: Optional[int] = None
    grupo_parcelas_id: Optional[str] = None
    favorecido: Optional[str] = None
    categoria_slug: Optional[str] = None
    data_competencia: Optional[date] = None
    # Dados do orçamento
    orcamento_numero: Optional[str] = None
    cliente_nome: Optional[str] = None
    pagamentos: List[PagamentoOut] = []

    class Config:
        from_attributes = True

    @field_serializer("valor", "valor_pago", "saldo_devedor")
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v)


# ── DASHBOARD / RESUMO FINANCEIRO ───────────────────────────────────────────

class ReceitaMensalItem(BaseModel):
    mes: str           # "2026-01"
    label: str         # "Jan/26"
    total: Decimal

    @field_serializer("total")
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v) if v is not None else 0.0


class ReceitaPorMeioItem(BaseModel):
    meio: str
    icone: str
    total: Decimal
    percentual: float

    @field_serializer("total")
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v) if v is not None else 0.0


class PrevisaoItem(BaseModel):
    entradas: Decimal
    saidas: Decimal
    saldo: Decimal

    @field_serializer("entradas", "saidas", "saldo")
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v) if v is not None else 0.0


class FinanceiroResumoOut(BaseModel):
    total_recebido_mes: Decimal
    total_a_receber: Decimal
    total_vencido: Decimal
    ticket_medio: Decimal
    receita_por_mes: List[ReceitaMensalItem]
    receita_por_meio: List[ReceitaPorMeioItem]
    # Novos KPIs (i001)
    total_a_pagar: Decimal = Decimal("0")
    vencendo_hoje: int = 0
    em_atraso: int = 0
    previsao_7_dias: Optional[PrevisaoItem] = None
    previsao_30_dias: Optional[PrevisaoItem] = None
    # Saldo em caixa (Sprint 1.3)
    saldo_caixa: Decimal = Decimal("0")

    class Config:
        from_attributes = True

    @field_serializer(
        "total_recebido_mes", "total_a_receber", "total_vencido", 
        "ticket_medio", "total_a_pagar", "saldo_caixa"
    )
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v) if v is not None else 0.0


# ── TEMPLATE DE NOTIFICAÇÃO ─────────────────────────────────────────────────

class TemplateNotificacaoOut(BaseModel):
    id: int
    empresa_id: int
    tipo: str
    corpo: str
    ativo: bool
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TemplateNotificacaoUpdate(BaseModel):
    corpo: Optional[str] = None
    ativo: Optional[bool] = None


# ── FLUXO DE CAIXA ───────────────────────────────────────────────────────────

class FluxoCaixaDia(BaseModel):
    data: date
    entradas: Decimal
    saidas: Decimal
    saldo_dia: Decimal
    saldo_acumulado: Decimal

    @field_serializer("entradas", "saidas", "saldo_dia", "saldo_acumulado")
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v) if v is not None else 0.0


class FluxoCaixaOut(BaseModel):
    data_inicio: date
    data_fim: date
    total_entradas: Decimal
    total_saidas: Decimal
    saldo_periodo: Decimal
    por_data: List[FluxoCaixaDia]
    alertas: List[str] = []   # datas com saldo negativo

    @field_serializer("total_entradas", "total_saidas", "saldo_periodo")
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v) if v is not None else 0.0


# ── HISTÓRICO DE COBRANÇA ────────────────────────────────────────────────────

class HistoricoCobrancaOut(BaseModel):
    id: int
    empresa_id: int
    conta_id: Optional[int]
    enviado_em: datetime
    canal: str
    destinatario: Optional[str]
    status: str
    erro: Optional[str]
    mensagem_corpo: Optional[str]

    class Config:
        from_attributes = True


# ── CONFIGURAÇÃO FINANCEIRA ──────────────────────────────────────────────────

class ConfiguracaoFinanceiraOut(BaseModel):
    id: int
    empresa_id: int
    dias_vencimento_padrao: int
    gerar_contas_ao_aprovar: bool
    automacoes_ativas: bool
    dias_lembrete_antes: int
    dias_lembrete_apos: int
    categorias_despesa: Optional[str]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ConfiguracaoFinanceiraUpdate(BaseModel):
    dias_vencimento_padrao: Optional[int] = Field(None, ge=0, le=365)
    gerar_contas_ao_aprovar: Optional[bool] = None
    automacoes_ativas: Optional[bool] = None
    dias_lembrete_antes: Optional[int] = Field(None, ge=0, le=30)
    dias_lembrete_apos: Optional[int] = Field(None, ge=0, le=30)
    categorias_despesa: Optional[str] = None


# ── FORMAS DE PAGAMENTO (i001: novos campos) ─────────────────────────────────

class FormaPagamentoConfigUpdateV2(FormaPagamentoConfigUpdate):
    numero_parcelas_saldo: Optional[int] = Field(None, ge=1, le=60)
    intervalo_dias_parcela: Optional[int] = Field(None, ge=1, le=365)


# ── CONTA RÁPIDO (Sprint 1.1) ─────────────────────────────────────────────────

class ContaRapidoCreate(BaseModel):
    """Schema simplificado para criação rápida de contas a receber."""
    tipo: TipoConta = TipoConta.RECEBER
    cliente_id: Optional[int] = None
    cliente_nome: Optional[str] = Field(None, max_length=200)
    valor: Decimal = Field(..., gt=0)
    vencimento: Optional[date] = None
    descricao: str = Field(..., min_length=1, max_length=300)
    parcelas: int = Field(default=1, ge=1, le=60)
    orcamento_id: Optional[int] = None


class ContaRapidoOut(BaseModel):
    """Resposta da criação rápida de conta."""
    sucesso: bool
    conta_id: Optional[int] = None
    mensagem: str
    parcelas_criadas: int = 1


# ── CANCELAMENTO E EXCLUSÃO (Sprint 1.2) ──────────────────────────────────────

class CancelarContaRequest(BaseModel):
    """Request para cancelar uma conta financeira."""
    motivo: str = Field(..., min_length=1, max_length=500)


class ExcluirContaRequest(BaseModel):
    """Request para soft delete de conta com motivo."""
    motivo: str = Field(..., min_length=1, max_length=500)


# ── SALDO DETALHADO (Sprint 1.3) ────────────────────────────────────────────────

class SaldoDetalhadoOut(BaseModel):
    """Resposta detalhada do endpoint /financeiro/saldo."""
    saldo_caixa: Decimal
    saldo_banco: Decimal = Decimal("0")
    total_disponivel: Decimal
    a_receber_30_dias: Decimal
    a_pagar_30_dias: Decimal
    projecao_30_dias: Decimal
    saldo_inicial_configurado: Decimal = Decimal("0")

    @field_serializer(
        "saldo_caixa", "saldo_banco", "total_disponivel", 
        "a_receber_30_dias", "a_pagar_30_dias", "projecao_30_dias", 
        "saldo_inicial_configurado"
    )
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v) if v is not None else 0.0


class SaldoInicialRequest(BaseModel):
    """Request para definir saldo inicial."""
    valor: Decimal = Field(..., ge=0)


# ── MOVIMENTAÇÃO DE CAIXA (Sprint 2.1) ───────────────────────────────────────

from enum import Enum as PyEnum


class TipoMovimentacaoCaixa(str, PyEnum):
    ENTRADA = "entrada"
    SAIDA = "saida"


class MovimentacaoCaixaCreate(BaseModel):
    """Criação de movimentação de caixa."""
    tipo: TipoMovimentacaoCaixa
    valor: Decimal = Field(..., gt=0)
    descricao: str = Field(..., min_length=1, max_length=300)
    categoria: str = Field(default="geral", max_length=100)
    data: Optional[date] = None
    comprovante_url: Optional[str] = Field(None, max_length=500)


class MovimentacaoCaixaOut(BaseModel):
    """Resposta de movimentação de caixa."""
    id: int
    empresa_id: int
    tipo: TipoMovimentacaoCaixa
    valor: Decimal
    descricao: str
    categoria: str
    data: date
    confirmado: bool
    comprovante_url: Optional[str] = None
    criado_por_id: Optional[int] = None
    criado_em: datetime

    class Config:
        from_attributes = True

    @field_serializer("valor")
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v) if v is not None else 0.0


class EntradaCaixaRequest(BaseModel):
    """Request para registrar entrada no caixa."""
    valor: Decimal = Field(..., gt=0)
    descricao: str = Field(..., min_length=1, max_length=300)
    categoria: str = Field(default="venda", max_length=100)
    data: Optional[date] = None
    comprovante_url: Optional[str] = Field(None, max_length=500)


class SaidaCaixaRequest(BaseModel):
    """Request para registrar saída do caixa."""
    valor: Decimal = Field(..., gt=0)
    descricao: str = Field(..., min_length=1, max_length=300)
    categoria: str = Field(default="despesa", max_length=100)
    data: Optional[date] = None
    comprovante_url: Optional[str] = Field(None, max_length=500)


class SaldoCaixaOut(BaseModel):
    """Resposta com saldo atual do caixa."""
    saldo_atual: Decimal
    total_entradas: Decimal
    total_saidas: Decimal
    movimentacoes_hoje: int
    ultima_atualizacao: Optional[datetime] = None

    @field_serializer("saldo_atual", "total_entradas", "total_saidas")
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v) if v is not None else 0.0


# ── CATEGORIA FINANCEIRA (Sprint 2.2) ─────────────────────────────────────────

class TipoCategoria(str, PyEnum):
    RECEITA = "receita"
    DESPESA = "despesa"
    AMBOS = "ambos"


class CategoriaFinanceiraCreate(BaseModel):
    """Criação de categoria financeira customizável."""
    nome: str = Field(..., min_length=1, max_length=100)
    tipo: TipoCategoria = TipoCategoria.DESPESA
    cor: str = Field(default="#00e5a0", max_length=7)
    icone: str = Field(default="📁", max_length=10)
    ordem: int = 0


class CategoriaFinanceiraUpdate(BaseModel):
    """Atualização de categoria financeira."""
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    tipo: Optional[TipoCategoria] = None
    cor: Optional[str] = Field(None, max_length=7)
    icone: Optional[str] = Field(None, max_length=10)
    ativo: Optional[bool] = None
    ordem: Optional[int] = None


class CategoriaFinanceiraOut(BaseModel):
    """Resposta de categoria financeira."""
    id: int
    empresa_id: int
    nome: str
    tipo: TipoCategoria
    cor: str
    icone: str
    ativo: bool
    ordem: int
    criado_em: datetime

    class Config:
        from_attributes = True


# ── BUSCA/ORÇAMENTOS (Sprint 2.3) ─────────────────────────────────────────────

class OrcamentoBuscaOut(BaseModel):
    """Resultado de busca de orçamentos para autocomplete."""
    id: int
    numero: str
    cliente_nome: Optional[str] = None
    cliente_telefone: Optional[str] = None
    total: Decimal
    status: str
    data_criacao: date

    class Config:
        from_attributes = True

    @field_serializer("total")
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v) if v is not None else 0.0


class ClienteBuscaOut(BaseModel):
    """Resultado de busca de clientes para autocomplete."""
    id: int
    nome: str
    telefone: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True
