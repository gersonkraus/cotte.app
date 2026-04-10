from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
    Enum,
    Boolean,
    UniqueConstraint,
    Date,
    Numeric,
    Index,
    JSON,
    text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from decimal import Decimal
import enum
from datetime import date


# ── PACOTES E PLANOS (v11) ──────────────────────────────────────────────────


class ModuloSistema(Base):
    """Ex: 'Financeiro', 'IA Hub', 'WhatsApp Próprio', 'CRM Comercial'"""

    __tablename__ = "modulos_sistema"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, index=True)  # 'financeiro', 'ia', etc.
    descricao = Column(Text, nullable=True)
    acoes = Column(
        JSON, default=["leitura", "escrita", "exclusao", "admin"]
    )  # ações suportadas pelo módulo
    ativo = Column(Boolean, default=True)

    planos = relationship("Plano", secondary="plano_modulos", back_populates="modulos")


class Plano(Base):
    """Pacotes configuráveis pelo SuperAdmin."""

    __tablename__ = "planos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=True)

    # Limites
    limite_usuarios = Column(Integer, default=1)
    limite_orcamentos = Column(Integer, default=50)
    total_mensagem_ia = Column(Integer, default=100)
    total_mensagem_whatsapp = Column(Integer, default=500)

    preco_mensal = Column(Numeric(10, 2), default=0.0)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    modulos = relationship(
        "ModuloSistema", secondary="plano_modulos", back_populates="planos"
    )
    empresas = relationship("Empresa", back_populates="pacote")


class PlanoModulo(Base):
    """Associação Many-to-Many entre Planos e Módulos."""

    __tablename__ = "plano_modulos"

    plano_id = Column(Integer, ForeignKey("planos.id"), primary_key=True)
    modulo_id = Column(Integer, ForeignKey("modulos_sistema.id"), primary_key=True)


# ── ENUMS ──────────────────────────────────────────────────────────────────


class StatusOrcamento(str, enum.Enum):
    RASCUNHO = "rascunho"
    ENVIADO = "enviado"
    APROVADO = "aprovado"
    EM_EXECUCAO = "em_execucao"
    AGUARDANDO_PAGAMENTO = "aguardando_pagamento"
    RECUSADO = "recusado"
    EXPIRADO = "expirado"
    CONCLUIDO = "concluido"


class FormaPagamento(str, enum.Enum):
    A_VISTA = "a_vista"
    PIX = "pix"
    DOIS_X = "2x"
    TRES_X = "3x"
    QUATRO_X = "4x"


# ── ENUMS FINANCEIROS ──────────────────────────────────────────────────────


class TipoPagamento(str, enum.Enum):
    SINAL = "sinal"  # entrada / adiantamento
    PARCELA = "parcela"  # parcela intermediária
    QUITACAO = "quitacao"  # pagamento final / total


class StatusConta(str, enum.Enum):
    PENDENTE = "pendente"
    PARCIAL = "parcial"
    PAGO = "pago"
    VENCIDO = "vencido"
    CANCELADO = "cancelado"


class TipoConta(str, enum.Enum):
    RECEBER = "receber"
    PAGAR = "pagar"


class OrigemRegistro(str, enum.Enum):
    MANUAL = "manual"
    WHATSAPP = "whatsapp"
    ASSISTENTE_IA = "assistente_ia"
    WEBHOOK = "webhook"
    SISTEMA = "sistema"


class StatusPagamentoFinanceiro(str, enum.Enum):
    CONFIRMADO = "confirmado"
    ESTORNADO = "estornado"


class TipoDocumentoEmpresa(str, enum.Enum):
    CERTIFICADO_GARANTIA = "certificado_garantia"
    CONTRATO = "contrato"
    TERMO = "termo"
    DOCUMENTO_TECNICO = "documento_tecnico"
    ANEXO = "anexo"
    OUTRO = "outro"


class StatusDocumentoEmpresa(str, enum.Enum):
    ATIVO = "ativo"
    INATIVO = "inativo"
    ARQUIVADO = "arquivado"


class TipoConteudoDocumento(str, enum.Enum):
    PDF = "pdf"
    HTML = "html"


class ModoAgendamentoOrcamento(str, enum.Enum):
    NAO_USA = "NAO_USA"
    OPCIONAL = "OPCIONAL"
    OBRIGATORIO = "OBRIGATORIO"


class CanalAprovacaoOrcamento(str, enum.Enum):
    """Canal em que o orçamento foi aprovado (painel de pré-agendamento)."""

    PUBLICO = "publico"
    WHATSAPP = "whatsapp"
    MANUAL = "manual"
    IA = "ia"


# ── EMPRESA ────────────────────────────────────────────────────────────────


