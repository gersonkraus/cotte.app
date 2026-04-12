"""Tools de orçamento: listar, obter e criar."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload

from app.models.models import (
    Cliente,
    ItemOrcamento,
    Orcamento,
    Servico,
    StatusOrcamento,
    Usuario,
)

from ._base import ToolSpec


# ── listar_orcamentos ──────────────────────────────────────────────────────
class ListarOrcamentosInput(BaseModel):
    status: Optional[str] = Field(
        default=None,
        description="Status do orçamento (ex: RASCUNHO, ENVIADO, APROVADO, RECUSADO).",
    )
    cliente_id: Optional[int] = None
    dias: int = Field(default=30, ge=1, le=365)
    limit: int = Field(default=10, ge=1, le=50)


async def _listar_orcamentos(
    inp: ListarOrcamentosInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    desde = date.today() - timedelta(days=inp.dias)
    q = (
        db.query(Orcamento)
        .options(selectinload(Orcamento.cliente))
        .filter(
            Orcamento.empresa_id == current_user.empresa_id,
            Orcamento.criado_em >= desde,
        )
        .order_by(Orcamento.criado_em.desc())
    )
    if inp.status:
        try:
            status_raw = str(inp.status or "").strip()
            status_key = status_raw.upper()
            status_aliases = {
                "PENDENTE": "ENVIADO",
                "PENDENTES": "ENVIADO",
                "EM_ABERTO": "ENVIADO",
                "ABERTO": "ENVIADO",
                "ABERTOS": "ENVIADO",
                "A_RECEBER": "APROVADO",
                "RECEBER": "APROVADO",
            }
            status_key = status_aliases.get(status_key, status_key)
            status_enum = StatusOrcamento[status_key]
            q = q.filter(Orcamento.status == status_enum)
        except ValueError:
            return {"error": f"status inválido: {inp.status}", "code": "invalid_input"}
        except KeyError:
            return {"error": f"status inválido: {inp.status}", "code": "invalid_input"}
    if inp.cliente_id:
        q = q.filter(Orcamento.cliente_id == inp.cliente_id)

    items = q.limit(inp.limit).all()
    return {
        "total": len(items),
        "orcamentos": [
            {
                "id": o.id,
                "numero": o.numero,
                "status": o.status.value if o.status else None,
                "total": float(o.total or 0),
                "cliente_id": o.cliente_id,
                "cliente_nome": o.cliente.nome if o.cliente else None,
                "criado_em": o.criado_em.isoformat() if o.criado_em else None,
            }
            for o in items
        ],
    }


listar_orcamentos = ToolSpec(
    name="listar_orcamentos",
    description=(
        "Lista orçamentos da empresa. Filtros: status (RASCUNHO/ENVIADO/APROVADO/RECUSADO), "
        "cliente_id, dias (janela). Para 'quem está devendo / inadimplentes': "
        "use status='ENVIADO' (enviado mas não pago). Para 'orçamentos aprovados a receber': "
        "use status='APROVADO'. CHAME UMA ÚNICA VEZ por consulta — não repita a mesma tool."
    ),
    input_model=ListarOrcamentosInput,
    handler=_listar_orcamentos,
    destrutiva=False,
    cacheable_ttl=15,
    permissao_recurso="orcamentos",
    permissao_acao="leitura",
)


# ── obter_orcamento ────────────────────────────────────────────────────────
class ObterOrcamentoInput(BaseModel):
    id: int | str = Field(
        description="ID NÚMERICO ou NÚMERO do orçamento (ex: 104 ou 'O-104')."
    )


async def _obter_orcamento(
    inp: ObterOrcamentoInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    o = _get_orcamento_da_empresa(db, inp.id, current_user.empresa_id)
    if not o:
        return {"error": "orçamento não encontrado", "code": "not_found"}
    return {
        "id": o.id,
        "numero": o.numero,
        "status": o.status.value if o.status else None,
        "total": float(o.total or 0),
        "desconto": float(o.desconto or 0),
        "observacoes": o.observacoes,
        "cliente": (
            {"id": o.cliente.id, "nome": o.cliente.nome} if o.cliente else None
        ),
        "itens": [
            {
                "descricao": i.descricao,
                "quantidade": float(i.quantidade or 0),
                "valor_unit": float(i.valor_unit or 0),
                "total": float(i.total or 0),
            }
            for i in (o.itens or [])
        ],
        "criado_em": o.criado_em.isoformat() if o.criado_em else None,
    }


obter_orcamento = ToolSpec(
    name="obter_orcamento",
    description="Retorna detalhes completos de um orçamento específico (por ID).",
    input_model=ObterOrcamentoInput,
    handler=_obter_orcamento,
    destrutiva=False,
    cacheable_ttl=15,
    permissao_recurso="orcamentos",
    permissao_acao="leitura",
)


# ── criar_orcamento (DESTRUTIVA) ───────────────────────────────────────────
class ItemOrcamentoInput(BaseModel):
    descricao: str = Field(min_length=1, max_length=300)
    quantidade: float = Field(default=1.0, gt=0)
    valor_unit: Optional[float] = Field(default=None, gt=0)
    servico_id: Optional[int] = Field(default=None, gt=0)


class CriarOrcamentoInput(BaseModel):
    cliente_id: Optional[int] = Field(default=None, gt=0)
    cliente_nome: Optional[str] = Field(default=None, min_length=1, max_length=200)
    itens: List[ItemOrcamentoInput] = Field(min_length=1)
    observacoes: Optional[str] = Field(default=None, max_length=2000)
    cadastrar_materiais_novos: bool = Field(
        default=False,
        description="Se True, cadastra no catálogo os itens que não tiverem correspondência.",
    )


def _resolver_cliente(inp: "CriarOrcamentoInput", db: Session, current_user: Usuario):
    """Retorna (cliente, auto_criado, error_dict)."""
    from app.schemas.schemas import ClienteCreate
    from app.services.cliente_service import ClienteService

    if inp.cliente_id:
        c = (
            db.query(Cliente)
            .filter(
                Cliente.id == inp.cliente_id,
                Cliente.empresa_id == current_user.empresa_id,
            )
            .first()
        )
        if not c:
            return None, False, {"error": "cliente não encontrado", "code": "not_found"}
        return c, False, None

    if inp.cliente_nome:
        base = db.query(Cliente).filter(Cliente.empresa_id == current_user.empresa_id)
        nome = inp.cliente_nome.strip()

        # 1) exato (case-insensitive)
        candidatos = base.filter(Cliente.nome.ilike(nome)).limit(5).all()
        # 2) começa com (ex: "Ana" → "Ana Paula")
        if not candidatos:
            candidatos = base.filter(Cliente.nome.ilike(f"{nome}%")).limit(5).all()
        # 3) contém (fallback amplo)
        if not candidatos:
            candidatos = base.filter(Cliente.nome.ilike(f"%{nome}%")).limit(5).all()

        if len(candidatos) == 0:
            c = ClienteService(db).criar_cliente(ClienteCreate(nome=nome), current_user)
            db.flush()
            return c, True, None
        if len(candidatos) == 1:
            return candidatos[0], False, None
        # múltiplos — verificar se algum é exato
        exatos = [c for c in candidatos if c.nome.lower() == nome.lower()]
        if len(exatos) == 1:
            return exatos[0], False, None
        return (
            None,
            False,
            {
                "error": f"Múltiplos clientes para '{nome}'. Especifique o cliente_id.",
                "code": "ambiguous_cliente",
                "candidatos": [{"id": c.id, "nome": c.nome} for c in candidatos],
            },
        )

    return (
        None,
        False,
        {"error": "Informe cliente_id ou cliente_nome.", "code": "missing_cliente"},
    )


def _resolver_itens(inp: "CriarOrcamentoInput", db: Session, current_user: Usuario):
    """Retorna (itens_resolvidos, materiais_novos, error_dict).
    itens_resolvidos = [{"descricao", "quantidade", "valor_unit", "servico_id"}]
    materiais_novos  = [{"descricao", "valor_unit"}]
    """
    itens_resolvidos = []
    materiais_novos = []

    for it in inp.itens:
        servico_id = it.servico_id
        descricao = it.descricao
        valor_unit = it.valor_unit

        if servico_id:
            svc_obj = (
                db.query(Servico)
                .filter(
                    Servico.id == servico_id,
                    Servico.empresa_id == current_user.empresa_id,
                )
                .first()
            )
            if svc_obj and valor_unit is None:
                valor_unit = float(svc_obj.preco_padrao or 0)
        else:
            matches = (
                db.query(Servico)
                .filter(
                    Servico.empresa_id == current_user.empresa_id,
                    Servico.nome.ilike(f"%{descricao}%"),
                    Servico.ativo.is_(True),
                )
                .limit(3)
                .all()
            )
            if matches:
                servico_id = matches[0].id
                if valor_unit is None:
                    valor_unit = float(matches[0].preco_padrao or 0)
            else:
                if valor_unit is None:
                    return (
                        None,
                        None,
                        {
                            "error": f"Item '{descricao}' não está no catálogo e o valor não foi informado.",
                            "code": "missing_valor",
                            "item": descricao,
                        },
                    )
                materiais_novos.append(
                    {"descricao": descricao, "valor_unit": valor_unit}
                )

        if valor_unit is None or valor_unit <= 0:
            return (
                None,
                None,
                {
                    "error": f"Valor inválido ou zero para o item '{descricao}'.",
                    "code": "missing_valor",
                    "item": descricao,
                },
            )

        itens_resolvidos.append(
            {
                "descricao": descricao,
                "quantidade": it.quantidade,
                "valor_unit": valor_unit,
                "servico_id": servico_id,
            }
        )

    return itens_resolvidos, materiais_novos, None


async def _criar_orcamento(
    inp: CriarOrcamentoInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    import secrets
    from sqlalchemy.exc import IntegrityError
    from app.utils.orcamento_utils import gerar_numero

    cliente, cliente_auto_criado, err = _resolver_cliente(inp, db, current_user)
    if err:
        return err

    itens_resolvidos, materiais_novos, err = _resolver_itens(inp, db, current_user)
    if err:
        return err

    # Cadastrar materiais novos no catálogo se solicitado
    if inp.cadastrar_materiais_novos and materiais_novos:
        for mn in materiais_novos:
            novo_svc = Servico(
                empresa_id=current_user.empresa_id,
                nome=mn["descricao"],
                preco_padrao=Decimal(str(mn["valor_unit"])),
                ativo=True,
            )
            db.add(novo_svc)
            db.flush()
            for ir in itens_resolvidos:
                if ir["descricao"] == mn["descricao"] and ir["servico_id"] is None:
                    ir["servico_id"] = novo_svc.id
                    break

    total = Decimal("0")
    for ir in itens_resolvidos:
        qtd = Decimal(str(ir["quantidade"]))
        vu = Decimal(str(ir["valor_unit"]))
        total += (qtd * vu).quantize(Decimal("0.01"))

    from app.models.models import ModoAgendamentoOrcamento

    empresa = current_user.empresa
    agendamento_modo_ia = ModoAgendamentoOrcamento.NAO_USA
    if empresa and getattr(empresa, "agendamento_modo_padrao", None):
        agendamento_modo_ia = empresa.agendamento_modo_padrao
    if empresa and getattr(empresa, "agendamento_escolha_obrigatoria", False):
        agendamento_modo_ia = ModoAgendamentoOrcamento.NAO_USA

    orc = None
    for tentativa in range(3):
        if tentativa > 0:
            db.rollback()
        _numero, _seq = gerar_numero(current_user.empresa, db, offset=tentativa)
        orc = Orcamento(
            empresa_id=current_user.empresa_id,
            cliente_id=cliente.id,
            criado_por_id=current_user.id,
            numero=_numero,
            sequencial_numero=_seq,
            status=StatusOrcamento.RASCUNHO,
            total=total,
            observacoes=inp.observacoes,
            link_publico=secrets.token_urlsafe(24),
            agendamento_modo=agendamento_modo_ia,
        )
        db.add(orc)
        try:
            db.flush()
            break
        except IntegrityError as e:
            if any(
                k in str(e.orig)
                for k in (
                    "ix_orcamentos",
                    "orcamentos_numero",
                    "uq_orcamentos_empresa_numero",
                    "numero",
                )
            ):
                db.rollback()
                continue
            raise
    else:
        return {
            "error": "Não foi possível gerar número único",
            "code": "numero_conflict",
        }

    for ir in itens_resolvidos:
        qtd = Decimal(str(ir["quantidade"]))
        vu = Decimal(str(ir["valor_unit"]))
        db.add(
            ItemOrcamento(
                orcamento_id=orc.id,
                descricao=ir["descricao"],
                quantidade=qtd,
                valor_unit=vu,
                total=(qtd * vu).quantize(Decimal("0.01")),
                servico_id=ir["servico_id"],
            )
        )

    db.commit()
    db.refresh(orc)
    # Recarrega com itens para exibir no card
    orc_com_itens = (
        db.query(Orcamento)
        .options(selectinload(Orcamento.itens), selectinload(Orcamento.cliente))
        .filter(Orcamento.id == orc.id)
        .first()
    )
    return _build_orcamento_response(
        orc_com_itens,
        {
            "cliente_auto_criado": cliente_auto_criado,
            "materiais_novos": materiais_novos,
            "criado": True,
        },
    )


async def preview_criar_orcamento(
    args_dict: dict, *, db: Session, current_user: Usuario
) -> dict:
    """Dry-run read-only: verifica cliente/itens sem gravar nada. Retorna extras para o card."""
    try:
        inp = CriarOrcamentoInput(**args_dict)
    except Exception:
        return {}

    # Resolve cliente — apenas leitura, sem criar
    cliente_auto_criar = False
    cliente_nome_resolvido = inp.cliente_nome or ""
    if inp.cliente_id:
        c = (
            db.query(Cliente)
            .filter(
                Cliente.id == inp.cliente_id,
                Cliente.empresa_id == current_user.empresa_id,
            )
            .first()
        )
        cliente_nome_resolvido = c.nome if c else str(inp.cliente_id)
    elif inp.cliente_nome:
        _nome = inp.cliente_nome.strip()
        _base = db.query(Cliente).filter(Cliente.empresa_id == current_user.empresa_id)
        candidatos = _base.filter(Cliente.nome.ilike(_nome)).limit(5).all()
        if not candidatos:
            candidatos = _base.filter(Cliente.nome.ilike(f"{_nome}%")).limit(5).all()
        if not candidatos:
            candidatos = _base.filter(Cliente.nome.ilike(f"%{_nome}%")).limit(5).all()
        if len(candidatos) == 0:
            cliente_auto_criar = True
            cliente_nome_resolvido = _nome
        elif len(candidatos) == 1:
            cliente_nome_resolvido = candidatos[0].nome
        else:
            exatos = [c for c in candidatos if c.nome.lower() == _nome.lower()]
            cliente_nome_resolvido = (
                exatos[0].nome if len(exatos) == 1 else candidatos[0].nome
            )

    # Resolve itens — apenas leitura, sem criar
    materiais_novos = []
    for it in inp.itens:
        if not it.servico_id:
            matches = (
                db.query(Servico)
                .filter(
                    Servico.empresa_id == current_user.empresa_id,
                    Servico.nome.ilike(f"%{it.descricao}%"),
                    Servico.ativo.is_(True),
                )
                .limit(1)
                .all()
            )
            if not matches:
                materiais_novos.append(
                    {"descricao": it.descricao, "valor_unit": it.valor_unit}
                )

    return {
        "cliente_auto_criar": cliente_auto_criar,
        "cliente_nome_resolvido": cliente_nome_resolvido,
        "materiais_novos": materiais_novos,
    }


criar_orcamento = ToolSpec(
    name="criar_orcamento",
    description=(
        "Cria um novo orçamento em RASCUNHO. Use cliente_nome quando o ID não for conhecido — o backend "
        "faz match por nome ou cria o cliente automaticamente (sem precisar chamar listar_clientes antes). "
        "Itens aceitam nome livre (sem servico_id); valor_unit informado sempre prevalece sobre catálogo. "
        "NUNCA chame listar_clientes ou listar_materiais antes desta tool. AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=CriarOrcamentoInput,
    handler=_criar_orcamento,
    destrutiva=True,
    permissao_recurso="orcamentos",
    permissao_acao="escrita",
)


# ── helper: carregar orçamento da empresa ─────────────────────────────────
def _build_orcamento_response(orc: Orcamento, extra_fields: dict = None) -> dict:
    itens_lista = [
        {"descricao": i.descricao, "total": float(i.total or 0)}
        for i in (orc.itens or [])
    ]
    resp = {
        "id": orc.id,
        "numero": orc.numero,
        "status": orc.status.value if orc.status else None,
        "total": float(orc.total or 0),
        "cliente_id": orc.cliente_id,
        "cliente_nome": orc.cliente.nome if orc.cliente else "",
        "link_publico": orc.link_publico or "",
        "itens": itens_lista,
        "tem_telefone": bool(orc.cliente and getattr(orc.cliente, "telefone", None)),
        "tem_email": bool(orc.cliente and getattr(orc.cliente, "email", None)),
    }
    if extra_fields:
        resp.update(extra_fields)
    return resp


def _get_orcamento_da_empresa(
    db: Session, orcamento_id: int | str, empresa_id: int
) -> Optional[Orcamento]:
    from sqlalchemy import or_
    import re

    val_str = str(orcamento_id).strip()

    q = (
        db.query(Orcamento)
        .options(selectinload(Orcamento.itens), selectinload(Orcamento.cliente))
        .filter(Orcamento.empresa_id == empresa_id)
    )

    exact = q.filter(Orcamento.numero == val_str).first()
    if exact:
        return exact

    match = re.search(r"\d+", val_str)
    if match:
        val_int = int(match.group())

        candidatos = q.filter(
            or_(Orcamento.id == val_int, Orcamento.sequencial_numero == val_int)
        ).all()
        if not candidatos:
            return None

        for c in candidatos:
            if c.sequencial_numero == val_int:
                return c

        return candidatos[0]

    return None


# ── aprovar_orcamento (DESTRUTIVA) ─────────────────────────────────────────
class AprovarOrcamentoInput(BaseModel):
    orcamento_id: int | str = Field(
        description="ID NÚMERICO ou NÚMERO do orçamento a aprovar."
    )


async def _aprovar_orcamento(
    inp: AprovarOrcamentoInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    from app.services import financeiro_service
    from app.services.quote_notification_service import handle_quote_status_changed

    orc = _get_orcamento_da_empresa(db, inp.orcamento_id, current_user.empresa_id)
    if not orc:
        return {"error": "Orçamento não encontrado", "code": "not_found"}
    if orc.status == StatusOrcamento.APROVADO:
        return _build_orcamento_response(
            orc, {"ja_aprovado": True, "status": "aprovado"}
        )

    old_status = orc.status
    orc.status = StatusOrcamento.APROVADO
    try:
        financeiro_service.criar_contas_receber_aprovacao(
            orc, current_user.empresa_id, db
        )
    except Exception as e:
        db.rollback()
        return {
            "error": f"Falha ao criar contas a receber: {e}",
            "code": "financeiro_error",
        }
    db.commit()
    db.refresh(orc)
    try:
        await handle_quote_status_changed(
            db=db,
            quote=orc,
            old_status=old_status,
            new_status=orc.status,
            source="assistente_tool",
        )
    except Exception:
        pass
    return _build_orcamento_response(orc, {"status": "aprovado"})


aprovar_orcamento = ToolSpec(
    name="aprovar_orcamento",
    description=(
        "Aprova um orçamento pelo ID. Gera contas a receber automaticamente. "
        "AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=AprovarOrcamentoInput,
    handler=_aprovar_orcamento,
    destrutiva=True,
    permissao_recurso="orcamentos",
    permissao_acao="escrita",
)


# ── recusar_orcamento (DESTRUTIVA) ─────────────────────────────────────────
class RecusarOrcamentoInput(BaseModel):
    orcamento_id: int | str = Field(
        description="ID NÚMERICO ou NÚMERO do orçamento a recusar."
    )
    motivo: Optional[str] = Field(default=None, max_length=500)


async def _recusar_orcamento(
    inp: RecusarOrcamentoInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    from datetime import datetime, timezone
    from app.models.models import ContaFinanceira, StatusConta
    from app.services.quote_notification_service import handle_quote_status_changed

    orc = _get_orcamento_da_empresa(db, inp.orcamento_id, current_user.empresa_id)
    if not orc:
        return {"error": "Orçamento não encontrado", "code": "not_found"}
    if orc.status == StatusOrcamento.RECUSADO:
        return {"id": orc.id, "ja_recusado": True, "numero": orc.numero}

    old_status = orc.status
    orc.status = StatusOrcamento.RECUSADO
    if hasattr(orc, "recusa_em"):
        orc.recusa_em = datetime.now(timezone.utc)
    if inp.motivo and hasattr(orc, "recusa_motivo"):
        orc.recusa_motivo = inp.motivo
    contas_pendentes = (
        db.query(ContaFinanceira)
        .filter(
            ContaFinanceira.orcamento_id == orc.id,
            ContaFinanceira.status == StatusConta.PENDENTE,
            ContaFinanceira.valor_pago == 0,
        )
        .all()
    )
    qtd_pendentes = len(contas_pendentes)
    valor_pendente = round(sum(float(c.valor or 0) for c in contas_pendentes), 2)

    db.commit()
    db.refresh(orc)
    try:
        await handle_quote_status_changed(
            db=db,
            quote=orc,
            old_status=old_status,
            new_status=orc.status,
            source="assistente_tool",
        )
    except Exception:
        pass
    return _build_orcamento_response(orc, {
        "status": "recusado",
        "impacto_financeiro": {
            "contas_pendentes_removidas": qtd_pendentes,
            "valor_total_pendente_removido": valor_pendente,
            "observacao": (
                "Ao sair de APROVADO, contas a receber pendentes sem pagamento são removidas; "
                "contas com pagamento permanecem para preservar histórico."
            ),
        },
    })


recusar_orcamento = ToolSpec(
    name="recusar_orcamento",
    description=(
        "Recusa um orçamento pelo ID, opcionalmente com motivo. "
        "AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=RecusarOrcamentoInput,
    handler=_recusar_orcamento,
    destrutiva=True,
    permissao_recurso="orcamentos",
    permissao_acao="escrita",
)


# ── enviar_orcamento_whatsapp (DESTRUTIVA) ────────────────────────────────
class EnviarOrcamentoWhatsappInput(BaseModel):
    orcamento_id: int | str = Field(
        description="ID NÚMERICO ou NÚMERO do orçamento a enviar (ex: 104 ou 'O-104')."
    )


async def _enviar_orcamento_whatsapp(
    inp: EnviarOrcamentoWhatsappInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    from app.services.pdf_service import gerar_pdf_orcamento
    from app.services.whatsapp_service import enviar_orcamento_completo
    from app.utils.pdf_utils import (
        get_empresa_dict_for_pdf,
        get_orcamento_dict_for_pdf,
    )

    orc = _get_orcamento_da_empresa(db, inp.orcamento_id, current_user.empresa_id)
    if not orc:
        return {"error": "Orçamento não encontrado", "code": "not_found"}
    if not orc.cliente or not orc.cliente.telefone:
        return {
            "error": "Cliente sem telefone cadastrado",
            "code": "missing_phone",
        }

    try:
        orc_dict = get_orcamento_dict_for_pdf(orc, db)
        empresa_dict = get_empresa_dict_for_pdf(orc.empresa)
        orc_dict["cliente_nome"] = orc.cliente.nome
        orc_dict["empresa_nome"] = orc.empresa.nome
        pdf_bytes = gerar_pdf_orcamento(orc_dict, empresa_dict)
        await enviar_orcamento_completo(
            orc.cliente.telefone, orc_dict, pdf_bytes or b"", orc.empresa
        )
    except Exception as e:
        return {"error": f"Falha no envio: {e}", "code": "send_error"}

    return {
        "id": orc.id,
        "numero": orc.numero,
        "canal": "whatsapp",
        "enviado": True,
    }


enviar_orcamento_whatsapp = ToolSpec(
    name="enviar_orcamento_whatsapp",
    description=(
        "Envia um orçamento por WhatsApp (PDF + mensagem) para o telefone do "
        "cliente vinculado. AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=EnviarOrcamentoWhatsappInput,
    handler=_enviar_orcamento_whatsapp,
    destrutiva=True,
    permissao_recurso="orcamentos",
    permissao_acao="escrita",
)


# ── enviar_orcamento_email (DESTRUTIVA) ───────────────────────────────────
class EnviarOrcamentoEmailInput(BaseModel):
    orcamento_id: int | str = Field(
        description="ID NÚMERICO ou NÚMERO do orçamento a enviar (ex: 104 ou 'O-104')."
    )


async def _enviar_orcamento_email(
    inp: EnviarOrcamentoEmailInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    from app.core.config import settings
    from app.services.email_service import enviar_orcamento_por_email
    from app.services.pdf_service import gerar_pdf_orcamento
    from app.utils.pdf_utils import (
        get_empresa_dict_for_pdf,
        get_orcamento_dict_for_pdf,
    )

    orc = _get_orcamento_da_empresa(db, inp.orcamento_id, current_user.empresa_id)
    if not orc:
        return {"error": "Orçamento não encontrado", "code": "not_found"}
    if not orc.cliente or not orc.cliente.email:
        return {
            "error": "Cliente sem e-mail cadastrado",
            "code": "missing_email",
        }
    if not orc.link_publico:
        return {
            "error": "Orçamento sem link público",
            "code": "missing_link",
        }

    try:
        orc_dict = get_orcamento_dict_for_pdf(orc, db)
        empresa_dict = get_empresa_dict_for_pdf(orc.empresa)
        pdf_bytes = gerar_pdf_orcamento(orc_dict, empresa_dict)
        base_url = (settings.APP_URL or "").rstrip("/")
        ok = enviar_orcamento_por_email(
            destinatario=orc.cliente.email,
            cliente_nome=orc.cliente.nome,
            numero_orcamento=orc.numero,
            empresa_nome=orc.empresa.nome,
            link_publico=f"{base_url}/o/{orc.link_publico}"
            if base_url
            else orc.link_publico,
            pdf_bytes=pdf_bytes,
            anexar_pdf=True,
            valor_total=float(orc.total or 0),
        )
    except Exception as e:
        return {"error": f"Falha no envio: {e}", "code": "send_error"}

    if not ok:
        return {"error": "Envio retornou falha", "code": "send_failed"}
    return {
        "id": orc.id,
        "numero": orc.numero,
        "canal": "email",
        "enviado": True,
    }


enviar_orcamento_email = ToolSpec(
    name="enviar_orcamento_email",
    description=(
        "Envia um orçamento por e-mail (com PDF anexo) para o e-mail do cliente "
        "vinculado. AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=EnviarOrcamentoEmailInput,
    handler=_enviar_orcamento_email,
    destrutiva=True,
    permissao_recurso="orcamentos",
    permissao_acao="escrita",
)


# ── duplicar_orcamento (DESTRUTIVA) ────────────────────────────────────────
class DuplicarOrcamentoInput(BaseModel):
    orcamento_id: int | str = Field(
        description="ID NÚMERICO ou NÚMERO do orçamento (ex: 104 ou 'O-104')."
    )


async def _duplicar_orcamento(
    inp: DuplicarOrcamentoInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    import secrets
    from sqlalchemy.exc import IntegrityError
    from app.utils.orcamento_utils import gerar_numero

    orc = _get_orcamento_da_empresa(db, inp.orcamento_id, current_user.empresa_id)
    if not orc:
        return {"error": "Orçamento não encontrado", "code": "not_found"}

    novo = None
    for tentativa in range(3):
        if tentativa > 0:
            db.rollback()
        _num, _seq = gerar_numero(current_user.empresa, db, offset=tentativa)
        novo = Orcamento(
            empresa_id=orc.empresa_id,
            cliente_id=orc.cliente_id,
            criado_por_id=current_user.id,
            numero=_num,
            sequencial_numero=_seq,
            status=StatusOrcamento.RASCUNHO,
            forma_pagamento=orc.forma_pagamento,
            validade_dias=orc.validade_dias,
            observacoes=orc.observacoes,
            desconto=orc.desconto,
            desconto_tipo=orc.desconto_tipo,
            total=orc.total,
            link_publico=secrets.token_urlsafe(24),
            origem_whatsapp=False,
            agendamento_modo=orc.agendamento_modo,
        )
        db.add(novo)
        try:
            db.flush()
            break
        except IntegrityError as e:
            if any(
                k in str(e.orig)
                for k in (
                    "ix_orcamentos",
                    "orcamentos_numero",
                    "uq_orcamentos_empresa_numero",
                    "numero",
                )
            ):
                db.rollback()
                continue
            raise
    else:
        return {
            "error": "Não foi possível gerar número único",
            "code": "numero_conflict",
        }

    for item in orc.itens:
        db.add(
            ItemOrcamento(
                orcamento_id=novo.id,
                descricao=item.descricao,
                quantidade=item.quantidade,
                valor_unit=item.valor_unit,
                total=item.total,
            )
        )
    db.commit()
    db.refresh(novo)
    return {
        "id": novo.id,
        "numero": novo.numero,
        "total": float(novo.total or 0),
        "duplicado_de": orc.id,
        "criado": True,
    }


duplicar_orcamento = ToolSpec(
    name="duplicar_orcamento",
    description=(
        "Duplica um orçamento existente: cria um novo em RASCUNHO com os mesmos itens, "
        "cliente e valores. Gera novo número e link público. AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=DuplicarOrcamentoInput,
    handler=_duplicar_orcamento,
    destrutiva=True,
    permissao_recurso="orcamentos",
    permissao_acao="escrita",
)


# ── editar_orcamento (DESTRUTIVA, só em RASCUNHO) ──────────────────────────
class EditarOrcamentoInput(BaseModel):
    orcamento_id: int | str = Field(
        description="ID NÚMERICO ou NÚMERO do orçamento (ex: 104 ou 'O-104')."
    )
    observacoes: Optional[str] = Field(default=None, max_length=2000)
    desconto: Optional[Decimal] = Field(default=None, ge=0)
    desconto_tipo: Optional[str] = Field(
        default=None, description="'percentual' ou 'valor'."
    )
    validade_dias: Optional[int] = Field(default=None, ge=1, le=365)
    valor_total: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Novo valor total desejado para o orçamento. Se houver 1 item, ajusta o preço unitário. Se houver múltiplos itens, aplica desconto fixo para atingir o total.",
    )


async def _editar_orcamento(
    inp: EditarOrcamentoInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    orc = _get_orcamento_da_empresa(db, inp.orcamento_id, current_user.empresa_id)
    if not orc:
        return {"error": "Orçamento não encontrado", "code": "not_found"}
    if orc.status != StatusOrcamento.RASCUNHO:
        return {
            "error": f"Orçamento em status {orc.status.value} não pode ser editado (apenas RASCUNHO).",
            "code": "invalid_state",
        }
    mudou = False
    if inp.observacoes is not None:
        orc.observacoes = inp.observacoes
        mudou = True
    if inp.desconto is not None:
        orc.desconto = inp.desconto
        mudou = True
    if inp.desconto_tipo is not None:
        if inp.desconto_tipo not in ("percentual", "valor"):
            return {"error": "desconto_tipo inválido", "code": "invalid_input"}
        orc.desconto_tipo = inp.desconto_tipo
        mudou = True
    if inp.validade_dias is not None:
        orc.validade_dias = inp.validade_dias
        mudou = True
    if inp.valor_total is not None:
        db.refresh(orc)
        itens = orc.itens or []
        if len(itens) == 1:
            item = itens[0]
            item.valor_unit = inp.valor_total / (
                Decimal(str(item.quantidade)) if item.quantidade else Decimal("1")
            )
            item.total = inp.valor_total
        elif len(itens) > 1:
            subtotal = sum(Decimal(str(i.total or 0)) for i in itens)
            orc.desconto = max(Decimal("0"), subtotal - inp.valor_total)
            orc.desconto_tipo = "valor"
        orc.total = inp.valor_total
        mudou = True
    if not mudou:
        return {"error": "nenhum campo para atualizar", "code": "invalid_input"}
    db.commit()
    db.refresh(orc)
    return _build_orcamento_response(
        orc,
        {
            "atualizado": True,
        },
    )


editar_orcamento = ToolSpec(
    name="editar_orcamento",
    description=(
        "Edita campos de um orçamento em RASCUNHO: observações, desconto, tipo de desconto, "
        "validade e valor_total (novo valor total desejado). AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=EditarOrcamentoInput,
    handler=_editar_orcamento,
    destrutiva=True,
    permissao_recurso="orcamentos",
    permissao_acao="escrita",
)


# ── editar_item_orcamento (DESTRUTIVA) ────────────────────────────────────
class EditarItemOrcamentoInput(BaseModel):
    orcamento_id: int | str = Field(
        description="ID numérico ou número do orçamento (ex: 104 ou 'O-104')."
    )
    num_item: int = Field(
        ge=1, description="Número do item (1 = primeiro, 2 = segundo, etc.)."
    )
    descricao: Optional[str] = Field(
        default=None, max_length=500, description="Nova descrição do item."
    )
    valor_unit: Optional[Decimal] = Field(
        default=None, ge=0, description="Novo valor unitário do item."
    )
    quantidade: Optional[Decimal] = Field(
        default=None, gt=0, description="Nova quantidade do item."
    )


async def _editar_item_orcamento(
    inp: EditarItemOrcamentoInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    orc = _get_orcamento_da_empresa(db, inp.orcamento_id, current_user.empresa_id)
    if not orc:
        return {"error": "Orçamento não encontrado", "code": "not_found"}
    if orc.status != StatusOrcamento.RASCUNHO:
        return {
            "error": f"Orçamento em status {orc.status.value} não pode ser editado (apenas RASCUNHO).",
            "code": "invalid_state",
        }
    itens = orc.itens or []
    if not itens:
        return {
            "error": "Orçamento não tem itens para editar.",
            "code": "invalid_input",
        }
    if inp.num_item > len(itens):
        return {
            "error": f"Item {inp.num_item} não existe. O orçamento tem {len(itens)} item(ns).",
            "code": "invalid_input",
        }
    item = itens[inp.num_item - 1]
    mudou = False
    if inp.descricao is not None:
        item.descricao = inp.descricao
        mudou = True
    if inp.valor_unit is not None:
        item.valor_unit = inp.valor_unit
        mudou = True
    if inp.quantidade is not None:
        item.quantidade = inp.quantidade
        mudou = True
    if not mudou:
        return {"error": "nenhum campo para atualizar", "code": "invalid_input"}
    # Recalcula total do item e do orçamento
    qty = Decimal(str(item.quantidade or 1))
    vunit = Decimal(str(item.valor_unit or 0))
    item.total = qty * vunit
    subtotal = sum(Decimal(str(i.total or 0)) for i in itens)
    desconto = Decimal(str(orc.desconto or 0))
    if orc.desconto_tipo == "percentual":
        orc.total = max(Decimal("0"), subtotal - subtotal * desconto / 100)
    else:
        orc.total = max(Decimal("0"), subtotal - desconto)
    db.commit()
    db.refresh(orc)
    return _build_orcamento_response(
        orc,
        {
            "item_editado": inp.num_item,
            "atualizado": True,
        },
    )


editar_item_orcamento = ToolSpec(
    name="editar_item_orcamento",
    description=(
        "Edita um item específico de um orçamento em RASCUNHO: descrição, valor unitário e/ou quantidade. "
        "Use quando o usuário mencionar 'item 1', 'primeiro item', 'trocar preço do serviço X', etc. "
        "AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=EditarItemOrcamentoInput,
    handler=_editar_item_orcamento,
    destrutiva=True,
    permissao_recurso="orcamentos",
    permissao_acao="escrita",
)


# ── anexar_documento_orcamento (DESTRUTIVA) ────────────────────────────────
class AnexarDocumentoOrcamentoInput(BaseModel):
    orcamento_id: int = Field(gt=0)
    documento_id: int = Field(
        gt=0, description="ID do documento da empresa (biblioteca)."
    )
    exibir_no_portal: bool = Field(default=True)
    enviar_por_email: bool = Field(default=True)
    enviar_por_whatsapp: bool = Field(default=False)
    obrigatorio: bool = Field(default=False)


async def _anexar_documento_orcamento(
    inp: AnexarDocumentoOrcamentoInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    from sqlalchemy import func
    from app.models.models import DocumentoEmpresa, OrcamentoDocumento

    orc = _get_orcamento_da_empresa(db, inp.orcamento_id, current_user.empresa_id)
    if not orc:
        return {"error": "Orçamento não encontrado", "code": "not_found"}

    doc = (
        db.query(DocumentoEmpresa)
        .filter(
            DocumentoEmpresa.id == inp.documento_id,
            DocumentoEmpresa.empresa_id == current_user.empresa_id,
            DocumentoEmpresa.deletado_em.is_(None),
        )
        .first()
    )
    if not doc:
        return {"error": "Documento não encontrado", "code": "not_found"}

    existente = (
        db.query(OrcamentoDocumento)
        .filter(
            OrcamentoDocumento.orcamento_id == orc.id,
            OrcamentoDocumento.documento_id == doc.id,
        )
        .first()
    )
    if existente:
        return {
            "error": "Documento já vinculado a este orçamento",
            "code": "already_exists",
        }

    max_ordem = (
        db.query(func.max(OrcamentoDocumento.ordem))
        .filter(OrcamentoDocumento.orcamento_id == orc.id)
        .scalar()
        or 0
    )
    vinc = OrcamentoDocumento(
        orcamento_id=orc.id,
        documento_id=doc.id,
        ordem=int(max_ordem) + 1,
        exibir_no_portal=inp.exibir_no_portal,
        enviar_por_email=inp.enviar_por_email,
        enviar_por_whatsapp=inp.enviar_por_whatsapp,
        obrigatorio=inp.obrigatorio,
        documento_nome=doc.nome,
        documento_tipo=getattr(doc.tipo, "value", str(doc.tipo)),
    )
    db.add(vinc)
    db.commit()
    db.refresh(vinc)
    return {
        "id": vinc.id,
        "orcamento_id": orc.id,
        "documento_id": doc.id,
        "documento_nome": doc.nome,
        "criado": True,
    }


anexar_documento_orcamento = ToolSpec(
    name="anexar_documento_orcamento",
    description=(
        "Vincula um documento existente da biblioteca da empresa (contrato, termo, etc) "
        "a um orçamento. AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=AnexarDocumentoOrcamentoInput,
    handler=_anexar_documento_orcamento,
    destrutiva=True,
    permissao_recurso="orcamentos",
    permissao_acao="escrita",
)
