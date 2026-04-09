from app.models.models import Orcamento, Empresa, OrcamentoDocumento
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

def get_orcamento_dict_for_pdf(orc: Orcamento, db: Session) -> dict:
    """Prepara o dicionário de orçamento para o template PDF."""
    subtotal = sum(i.total for i in orc.itens)
    desconto_v = 0.0
    if orc.desconto and orc.desconto > 0:
        try:
            if orc.desconto_tipo == "percentual":
                desconto_v = float(subtotal) * (float(orc.desconto) / 100)
            else:
                desconto_v = float(orc.desconto)
        except (TypeError, ValueError):
            desconto_v = 0.0

    return {
        "numero": str(orc.numero or "S/N"),
        "total": float(orc.total or 0),
        "subtotal": float(subtotal or 0),
        "desconto": float(orc.desconto or 0.0),
        "desconto_valor": float(desconto_v),
        "desconto_tipo": str(orc.desconto_tipo or "percentual"),
        "validade_dias": int(orc.validade_dias or 7),
        "observacoes": str(orc.observacoes or ""),
        "forma_pagamento": str(
            orc.forma_pagamento.value
            if hasattr(orc.forma_pagamento, "value")
            else orc.forma_pagamento
        ) if orc.forma_pagamento else "PIX",
        "status": str(orc.status.value if hasattr(orc.status, "value") else orc.status) if orc.status else "enviado",
        "link_publico": str(orc.link_publico or ""),
        "aceite_nome": str(orc.aceite_nome or ""),
        "aceite_em": orc.aceite_em.strftime("%d/%m/%Y %H:%M") if orc.aceite_em else None,
        "cliente": {
            "nome": str(orc.cliente.nome if orc.cliente else "Cliente"),
            "telefone": str(orc.cliente.telefone if orc.cliente else ""),
            "email": str(orc.cliente.email if orc.cliente else ""),
            "documento": str(
                (getattr(orc.cliente, "cnpj", None) or getattr(orc.cliente, "cpf", None))
                if orc.cliente
                else ""
            ),
        },
        "itens": [
            {
                "descricao": str(i.descricao or "Item"),
                "quantidade": float(i.quantidade or 0),
                "valor_unit": float(i.valor_unit or 0),
                "total": float(i.total or 0),
            }
            for i in orc.itens
        ],
        "documentos": [
            {
                "nome": str(d.documento_nome or "Documento"),
                "tipo": str(d.documento_tipo or ""),
                "versao": str(d.documento_versao or ""),
            }
            for d in orc.documentos
        ],
    }

def get_empresa_dict_for_pdf(empresa: Empresa) -> dict:
    """Prepara o dicionário de empresa para o template PDF."""
    return {
        "nome": str(empresa.nome if empresa else "Empresa"),
        "cnpj": str(getattr(empresa, "cnpj", "") if empresa else ""),
        "endereco": str(getattr(empresa, "endereco", "") if empresa else ""),
        "telefone": str(empresa.telefone if empresa else ""),
        "email": str(empresa.email if empresa else ""),
        "logo_url": getattr(empresa, "logo_url", None) if empresa else None,
        "cor_primaria": str(empresa.cor_primaria if empresa else "#00e5a0"),
        "template_orcamento": str(
            getattr(empresa, "template_orcamento", "classico")
            if empresa
            else "classico"
        ),
    }
