from pydantic import BaseModel, EmailStr, Field, field_serializer, field_validator
from typing import Optional, List, Literal
from datetime import datetime, date
from decimal import Decimal
from app.models.models import (
    StatusOrcamento,
    FormaPagamento,
    ModoAgendamentoOrcamento,
    TipoDocumentoEmpresa,
    StatusDocumentoEmpresa,
    TipoConteudoDocumento,
)


# ── CLIENTE ────────────────────────────────────────────────────────────────


class ClienteBase(BaseModel):
    nome: str
    telefone: Optional[str] = None
    email: Optional[str] = None
    endereco: Optional[str] = None
    # Campos individuais de endereço
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    observacoes: Optional[str] = None
    # Campos fiscais
    tipo_pessoa: Optional[str] = "PF"
    cpf: Optional[str] = None
    cnpj: Optional[str] = None
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    inscricao_municipal: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    """Atualização parcial (PATCH) — todos os campos opcionais."""

    nome: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    endereco: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    observacoes: Optional[str] = None
    # Campos fiscais
    tipo_pessoa: Optional[str] = None
    cpf: Optional[str] = None
    cnpj: Optional[str] = None
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    inscricao_municipal: Optional[str] = None


class ClienteOut(ClienteBase):
    id: int
    empresa_id: int
    criado_em: datetime

    class Config:
        from_attributes = True


# ── ITEM DO ORÇAMENTO ──────────────────────────────────────────────────────


class ItemOrcamentoBase(BaseModel):
    descricao: str
    quantidade: Decimal = Field(default=Decimal("1.0"), ge=0)
    valor_unit: Decimal = Field(..., ge=0)


class ItemOrcamentoCreate(ItemOrcamentoBase):
    servico_id: Optional[int] = None  # vínculo opcional com catálogo


class ItemOrcamentoOut(ItemOrcamentoBase):
    id: int
    total: Decimal
    servico_id: Optional[int] = None
    imagem_url: Optional[str] = (
        None  # do serviço vinculado (catálogo), para exibir no orçamento
    )

    class Config:
        from_attributes = True

    @field_serializer("quantidade", "valor_unit", "total")
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v) if v is not None else 0.0


# ── HISTÓRICO DE EDIÇÕES ────────────────────────────────────────────────────


class HistoricoEdicaoOut(BaseModel):
    id: int
    editado_por_nome: Optional[str] = None
    editado_em: datetime
    descricao: Optional[str] = None

    class Config:
        from_attributes = True


# ── LINHA DO TEMPO ──────────────────────────────────────────────────────────


class TimelineEventOut(BaseModel):
    tipo: str  # "criado" | "enviado" | "visualizado" | "lembrete" | "editado" | "aprovado" | "recusado" | "expirado" | "ajuste" | ...
    timestamp: datetime
    titulo: str
    detalhe: Optional[str] = (
        None  # Mensagem do cliente, motivo de recusa, nº de visualizações…
    )
    autor: Optional[str] = None  # Nome do usuário ou do cliente que realizou a ação
    indicador: Optional[str] = None  # Ex.: "Com anexo" | "Sem anexo"

    class Config:
        from_attributes = True


# ── ORÇAMENTO ──────────────────────────────────────────────────────────────


class OrcamentoCreate(BaseModel):
    cliente_id: int
    itens: List[ItemOrcamentoCreate] = Field(..., min_length=1)
    forma_pagamento: FormaPagamento = FormaPagamento.PIX
    validade_dias: int = 7
    observacoes: Optional[str] = None
    desconto: Decimal = Field(default=Decimal("0.0"), ge=0)
    desconto_tipo: Literal["percentual", "fixo"] = "percentual"
    regra_pagamento_id: Optional[int] = None  # f002: ID de FormaPagamentoConfig
    exigir_otp: bool = False
    # None = omitido no JSON: o servidor usa agendamento_modo_padrao da empresa
    agendamento_modo: Optional[ModoAgendamentoOrcamento] = None


class OrcamentoOut(BaseModel):
    id: int
    numero: str
    status: StatusOrcamento
    total: Decimal
    desconto: Decimal = Decimal("0.0")
    desconto_tipo: str = "percentual"
    forma_pagamento: FormaPagamento
    validade_dias: int
    observacoes: Optional[str]
    pdf_url: Optional[str]
    link_publico: Optional[str]
    criado_em: datetime
    visualizado_em: Optional[datetime] = None
    visualizacoes: int = 0
    enviado_em: Optional[datetime] = None
    lembrete_enviado_em: Optional[datetime] = None
    aceite_nome: Optional[str] = None
    aceite_em: Optional[datetime] = None
    aceite_mensagem: Optional[str] = None
    aceite_confirmado_otp: bool = False
    exigir_otp: bool = False
    recusa_motivo: Optional[str] = None
    agendamento_modo: ModoAgendamentoOrcamento = ModoAgendamentoOrcamento.NAO_USA
    # PIX e Pagamento (v9)
    pix_chave: Optional[str] = None
    pix_tipo: Optional[str] = None
    pix_titular: Optional[str] = None
    pix_payload: Optional[str] = None
    pix_qrcode: Optional[str] = None
    pix_informado_em: Optional[datetime] = None
    valor_sinal_pix: Optional[Decimal] = None
    pagamento_recebido_em: Optional[datetime] = None
    pagamento_recebido_por_id: Optional[int] = None
    # Regra de pagamento — snapshot f002
    regra_pagamento_id: Optional[int] = None
    regra_pagamento_nome: Optional[str] = None
    regra_entrada_percentual: Optional[Decimal] = None
    regra_entrada_metodo: Optional[str] = None
    regra_saldo_percentual: Optional[Decimal] = None
    regra_saldo_metodo: Optional[str] = None
    cliente: ClienteOut
    itens: List[ItemOrcamentoOut]
    pagamentos_financeiros: List["PagamentoPublicoOut"] = []

    class Config:
        from_attributes = True

    @field_serializer(
        "total",
        "desconto",
        "valor_sinal_pix",
        "regra_entrada_percentual",
        "regra_saldo_percentual",
    )
    def serialize_decimal(self, v: Decimal) -> Optional[float]:
        return float(v) if v is not None else None


# ── ORÇAMENTO PÚBLICO (sem dados sensíveis, para o cliente) ────────────────