class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    telefone = Column(String(20))
    telefone_operador = Column(
        String(20), index=True
    )  # número do WhatsApp que cria orçamentos
    email = Column(String(100))
    logo_url = Column(String(300))
    cor_primaria = Column(String(7), default="#00e5a0")  # hex
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    # Configurações de orçamento (#10)
    validade_padrao_dias = Column(
        Integer, default=7
    )  # validade padrão ao criar orçamentos
    agendamento_modo_padrao = Column(
        Enum(ModoAgendamentoOrcamento, values_callable=lambda e: [m.value for m in e]),
        default=ModoAgendamentoOrcamento.NAO_USA,
        nullable=False,
    )  # padrão ao abrir modal de novo orçamento (quando não exige escolha explícita)
    agendamento_escolha_obrigatoria = Column(
        Boolean,
        default=False,
        nullable=False,
    )  # True: operador deve escolher Sim/Não a cada orçamento (sem padrão automático)
    desconto_max_percent = Column(
        Integer, default=100
    )  # desconto percentual máximo permitido (ex.: 100 = até 100%)
    # Lembretes automáticos (#3)
    lembrete_dias = Column(
        Integer, nullable=True
    )  # None = desativado; N = dias após envio para lembrar cliente
    lembrete_texto = Column(
        Text, nullable=True
    )  # None = usa texto padrão; variáveis: {cliente_nome}, {numero_orc}, {empresa_nome}, {link}
    # Legado (deprecated): mantido por compatibilidade de schema, sem uso ativo.
    notif_email_aprovado = Column(Boolean, default=True)
    notif_email_expirado = Column(Boolean, default=False)
    anexar_pdf_email = Column(
        Boolean, default=False
    )  # anexa PDF automaticamente no envio por e-mail
    assinatura_email = Column(
        Text, nullable=True
    )  # assinatura personalizada no rodapé dos e-mails ao cliente
    # Mensagem de boas-vindas via WhatsApp
    msg_boas_vindas = Column(
        Text, nullable=True
    )  # texto configurável; None = usa padrão
    boas_vindas_ativo = Column(
        Boolean, default=True
    )  # habilita/desabilita mensagem automática de boas-vindas
    # Overrides por empresa (limites e permissões além do plano)
    limite_orcamentos_custom = Column(
        Integer, nullable=True
    )  # None = usa limite do plano
    limite_usuarios_custom = Column(
        Integer, nullable=True
    )  # None = usa limite do plano
    desativar_ia = Column(Boolean, default=False)
    assistente_instrucoes = Column(
        Text, nullable=True
    )  # guardrails/instruções da empresa para o assistente IA
    desativar_lembretes = Column(Boolean, default=False)
    desativar_relatorios = Column(Boolean, default=False)
    # Automação de status de orçamento
    auto_status_orcamento = Column(
        Boolean, default=True
    )  # ativa transições automáticas de status (agendamento/pagamento)
    agendamento_exige_pagamento_100 = Column(
        Boolean, default=False
    )  # bloqueia confirmação de agendamento sem pagamento 100%
    utilizar_agendamento_automatico = Column(
        Boolean, default=True, nullable=False
    )  # cria agendamento com opções ao aprovar orçamento (OPCIONAL/OBRIGATORIO)
    agendamento_opcoes_somente_apos_liberacao = Column(
        Boolean, default=False, nullable=False
    )  # True: não gera opções na aprovação; entra na fila até liberação manual
    # Numeração de orçamentos personalizável (z011)
    numero_prefixo = Column(
        String(20), default="ORC"
    )  # prefixo padrão (ex: ORC, PROP, COT)
    numero_incluir_ano = Column(
        Boolean, default=True
    )  # incluir ano de 2 dígitos no número
    numero_prefixo_aprovado = Column(
        String(20), nullable=True
    )  # prefixo após aprovação (ex: PED); None = não renomeia
    # Assinatura Kiwify (v8)
    plano_id = Column(
        Integer, ForeignKey("planos.id"), nullable=True
    )  # Vínculo com novo sistema de planos
    plano = Column(String(20), default="trial")  # trial/starter/pro/business (LEGADO)
    assinatura_valida_ate = Column(
        DateTime(timezone=True), nullable=True
    )  # None = sem vencimento
    trial_ate = Column(DateTime(timezone=True), nullable=True)
    cupom_kiwify = Column(String(100), nullable=True)  # último cupom usado na compra
    # WhatsApp próprio (planos Pro/Business)
    whatsapp_proprio_ativo = Column(
        Boolean, default=False
    )  # recurso habilitado pela empresa
    evolution_instance = Column(
        String(100), nullable=True, unique=True
    )  # ex: "empresa-42"
    whatsapp_numero = Column(
        String(20), nullable=True
    )  # número confirmado após conexão
    whatsapp_conectado = Column(
        Boolean, default=False
    )  # True quando o QR code foi lido
    # Comunicação na página pública do orçamento (Configurações → Comunicação)
    descricao_publica_empresa = Column(Text, nullable=True)  # card "Sobre a empresa"
    texto_aviso_aceite = Column(
        Text, nullable=True
    )  # aviso no modal de confirmação de aceite
    mostrar_botao_whatsapp = Column(
        Boolean, default=True
    )  # exibir botão "Tirar dúvidas pelo WhatsApp"
    texto_assinatura_proposta = Column(
        String(200), nullable=True
    )  # ex.: "Proposta elaborada por"
    mensagem_confianca_proposta = Column(
        Text, nullable=True
    )  # mensagem de confiança antes dos botões de ação
    mostrar_mensagem_confianca = Column(
        Boolean, default=True
    )  # exibir ou não a mensagem de confiança
    exigir_otp_aceite = Column(
        Boolean, default=False
    )  # confirmar identidade por SMS/email no aceite público
    otp_valor_minimo = Column(
        Numeric(10, 2), default=0.0
    )  # exige OTP apenas se o orçamento for >= que este valor
    # Notificações internas via WhatsApp
    notif_whats_visualizacao = Column(
        Boolean, default=True
    )  # envia WhatsApp ao operador quando cliente abre o link
    # PIX padrão da empresa (pré-preenche o formulário de PIX nos orçamentos)
    pix_chave_padrao = Column(String(200), nullable=True)  # chave PIX padrão
    pix_tipo_padrao = Column(
        String(20), nullable=True
    )  # cpf | cnpj | email | telefone | aleatoria
    pix_titular_padrao = Column(String(150), nullable=True)  # nome do titular da conta
    # Monitoramento SaaS
    ultima_atividade_em = Column(DateTime(timezone=True), nullable=True)
    total_mensagens_ia = Column(Integer, default=0)
    total_mensagens_whatsapp = Column(Integer, default=0)
    # Template da página pública do orçamento
    template_publico = Column(
        String(50), default="classico"
    )  # moderno | classico — define o layout da página pública /o/{hash}
    # Template do PDF do orçamento
    template_orcamento = Column(
        String(50), default="classico"
    )  # moderno | classico — define o layout do PDF gerado
    enviar_pdf_whatsapp = Column(
        Boolean, default=False
    )  # se true, anexa o arquivo PDF no disparo do WhatsApp

    pacote = relationship("Plano", back_populates="empresas")
    papeis = relationship("Papel", back_populates="empresa", order_by="Papel.nome")
    usuarios = relationship(
        "Usuario", back_populates="empresa", cascade="all, delete-orphan"
    )
    clientes = relationship(
        "Cliente", back_populates="empresa", cascade="all, delete-orphan"
    )
    orcamentos = relationship(
        "Orcamento", back_populates="empresa", cascade="all, delete-orphan"
    )
    servicos = relationship(
        "Servico", back_populates="empresa", cascade="all, delete-orphan"
    )
    notificacoes = relationship(
        "Notificacao", back_populates="empresa", cascade="all, delete-orphan"
    )
    documentos = relationship(
        "DocumentoEmpresa", back_populates="empresa", cascade="all, delete-orphan"
    )
    bancos_pix = relationship(
        "BancoPIXEmpresa", back_populates="empresa", cascade="all, delete-orphan"
    )


class BancoPIXEmpresa(Base):
    """Cadastro de contas/bancos da empresa com chave PIX associada."""

    __tablename__ = "bancos_pix_empresa"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)

    nome_banco = Column(String(100), nullable=False)  # Ex.: Nubank, Itaú, Caixa
    apelido = Column(String(100), nullable=True)  # Ex.: Conta principal, PJ Nubank

    # Dados opcionais da conta bancária (caso queira exibir no futuro)
    agencia = Column(String(20), nullable=True)
    conta = Column(String(30), nullable=True)
    tipo_conta = Column(String(30), nullable=True)  # corrente, poupanca, etc.

    # Dados de PIX
    pix_tipo = Column(
        String(20), nullable=True
    )  # cpf | cnpj | email | telefone | aleatoria
    pix_chave = Column(String(200), nullable=True)
    pix_titular = Column(String(150), nullable=True)

    padrao_pix = Column(
        Boolean, default=False, nullable=False
    )  # se true, é o PIX padrão da empresa

    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="bancos_pix")


# ── PAPÉIS (RBAC) ──────────────────────────────────────────────────────────


class Papel(Base):
    """Papel/role de acesso por empresa. Ex: Gestor, Vendedor, Financeiro."""

    __tablename__ = "papeis"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    nome = Column(String(100), nullable=False)
    slug = Column(String(50), nullable=False)
    descricao = Column(String(500), nullable=True)
    # Lista de strings "modulo:acao", ex: ["financeiro:leitura", "orcamentos:escrita"]
    permissoes = Column(JSON, default=[])
    is_default = Column(Boolean, default=False)  # papel padrão para novos usuários
    is_sistema = Column(
        Boolean, default=False
    )  # criado pelo seed, não pode ser excluído
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="papeis")
    usuarios = relationship("Usuario", back_populates="papel")

    __table_args__ = (
        UniqueConstraint("empresa_id", "slug", name="uq_papel_empresa_slug"),
    )


# ── USUÁRIO ────────────────────────────────────────────────────────────────


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    senha_hash = Column(String(200), nullable=False)
    ativo = Column(Boolean, default=True)
    is_superadmin = Column(Boolean, default=False)
    is_gestor = Column(Boolean, default=False)
    permissoes = Column(
        JSON, default={}
    )  # { "catalogo": "escrita", "financeiro": "leitura" }
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    ultima_atividade_em = Column(
        DateTime(timezone=True), nullable=True
    )  # atualizado a cada request autenticado
    token_versao = Column(
        Integer, default=0
    )  # incrementado a cada login; invalida tokens antigos (uma sessão por usuário)
    reset_senha_token_hash = Column(String(64), nullable=True)
    reset_senha_expira_em = Column(DateTime(timezone=True), nullable=True)
    # Desconto máximo em orçamentos (por usuário); None = usa o da empresa
    desconto_max_percent = Column(Integer, nullable=True)
    # Papel/role do usuário (RBAC); None = usa permissoes JSON legado
    papel_id = Column(Integer, ForeignKey("papeis.id"), nullable=True)
    # WhatsApp individual do operador — permite acesso ao assistente via WPP
    telefone_operador = Column(String(20), nullable=True, index=True)

    empresa = relationship("Empresa", back_populates="usuarios")
    papel = relationship("Papel", back_populates="usuarios")
    orcamentos = relationship(
        "Orcamento", back_populates="criado_por", foreign_keys="Orcamento.criado_por_id"
    )


# ── AUDIT LOG ──────────────────────────────────────────────────────────────


