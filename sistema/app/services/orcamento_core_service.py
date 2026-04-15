import secrets
import logging
from decimal import Decimal
from typing import Optional, List, Literal

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.models import (
    Orcamento,
    ItemOrcamento,
    Cliente,
    Usuario,
    HistoricoEdicao,
    Empresa,
    ModoAgendamentoOrcamento,
)
from app.schemas.schemas import ItemOrcamentoCreate
from app.services.plano_service import checar_limite_orcamentos
from app.utils.desconto import erro_validacao_desconto, resolver_max_percent_desconto, aplicar_desconto
from app.utils.orcamento_utils import gerar_numero

logger = logging.getLogger(__name__)

def _resolver_agendamento_modo_criacao(
    solicitado: Optional[ModoAgendamentoOrcamento],
    empresa: Optional[Empresa],
) -> ModoAgendamentoOrcamento:
    """Define agendamento_modo na criação do orçamento."""
    if solicitado is not None:
        return solicitado
    if empresa is not None and getattr(
        empresa, "agendamento_escolha_obrigatoria", False
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Informe se haverá agendamento neste orçamento (Sim ou Não). "
                "A configuração da empresa exige escolha explícita em cada proposta."
            ),
        )
    if (
        empresa is not None
        and getattr(empresa, "agendamento_modo_padrao", None) is not None
    ):
        return empresa.agendamento_modo_padrao
    return ModoAgendamentoOrcamento.NAO_USA

def criar_orcamento_core(
    db: Session,
    empresa: Empresa,
    usuario_criador: Usuario | None,
    cliente_id: int,
    itens: list,
    origem: str = "Manual",
    forma_pagamento: str = "pix",
    validade_dias: int | None = None,
    observacoes: str | None = None,
    desconto: Decimal | float = Decimal("0.0"),
    desconto_tipo: Literal["percentual", "fixo"] = "percentual",
    agendamento_modo: Optional[ModoAgendamentoOrcamento] = None,
    regra_pagamento_id: Optional[int] = None,
    mensagem_ia: Optional[str] = None,
) -> Orcamento:
    """
    Core centralizado de criação de orçamentos.
    Garante aplicação das regras de limites, validações de negócio, agendamento_modo,
    observações padrão e persistência de linha do tempo com a origem da ação.
    """
    # 1. Checa limite
    checar_limite_orcamentos(db, empresa)
    
    # 2. Valida cliente
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id, Cliente.empresa_id == empresa.id).first()
    if not cliente:
        raise ValueError("Cliente não encontrado")

    # 3. Resolve agendamento
    modo_agendamento = _resolver_agendamento_modo_criacao(agendamento_modo, empresa)

    # 4. Resolve validade padrão
    if validade_dias is None:
        validade_dias = getattr(empresa, "validade_padrao_dias", 7)

    # 5. Cálculos (subtotal, desconto, total)
    subtotal = Decimal("0")
    for item in itens:
        if isinstance(item, dict):
            subtotal += Decimal(str(item.get("quantidade", 1))) * Decimal(str(item.get("valor_unit", 0)))
        else:
            subtotal += Decimal(str(item.quantidade)) * Decimal(str(item.valor_unit))
            
    # Se há desconto, validar e aplicar
    max_pct = resolver_max_percent_desconto(usuario_criador, empresa) if usuario_criador else 100
    err_desconto = erro_validacao_desconto(
        subtotal, Decimal(str(desconto)), desconto_tipo, max_pct
    )
    if err_desconto:
        raise ValueError(err_desconto)
        
    total = aplicar_desconto(subtotal, Decimal(str(desconto)), desconto_tipo)

    # 6. Criar Orçamento (com retry para colisão de número)
    orcamento = None
    for tentativa in range(3):
        if tentativa > 0:
            db.rollback()
            
        _numero, _seq = gerar_numero(empresa, db, offset=tentativa)
        orcamento = Orcamento(
            empresa_id=empresa.id,
            cliente_id=cliente_id,
            criado_por_id=usuario_criador.id if usuario_criador else None,
            numero=_numero,
            sequencial_numero=_seq,
            forma_pagamento=forma_pagamento,
            validade_dias=validade_dias,
            observacoes=observacoes,
            desconto=Decimal(str(desconto)),
            desconto_tipo=desconto_tipo,
            total=total,
            link_publico=secrets.token_urlsafe(24),
            agendamento_modo=modo_agendamento,
            origem_whatsapp=(origem == "WhatsApp"),
            mensagem_ia=mensagem_ia,
        )
        db.add(orcamento)
        try:
            db.flush()
            break
        except Exception as e:
            if "ix_orcamentos" in str(e).lower() or "uq_orcamentos" in str(e).lower() or "orcamentos_numero" in str(e).lower():
                logger.warning("Colisão de número de orçamento (tentativa %d): %s", tentativa + 1, str(e))
                continue
            raise
    else:
        raise RuntimeError("Não foi possível gerar número de orçamento único. Tente novamente.")

    # 7. Adicionar Itens
    for item_data in itens:
        if isinstance(item_data, dict):
            servico_id = item_data.get("servico_id")
            descricao = item_data.get("descricao")
            quantidade = item_data.get("quantidade", 1)
            valor_unit = item_data.get("valor_unit", 0)
        else:
            servico_id = getattr(item_data, "servico_id", None)
            descricao = item_data.descricao
            quantidade = item_data.quantidade
            valor_unit = item_data.valor_unit
            
        total_item = Decimal(str(quantidade)) * Decimal(str(valor_unit))
        
        item = ItemOrcamento(
            orcamento_id=orcamento.id,
            servico_id=servico_id,
            descricao=descricao,
            quantidade=quantidade,
            valor_unit=valor_unit,
            total=total_item,
        )
        db.add(item)

    # 8. Regra de Pagamento
    from app.routers.orcamentos import _aplicar_regra_pagamento
    _aplicar_regra_pagamento(orcamento, regra_pagamento_id, empresa.id, db)

    # 9. Histórico com identificação de Origem (Linha do Tempo visual)
    origem_formatada = f"[{origem}]" if origem else "[Manual]"
    texto_hist = f"{origem_formatada} Orçamento criado (Total: R$ {total:.2f})."
    
    db.add(
        HistoricoEdicao(
            orcamento_id=orcamento.id,
            editado_por_id=usuario_criador.id if usuario_criador else None,
            descricao=texto_hist,
        )
    )

    return orcamento