class EmpresaPublicoOut(BaseModel):
    nome: str
    telefone: Optional[str] = None
    telefone_operador: Optional[str] = (
        None  # WhatsApp do responsável (para botão "Tirar dúvidas")
    )
    email: Optional[str] = None
    logo_url: Optional[str] = None
    cor_primaria: Optional[str] = None
    # Comunicação na página pública do orçamento
    descricao_publica_empresa: Optional[str] = None
    texto_aviso_aceite: Optional[str] = None
    mostrar_botao_whatsapp: bool = True
    texto_assinatura_proposta: Optional[str] = None
    mensagem_confianca_proposta: Optional[str] = None
    mostrar_mensagem_confianca: bool = True
    exigir_otp_aceite: bool = False
    otp_valor_minimo: Decimal = Decimal("0.0")
    template_publico: str = "classico"
    template_orcamento: str = "classico"
    enviar_pdf_whatsapp: bool = False

    class Config:
        from_attributes = True


class ClientePublicoOut(BaseModel):
    nome: str
    telefone: Optional[str] = None

    class Config:
        from_attributes = True


class OrcamentoDocumentoPublicoOut(BaseModel):
    id: int
    documento_nome: str
    documento_tipo: Optional[str] = None
    documento_versao: Optional[str] = None
    permite_download: bool = True

    class Config:
        from_attributes = True


class OrcamentoPublicoOut(BaseModel):
    numero: str
    status: StatusOrcamento
    total: Decimal
    desconto: Decimal = Decimal("0.0")
    desconto_tipo: str = "percentual"
    forma_pagamento: FormaPagamento
    validade_dias: int
    observacoes: Optional[str] = None
    criado_em: datetime
    aceite_nome: Optional[str] = None
    aceite_em: Optional[datetime] = None
    aceite_mensagem: Optional[str] = None
    aceite_confirmado_otp: bool = False
    exigir_otp: bool = False
    recusa_motivo: Optional[str] = None
    agendamento_modo: ModoAgendamentoOrcamento = ModoAgendamentoOrcamento.NAO_USA
    has_agendamento_pendente: bool = (
        False  # True se há agendamento com opcoes p/ o cliente escolher
    )
    agendamento_auto_alerta: Optional[str] = None
    # PIX e Pagamento (v9)
    pix_chave: Optional[str] = None
    pix_tipo: Optional[str] = None
    pix_titular: Optional[str] = None
    pix_payload: Optional[str] = None
    pix_qrcode: Optional[str] = None
    pix_informado_em: Optional[datetime] = None
    valor_sinal_pix: Optional[Decimal] = None
    pagamento_recebido_em: Optional[datetime] = None
    # Regra de pagamento — snapshot f002
    regra_pagamento_id: Optional[int] = None
    regra_pagamento_nome: Optional[str] = None
    regra_entrada_percentual: Optional[Decimal] = None
    regra_entrada_metodo: Optional[str] = None
    regra_saldo_percentual: Optional[Decimal] = None
    regra_saldo_metodo: Optional[str] = None
    empresa: EmpresaPublicoOut
    cliente: ClientePublicoOut
    itens: List[ItemOrcamentoOut]
    documentos: List[OrcamentoDocumentoPublicoOut] = []
    pagamentos_financeiros: List["PagamentoPublicoOut"] = []
    contas_financeiras_publico: List["ContaPublicoOut"] = []

    class Config:
        from_attributes = True


class ContaPublicoOut(BaseModel):
    """Conta a receber exposta na página pública (apenas dados não-sensíveis)."""

    id: int
    descricao: str
    valor: Decimal
    valor_pago: Decimal
    status: str
    data_vencimento: Optional[date] = None
    tipo_lancamento: Optional[str] = None
    numero_parcela: Optional[int] = None
    total_parcelas: Optional[int] = None

    class Config:
        from_attributes = True


class PagamentoPublicoOut(BaseModel):
    """Pagamento exposto na página pública (sem dados sensíveis do operador)."""

    id: int
    valor: Decimal
    tipo: str
    data_pagamento: date
    status: str
    forma_pagamento_nome: Optional[str] = None
    forma_pagamento_icone: Optional[str] = None

    class Config:
        from_attributes = True


# ── DOCUMENTOS DA EMPRESA ───────────────────────────────────────────────────


class DocumentoEmpresaOut(BaseModel):
    id: int
    empresa_id: int
    criado_por_id: Optional[int] = None
    nome: str
    slug: Optional[str] = None
    tipo: TipoDocumentoEmpresa
    descricao: Optional[str] = None
    arquivo_nome_original: Optional[str] = None
    mime_type: Optional[str] = None
    tamanho_bytes: Optional[int] = None
    tipo_conteudo: TipoConteudoDocumento
    conteudo_html: Optional[str] = None
    variaveis_suportadas: Optional[list] = None
    versao: Optional[str] = None
    status: StatusDocumentoEmpresa

    class Config:
        from_attributes = True


class DocumentoEmpresaUpdate(BaseModel):
    nome: Optional[str] = None
    slug: Optional[str] = None
    tipo: Optional[TipoDocumentoEmpresa] = None
    descricao: Optional[str] = None
    versao: Optional[str] = None
    status: Optional[StatusDocumentoEmpresa] = None
    permite_download: Optional[bool] = None
    visivel_no_portal: Optional[bool] = None
    tipo_conteudo: Optional[TipoConteudoDocumento] = None
    conteudo_html: Optional[str] = None
    variaveis_suportadas: Optional[list] = None


class OrcamentoDocumentoOut(BaseModel):
    id: int
    orcamento_id: int
    documento_id: Optional[int] = None
    ordem: int = 0
    exibir_no_portal: bool = True
    enviar_por_email: bool = False
    enviar_por_whatsapp: bool = False
    obrigatorio: bool = False
    documento_nome: str
    documento_tipo: Optional[str] = None
    documento_versao: Optional[str] = None
    arquivo_nome_original: Optional[str] = None
    mime_type: Optional[str] = None
    tamanho_bytes: Optional[int] = None
    conteudo_html: Optional[str] = None
    permite_download: bool = True
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrcamentoDocumentoCreate(BaseModel):
    documento_id: int
    exibir_no_portal: bool = True
    enviar_por_email: bool = False
    enviar_por_whatsapp: bool = False
    obrigatorio: bool = False


class OrcamentoDocumentoUpdate(BaseModel):
    ordem: Optional[int] = None
    exibir_no_portal: Optional[bool] = None
    enviar_por_email: Optional[bool] = None
    enviar_por_whatsapp: Optional[bool] = None
    obrigatorio: Optional[bool] = None


class OrcamentoDocumentosReorderRequest(BaseModel):
    ids_em_ordem: List[int]


class OrcamentoUpdate(BaseModel):
    itens: List[ItemOrcamentoCreate] = Field(..., min_length=1)
    forma_pagamento: FormaPagamento = FormaPagamento.PIX
    validade_dias: int = 7
    observacoes: Optional[str] = None
    desconto: Decimal = Field(default=Decimal("0.0"), ge=0)
    desconto_tipo: Literal["percentual", "fixo"] = "percentual"
    regra_pagamento_id: Optional[int] = None  # f002: ID de FormaPagamentoConfig
    exigir_otp: Optional[bool] = None
    agendamento_modo: Optional[ModoAgendamentoOrcamento] = None


