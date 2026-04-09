"""Utilitários compartilhados para geração e formatação de números de orçamento."""

from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Orcamento

if TYPE_CHECKING:
    from app.models.models import ItemOrcamento


def formatar_numero_orcamento(empresa, sequencial: int, aprovado: bool = False) -> str:
    """Formata o número do orçamento de acordo com a configuração da empresa.

    Exemplos:
        prefixo=ORC, ano=True  → ORC-150-26
        prefixo=PROP, ano=False → PROP-150
        prefixo=ORC, aprovado=True, prefixo_aprovado=PED, ano=True → PED-150-26
    """
    prefixo = (getattr(empresa, "numero_prefixo", None) or "ORC").strip().upper()
    if aprovado:
        prefixo_ap = getattr(empresa, "numero_prefixo_aprovado", None)
        if prefixo_ap:
            prefixo = prefixo_ap.strip().upper()
    incluir_ano = getattr(empresa, "numero_incluir_ano", True)
    if incluir_ano is None:
        incluir_ano = True
    if incluir_ano:
        ano_curto = str(datetime.now().year)[-2:]
        return f"{prefixo}-{sequencial}-{ano_curto}"
    return f"{prefixo}-{sequencial}"


def gerar_numero(empresa, db: Session, offset: int = 0) -> tuple[str, int]:
    """Retorna (numero_formatado, sequencial) para um novo orçamento.

    Usa MAX(sequencial_numero) por empresa — tolerante a gaps (orçamentos deletados).
    offset é usado no retry em caso de colisão (race condition).

    Após calcular o candidato, verifica se o numero formatado já existe no banco
    (garante segurança contra orçamentos com sequencial_numero=NULL não backfillados).
    """
    empresa_id = empresa.id if hasattr(empresa, "id") else int(empresa)
    resultado = (
        db.query(func.max(Orcamento.sequencial_numero))
        .filter(Orcamento.empresa_id == empresa_id)
        .scalar()
    )
    # Fallback seguro: se não houver sequencial_numero (banco antigo sem backfill),
    # usa o método legado via split_part para não gerar duplicatas
    if resultado is None:
        ano_curto = str(datetime.now().year)[-2:]
        resultado = (
            db.query(
                func.max(
                    func.cast(
                        func.split_part(
                            func.split_part(Orcamento.numero, "-", 2), "-", 1
                        ),
                        sa.Integer,
                    )
                )
            )
            .filter(
                Orcamento.empresa_id == empresa_id,
                Orcamento.numero.like(f"%-%-{ano_curto}"),
            )
            .scalar()
        )
    seq = (resultado or 0) + 1 + offset
    numero = formatar_numero_orcamento(empresa, seq)

    # Proteção contra colisão: avança o sequencial até encontrar um número livre
    # Cobre o caso de orçamentos antigos com sequencial_numero=NULL não backfillados
    while (
        db.query(Orcamento.id)
        .filter(Orcamento.empresa_id == empresa_id, Orcamento.numero == numero)
        .scalar()
        is not None
    ):
        seq += 1
        numero = formatar_numero_orcamento(empresa, seq)

    return numero, seq


def renomear_numero_aprovado(orc, empresa=None) -> None:
    """Se a empresa tiver numero_prefixo_aprovado configurado, renomeia orc.numero.

    Mantém sequencial e ano — apenas troca o prefixo.
    Ex.: ORC-150-26 → PED-150-26

    Chamada nos 5 pontos de aprovação do sistema.
    """
    emp = empresa or getattr(orc, "empresa", None)
    if not emp:
        return
    prefixo_novo = getattr(emp, "numero_prefixo_aprovado", None)
    if not prefixo_novo:
        return
    prefixo_atual = (getattr(emp, "numero_prefixo", None) or "ORC").strip().upper()
    prefixo_novo = prefixo_novo.strip().upper()
    if orc.numero and orc.numero.upper().startswith(f"{prefixo_atual}-"):
        orc.numero = prefixo_novo + orc.numero[len(prefixo_atual) :]


def brl_fmt(valor: float) -> str:
    """Formata valor monetário para padrão brasileiro: R$ 1.234,56"""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def listar_itens_txt(itens) -> str:
    """Lista itens do orçamento em texto formatado."""
    if not itens:
        return "Sem itens"
    linhas = []
    for i, item in enumerate(itens, 1):
        qtd = (
            int(item.quantidade)
            if item.quantidade == int(item.quantidade)
            else item.quantidade
        )
        linhas.append(
            f"{i}. {item.descricao} — {brl_fmt(float(item.total))}"
            + (f" (x{qtd})" if qtd != 1 else "")
        )
    return "\n".join(linhas)