class AuditLog(Base):
    """Registro imutável de ações sensíveis no sistema."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    usuario_nome = Column(String(100), nullable=True)
    acao = Column(
        String(100), nullable=False
    )  # ex: "usuario_criado", "orcamento_aprovado"
    recurso = Column(String(100), nullable=True)  # ex: "orcamento", "usuario"
    recurso_id = Column(String(50), nullable=True)  # id do objeto afetado
    detalhes = Column(Text, nullable=True)  # JSON livre com contexto adicional
    ip = Column(String(50), nullable=True)
    criado_em = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


# ── CLIENTE ────────────────────────────────────────────────────────────────


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    criado_por_id = Column(
        Integer, ForeignKey("usuarios.id"), nullable=True, index=True
    )
    nome = Column(String(150), nullable=False)
    telefone = Column(String(20), index=True)
    email = Column(String(100))
    # Endereço composto (mantido para compatibilidade)
    endereco = Column(String(500))
    # Campos individuais de endereço
    cep = Column(String(9))
    logradouro = Column(String(200))
    numero = Column(String(20))
    complemento = Column(String(100))
    bairro = Column(String(100))
    cidade = Column(String(100))
    estado = Column(String(2))
    observacoes = Column(Text)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    # Campos fiscais
    tipo_pessoa = Column(String(2), nullable=True, default="PF")  # PF ou PJ
    cpf = Column(String(14), nullable=True)
    cnpj = Column(String(18), nullable=True)
    razao_social = Column(String(200), nullable=True)
    nome_fantasia = Column(String(200), nullable=True)
    inscricao_estadual = Column(String(20), nullable=True)
    inscricao_municipal = Column(String(20), nullable=True)

    empresa = relationship("Empresa", back_populates="clientes")
    criado_por = relationship("Usuario", foreign_keys=[criado_por_id])
    orcamentos = relationship("Orcamento", back_populates="cliente")


# ── CONFIGURAÇÕES GLOBAIS DA PLATAFORMA ─────────────────────────────────────


class ConfigGlobal(Base):
    __tablename__ = "config_global"

    chave = Column(String(100), primary_key=True)
    valor = Column(Text, nullable=True)


# ── CATEGORIAS DO CATÁLOGO ──────────────────────────────────────────────────


class CategoriaCatalogo(Base):
    __tablename__ = "categorias_catalogo"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    nome = Column(String(100), nullable=False)

    servicos = relationship("Servico", back_populates="categoria")


# ── SERVIÇO (catálogo) ─────────────────────────────────────────────────────


class Servico(Base):
    __tablename__ = "servicos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    nome = Column(String(200), nullable=False)
    descricao = Column(Text)
    preco_padrao = Column(Numeric(10, 2), default=0.0)
    preco_custo = Column(Numeric(10, 2), nullable=True)
    unidade = Column(String(30), default="un")  # un, m², hora, etc.
    ativo = Column(Boolean, default=True)
    imagem_url = Column(String(300))
    categoria_id = Column(Integer, ForeignKey("categorias_catalogo.id"), nullable=True)

    empresa = relationship("Empresa", back_populates="servicos")
    categoria = relationship("CategoriaCatalogo", back_populates="servicos")


# ── DOCUMENTOS DA EMPRESA ───────────────────────────────────────────────────


class DocumentoEmpresa(Base):
    __tablename__ = "documentos_empresa"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id", "slug", name="uq_documentos_empresa_empresa_slug"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    nome = Column(String(200), nullable=False)
    slug = Column(String(220), nullable=True)
    tipo = Column(
        Enum(
            TipoDocumentoEmpresa,
            name="tipo_documento_empresa",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=TipoDocumentoEmpresa.OUTRO,
    )
    descricao = Column(Text, nullable=True)

    arquivo_path = Column(String(500), nullable=True)
    arquivo_nome_original = Column(String(255), nullable=True)
    mime_type = Column(String(120), nullable=True)
    tamanho_bytes = Column(Integer, nullable=True)

    tipo_conteudo = Column(
        Enum(
            TipoConteudoDocumento,
            name="tipo_conteudo_documento",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=TipoConteudoDocumento.PDF,
    )
    conteudo_html = Column(Text, nullable=True)
    variaveis_suportadas = Column(JSON, nullable=True)

    versao = Column(String(50), nullable=True)
    status = Column(
        Enum(
            StatusDocumentoEmpresa,
            name="status_documento_empresa",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=StatusDocumentoEmpresa.ATIVO,
    )
    permite_download = Column(Boolean, default=True)
    visivel_no_portal = Column(Boolean, default=True)

    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())
    deletado_em = Column(DateTime(timezone=True), nullable=True)

    empresa = relationship("Empresa", back_populates="documentos")
    criado_por = relationship("Usuario")
    orcamentos = relationship("OrcamentoDocumento", back_populates="documento")


class OrcamentoDocumento(Base):
    __tablename__ = "orcamento_documentos"
    __table_args__ = (
        UniqueConstraint(
            "orcamento_id",
            "documento_id",
            name="uq_orcamento_documentos_orcamento_documento",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    orcamento_id = Column(
        Integer,
        ForeignKey("orcamentos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    documento_id = Column(
        Integer,
        ForeignKey("documentos_empresa.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    ordem = Column(Integer, default=0)
    exibir_no_portal = Column(Boolean, default=True)
    enviar_por_email = Column(Boolean, default=False)
    enviar_por_whatsapp = Column(Boolean, default=False)
    obrigatorio = Column(Boolean, default=False)

    documento_nome = Column(String(200), nullable=False)
    documento_tipo = Column(String(50), nullable=True)
    documento_versao = Column(String(50), nullable=True)
    arquivo_path = Column(String(500), nullable=True)
    arquivo_nome_original = Column(String(255), nullable=True)
    mime_type = Column(String(120), nullable=True)
    tamanho_bytes = Column(Integer, nullable=True)
    conteudo_html = Column(
        Text, nullable=True
    )  # Snapshot do conteúdo se tipo_conteudo for HTML
    permite_download = Column(Boolean, default=True)

    # Rastreamento de interação do cliente
    visualizado_em = Column(
        DateTime(timezone=True), nullable=True
    )  # quando cliente abriu o documento
    aceito_em = Column(
        DateTime(timezone=True), nullable=True
    )  # quando cliente marcou "Li e aceito"

    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    orcamento = relationship("Orcamento", back_populates="documentos")
    documento = relationship("DocumentoEmpresa", back_populates="orcamentos")


# ── ORÇAMENTO ──────────────────────────────────────────────────────────────


class Orcamento(Base):
    __tablename__ = "orcamentos"
    __table_args__ = (
        UniqueConstraint("empresa_id", "numero", name="uq_orcamentos_empresa_numero"),
        Index(
            "ix_orcamentos_empresa_criado",
            "empresa_id",
            "criado_em",
            postgresql_using="btree",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    numero = Column(String(20), index=True)  # ex: ORC-150-26 (único por empresa)
    status = Column(Enum(StatusOrcamento), default=StatusOrcamento.RASCUNHO)
    forma_pagamento = Column(Enum(FormaPagamento), default=FormaPagamento.PIX)

    observacoes = Column(Text)
    validade_dias = Column(Integer, default=7)
    desconto = Column(Numeric(10, 2), default=0.0)  # valor do desconto
    desconto_tipo = Column(String, default="percentual")  # percentual ou fixo
    total = Column(Numeric(10, 2), default=0.0)  # já com desconto aplicado

    pdf_url = Column(String(300))  # link do PDF gerado
    link_publico = Column(String(100), index=True)  # token de acesso público

    # Origem do orçamento
    origem_whatsapp = Column(Boolean, default=False)
    mensagem_ia = Column(Text)  # texto original enviado pelo usuário

    # Numeração personalizável (z011)
    sequencial_numero = Column(
        Integer, nullable=True
    )  # sequencial puro; número formatado fica em `numero`

    # Rastreamento de visualização (item 2)
    visualizado_em = Column(DateTime(timezone=True))  # 1ª abertura pelo cliente
    visualizacoes = Column(Integer, default=0)  # contador de aberturas

    # Lembrete automático (#3)
    lembrete_enviado_em = Column(
        DateTime(timezone=True)
    )  # quando o lembrete foi enviado ao cliente

    # Linha do tempo (v7)
    enviado_em = Column(
        DateTime(timezone=True)
    )  # quando foi enviado ao cliente via WhatsApp
    recusa_em = Column(DateTime(timezone=True))  # quando o cliente recusou digitalmente
    approved_notification_sent_at = Column(DateTime(timezone=True), nullable=True)
    aceite_pendente_em = Column(
        DateTime(timezone=True), nullable=True
    )  # confirmação de aceite via WhatsApp pendente

    # Aceite digital (item 3)
    aceite_nome = Column(String(150))  # nome digitado pelo cliente
    aceite_em = Column(DateTime(timezone=True))  # timestamp do aceite
    aceite_mensagem = Column(Text)  # mensagem opcional deixada pelo cliente no aceite
    aceite_confirmado_otp = Column(
        Boolean, default=False
    )  # True se o aceite foi confirmado via OTP
    exigir_otp = Column(
        Boolean, default=False
    )  # Força OTP para este orçamento específico
    recusa_motivo = Column(Text)  # motivo informado pelo cliente ao recusar

    # Agendamento
    agendamento_modo = Column(
        Enum(ModoAgendamentoOrcamento, values_callable=lambda e: [m.value for m in e]),
        default=ModoAgendamentoOrcamento.NAO_USA,
        nullable=False,
    )  # NAO_USA | OPCIONAL | OBRIGATORIO

    # Rastreamento de aprovação e fila de pré-agendamento (z018)
    aprovado_canal = Column(String(20), nullable=True)
    aprovado_em = Column(DateTime(timezone=True), nullable=True)
    agendamento_opcoes_pendente_liberacao = Column(Boolean, default=False, nullable=False)
    agendamento_opcoes_liberado_em = Column(DateTime(timezone=True), nullable=True)
    agendamento_opcoes_liberado_por_id = Column(
        Integer, ForeignKey("usuarios.id"), nullable=True
    )
    observacao_liberacao_agendamento = Column(Text, nullable=True)

    # PIX (v9)
    pix_chave = Column(String(200), nullable=True)  # Chave PIX bruta
    pix_tipo = Column(
        String(20), nullable=True
    )  # "cpf", "cnpj", "email", "telefone", "aleatoria"
    pix_titular = Column(String(150), nullable=True)  # Nome do titular da conta
    pix_payload = Column(
        Text, nullable=True
    )  # Payload EMV BRCode completo (Pix Copia e Cola)
    pix_qrcode = Column(Text, nullable=True)  # QR code em base64 (PNG)
    pix_informado_em = Column(
        DateTime(timezone=True), nullable=True
    )  # Quando foi configurado
    valor_sinal_pix = Column(
        Numeric(10, 2), nullable=True
    )  # Valor do sinal PIX em R$ (salvo pelo operador)

    # Status de Pagamento (v9)
    pagamento_recebido_em = Column(
        DateTime(timezone=True), nullable=True
    )  # NULL = não recebido
    pagamento_recebido_por_id = Column(
        Integer, ForeignKey("usuarios.id"), nullable=True
    )  # Quem confirmou (manual)

    # Regra de pagamento (f002) — FK + snapshot
    regra_pagamento_id = Column(
        Integer, ForeignKey("formas_pagamento_config.id"), nullable=True
    )
    regra_pagamento_nome = Column(String(150), nullable=True)  # snapshot do nome
    regra_entrada_percentual = Column(Numeric(5, 2), nullable=True)  # snapshot do %
    regra_entrada_metodo = Column(
        String(30), nullable=True
    )  # 'pix','dinheiro','cartao', etc.
    regra_saldo_percentual = Column(Numeric(5, 2), nullable=True)  # snapshot do %
    regra_saldo_metodo = Column(String(30), nullable=True)
    contas_receber_geradas_em = Column(
        DateTime(timezone=True), nullable=True
    )  # idempotency guard

    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="orcamentos")
    cliente = relationship("Cliente", back_populates="orcamentos")
    criado_por = relationship(
        "Usuario", back_populates="orcamentos", foreign_keys=[criado_por_id]
    )
    itens = relationship(
        "ItemOrcamento", back_populates="orcamento", cascade="all, delete-orphan"
    )
    notificacoes = relationship(
        "Notificacao", back_populates="orcamento", cascade="all, delete-orphan"
    )
    historico = relationship(
        "HistoricoEdicao",
        back_populates="orcamento",
        cascade="all, delete-orphan",
        order_by="HistoricoEdicao.editado_em.desc()",
    )
    logs_email = relationship(
        "LogEmailOrcamento", back_populates="orcamento", cascade="all, delete-orphan"
    )
    documentos = relationship(
        "OrcamentoDocumento",
        back_populates="orcamento",
        cascade="all, delete-orphan",
        order_by="OrcamentoDocumento.ordem.asc()",
    )
    contas_financeiras = relationship(
        "ContaFinanceira",
        back_populates="orcamento",
        order_by="ContaFinanceira.data_criacao",
    )
    pagamentos_financeiros = relationship(
        "PagamentoFinanceiro",
        back_populates="orcamento",
        order_by="PagamentoFinanceiro.data_pagamento",
    )
    regra_pagamento = relationship(
        "FormaPagamentoConfig", foreign_keys=[regra_pagamento_id]
    )
    agendamento_opcoes_liberado_por = relationship(
        "Usuario", foreign_keys=[agendamento_opcoes_liberado_por_id]
    )
    agendamentos = relationship(
        "Agendamento",
        back_populates="orcamento",
        foreign_keys="Agendamento.orcamento_id",
    )


# ── ITEM DO ORÇAMENTO ──────────────────────────────────────────────────────


class ItemOrcamento(Base):
    __tablename__ = "itens_orcamento"

    id = Column(Integer, primary_key=True, index=True)
    orcamento_id = Column(
        Integer, ForeignKey("orcamentos.id"), nullable=False, index=True
    )
    servico_id = Column(
        Integer, ForeignKey("servicos.id"), nullable=True
    )  # vínculo com catálogo
    descricao = Column(String(300), nullable=False)
    quantidade = Column(Numeric(10, 2), default=1.0)
    valor_unit = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)

    orcamento = relationship("Orcamento", back_populates="itens")
    servico = relationship("Servico")

    @property
    def imagem_url(self):
        """URL da imagem do serviço vinculado (catálogo), para exibir no orçamento."""
        if self.servico and getattr(self.servico, "imagem_url", None):
            return self.servico.imagem_url
        return None


# ── HISTÓRICO DE EDIÇÕES ────────────────────────────────────────────────────


class HistoricoEdicao(Base):
    __tablename__ = "historico_edicoes"

    id = Column(Integer, primary_key=True, index=True)
    orcamento_id = Column(
        Integer, ForeignKey("orcamentos.id"), nullable=False, index=True
    )
    editado_por_id = Column(
        Integer, ForeignKey("usuarios.id"), nullable=True
    )  # None = Sistema ou cliente (link/WhatsApp)
    editado_em = Column(DateTime(timezone=True), server_default=func.now())
    descricao = Column(Text)  # ex: "Itens atualizados, novo total R$ 1.200,00"

    orcamento = relationship("Orcamento", back_populates="historico")
    editado_por = relationship("Usuario")


# ── NOTIFICAÇÃO (in-app) ────────────────────────────────────────────────────


class Notificacao(Base):
    __tablename__ = "notificacoes"
    __table_args__ = (
        Index(
            "ix_notificacoes_empresa_lida",
            "empresa_id",
            "lida",
            postgresql_using="btree",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    orcamento_id = Column(
        Integer, ForeignKey("orcamentos.id"), nullable=True
    )  # opcional
    tipo = Column(String(20), nullable=False)  # "aprovado", "recusado", etc.
    titulo = Column(String(200), nullable=False)
    mensagem = Column(Text)
    lida = Column(Boolean, default=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    empresa = relationship("Empresa", back_populates="notificacoes")
    orcamento = relationship("Orcamento", back_populates="notificacoes")


# ── LOG DE ENVIO DE EMAIL ───────────────────────────────────────────────────


class LogEmailOrcamento(Base):
    __tablename__ = "log_email_orcamento"

    id = Column(Integer, primary_key=True, index=True)
    orcamento_id = Column(Integer, ForeignKey("orcamentos.id"), nullable=False)
    destinatario = Column(String(150), nullable=False)  # email do cliente
    status = Column(String(20), default="pendente")  # pendente, enviado, erro
    pdf_anexado = Column(
        Boolean, default=False
    )  # indica se o envio inclui PDF em anexo
    mensagem_erro = Column(Text)  # detalhes do erro, se houver
    tentativas = Column(Integer, default=1)  # número de tentativas de envio
    enviado_em = Column(DateTime(timezone=True))  # quando foi enviado com sucesso
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    orcamento = relationship("Orcamento", back_populates="logs_email")


# ── MÓDULO COMERCIAL (CRM interno) ───────────────────────────────────────────


class StatusPipeline(str, enum.Enum):
    NOVO = "novo"
    CONTATO_INICIADO = "contato_iniciado"
    PROPOSTA_ENVIADA = "proposta_enviada"
    NEGOCIACAO = "negociacao"
    FECHADO_GANHO = "fechado_ganho"
    FECHADO_PERDIDO = "fechado_perdido"


class PipelineStage(Base):
    """Etapas configuráveis do kanban comercial."""

    __tablename__ = "pipeline_stages"

    id = Column(Integer, primary_key=True)
    slug = Column(String(50), unique=True, nullable=False)
    label = Column(String(100), nullable=False)
    cor = Column(String(20), default="#94a3b8")
    emoji = Column(String(10), default="")
    ordem = Column(Integer, default=0)
    ativo = Column(Boolean, default=True)
    fechado = Column(Boolean, default=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())


# Enums legados (mantidos para compatibilidade com migration 002 no banco)
class OrigemLead(str, enum.Enum):
    INDICACAO = "indicacao"
    SITE = "site"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    REDES_SOCIAIS = "redes_sociais"
    LIGACAO = "ligacao"
    EVENTO = "evento"
    OUTRO = "outro"


class SegmentoLead(str, enum.Enum):
    INSTALADOR_AR = "instalador_ar"
    ELETRICISTA = "eletricista"
    PINTOR = "pintor"
    MANUTENCAO = "manutencao"
    OUTRO = "outro"


class InteressePlano(str, enum.Enum):
    TRIAL = "trial"
    STARTER = "starter"
    PRO = "pro"
    BUSINESS = "business"


class LeadScore(str, enum.Enum):
    QUENTE = "quente"
    MORNO = "morno"
    FRIO = "frio"


class TipoTemplate(str, enum.Enum):
    MENSAGEM_INICIAL = "mensagem_inicial"
    FOLLOWUP = "followup"
    PROPOSTA_COMERCIAL = "proposta_comercial"
    EMAIL_COMERCIAL = "email_comercial"


class CanalTemplate(str, enum.Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    AMBOS = "ambos"


class StatusLembrete(str, enum.Enum):
    PENDENTE = "pendente"
    CONCLUIDO = "concluido"
    ATRASADO = "atrasado"


class CanalSugerido(str, enum.Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    LIGACAO = "ligacao"
    REUNIAO = "reuniao"


class TipoInteracao(str, enum.Enum):
    OBSERVACAO = "observacao"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    PROPOSTA = "proposta"
    MUDANCA_STATUS = "mudanca_status"
    LEMBRETE = "lembrete"


class CanalInteracao(str, enum.Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    LIGACAO = "ligacao"
    REUNIAO = "reuniao"
    OUTRO = "outro"


class StatusProposta(str, enum.Enum):
    RASCUNHO = "rascunho"
    ENVIADA = "enviada"
    VISUALIZADA = "visualizada"
    ACEITA = "aceita"
    EXPIRADA = "expirada"
    SUBSTITUIDA = "substituida"


class TipoBlocoProposta(str, enum.Enum):
    HERO = "hero"
    PROBLEMA_SOLUCAO = "problema_solucao"
    FUNCIONALIDADES = "funcionalidades"
    PLANOS_PRECOS = "planos_precos"
    DEPOIMENTOS = "depoimentos"
    ROI_ESTIMADO = "roi_estimado"
    CTA_ACEITE = "cta_aceite"


# ── Cadastros auxiliares do Comercial ─────────────────────────────────────


class CommercialSegment(Base):
    """Segmentos de mercado para leads comerciais."""

    __tablename__ = "commercial_segments"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False, unique=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    leads = relationship("CommercialLead", back_populates="segmento_rel")


class CommercialLeadSource(Base):
    """Origens de lead para o módulo comercial."""

    __tablename__ = "commercial_lead_sources"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False, unique=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    leads = relationship("CommercialLead", back_populates="origem_rel")


# ── Templates do Comercial ────────────────────────────────────────────────


class CommercialTemplate(Base):
    """Modelos/templates de mensagem do módulo comercial."""

    __tablename__ = "commercial_templates"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    tipo = Column(Enum(TipoTemplate), nullable=False)
    canal = Column(Enum(CanalTemplate), nullable=False)
    assunto = Column(String(200), nullable=True)
    conteudo = Column(Text, nullable=False)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())


# ── Lembretes do Comercial ────────────────────────────────────────────────


class CommercialReminder(Base):
    """Lembretes associados a leads comerciais."""

    __tablename__ = "commercial_reminders"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(
        Integer, ForeignKey("commercial_leads.id"), nullable=False, index=True
    )
    titulo = Column(String(200), nullable=False)
    descricao = Column(Text, nullable=True)
    data_hora = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(StatusLembrete), default=StatusLembrete.PENDENTE)
    canal_sugerido = Column(Enum(CanalSugerido), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    concluido_em = Column(DateTime(timezone=True), nullable=True)

    lead = relationship("CommercialLead", back_populates="lembretes")


# ── Configurações do Comercial ────────────────────────────────────────────


class CommercialConfig(Base):
    """Configurações gerais do módulo comercial (singleton-like, 1 row)."""

    __tablename__ = "commercial_config"

    id = Column(Integer, primary_key=True, index=True)
    link_demo = Column(String(300), nullable=True)
    link_proposta = Column(String(300), nullable=True)
    assinatura_comercial = Column(Text, nullable=True)
    canal_preferencial = Column(String(20), default="whatsapp")
    textos_auxiliares = Column(Text, nullable=True)
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())


# ── Propostas Públicas ───────────────────────────────────────────────────────


class PropostaPublica(Base):
    """Templates de propostas públicas interativas."""

    __tablename__ = "propostas_publicas"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    nome = Column(String(150), nullable=False)
    tipo = Column(String(20), default="proposta_publica")
    blocos = Column(JSON, default=list)  # Array ordenado de blocos ativos/inativos
    variaveis = Column(JSON, default=list)  # Campos personalizáveis
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa")
    enviadas = relationship("PropostaEnviada", back_populates="proposta_template")


class PropostaEnviada(Base):
    """Instância de proposta enviada para um lead específico."""

    __tablename__ = "propostas_enviadas"

    id = Column(Integer, primary_key=True, index=True)
    proposta_publica_id = Column(Integer, ForeignKey("propostas_publicas.id"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("commercial_leads.id"), nullable=False, index=True)
    slug = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    dados_personalizados = Column(JSON, default=dict)  # Valores das variáveis
    validade_dias = Column(Integer, default=7)
    expira_em = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(StatusProposta), default=StatusProposta.RASCUNHO)
    aceita_em = Column(DateTime(timezone=True), nullable=True)
    aceita_por_nome = Column(String(100), nullable=True)
    aceita_por_email = Column(String(100), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    proposta_template = relationship("PropostaPublica", back_populates="enviadas")
    lead = relationship("CommercialLead")
    visualizacoes = relationship("PropostaVisualizacao", back_populates="proposta_enviada")


class PropostaVisualizacao(Base):
    """Log de rastreamento de visualizações da proposta."""

    __tablename__ = "propostas_visualizacoes"

    id = Column(Integer, primary_key=True, index=True)
    proposta_enviada_id = Column(Integer, ForeignKey("propostas_enviadas.id"), nullable=False, index=True)
    ip = Column(String(45), nullable=True)  # IPv4 ou IPv6
    user_agent = Column(Text, nullable=True)
    secao_mais_vista = Column(String(50), nullable=True)
    tempo_segundos = Column(Integer, default=0)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    proposta_enviada = relationship("PropostaEnviada", back_populates="visualizacoes")


# ── Lead Comercial (refatorado) ──────────────────────────────────────────


class CommercialLead(Base):
    """Leads do módulo comercial - CRM interno do COTTE."""

    __tablename__ = "commercial_leads"

    id = Column(Integer, primary_key=True, index=True)
    nome_responsavel = Column(String(100), nullable=False)
    nome_empresa = Column(String(150), nullable=False)
    whatsapp = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    cidade = Column(String(100), nullable=True)
    # FKs para cadastros auxiliares
    segmento_id = Column(Integer, ForeignKey("commercial_segments.id"), nullable=True)
    origem_lead_id = Column(
        Integer, ForeignKey("commercial_lead_sources.id"), nullable=True
    )
    # Vínculo com empresa (quando o lead já tem conta criada no sistema)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True, index=True)
    # Data quando a conta foi criada a partir deste lead
    conta_criada_em = Column(DateTime(timezone=True), nullable=True)
    # Campos legados (mantidos para não quebrar migration 002)
    segmento = Column(Enum(SegmentoLead), nullable=True)
    origem_lead = Column(Enum(OrigemLead), default=OrigemLead.OUTRO)
    interesse_plano = Column(Enum(InteressePlano), nullable=True)
    valor_proposto = Column(Numeric(10, 2), nullable=True)
    status_pipeline = Column(String(50), default="novo")
    lead_score = Column(Enum(LeadScore), default=LeadScore.FRIO)
    status_envio = Column(
        String(20), default="nao_enviado"
    )  # nao_enviado, enviado, respondido
    observacoes = Column(Text, nullable=True)
    ultimo_contato_em = Column(DateTime(timezone=True), nullable=True)
    proximo_contato_em = Column(DateTime(timezone=True), nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    segmento_rel = relationship("CommercialSegment", back_populates="leads")
    origem_rel = relationship("CommercialLeadSource", back_populates="leads")
    empresa_rel = relationship("Empresa", foreign_keys=[empresa_id])
    interacoes = relationship(
        "CommercialInteraction",
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="CommercialInteraction.criado_em.desc()",
    )
    lembretes = relationship(
        "CommercialReminder",
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="CommercialReminder.data_hora.desc()",
    )


class CommercialInteraction(Base):
    """Histórico de interações com leads comerciais."""

    __tablename__ = "commercial_interactions"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(
        Integer, ForeignKey("commercial_leads.id"), nullable=False, index=True
    )
    tipo = Column(Enum(TipoInteracao), nullable=False)
    canal = Column(Enum(CanalInteracao), nullable=True)
    conteudo = Column(Text, nullable=True)  # mensagem enviada ou observação
    status_envio = Column(String(20), default="enviado")  # enviado, falha, pendente
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    enviado_em = Column(DateTime(timezone=True), nullable=True)

    lead = relationship("CommercialLead", back_populates="interacoes")


# ── MÓDULO FINANCEIRO ───────────────────────────────────────────────────────


class FormaPagamentoConfig(Base):
    """Formas de pagamento configuráveis por empresa (PIX, Cartão, Dinheiro, etc.)."""

    __tablename__ = "formas_pagamento_config"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    nome = Column(String(100), nullable=False)  # ex: "PIX", "Cartão de Crédito"
    slug = Column(String(50), nullable=False)  # ex: "pix", "cartao_credito"
    icone = Column(String(10), default="💳")  # emoji
    cor = Column(String(7), default="#00e5a0")  # hex
    ativo = Column(Boolean, default=True)
    aceita_parcelamento = Column(Boolean, default=False)
    max_parcelas = Column(Integer, default=1)
    taxa_percentual = Column(Numeric(5, 2), default=0)  # taxa sobre o valor (%)
    gera_pix_qrcode = Column(Boolean, default=False)  # gera QR ao registrar pagamento
    ordem = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Regra de pagamento (f002)
    descricao = Column(Text, nullable=True)
    padrao = Column(Boolean, default=False)  # padrão da empresa
    exigir_entrada_na_aprovacao = Column(
        Boolean, default=False
    )  # cobrar entrada ao aprovar?
    percentual_entrada = Column(Numeric(5, 2), default=Decimal("0"))  # 0–100
    metodo_entrada = Column(
        String(30), nullable=True
    )  # 'pix','dinheiro','cartao','na_execucao','na_entrega','outro'
    percentual_saldo = Column(Numeric(5, 2), default=Decimal("0"))  # 0–100
    metodo_saldo = Column(String(30), nullable=True)
    dias_vencimento_saldo = Column(Integer, nullable=True)  # dias após aprovação
    # Parcelamento do saldo (i001)
    numero_parcelas_saldo = Column(
        Integer, default=1
    )  # ex: 3 → gera 3 parcelas do saldo
    intervalo_dias_parcela = Column(Integer, default=30)  # dias entre parcelas
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    empresa = relationship("Empresa")
    pagamentos = relationship(
        "PagamentoFinanceiro", back_populates="forma_pagamento_config"
    )


class ContaFinanceira(Base):
    """Conta a receber ou a pagar vinculada a um orçamento."""

    __tablename__ = "contas_financeiras"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    orcamento_id = Column(
        Integer, ForeignKey("orcamentos.id"), nullable=True, index=True
    )
    tipo = Column(
        Enum(TipoConta, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=TipoConta.RECEBER,
    )
    descricao = Column(String(300), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)  # valor original
    valor_pago = Column(Numeric(10, 2), default=0)  # soma dos pagamentos confirmados
    status = Column(
        Enum(StatusConta, values_callable=lambda e: [m.value for m in e]),
        default=StatusConta.PENDENTE,
    )
    data_vencimento = Column(Date, nullable=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    categoria = Column(String(100), nullable=True)  # ex: "Serviço", "Material"
    origem = Column(
        Enum(OrigemRegistro, values_callable=lambda e: [m.value for m in e]),
        default=OrigemRegistro.SISTEMA,
    )
    metadata_ia = Column(Text, nullable=True)  # JSON com dados da IA (stub)
    ultima_cobranca_em = Column(DateTime(timezone=True), nullable=True)
    # Campos f002
    metodo_previsto = Column(
        String(30), nullable=True
    )  # 'pix','cartao','na_execucao', etc.
    tipo_lancamento = Column(String(20), nullable=True)  # 'entrada','saldo','integral'
    # Parcelamento real (i001)
    numero_parcela = Column(Integer, nullable=True)  # 1, 2, 3...
    total_parcelas = Column(Integer, nullable=True)  # total do grupo (ex: 3)
    grupo_parcelas_id = Column(
        String(36), nullable=True
    )  # UUID — agrupa parcelas do mesmo orçamento
    favorecido = Column(String(200), nullable=True)  # para despesas sem orçamento
    categoria_slug = Column(
        String(50), nullable=True
    )  # "material", "mao_de_obra", etc.
    data_competencia = Column(Date, nullable=True)  # mês de competência da despesa
    # Soft delete e cancelamento (Sprint 1.2)
    excluido_em = Column(DateTime(timezone=True), nullable=True)
    excluido_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    motivo_exclusao = Column(String(500), nullable=True)
    cancelado_em = Column(DateTime(timezone=True), nullable=True)
    cancelado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    motivo_cancelamento = Column(String(500), nullable=True)

    empresa = relationship("Empresa")
    orcamento = relationship("Orcamento", back_populates="contas_financeiras")
    pagamentos = relationship(
        "PagamentoFinanceiro",
        back_populates="conta",
        order_by="PagamentoFinanceiro.data_pagamento",
    )
    excluido_por = relationship("Usuario", foreign_keys=[excluido_por_id])
    cancelado_por = relationship("Usuario", foreign_keys=[cancelado_por_id])


class PagamentoFinanceiro(Base):
    """Registro de pagamento recebido vinculado a uma conta financeira."""

    __tablename__ = "pagamentos_financeiros"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True, index=True)
    orcamento_id = Column(
        Integer, ForeignKey("orcamentos.id"), nullable=True, index=True
    )
    conta_id = Column(
        Integer, ForeignKey("contas_financeiras.id"), nullable=True, index=True
    )
    forma_pagamento_id = Column(
        Integer, ForeignKey("formas_pagamento_config.id"), nullable=True
    )
    valor = Column(Numeric(10, 2), nullable=False)
    tipo = Column(
        Enum(TipoPagamento, values_callable=lambda e: [m.value for m in e]),
        default=TipoPagamento.QUITACAO,
    )
    data_pagamento = Column(Date, nullable=False)
    confirmado_em = Column(DateTime(timezone=True), server_default=func.now())
    confirmado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    observacao = Column(String(500), nullable=True)
    comprovante_url = Column(String(500), nullable=True)
    origem = Column(
        Enum(OrigemRegistro, values_callable=lambda e: [m.value for m in e]),
        default=OrigemRegistro.MANUAL,
    )
    metadata_ia = Column(Text, nullable=True)  # JSON stub para IA futura
    confianca_ia = Column(Float, nullable=True)  # 0.0–1.0
    parcela_numero = Column(Integer, nullable=True)  # para parcelamentos
    status = Column(
        Enum(StatusPagamentoFinanceiro, values_callable=lambda e: [m.value for m in e]),
        default=StatusPagamentoFinanceiro.CONFIRMADO,
    )
    txid_pix = Column(String(35), nullable=True)  # txid para conciliação futura
    idempotency_key = Column(
        String(128), nullable=True
    )  # chave de deduplicação por empresa

    orcamento = relationship("Orcamento", back_populates="pagamentos_financeiros")
    conta = relationship("ContaFinanceira", back_populates="pagamentos")
    forma_pagamento_config = relationship(
        "FormaPagamentoConfig", back_populates="pagamentos"
    )
    confirmado_por = relationship("Usuario")

    @property
    def forma_pagamento_nome(self) -> str | None:
        return self.forma_pagamento_config.nome if self.forma_pagamento_config else None

    @property
    def forma_pagamento_icone(self) -> str | None:
        return (
            self.forma_pagamento_config.icone if self.forma_pagamento_config else None
        )


class TemplateNotificacao(Base):
    """Templates de mensagem editáveis por empresa para notificações financeiras."""

    __tablename__ = "templates_notificacao"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo = Column(String(50), nullable=False)  # ex: "cobranca_saldo", "confirmacao_pag"
    corpo = Column(Text, nullable=False)
    ativo = Column(Boolean, default=True)
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    empresa = relationship("Empresa")


class HistoricoCobranca(Base):
    """Histórico de cobranças enviadas por WhatsApp/e-mail para contas financeiras."""

    __tablename__ = "historico_cobrancas"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    conta_id = Column(
        Integer, ForeignKey("contas_financeiras.id"), nullable=True, index=True
    )
    enviado_em = Column(DateTime(timezone=True), server_default=func.now())
    canal = Column(String(20), nullable=False)  # "whatsapp" | "email"
    destinatario = Column(String(200), nullable=True)  # número/email
    status = Column(String(20), nullable=False)  # "enviado" | "erro"
    erro = Column(Text, nullable=True)
    mensagem_corpo = Column(Text, nullable=True)

    empresa = relationship("Empresa")
    conta = relationship("ContaFinanceira", backref="historico_cobrancas")


class ConfiguracaoFinanceira(Base):
    """Configurações financeiras por empresa (1 registro por empresa)."""

    __tablename__ = "configuracoes_financeiras"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(
        Integer, ForeignKey("empresas.id"), nullable=False, unique=True, index=True
    )
    dias_vencimento_padrao = Column(Integer, default=7)
    gerar_contas_ao_aprovar = Column(Boolean, default=True)
    automacoes_ativas = Column(Boolean, default=False)
    dias_lembrete_antes = Column(Integer, default=2)
    dias_lembrete_apos = Column(Integer, default=3)
    categorias_despesa = Column(Text, nullable=True)  # JSON list customizável
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    empresa = relationship("Empresa")


# ── MODELOS FASE 2 (SPRINTS 2.1 E 2.2) ─────────────────────────────────────


class MovimentacaoCaixa(Base):
    """Movimentação de caixa - entradas e saídas manuais."""

    __tablename__ = "movimentacoes_caixa"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo = Column(String(10), nullable=False)  # 'entrada', 'saida'
    valor = Column(Numeric(10, 2), nullable=False)
    descricao = Column(String(300), nullable=False)
    categoria = Column(
        String(100), default="geral"
    )  # 'venda', 'despesa', 'transferencia', etc.
    data = Column(Date, nullable=False, default=date.today)
    confirmado = Column(Boolean, default=True)
    comprovante_url = Column(String(500), nullable=True)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    empresa = relationship("Empresa")
    criado_por = relationship("Usuario")


class CategoriaFinanceira(Base):
    """Categorias customizáveis para receitas e despesas."""

    __tablename__ = "categorias_financeiras"
    __table_args__ = (
        Index(
            "uq_categoria_nome_tipo_empresa",
            "empresa_id",
            "nome",
            "tipo",
            unique=True,
            postgresql_where=Column("ativo") == True,
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    nome = Column(String(100), nullable=False)
    tipo = Column(
        String(10), nullable=False, default="despesa"
    )  # 'receita', 'despesa', 'ambos'
    cor = Column(String(7), default="#00e5a0")
    icone = Column(String(10), default="📁")
    ativo = Column(Boolean, default=True)
    ordem = Column(Integer, default=0)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    empresa = relationship("Empresa")


class SaldoCaixaConfig(Base):
    """Configuração de saldo inicial de caixa por empresa."""

    __tablename__ = "saldo_caixa_configs"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(
        Integer, ForeignKey("empresas.id"), nullable=False, unique=True, index=True
    )
    saldo_inicial = Column(Numeric(10, 2), default=0)
    configurado_em = Column(DateTime(timezone=True), server_default=func.now())
    configurado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    empresa = relationship("Empresa")
    configurado_por = relationship("Usuario")


# ── IMPORTAÇÃO DE LEADS ─────────────────────────────────────────────────────


class LeadImportacao(Base):
    """Registro de importações em massa de leads."""

    __tablename__ = "lead_importacoes"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    nome = Column(String(200), nullable=False)  # Nome da importação
    metodo = Column(String(20), nullable=False)  # 'colar' ou 'csv'
    total_importados = Column(Integer, default=0)
    total_validos = Column(Integer, default=0)
    total_invalidos = Column(Integer, default=0)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa")
    criado_por = relationship("Usuario")


class LeadImportacaoItem(Base):
    """Itens individuais de uma importação."""

    __tablename__ = "lead_importacao_itens"

    id = Column(Integer, primary_key=True, index=True)
    importacao_id = Column(
        Integer, ForeignKey("lead_importacoes.id"), nullable=False, index=True
    )
    nome_responsavel = Column(String(100), nullable=False)
    nome_empresa = Column(String(150), nullable=False)
    whatsapp = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    cidade = Column(String(100), nullable=True)
    observacoes = Column(Text, nullable=True)
    status = Column(String(20), default="valido")  # 'valido', 'invalido', 'duplicata'
    erro = Column(Text, nullable=True)
    lead_id = Column(
        Integer, ForeignKey("commercial_leads.id"), nullable=True, index=True
    )
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    importacao = relationship("LeadImportacao")
    lead = relationship("CommercialLead")


# ── CAMPANHAS ───────────────────────────────────────────────────────────────


class Campaign(Base):
    """Campanhas de disparo de propostas em massa."""

    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    nome = Column(String(200), nullable=False)
    template_id = Column(Integer, ForeignKey("commercial_templates.id"), nullable=False)
    canal = Column(String(20), nullable=False)  # 'whatsapp', 'email', 'ambos'
    status = Column(
        String(20), default="agendada"
    )  # 'agendada', 'em_andamento', 'concluida', 'cancelada'
    total_leads = Column(Integer, default=0)
    enviados = Column(Integer, default=0)
    entregues = Column(Integer, default=0)
    respondidos = Column(Integer, default=0)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa")
    template = relationship("CommercialTemplate")


class CampaignLead(Base):
    """Relacionamento entre campanha e lead, com status de disparo."""

    __tablename__ = "campaign_leads"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(
        Integer, ForeignKey("campaigns.id"), nullable=False, index=True
    )
    lead_id = Column(
        Integer, ForeignKey("commercial_leads.id"), nullable=False, index=True
    )
    status = Column(
        String(20), default="pendente"
    )  # 'pendente', 'enviado', 'entregue', 'respondido', 'erro'
    data_envio = Column(DateTime(timezone=True), nullable=True)
    data_entrega = Column(DateTime(timezone=True), nullable=True)
    data_resposta = Column(DateTime(timezone=True), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    campaign = relationship("Campaign")
    lead = relationship("CommercialLead")


class FeedbackAssistente(Base):
    """Avaliações de utilidade das respostas do assistente IA."""

    __tablename__ = "feedback_assistente"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    sessao_id = Column(String(64), nullable=True)
    pergunta = Column(Text, nullable=False)
    resposta = Column(Text, nullable=False)
    avaliacao = Column(String(10), nullable=False)  # 'positivo' | 'negativo'
    comentario = Column(Text, nullable=True)  # campo livre opcional (após 👎)
    modulo_origem = Column(String(50), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    empresa = relationship("Empresa")


class AssistentePreferenciaUsuario(Base):
    """Preferências adaptativas de visualização por usuário para o assistente IA."""

    __tablename__ = "assistente_preferencias_usuario"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    dominio = Column(String(50), nullable=False, default="geral", index=True)
    formato_preferido = Column(
        String(20), nullable=False, default="auto"
    )  # auto|resumo|tabela
    confianca = Column(Float, nullable=False, default=0.5)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa")
    usuario = relationship("Usuario")

    __table_args__ = (
        UniqueConstraint(
            "empresa_id",
            "usuario_id",
            "dominio",
            name="uq_assistente_pref_empresa_usuario_dominio",
        ),
    )


# ── BROADCAST (mensagens do admin para todas as empresas) ─────────────────────


class Broadcast(Base):
    """Mensagem global enviada pelo superadmin para todas as empresas."""

    __tablename__ = "broadcasts"

    id = Column(Integer, primary_key=True, index=True)
    mensagem = Column(Text, nullable=False)
    tipo = Column(String(20), default="info")  # info, aviso, urgente
    ativo = Column(Boolean, default=True)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    expira_em = Column(DateTime(timezone=True), nullable=True)  # NULL = nunca expira

    criado_por = relationship("Usuario")


# ══════════════════════════════════════════════════════════════════════════════
# AGENDAMENTOS
# ══════════════════════════════════════════════════════════════════════════════


class StatusAgendamento(str, enum.Enum):
    AGUARDANDO_ESCOLHA = "aguardando_escolha"
    PENDENTE = "pendente"
    CONFIRMADO = "confirmado"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDO = "concluido"
    REAGENDADO = "reagendado"
    CANCELADO = "cancelado"
    NAO_COMPARECEU = "nao_compareceu"


class TipoAgendamento(str, enum.Enum):
    ENTREGA = "entrega"
    SERVICO = "servico"
    INSTALACAO = "instalacao"
    MANUTENCAO = "manutencao"
    VISITA_TECNICA = "visita_tecnica"
    OUTRO = "outro"


class OrigemAgendamento(str, enum.Enum):
    MANUAL = "manual"
    WHATSAPP = "whatsapp"
    ASSISTENTE_IA = "assistente_ia"
    AUTOMATICO = "automatico"


class Agendamento(Base):
    __tablename__ = "agendamentos"
    __table_args__ = (
        UniqueConstraint("empresa_id", "numero", name="uq_agendamentos_empresa_numero"),
    )

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    orcamento_id = Column(
        Integer, ForeignKey("orcamentos.id"), nullable=True, index=True
    )
    criado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    responsavel_id = Column(
        Integer, ForeignKey("usuarios.id"), nullable=True, index=True
    )

    numero = Column(String(20), index=True)  # ex: AGD-150-01
    status = Column(Enum(StatusAgendamento), default=StatusAgendamento.PENDENTE)
    tipo = Column(Enum(TipoAgendamento), default=TipoAgendamento.SERVICO)
    origem = Column(Enum(OrigemAgendamento), default=OrigemAgendamento.MANUAL)

    data_agendada = Column(
        DateTime(timezone=True), nullable=True
    )  # NULL até cliente escolher
    data_fim = Column(DateTime(timezone=True), nullable=True)
    duracao_estimada_min = Column(Integer, default=60)

    opcao_escolhida_id = Column(
        Integer, ForeignKey("agendamento_opcoes.id"), nullable=True
    )  # qual opção o cliente escolheu

    endereco = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    motivo_cancelamento = Column(Text, nullable=True)

    confirmado_em = Column(DateTime(timezone=True), nullable=True)
    cancelado_em = Column(DateTime(timezone=True), nullable=True)
    concluido_em = Column(DateTime(timezone=True), nullable=True)
    reagendamento_anterior_id = Column(
        Integer, ForeignKey("agendamentos.id"), nullable=True
    )

    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa")
    cliente = relationship("Cliente")
    orcamento = relationship("Orcamento", foreign_keys=[orcamento_id])
    criado_por = relationship("Usuario", foreign_keys=[criado_por_id])
    responsavel = relationship("Usuario", foreign_keys=[responsavel_id])
    historico = relationship(
        "HistoricoAgendamento",
        back_populates="agendamento",
        cascade="all, delete-orphan",
        order_by="HistoricoAgendamento.criado_em.desc()",
    )
    opcoes = relationship(
        "AgendamentoOpcao",
        back_populates="agendamento",
        cascade="all, delete-orphan",
        order_by="AgendamentoOpcao.data_hora.asc()",
        foreign_keys="[AgendamentoOpcao.agendamento_id]",
    )


class HistoricoAgendamento(Base):
    __tablename__ = "historico_agendamentos"

    id = Column(Integer, primary_key=True, index=True)
    agendamento_id = Column(
        Integer, ForeignKey("agendamentos.id"), nullable=False, index=True
    )
    status_anterior = Column(String(30), nullable=True)
    status_novo = Column(String(30), nullable=False)
    descricao = Column(Text, nullable=True)
    editado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    agendamento = relationship("Agendamento", back_populates="historico")
    editado_por = relationship("Usuario")


class AgendamentoOpcao(Base):
    """Opção de data/hora oferecida pela empresa ao cliente."""

    __tablename__ = "agendamento_opcoes"

    id = Column(Integer, primary_key=True, index=True)
    agendamento_id = Column(
        Integer, ForeignKey("agendamentos.id"), nullable=False, index=True
    )
    data_hora = Column(DateTime(timezone=True), nullable=False)
    disponivel = Column(Boolean, default=True)  # False quando escolhida ou removida
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    agendamento = relationship(
        "Agendamento", back_populates="opcoes", foreign_keys=[agendamento_id]
    )


class ConfigAgendamento(Base):
    """Configuração de agendamento por empresa."""

    __tablename__ = "config_agendamento"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(
        Integer, ForeignKey("empresas.id"), unique=True, nullable=False, index=True
    )

    horario_inicio = Column(String(5), default="08:00")  # HH:MM
    horario_fim = Column(String(5), default="18:00")
    dias_trabalho = Column(JSON, default=[0, 1, 2, 3, 4])  # 0=seg .. 4=sex
    duracao_padrao_min = Column(Integer, default=60)
    intervalo_minimo_min = Column(Integer, default=30)
    antecedencia_minima_horas = Column(Integer, default=1)
    permite_agendamento_cliente = Column(Boolean, default=False)
    requer_confirmacao = Column(Boolean, default=True)
    lembrete_antecedencia_horas = Column(JSON, default=[24, 2])
    mensagem_confirmacao = Column(Text, nullable=True)
    mensagem_lembrete = Column(Text, nullable=True)
    mensagem_reagendamento = Column(Text, nullable=True)
    usa_agendamento = Column(Boolean, default=False)  # habilita módulo de agendamento
    ativo = Column(Boolean, default=True)

    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa")


class ConfigAgendamentoUsuario(Base):
    """Override de configuração de agendamento por funcionário."""

    __tablename__ = "config_agendamento_usuario"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    usuario_id = Column(
        Integer, ForeignKey("usuarios.id"), nullable=False, unique=True, index=True
    )

    horario_inicio = Column(String(5), nullable=True)  # NULL = usa empresa
    horario_fim = Column(String(5), nullable=True)
    dias_trabalho = Column(JSON, nullable=True)
    duracao_padrao_min = Column(Integer, nullable=True)
    ativo = Column(Boolean, default=True)

    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa")
    usuario = relationship("Usuario")

    __table_args__ = (
        UniqueConstraint(
            "empresa_id", "usuario_id", name="uq_config_agd_empresa_usuario"
        ),
    )


class SlotBloqueado(Base):
    """Bloqueio de horário — empresa-wide (usuario_id NULL) ou individual."""

    __tablename__ = "slots_bloqueados"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    usuario_id = Column(
        Integer, ForeignKey("usuarios.id"), nullable=True, index=True
    )  # NULL = empresa toda

    data_inicio = Column(DateTime(timezone=True), nullable=False)
    data_fim = Column(DateTime(timezone=True), nullable=False)
    motivo = Column(String(300), nullable=True)
    recorrente = Column(Boolean, default=False)
    recorrencia_tipo = Column(String(20), nullable=True)  # "diario", "semanal"

    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    empresa = relationship("Empresa")
    usuario = relationship("Usuario")


# ── IDEMPOTÊNCIA DE WEBHOOKS ─────────────────────────────────────────────────


class WebhookEvent(Base):
    """Registro de eventos de webhook já processados (idempotência).

    Garante que cada evento seja processado apenas uma vez,
    mesmo que o provedor reenvie o mesmo webhook múltiplas vezes.
    """

    __tablename__ = "webhook_events"

    event_id = Column(String(200), primary_key=True)  # hash SHA-256 do payload
    provider = Column(
        String(50), nullable=False, index=True
    )  # "kiwify", "stripe", etc.
    evento = Column(String(100), nullable=True)  # tipo do evento ex: "order_approved"
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True, index=True)
    payload_hash = Column(String(64), nullable=False)  # SHA-256 do body bruto
    processado_em = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ToolCallLog(Base):
    """Auditoria de cada chamada de tool feita pelo assistente IA (Tool Use / function calling)."""

    __tablename__ = "tool_call_log"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    sessao_id = Column(String(64), nullable=True, index=True)
    tool = Column(String(100), nullable=False, index=True)
    args_json = Column(JSON, nullable=True)
    resultado_json = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, index=True)  # ok|erro|forbidden|pending|invalid_input|unknown_tool
    latencia_ms = Column(Integer, nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    criado_em = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class AIChatSessao(Base):
    """Sessão persistente do chat da IA."""
    __tablename__ = "ai_chat_sessoes"

    id = Column(String(64), primary_key=True, index=True) # sessao_id client-side UUID
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    mensagens = relationship("AIChatMensagem", back_populates="sessao", cascade="all, delete-orphan", order_by="AIChatMensagem.criado_em")


class AIChatMensagem(Base):
    """Mensagem de uma sessão de chat."""
    __tablename__ = "ai_chat_mensagens"

    id = Column(Integer, primary_key=True, index=True)
    sessao_id = Column(String(64), ForeignKey("ai_chat_sessoes.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user', 'assistant'
    content = Column(Text, nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    sessao = relationship("AIChatSessao", back_populates="mensagens")