class DadosPIXUpdate(BaseModel):
    """Dados para configurar PIX de um orçamento"""

    pix_chave: str = Field(
        ..., description="Chave PIX (CPF, CNPJ, email, telefone ou aleatória)"
    )
    pix_tipo: str = Field(
        ..., description="Tipo da chave: cpf, cnpj, email, telefone, aleatoria"
    )
    pix_titular: str = Field(..., description="Nome do titular da conta")


class PixGerarRequest(BaseModel):
    """Requisição para gerar QR code PIX on-the-fly sem persistir"""

    valor: Decimal = Field(..., gt=0, description="Valor da transação em R$")


class PixGerarResponse(BaseModel):
    """Resposta com QR code e payload PIX gerados dinamicamente"""

    qrcode: str
    payload: str
    valor: Decimal


class PixSinalUpdate(BaseModel):
    """Salva o valor do sinal PIX no orçamento e regenera QR/payload"""

    valor_sinal_pix: Optional[Decimal] = Field(
        None, ge=0, description="Valor do sinal em R$; None para limpar"
    )


class PagamentoRecebidoBody(BaseModel):
    """Body opcional para POST /orcamentos/{id}/pagamento-recebido.
    Permite especificar valor e tipo; se omitidos, o backend calcula saldo devedor."""

    valor: Optional[Decimal] = Field(
        None, gt=0, description="Valor recebido (None = saldo total)"
    )
    tipo: Optional[str] = Field("quitacao", description="sinal | parcela | quitacao")
    forma_pagamento_id: Optional[int] = None


class RegistrarSinalBody(BaseModel):
    """Body para POST /orcamentos/{id}/registrar-sinal (confirmar sinal PIX recebido)."""

    valor: Decimal = Field(..., gt=0, description="Valor do sinal recebido")


class ClienteListagemOrcamentoOut(BaseModel):
    """Cliente resumido para listagem de orçamentos (sem payload fiscal completo)."""

    id: int
    nome: str

    class Config:
        from_attributes = True


class OrcamentoListItem(BaseModel):
    """Resposta da listagem GET /orcamentos/: sem PIX payload/QRCode e sem pagamentos_financeiros."""

    id: int
    numero: str
    status: StatusOrcamento
    total: Decimal
    desconto: Decimal = Decimal("0.0")
    desconto_tipo: str = "percentual"
    forma_pagamento: FormaPagamento
    validade_dias: int
    observacoes: Optional[str] = None
    criado_em: datetime
    enviado_em: Optional[datetime] = None
    lembrete_enviado_em: Optional[datetime] = None
    exigir_otp: bool = False
    regra_pagamento_id: Optional[int] = None
    regra_pagamento_nome: Optional[str] = None
    regra_entrada_percentual: Optional[Decimal] = None
    regra_entrada_metodo: Optional[str] = None
    regra_saldo_percentual: Optional[Decimal] = None
    regra_saldo_metodo: Optional[str] = None
    cliente: ClienteListagemOrcamentoOut
    cliente_id: int
    cliente_nome: str
    cliente_endereco: Optional[str] = None
    itens: List[ItemOrcamentoOut] = []
    validade_ate: Optional[datetime] = None
    descricao_resumo: Optional[str] = None

    class Config:
        from_attributes = True

    @field_serializer(
        "total",
        "desconto",
        "regra_entrada_percentual",
        "regra_saldo_percentual",
    )
    def serialize_decimal_list(self, v: Decimal) -> Optional[float]:
        return float(v) if v is not None else None


# ── INTERPRETAÇÃO IA ───────────────────────────────────────────────────────


class IAInterpretacaoRequest(BaseModel):
    mensagem: str = Field(..., description="Texto ou transcrição de áudio do usuário")


class IAInterpretacaoOut(BaseModel):
    cliente_nome: str
    servico: str
    valor: Decimal
    desconto: Decimal = Decimal("0.0")
    desconto_tipo: str = "percentual"  # "percentual" ou "fixo"
    observacoes: Optional[str] = None
    confianca: float = Field(..., description="0.0 a 1.0 — quão segura a IA está")


# ── WHATSAPP WEBHOOK ───────────────────────────────────────────────────────

# --- Z-API ---


class WebhookZAPIText(BaseModel):
    message: Optional[str] = None


class WebhookZAPIAudio(BaseModel):
    audioUrl: Optional[str] = None


class WebhookZAPI(BaseModel):
    """Payload real enviado pela Z-API no webhook."""

    model_config = {"extra": "ignore"}

    phone: str
    fromMe: bool = False
    isGroup: bool = False
    isNewsletter: bool = False
    chatName: Optional[str] = None
    senderName: Optional[str] = None
    text: Optional[WebhookZAPIText] = None
    audio: Optional[WebhookZAPIAudio] = None

    @property
    def mensagem_texto(self) -> Optional[str]:
        return self.text.message if self.text else None

    @property
    def audio_url(self) -> Optional[str]:
        return self.audio.audioUrl if self.audio else None


# --- Evolution API ---


class WebhookEvolutionMessageData(BaseModel):
    """Conteúdo da mensagem no payload da Evolution API."""

    model_config = {"extra": "ignore"}

    conversation: Optional[str] = None  # mensagem de texto simples
    extendedTextMessage: Optional[dict] = None  # texto com preview de link


class WebhookEvolutionKey(BaseModel):
    model_config = {"extra": "ignore"}

    remoteJid: Optional[str] = None  # ex: "5548999887766@s.whatsapp.net"
    fromMe: bool = False
    id: Optional[str] = None


