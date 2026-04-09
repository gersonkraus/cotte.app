"""Templates de catálogo por segmento de atuação."""

import json
import os
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.models import Servico, CategoriaCatalogo

_CUSTOM_FILE = os.path.join(os.path.dirname(__file__), "catalogo_templates_custom.json")


def _ler_custom() -> Dict[str, Dict]:
    if not os.path.exists(_CUSTOM_FILE):
        return {}
    try:
        with open(_CUSTOM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _salvar_custom(data: Dict[str, Dict]) -> None:
    with open(_CUSTOM_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _todos_templates() -> Dict[str, Dict]:
    """Retorna hardcoded + custom (custom sobrescreve se mesmo slug)."""
    merged = dict(TEMPLATES_SEGMENTOS)
    merged.update(_ler_custom())
    return merged


TEMPLATES_SEGMENTOS: Dict[str, Dict] = {
    "eletricista": {
        "nome": "Eletricista",
        "descricao": "Serviços elétricos residenciais e comerciais",
        "categorias": ["Serviços", "Materiais elétricos", "Mão de obra"],
        "servicos": [
            {
                "nome": "Instalação de tomada",
                "preco_padrao": 80.00,
                "unidade": "un",
                "categoria": "Serviços",
            },
            {
                "nome": "Instalação de disjuntor",
                "preco_padrao": 120.00,
                "unidade": "un",
                "categoria": "Serviços",
            },
            {
                "nome": "Fiação 2.5mm (metro)",
                "preco_padrao": 3.50,
                "unidade": "m",
                "categoria": "Materiais elétricos",
            },
            {
                "nome": "Fiação 4mm (metro)",
                "preco_padrao": 5.00,
                "unidade": "m",
                "categoria": "Materiais elétricos",
            },
            {
                "nome": "Tomada 10A",
                "preco_padrao": 12.00,
                "unidade": "un",
                "categoria": "Materiais elétricos",
            },
            {
                "nome": "Tomada 20A",
                "preco_padrao": 15.00,
                "unidade": "un",
                "categoria": "Materiais elétricos",
            },
            {
                "nome": "Disjuntor 10A",
                "preco_padrao": 18.00,
                "unidade": "un",
                "categoria": "Materiais elétricos",
            },
            {
                "nome": "Disjuntor 20A",
                "preco_padrao": 22.00,
                "unidade": "un",
                "categoria": "Materiais elétricos",
            },
            {
                "nome": "Mão de obra elétrica (hora)",
                "preco_padrao": 80.00,
                "unidade": "hora",
                "categoria": "Mão de obra",
            },
        ],
    },
    "pedreiro": {
        "nome": "Pedreiro",
        "descricao": "Serviços de alvenaria e reformas",
        "categorias": ["Serviços", "Materiais de construção", "Mão de obra"],
        "servicos": [
            {
                "nome": "Assentamento de piso (m²)",
                "preco_padrao": 45.00,
                "unidade": "m²",
                "categoria": "Serviços",
            },
            {
                "nome": "Assentamento de azulejo (m²)",
                "preco_padrao": 55.00,
                "unidade": "m²",
                "categoria": "Serviços",
            },
            {
                "nome": "Reboco (m²)",
                "preco_padrao": 35.00,
                "unidade": "m²",
                "categoria": "Serviços",
            },
            {
                "nome": "Cimento (saco 50kg)",
                "preco_padrao": 32.00,
                "unidade": "un",
                "categoria": "Materiais de construção",
            },
            {
                "nome": "Areia (m³)",
                "preco_padrao": 120.00,
                "unidade": "m³",
                "categoria": "Materiais de construção",
            },
            {
                "nome": "Tijolo comum",
                "preco_padrao": 0.80,
                "unidade": "un",
                "categoria": "Materiais de construção",
            },
            {
                "nome": "Mão de obra pedreiro (dia)",
                "preco_padrao": 250.00,
                "unidade": "dia",
                "categoria": "Mão de obra",
            },
        ],
    },
    "pintor": {
        "nome": "Pintor",
        "descricao": "Serviços de pintura residencial e comercial",
        "categorias": ["Serviços", "Tintas e materiais", "Mão de obra"],
        "servicos": [
            {
                "nome": "Pintura interna (m²)",
                "preco_padrao": 25.00,
                "unidade": "m²",
                "categoria": "Serviços",
            },
            {
                "nome": "Pintura externa (m²)",
                "preco_padrao": 35.00,
                "unidade": "m²",
                "categoria": "Serviços",
            },
            {
                "nome": "Textura (m²)",
                "preco_padrao": 40.00,
                "unidade": "m²",
                "categoria": "Serviços",
            },
            {
                "nome": "Látex 18L",
                "preco_padrao": 180.00,
                "unidade": "un",
                "categoria": "Tintas e materiais",
            },
            {
                "nome": "Esmalte 3,6L",
                "preco_padrao": 85.00,
                "unidade": "un",
                "categoria": "Tintas e materiais",
            },
            {
                "nome": "Massa corrida 27kg",
                "preco_padrao": 95.00,
                "unidade": "un",
                "categoria": "Tintas e materiais",
            },
            {
                "nome": "Mão de obra pintor (dia)",
                "preco_padrao": 200.00,
                "unidade": "dia",
                "categoria": "Mão de obra",
            },
        ],
    },
    "encanador": {
        "nome": "Encanador",
        "descricao": "Serviços de hidráulica e encanamento",
        "categorias": ["Serviços", "Materiais hidráulicos", "Mão de obra"],
        "servicos": [
            {
                "nome": "Troca de torneira",
                "preco_padrao": 80.00,
                "unidade": "un",
                "categoria": "Serviços",
            },
            {
                "nome": "Desentupimento",
                "preco_padrao": 150.00,
                "unidade": "un",
                "categoria": "Serviços",
            },
            {
                "nome": "Instalação de vaso sanitário",
                "preco_padrao": 200.00,
                "unidade": "un",
                "categoria": "Serviços",
            },
            {
                "nome": "Tubo PVC 50mm (m)",
                "preco_padrao": 12.00,
                "unidade": "m",
                "categoria": "Materiais hidráulicos",
            },
            {
                "nome": "Tubo PVC 100mm (m)",
                "preco_padrao": 22.00,
                "unidade": "m",
                "categoria": "Materiais hidráulicos",
            },
            {
                "nome": "Joelho 90° PVC",
                "preco_padrao": 3.50,
                "unidade": "un",
                "categoria": "Materiais hidráulicos",
            },
            {
                "nome": "Mão de obra encanador (hora)",
                "preco_padrao": 90.00,
                "unidade": "hora",
                "categoria": "Mão de obra",
            },
        ],
    },
    "marceneiro": {
        "nome": "Marceneiro",
        "descricao": "Serviços de marcenaria e carpintaria",
        "categorias": ["Serviços", "Madeiras e materiais", "Mão de obra"],
        "servicos": [
            {
                "nome": "Porta de madeira (un)",
                "preco_padrao": 350.00,
                "unidade": "un",
                "categoria": "Serviços",
            },
            {
                "nome": "Prateleira sob medida (m)",
                "preco_padrao": 120.00,
                "unidade": "m",
                "categoria": "Serviços",
            },
            {
                "nome": "Armário planejado (m²)",
                "preco_padrao": 800.00,
                "unidade": "m²",
                "categoria": "Serviços",
            },
            {
                "nome": "Compensado 15mm (chapa)",
                "preco_padrao": 120.00,
                "unidade": "un",
                "categoria": "Madeiras e materiais",
            },
            {
                "nome": "MDF 15mm (chapa)",
                "preco_padrao": 150.00,
                "unidade": "un",
                "categoria": "Madeiras e materiais",
            },
            {
                "nome": "Dobradiça comum",
                "preco_padrao": 8.00,
                "unidade": "un",
                "categoria": "Madeiras e materiais",
            },
            {
                "nome": "Mão de obra marceneiro (dia)",
                "preco_padrao": 280.00,
                "unidade": "dia",
                "categoria": "Mão de obra",
            },
        ],
    },
    "geral": {
        "nome": "Geral",
        "descricao": "Template genérico para diversos tipos de serviço",
        "categorias": ["Serviços", "Materiais", "Mão de obra", "Transporte"],
        "servicos": [
            {
                "nome": "Serviço genérico",
                "preco_padrao": 100.00,
                "unidade": "un",
                "categoria": "Serviços",
            },
            {
                "nome": "Material genérico",
                "preco_padrao": 50.00,
                "unidade": "un",
                "categoria": "Materiais",
            },
            {
                "nome": "Mão de obra (hora)",
                "preco_padrao": 80.00,
                "unidade": "hora",
                "categoria": "Mão de obra",
            },
            {
                "nome": "Transporte (km)",
                "preco_padrao": 2.50,
                "unidade": "km",
                "categoria": "Transporte",
            },
        ],
    },
}


def listar_segmentos() -> List[Dict]:
    """Retorna lista resumida dos segmentos disponíveis (hardcoded + custom)."""
    return [
        {"slug": slug, "nome": t["nome"], "descricao": t["descricao"], "custom": slug not in TEMPLATES_SEGMENTOS}
        for slug, t in _todos_templates().items()
    ]


def obter_template(segmento: str) -> Dict | None:
    """Retorna o template completo de um segmento."""
    return _todos_templates().get(segmento)


# ── ADMIN: gerenciar templates custom ──────────────────────────────────

def admin_listar_templates() -> List[Dict]:
    """Lista todos os templates com flag de origem."""
    result = []
    custom = _ler_custom()
    for slug, t in TEMPLATES_SEGMENTOS.items():
        result.append({
            "slug": slug,
            "nome": t["nome"],
            "descricao": t["descricao"],
            "categorias": t["categorias"],
            "servicos": t["servicos"],
            "custom": False,
        })
    for slug, t in custom.items():
        result.append({
            "slug": slug,
            "nome": t["nome"],
            "descricao": t["descricao"],
            "categorias": t["categorias"],
            "servicos": t["servicos"],
            "custom": True,
        })
    return result


def admin_criar_template(slug: str, dados: Dict) -> Dict:
    """Cria um template custom."""
    custom = _ler_custom()
    if slug in custom:
        raise ValueError("Slug já existe em templates custom")
    custom[slug] = {
        "nome": dados["nome"],
        "descricao": dados.get("descricao", ""),
        "categorias": dados.get("categorias", []),
        "servicos": dados.get("servicos", []),
    }
    _salvar_custom(custom)
    return {**custom[slug], "slug": slug, "custom": True}


def admin_atualizar_template(slug: str, dados: Dict) -> Dict:
    """Atualiza um template custom (não pode editar hardcoded)."""
    if slug in TEMPLATES_SEGMENTOS and slug not in _ler_custom():
        raise ValueError("Templates padrão não podem ser editados")
    custom = _ler_custom()
    custom[slug] = {
        "nome": dados.get("nome", custom.get(slug, {}).get("nome", slug)),
        "descricao": dados.get("descricao", custom.get(slug, {}).get("descricao", "")),
        "categorias": dados.get("categorias", custom.get(slug, {}).get("categorias", [])),
        "servicos": dados.get("servicos", custom.get(slug, {}).get("servicos", [])),
    }
    _salvar_custom(custom)
    return {**custom[slug], "slug": slug, "custom": True}


def admin_deletar_template(slug: str) -> None:
    """Deleta um template custom (não pode deletar hardcoded)."""
    custom = _ler_custom()
    if slug not in custom:
        raise ValueError("Template não encontrado ou não é custom")
    del custom[slug]
    _salvar_custom(custom)


def importar_template_para_empresa(segmento: str, empresa_id: int, db: Session) -> Dict:
    """Importa categorias e serviços de um template para a empresa."""
    template = _todos_templates().get(segmento)
    if not template:
        return {"erro": "Segmento não encontrado"}

    categorias_criadas = []
    mapa_categorias = {}

    for nome_cat in template["categorias"]:
        existente = (
            db.query(CategoriaCatalogo)
            .filter(
                CategoriaCatalogo.empresa_id == empresa_id,
                CategoriaCatalogo.nome == nome_cat,
            )
            .first()
        )
        if existente:
            mapa_categorias[nome_cat] = existente.id
        else:
            nova = CategoriaCatalogo(empresa_id=empresa_id, nome=nome_cat)
            db.add(nova)
            db.flush()
            mapa_categorias[nome_cat] = nova.id
            categorias_criadas.append(nome_cat)

    nomes_existentes = {
        s.nome.lower()
        for s in db.query(Servico.nome).filter(Servico.empresa_id == empresa_id).all()
    }

    servicos_criados = 0
    for item in template["servicos"]:
        if item["nome"].lower() in nomes_existentes:
            continue
        servico = Servico(
            empresa_id=empresa_id,
            nome=item["nome"],
            preco_padrao=item["preco_padrao"],
            unidade=item["unidade"],
            categoria_id=mapa_categorias.get(item.get("categoria")),
            ativo=True,
        )
        db.add(servico)
        nomes_existentes.add(item["nome"].lower())
        servicos_criados += 1

    db.flush()

    return {
        "segmento": segmento,
        "categorias_criadas": len(categorias_criadas),
        "servicos_criados": servicos_criados,
    }