class WebhookEvolution(BaseModel):
    """
    Payload enviado pela Evolution API no webhook de mensagens recebidas.
    Evento: MESSAGES_UPSERT
    """

    model_config = {"extra": "ignore"}

    event: Optional[str] = None  # "messages.upsert"
    instance: Optional[str] = None  # nome da instância
    data: Optional[dict] = None  # dados brutos do evento

    @property
    def key(self) -> Optional[WebhookEvolutionKey]:
        if self.data and "key" in self.data:
            return WebhookEvolutionKey(**self.data["key"])
        return None

    @property
    def phone(self) -> Optional[str]:
        """Extrai o número de telefone limpo do remoteJid (remove @s.whatsapp.net)."""
        k = self.key
        if k and k.remoteJid:
            return k.remoteJid.split("@")[0]
        return None

    @property
    def fromMe(self) -> bool:
        k = self.key
        return k.fromMe if k else False

    @property
    def isGroup(self) -> bool:
        """Grupos têm remoteJid terminando em @g.us."""
        k = self.key
        if k and k.remoteJid:
            return k.remoteJid.endswith("@g.us")
        return False

    @property
    def mensagem_texto(self) -> Optional[str]:
        """Retorna o texto da mensagem: texto simples, preview de link ou voto de poll."""
        if not self.data:
            return None
        msg = self.data.get("message") or {}
        # Texto simples
        if "conversation" in msg:
            return msg["conversation"]
        # Texto com preview de link
        ext = msg.get("extendedTextMessage") or {}
        if "text" in ext:
            return ext["text"]
        # Resposta de poll — Evolution/Baileys encapsula como pollUpdateMessage
        poll_upd = msg.get("pollUpdateMessage") or {}
        if poll_upd:
            votes = poll_upd.get("vote", {}).get("selectedOptions", [])
            if votes:
                return votes[0]  # ex: "Confirmar" ou "Cancelar"
        return None

    @property
    def audio_message_data(self) -> Optional[dict]:
        """Retorna os dados do audioMessage se presente, para transcrição de voz."""
        if not self.data:
            return None
        msg = self.data.get("message") or {}
        if "audioMessage" in msg or "pttMessage" in msg:
            # Retorna a estrutura completa necessária para download via Evolution API
            return self.data
        return None


# ── CATÁLOGO (SERVIÇOS/PRODUTOS) ───────────────────────────────────────────


class CategoriaCatalogoOut(BaseModel):
    id: int
    nome: str

    class Config:
        from_attributes = True


class CategoriaCatalogoCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)


class ServicoBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    preco_padrao: Decimal = Decimal("0.0")
    preco_custo: Optional[Decimal] = None
    unidade: str = "un"
    categoria_id: Optional[int] = None


class ServicoCreate(ServicoBase):
    pass


class ServicoUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    preco_padrao: Optional[Decimal] = None
    preco_custo: Optional[Decimal] = None
    unidade: Optional[str] = None
    ativo: Optional[bool] = None
    categoria_id: Optional[int] = None


class ServicoOut(ServicoBase):
    id: int
    empresa_id: int
    ativo: bool
    imagem_url: Optional[str] = None
    categoria: Optional[CategoriaCatalogoOut] = None

    class Config:
        from_attributes = True


# ── EMPRESA ────────────────────────────────────────────────────────────────


class EmpresaUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    telefone_operador: Optional[str] = None
    email: Optional[str] = None
    cor_primaria: Optional[str] = None
    validade_padrao_dias: Optional[int] = None  # #10
    agendamento_modo_padrao: Optional[ModoAgendamentoOrcamento] = None
    agendamento_escolha_obrigatoria: Optional[bool] = (
        None  # True: cada novo orçamento exige escolha explícita de agendamento (Sim/Não)
    )
    desconto_max_percent: Optional[int] = (
        None  # desconto percentual máximo em orçamentos (ex.: 100)
    )
    lembrete_dias: Optional[int] = None  # #3 — None desativa
    lembrete_texto: Optional[str] = None  # #3 — None = usa texto padrão
    notif_email_aprovado: Optional[bool] = None  # deprecated (sem uso ativo)
    notif_email_expirado: Optional[bool] = None  # deprecated (sem uso ativo)
    anexar_pdf_email: Optional[bool] = (
        None  # anexa PDF automaticamente no envio por e-mail
    )
    assinatura_email: Optional[str] = (
        None  # assinatura personalizada no rodapé dos e-mails
    )
    msg_boas_vindas: Optional[str] = (
        None  # texto da mensagem de boas-vindas via WhatsApp
    )
    boas_vindas_ativo: Optional[bool] = (
        None  # habilita/desabilita mensagem de boas-vindas
    )
    # Comunicação na página pública do orçamento (Configurações → Comunicação)
    descricao_publica_empresa: Optional[str] = None
    texto_aviso_aceite: Optional[str] = None
    mostrar_botao_whatsapp: Optional[bool] = None
    texto_assinatura_proposta: Optional[str] = None
    mensagem_confianca_proposta: Optional[str] = None
    mostrar_mensagem_confianca: Optional[bool] = None
    exigir_otp_aceite: Optional[bool] = None
    otp_valor_minimo: Optional[Decimal] = None
    notif_whats_visualizacao: Optional[bool] = (
        None  # envia WhatsApp ao operador quando cliente abre o link
    )
    # PIX padrão da empresa
    pix_chave_padrao: Optional[str] = None
    pix_tipo_padrao: Optional[str] = None
    pix_titular_padrao: Optional[str] = None
    # Overrides por empresa (limites e permissões além do plano) - editável pelo admin
    limite_orcamentos_custom: Optional[int] = None
    limite_usuarios_custom: Optional[int] = None
    desativar_ia: Optional[bool] = None
    desativar_lembretes: Optional[bool] = None
    desativar_relatorios: Optional[bool] = None
    # Numeração de orçamentos personalizável (z011)
    numero_prefixo: Optional[str] = None
    numero_incluir_ano: Optional[bool] = None
    numero_prefixo_aprovado: Optional[str] = None
    # Template da página pública do orçamento
    template_publico: Optional[str] = None  # moderno | classico
    template_orcamento: Optional[str] = None  # moderno | classico (PDF)
    enviar_pdf_whatsapp: Optional[bool] = None  # anexa PDF no WhatsApp
    # Automação de status de orçamento
    auto_status_orcamento: Optional[bool] = None  # ativa transições automáticas
    agendamento_exige_pagamento_100: Optional[bool] = (
        None  # exige pagamento 100% para confirmar agendamento
    )
    utilizar_agendamento_automatico: Optional[bool] = (
        None  # cria agendamento com opções ao aprovar (quando modo do orçamento permitir)
    )
    agendamento_opcoes_somente_apos_liberacao: Optional[bool] = (
        None  # fila de pré-agendamento: só gera opções após liberação manual
    )
    # Plano pode ser alterado apenas pelo admin / webhook; mantido fora do update público.

    @field_validator("numero_prefixo", "numero_prefixo_aprovado", mode="before")
    @classmethod
    def validar_prefixo(cls, v):
        if v is None:
            return v
        limpo = str(v).upper().strip()
        import re

        if not re.match(r"^[A-Z0-9]{1,8}$", limpo):
            raise ValueError(
                "Prefixo deve conter apenas letras e números (máx. 8 caracteres)"
            )
        return limpo

    @field_validator("desconto_max_percent", mode="before")
    @classmethod
    def validar_desconto(cls, v):
        if v is None:
            return v
        v = int(v)
        if not (0 <= v <= 100):
            raise ValueError("desconto_max_percent deve estar entre 0 e 100")
        return v

    @field_validator("template_publico", mode="before")
    @classmethod
    def validar_template(cls, v):
        if v is None:
            return v
        v = str(v).strip().lower()
        if v not in ("moderno", "classico"):
            raise ValueError("template_publico deve ser 'moderno' ou 'classico'")
        return v


class EmpresaOut(BaseModel):
    id: int
    nome: str
    telefone: Optional[str]
    telefone_operador: Optional[str]
    email: Optional[str]
    logo_url: Optional[str]
    cor_primaria: Optional[str]
    validade_padrao_dias: Optional[int] = 7  # #10
    agendamento_modo_padrao: ModoAgendamentoOrcamento = ModoAgendamentoOrcamento.NAO_USA
    agendamento_escolha_obrigatoria: bool = False
    desconto_max_percent: Optional[int] = (
        100  # desconto percentual máximo em orçamentos
    )
    lembrete_dias: Optional[int] = None  # #3
    lembrete_texto: Optional[str] = None  # #3
    notif_email_aprovado: bool = True
    notif_email_expirado: bool = False
    anexar_pdf_email: bool = False
    assinatura_email: Optional[str] = None
    msg_boas_vindas: Optional[str] = None
    boas_vindas_ativo: bool = True
    plano: str = "trial"
    assinatura_valida_ate: Optional[datetime] = None
    trial_ate: Optional[datetime] = None
    limite_orcamentos_custom: Optional[int] = None
    limite_usuarios_custom: Optional[int] = None
    desativar_ia: bool = False
    desativar_lembretes: bool = False
    desativar_relatorios: bool = False
    # Comunicação na página pública do orçamento
    descricao_publica_empresa: Optional[str] = None
    texto_aviso_aceite: Optional[str] = None
    mostrar_botao_whatsapp: bool = True
    texto_assinatura_proposta: Optional[str] = None
    mensagem_confianca_proposta: Optional[str] = None
    mostrar_mensagem_confianca: bool = True
    exigir_otp_aceite: bool = False
    otp_valor_minimo: Decimal = Decimal("0.0")
    notif_whats_visualizacao: Optional[bool] = (
        True  # envia WhatsApp ao operador quando cliente abre o link
    )
    # PIX padrão da empresa
    pix_chave_padrao: Optional[str] = None
    pix_tipo_padrao: Optional[str] = None
    pix_titular_padrao: Optional[str] = None
    # WhatsApp próprio
    whatsapp_proprio_ativo: Optional[bool] = False
    whatsapp_numero: Optional[str] = None
    whatsapp_conectado: Optional[bool] = False
    # Numeração de orçamentos personalizável (z011)
    numero_prefixo: str = "ORC"
    numero_incluir_ano: bool = True
    numero_prefixo_aprovado: Optional[str] = None
    # Template da página pública do orçamento
    template_publico: str = "classico"
    template_orcamento: str = "classico"
    enviar_pdf_whatsapp: bool = False
    # Automação de status de orçamento
    auto_status_orcamento: bool = True
    agendamento_exige_pagamento_100: bool = False
    utilizar_agendamento_automatico: bool = True
    agendamento_opcoes_somente_apos_liberacao: bool = False

    class Config:
        from_attributes = True


class EmpresaUsoOut(BaseModel):
    plano: str
    nome_plano: str
    orcamentos_usados: int
    orcamentos_limite: Optional[int] = None  # None = ilimitado
    usuarios_usados: int
    usuarios_limite: Optional[int] = None  # None = ilimitado
    assinatura_valida_ate: Optional[datetime] = None
    trial_ate: Optional[datetime] = None
    ativo: bool

    class Config:
        from_attributes = True


class EmpresaSidebarOut(BaseModel):
    """Campos mínimos da empresa para a sidebar (GET /empresa/resumo-sidebar)."""

    id: int
    nome: str
    logo_url: Optional[str] = None
    plano: str = "trial"

    class Config:
        from_attributes = True


# ── BANCOS PIX DA EMPRESA ────────────────────────────────────────────────────


class BancoPIXBase(BaseModel):
    nome_banco: str
    apelido: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None
    tipo_conta: Optional[str] = None
    pix_tipo: Optional[str] = None
    pix_chave: Optional[str] = None
    pix_titular: Optional[str] = None
    padrao_pix: bool = False


class BancoPIXCreate(BancoPIXBase):
    pass


class BancoPIXUpdate(BaseModel):
    nome_banco: Optional[str] = None
    apelido: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None
    tipo_conta: Optional[str] = None
    pix_tipo: Optional[str] = None
    pix_chave: Optional[str] = None
    pix_titular: Optional[str] = None
    padrao_pix: Optional[bool] = None


class BancoPIXOut(BancoPIXBase):
    id: int

    class Config:
        from_attributes = True


# ── WHATSAPP PRÓPRIO ────────────────────────────────────────────────────────


class WhatsAppStatusOut(BaseModel):
    """Status do WhatsApp próprio da empresa."""

    habilitado: bool  # plano permite o recurso
    ativo: bool  # empresa habilitou o recurso
    conectado: bool  # QR code foi lido e está conectado
    numero: Optional[str]  # número confirmado após conexão
    instance: Optional[str]  # nome da instância na Evolution
    qrcode: Optional[str]  # base64 do QR code (quando disponível)

    class Config:
        from_attributes = True


# ── AUTH ───────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, v):
        return v.lower().strip() if isinstance(v, str) else v


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EsqueciSenhaRequest(BaseModel):
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, v):
        return v.lower().strip() if isinstance(v, str) else v


class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str = Field(..., min_length=8, max_length=128)


class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    empresa_nome: str  # cria empresa junto no cadastro

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, v):
        return v.lower().strip() if isinstance(v, str) else v


# ── PAPÉIS (RBAC) ──────────────────────────────────────────────────────────


class PapelBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    permissoes: List[str] = []  # ["modulo:acao", ...]
    is_default: bool = False


class PapelCreate(PapelBase):
    pass


class PapelUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    permissoes: Optional[List[str]] = None
    is_default: Optional[bool] = None
    ativo: Optional[bool] = None


class PapelOut(PapelBase):
    id: int
    slug: str
    is_sistema: bool
    ativo: bool
    empresa_id: int
    criado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class PapelResumo(BaseModel):
    """Versão resumida para exibição em listas de usuários."""

    id: int
    nome: str
    slug: str

    class Config:
        from_attributes = True


class ModuloComAcoes(BaseModel):
    """Para o frontend montar a tela de configuração de papéis."""

    id: int
    nome: str
    slug: str
    acoes: List[str]

    class Config:
        from_attributes = True


class AtribuirPapelRequest(BaseModel):
    """Para atribuir papel a um usuário."""

    papel_id: int


# ── USUÁRIO ─────────────────────────────────────────────────────────────────


class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: str
    empresa_id: int
    is_superadmin: bool = False
    is_gestor: bool = False
    permissoes: dict = {}
    papel: Optional[PapelResumo] = None
    telefone_operador: Optional[str] = None

    class Config:
        from_attributes = True


# ── ADMIN ──────────────────────────────────────────────────────────────────


class EmpresaAdminCreate(BaseModel):
    nome: str
    email: Optional[str] = None
    telefone: Optional[str] = None
    telefone_operador: Optional[str] = None
    cor_primaria: str = "#00e5a0"
    usuario_nome: str
    usuario_email: EmailStr
    usuario_senha: str

    @field_validator("email", "usuario_email", mode="before")
    @classmethod
    def normalizar_emails(cls, v):
        return v.lower().strip() if isinstance(v, str) else v


class EmpresaAdminOut(BaseModel):
    id: int
    nome: str
    email: Optional[str]
    telefone: Optional[str]
    telefone_operador: Optional[str]
    logo_url: Optional[str]
    cor_primaria: Optional[str]
    ativo: bool
    criado_em: datetime
    total_orcamentos: int = 0
    total_clientes: int = 0
    total_usuarios: int = 0
    total_mensagens_ia: int = 0
    ultima_atividade_em: Optional[datetime] = None
    # Assinatura (v11)
    plano_id: Optional[int] = None
    plano: str = "trial"
    assinatura_valida_ate: Optional[datetime] = None
    trial_ate: Optional[datetime] = None
    limite_orcamentos_custom: Optional[int] = None
    limite_usuarios_custom: Optional[int] = None
    desativar_ia: bool = False
    desativar_lembretes: bool = False
    desativar_relatorios: bool = False
    cupom_kiwify: Optional[str] = None

    class Config:
        from_attributes = True


class AssinaturaUpdate(BaseModel):
    plano: str  # trial/starter/pro/business (LEGADO)
    plano_id: Optional[int] = None  # NOVO SISTEMA
    assinatura_valida_ate: Optional[datetime] = None
    ativo: Optional[bool] = None


class UsuarioAdminCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, v):
        return v.lower().strip() if isinstance(v, str) else v


class UsuarioEmpresaUpdate(BaseModel):
    """Atualização de usuário pela empresa (todos opcionais)."""

    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    senha: Optional[str] = None
    ativo: Optional[bool] = None  # apenas gestor pode alterar
    is_gestor: Optional[bool] = None  # apenas superadmin via /admin pode alterar
    permissoes: Optional[dict] = None  # JSON de permissões granulares
    papel_id: Optional[int] = None  # papel RBAC; apenas gestor pode alterar
    desconto_max_percent: Optional[int] = (
        None  # limite de desconto em orçamentos; None = usa o da empresa
    )
    telefone_operador: Optional[str] = None  # WhatsApp para acesso ao assistente via WPP


class UsuarioAdminOut(BaseModel):
    id: int
    nome: str
    email: str
    empresa_id: int
    ativo: bool
    is_superadmin: bool
    is_gestor: bool = False
    permissoes: dict = {}
    papel_id: Optional[int] = None
    papel: Optional[PapelResumo] = None
    criado_em: datetime
    ultima_atividade_em: Optional[datetime] = None  # para exibir "online" no frontend
    desconto_max_percent: Optional[int] = (
        None  # limite de desconto em orçamentos; None = usa o da empresa
    )
    telefone_operador: Optional[str] = None

    class Config:
        from_attributes = True


class SuperAdminSetup(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    setup_key: str  # chave secreta para evitar acesso não autorizado

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, v):
        return v.lower().strip() if isinstance(v, str) else v


# ── REGISTRO PÚBLICO (self-service) ────────────────────────────────────────


class RegistroPublico(BaseModel):
    nome: str
    empresa_nome: str
    email: EmailStr
    telefone: str  # WhatsApp para receber as credenciais

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, v):
        return v.lower().strip() if isinstance(v, str) else v


# ── MÓDULO COMERCIAL (CRM interno) ─────────────────────────────────────────

from app.models.models import (
    StatusPipeline,
    OrigemLead,
    SegmentoLead,
    InteressePlano,
    TipoInteracao,
    CanalInteracao,
    LeadScore,
    TipoTemplate,
    CanalTemplate,
    StatusLembrete,
    CanalSugerido,
)


# ── Segmentos ────────────────────────────────────────────────────────────────


class SegmentCreate(BaseModel):
    nome: str


class SegmentUpdate(BaseModel):
    nome: Optional[str] = None
    ativo: Optional[bool] = None


class SegmentOut(BaseModel):
    id: int
    nome: str
    ativo: bool
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Origens de Lead ──────────────────────────────────────────────────────────


class LeadSourceCreate(BaseModel):
    nome: str


class LeadSourceUpdate(BaseModel):
    nome: Optional[str] = None
    ativo: Optional[bool] = None


class LeadSourceOut(BaseModel):
    id: int
    nome: str
    ativo: bool
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Templates ────────────────────────────────────────────────────────────────


class TemplateCreate(BaseModel):
    nome: str
    tipo: TipoTemplate
    canal: CanalTemplate
    assunto: Optional[str] = None
    conteudo: str


class TemplateUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[TipoTemplate] = None
    canal: Optional[CanalTemplate] = None
    assunto: Optional[str] = None
    conteudo: Optional[str] = None
    ativo: Optional[bool] = None


class TemplateOut(BaseModel):
    id: int
    nome: str
    tipo: TipoTemplate
    canal: CanalTemplate
    assunto: Optional[str] = None
    conteudo: str
    ativo: bool
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    @field_serializer("canal", "tipo")
    def serialize_enum(self, v) -> str:
        return v.value if hasattr(v, "value") else str(v)

    class Config:
        from_attributes = True


# ── Lembretes ────────────────────────────────────────────────────────────────


class ReminderCreate(BaseModel):
    lead_id: int
    titulo: str
    descricao: Optional[str] = None
    data_hora: datetime
    canal_sugerido: Optional[CanalSugerido] = None


class ReminderUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    data_hora: Optional[datetime] = None
    status: Optional[StatusLembrete] = None
    canal_sugerido: Optional[CanalSugerido] = None


class ReminderOut(BaseModel):
    id: int
    lead_id: int
    titulo: str
    descricao: Optional[str] = None
    data_hora: datetime
    status: StatusLembrete
    canal_sugerido: Optional[CanalSugerido] = None
    criado_em: datetime
    concluido_em: Optional[datetime] = None
    lead_nome_empresa: Optional[str] = None
    lead_nome_responsavel: Optional[str] = None

    class Config:
        from_attributes = True


# ── Configurações do Comercial ───────────────────────────────────────────────


class CommercialConfigUpdate(BaseModel):
    link_demo: Optional[str] = None
    link_proposta: Optional[str] = None
    assinatura_comercial: Optional[str] = None
    canal_preferencial: Optional[str] = None
    textos_auxiliares: Optional[str] = None


class CommercialConfigOut(BaseModel):
    id: int
    link_demo: Optional[str] = None
    link_proposta: Optional[str] = None
    assinatura_comercial: Optional[str] = None
    canal_preferencial: str = "whatsapp"
    textos_auxiliares: Optional[str] = None
    atualizado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Leads ────────────────────────────────────────────────────────────────────


class CommercialLeadBase(BaseModel):
    nome_responsavel: str
    nome_empresa: str
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    cidade: Optional[str] = None
    segmento_id: Optional[int] = None
    origem_lead_id: Optional[int] = None
    interesse_plano: Optional[InteressePlano] = None
    valor_proposto: Optional[Decimal] = None
    status_pipeline: str = "novo"
    lead_score: LeadScore = LeadScore.FRIO
    observacoes: Optional[str] = None
    proximo_contato_em: Optional[datetime] = None


class CommercialLeadCreate(CommercialLeadBase):
    pass


class CommercialLeadUpdate(BaseModel):
    """Atualização parcial do lead."""

    nome_responsavel: Optional[str] = None
    nome_empresa: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    cidade: Optional[str] = None
    segmento_id: Optional[int] = None
    origem_lead_id: Optional[int] = None
    interesse_plano: Optional[InteressePlano] = None
    valor_proposto: Optional[Decimal] = None
    status_pipeline: Optional[str] = None
    lead_score: Optional[LeadScore] = None
    observacoes: Optional[str] = None
    proximo_contato_em: Optional[datetime] = None
    ativo: Optional[bool] = None
    empresa_id: Optional[int] = None


class CommercialLeadOut(BaseModel):
    id: int
    nome_responsavel: str
    nome_empresa: str
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    cidade: Optional[str] = None
    segmento_id: Optional[int] = None
    origem_lead_id: Optional[int] = None
    segmento_nome: Optional[str] = None
    origem_nome: Optional[str] = None
    interesse_plano: Optional[InteressePlano] = None
    valor_proposto: Optional[Decimal] = None
    status_pipeline: str
    lead_score: Optional[LeadScore] = None
    observacoes: Optional[str] = None
    proximo_contato_em: Optional[datetime] = None
    ultimo_contato_em: Optional[datetime] = None
    ativo: bool = True
    criado_em: datetime
    atualizado_em: Optional[datetime] = None
    # Novos campos para vínculo com empresa
    empresa_id: Optional[int] = None
    conta_criada_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class UsuarioLeadOut(BaseModel):
    """Dados resumidos do usuário para display no lead."""

    id: int
    nome: str
    email: str
    ultima_atividade_em: Optional[datetime] = None
    ativo: bool = True

    class Config:
        from_attributes = True


class EmpresaLeadOut(BaseModel):
    """Dados da empresa vinculada ao lead."""

    id: int
    nome: str
    plano: Optional[str] = None
    ativo: bool = True
    trial_ate: Optional[datetime] = None
    assinatura_valida_ate: Optional[datetime] = None
    ultima_atividade_em: Optional[datetime] = None
    usuarios: List[UsuarioLeadOut] = []
    total_orcamentos: int = 0
    orcamentos_aprovados: int = 0
    orcamentos_pendentes: int = 0

    class Config:
        from_attributes = True


class LeadCompletoOut(CommercialLeadOut):
    """Lead completo com dados da empresa vinculada."""

    empresa: Optional[EmpresaLeadOut] = None

    class Config:
        from_attributes = True


class CriarEmpresaFromLeadRequest(BaseModel):
    """Request para criar empresa a partir de um lead."""

    pass


class ReenviarSenhaResponse(BaseModel):
    """Response para reenvio de senha."""

    sucesso: bool
    mensagem: str


class CommercialInteractionBase(BaseModel):
    tipo: TipoInteracao
    canal: Optional[CanalInteracao] = None
    conteudo: Optional[str] = None
    status_envio: str = "enviado"


class CommercialInteractionCreate(CommercialInteractionBase):
    lead_id: int


class CommercialInteractionOut(CommercialInteractionBase):
    id: int
    lead_id: int
    criado_em: datetime
    enviado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str


class PipelineStageCreate(BaseModel):
    slug: str
    label: str
    cor: str = "#94a3b8"
    emoji: str = ""
    ordem: int = 0
    fechado: bool = False


class PipelineStageUpdate(BaseModel):
    label: Optional[str] = None
    cor: Optional[str] = None
    emoji: Optional[str] = None
    ordem: Optional[int] = None
    ativo: Optional[bool] = None
    fechado: Optional[bool] = None


class PipelineStageOut(BaseModel):
    id: int
    slug: str
    label: str
    cor: str = "#94a3b8"
    emoji: str = ""
    ordem: int = 0
    ativo: bool = True
    fechado: bool = False

    class Config:
        from_attributes = True


class PipelineStageReorder(BaseModel):
    id: int
    ordem: int


class WhatsAppSend(BaseModel):
    mensagem: str
    template_id: Optional[int] = None


class EmailSend(BaseModel):
    assunto: str
    mensagem: str
    template_id: Optional[int] = None


class DashboardMetrics(BaseModel):
    total_leads: int
    novos: int
    propostas_enviadas: int
    negociacoes: int
    fechados_ganho: int
    fechados_perdido: int
    follow_ups_hoje: int
    lembretes_pendentes: int = 0
    leads_sem_contato: int = 0
    propostas_sem_retorno: int = 0
    empresas_em_trial: int = 0


class LeadWithInteractions(CommercialLeadOut):
    interacoes: List[CommercialInteractionOut] = []
    lembretes: List[ReminderOut] = []


class TemplatePreview(BaseModel):
    """Preview de template com variáveis renderizadas."""

    assunto: Optional[str] = None
    conteudo: str


# ── IMPORTAÇÃO DE LEADS ───────────────────────────────────────────────────────


class LeadImportItem(BaseModel):
    """Item individual de importação de lead."""

    nome_responsavel: str
    nome_empresa: str
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    cidade: Optional[str] = None
    observacoes: Optional[str] = None


class LeadImportRequest(BaseModel):
    """Requisição para importação de leads."""

    metodo: str = Field(..., description="Método de importação: 'colar' ou 'csv'")
    dados: str = Field(..., description="Texto colado ou base64 do CSV")
    segmento_id: Optional[int] = Field(None, description="ID do segmento padrão")
    origem_lead_id: Optional[int] = Field(
        None, description="ID da origem (padrão: Importação em Massa)"
    )
    campaign_id: Optional[int] = Field(
        None, description="ID da campanha para vincular os leads importados"
    )


class LeadImportResponse(BaseModel):
    """Resposta da importação de leads."""

    total_importados: int
    total_validos: int
    total_invalidos: int
    leads_criados: List[CommercialLeadOut]
    erros: List[str]


class LeadImportPreview(BaseModel):
    """Preview dos leads antes da importação."""

    leads: List[LeadImportItem]
    total: int
    duplicatas: int
    invalidos: int


# ── CAMPANHAS ────────────────────────────────────────────────────────────────


class CampaignCreate(BaseModel):
    """Criação de campanha de disparo."""

    nome: str
    template_id: int
    canal: str = Field(..., description="Canal: whatsapp, email ou ambos")
    lead_ids: List[int] = Field(..., description="IDs dos leads para disparo")


class CampaignUpdate(BaseModel):
    """Atualização de campanha."""

    nome: Optional[str] = None
    template_id: Optional[int] = None
    canal: Optional[str] = None
    status: Optional[str] = None


class CampaignOut(BaseModel):
    """Campanha retornada na API."""

    id: int
    nome: str
    template_id: int
    canal: str
    status: str
    total_leads: int
    enviados: int
    entregues: int
    respondidos: int
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class CampaignLeadOut(BaseModel):
    """Resultado de disparo para um lead específico."""

    id: int
    campaign_id: int
    lead_id: int
    status: str
    data_envio: Optional[datetime] = None
    data_entrega: Optional[datetime] = None
    data_resposta: Optional[datetime] = None
    lead_nome_empresa: Optional[str] = None
    lead_nome_responsavel: Optional[str] = None

    class Config:
        from_attributes = True


class CampaignMetrics(BaseModel):
    """Métricas de campanha."""

    total_leads: int
    enviados: int
    entregues: int
    respondidos: int
    taxa_entrega: float
    taxa_resposta: float
    leads_por_status: dict


class CampaignDisparoRequest(BaseModel):
    """Requisição para disparo de campanha."""

    campaign_id: int
    lead_ids: Optional[List[int]] = (
        None  # Se None, dispara para todos os leads da campanha
    )
    canal: Optional[str] = None  # Se None, usa o canal da campanha


# ── BROADCAST ────────────────────────────────────────────────────────────────


class BroadcastCreate(BaseModel):
    """Criação de broadcast pelo superadmin."""

    mensagem: str = Field(..., min_length=1, max_length=2000)
    tipo: str = Field(default="info", pattern="^(info|aviso|urgente)$")
    expira_em: Optional[datetime] = None


class BroadcastOut(BaseModel):
    """Resposta de broadcast."""

    id: int
    mensagem: str
    tipo: str
    ativo: bool
    criado_em: datetime
    expira_em: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── TEMPLATES DE SEGMENTO ─────────────────────────────────────────────────────


class TemplateSegmentoOut(BaseModel):
    """Resumo de um segmento disponível."""

    slug: str
    nome: str
    descricao: str


class TemplateDetalheOut(BaseModel):
    """Detalhe completo de um template de segmento."""

    slug: str
    nome: str
    descricao: str
    categorias: List[str]
    servicos: List[dict]


class TemplateImportResult(BaseModel):
    """Resultado da importação de um template."""

    segmento: str
    categorias_criadas: int
    servicos_criados: int


# ── PROPOSTAS PÚBLICAS ───────────────────────────────────────────────────────


class BlocoProposta(BaseModel):
    """Configuração de um bloco da proposta."""
    tipo: str
    ativo: bool = True
    ordem: int
    config: Optional[dict] = None


class VariavelProposta(BaseModel):
    """Definição de uma variável personalizável."""
    nome: str  # ex: "empresa"
    label: str  # ex: "Nome da Empresa"
    tipo: str = "texto"  # texto, numero, data
    obrigatorio: bool = False
    valor_padrao: Optional[str] = None


class PropostaPublicaCreate(BaseModel):
    """Criação de proposta pública."""
    nome: str = Field(..., min_length=1, max_length=150)
    blocos: Optional[List[BlocoProposta]] = None
    variaveis: Optional[List[VariavelProposta]] = None


class PropostaPublicaUpdate(BaseModel):
    """Atualização de proposta pública."""
    nome: Optional[str] = Field(None, min_length=1, max_length=150)
    blocos: Optional[List[BlocoProposta]] = None
    variaveis: Optional[List[VariavelProposta]] = None
    ativo: Optional[bool] = None


class PropostaPublicaOut(BaseModel):
    """Resposta de proposta pública."""
    id: int
    nome: str
    tipo: str
    blocos: List[dict]
    variaveis: List[dict]
    ativo: bool
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class PropostaEnviadaCreate(BaseModel):
    """Envio de proposta para lead."""
    proposta_publica_id: int
    dados_personalizados: dict
    validade_dias: int = Field(default=7, ge=1, le=365)


class PropostaPublicaResumoOut(BaseModel):
    """Resumo do template de proposta pública."""
    id: int
    nome: str

    class Config:
        from_attributes = True


class PropostaEnviadaOut(BaseModel):
    """Resposta de proposta enviada."""
    id: int
    proposta_publica_id: int
    proposta_template: Optional[PropostaPublicaResumoOut] = None
    lead_id: int
    slug: str
    dados_personalizados: dict
    validade_dias: int
    expira_em: Optional[datetime] = None
    status: str
    aceita_em: Optional[datetime] = None
    aceita_por_nome: Optional[str] = None
    aceita_por_email: Optional[str] = None
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class PropostaAceite(BaseModel):
    """Dados de aceite da proposta."""
    nome: str = Field(..., min_length=1, max_length=100)
    email: EmailStr


class PropostaPing(BaseModel):
    """Dados de rastreamento."""
    secao: Optional[str] = None
    tempo: int = Field(default=0, ge=0)


class PropostaVisualizacaoOut(BaseModel):
    """Resposta de visualização."""
    id: int
    proposta_enviada_id: int
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    secao_mais_vista: Optional[str] = None
    tempo_segundos: int
    criado_em: datetime

    class Config:
        from_attributes = True


class PropostaAnalytics(BaseModel):
    """Analytics da proposta enviada."""
    proposta: PropostaEnviadaOut
    total_visualizacoes: int
    tempo_medio_segundos: float
    secao_mais_vista: Optional[str] = None
    visualizacoes: List[PropostaVisualizacaoOut]


class PropostaPublicaView(BaseModel):
    """Dados limitados para página pública."""
    slug: str
    nome: str
    blocos: List[dict]
    dados_personalizados: dict
    validade_dias: int
    expira_em: Optional[datetime] = None
    status: str
    empresa: Optional[dict] = None  # nome, logo, cor

    class Config:
        from_attributes = True
