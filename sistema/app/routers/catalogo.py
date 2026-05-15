from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import os, shutil, uuid, csv, io, time
from collections import defaultdict

from app.core.database import get_db
from app.core.auth import exigir_permissao
from app.core.tenant_context import set_tenant_context
from app.models.models import Servico, Usuario, CategoriaCatalogo, Empresa
from app.schemas.schemas import (
    ServicoCreate,
    ServicoUpdate,
    ServicoOut,
    CategoriaCatalogoOut,
    CategoriaCatalogoCreate,
    FiscalSugestaoOut,
    FiscalUpdateRequest,
    SloganIARequest,
)
from app.services.ia_service import interpretar_tabela_catalogo
from app.services.fiscal_ai_service import sugerir_dados_fiscais
from app.services.r2_service import r2_service
from app.services.template_segmento_service import (
    listar_segmentos,
    obter_template,
    importar_template_para_empresa,
)

router = APIRouter(prefix="/catalogo", tags=["Catálogo"])

# Rate limit simples em memória: máx 10 chamadas de IA por empresa a cada 60s
_ia_calls: dict = defaultdict(list)
_IA_MAX_CALLS = 10
_IA_JANELA_SEG = 60


def _checar_rate_limit_ia(empresa_id: int) -> None:
    agora = time.monotonic()
    historico = _ia_calls[empresa_id]
    _ia_calls[empresa_id] = [t for t in historico if agora - t < _IA_JANELA_SEG]
    if len(_ia_calls[empresa_id]) >= _IA_MAX_CALLS:
        raise HTTPException(
            status_code=429,
            detail=f"Limite de {_IA_MAX_CALLS} análises por minuto atingido. Aguarde e tente novamente.",
        )
    _ia_calls[empresa_id].append(agora)

IMAGES_DIR = "static/images"
os.makedirs(IMAGES_DIR, exist_ok=True)

EXTENSOES_PERMITIDAS = {".png", ".jpg", ".jpeg", ".webp"}


# ── CATEGORIAS ──────────────────────────────────────────────────────────────
# Rotas de /categorias devem vir ANTES de /{servico_id} para evitar conflito


@router.get("/categorias", response_model=List[CategoriaCatalogoOut])
def listar_categorias(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "leitura")),
):
    """Lista categorias do catálogo da empresa."""
    return (
        db.query(CategoriaCatalogo)
        .filter(CategoriaCatalogo.empresa_id == usuario.empresa_id)
        .order_by(CategoriaCatalogo.nome)
        .all()
    )


@router.post("/categorias", response_model=CategoriaCatalogoOut, status_code=201)
def criar_categoria(
    dados: CategoriaCatalogoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "escrita")),
):
    """Cria uma nova categoria no catálogo."""
    cat = CategoriaCatalogo(empresa_id=usuario.empresa_id, nome=dados.nome.strip())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/categorias/{categoria_id}", status_code=204)
def deletar_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "admin")),
):
    """Remove uma categoria do catálogo."""
    cat = (
        db.query(CategoriaCatalogo)
        .filter(
            CategoriaCatalogo.id == categoria_id,
            CategoriaCatalogo.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    vinculados = db.query(Servico).filter(Servico.categoria_id == categoria_id).count()
    if vinculados > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Categoria possui {vinculados} item(s) vinculado(s). Desvincule antes de excluir.",
        )
    db.delete(cat)
    db.commit()


# ── SERVIÇOS ─────────────────────────────────────────────────────────────────


@router.get("/", response_model=List[ServicoOut])
def listar_catalogo(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "leitura")),
    apenas_ativos: bool = True,
    categoria_id: int = None,
    skip: int = 0,
    limit: int = 500,
):
    try:
        set_tenant_context(
            db,
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            is_superadmin=usuario.is_superadmin,
        )
        query = (
            db.query(Servico)
            .options(joinedload(Servico.categoria))
            .filter(Servico.empresa_id == usuario.empresa_id)
        )
        if apenas_ativos:
            query = query.filter(Servico.ativo == True)
        if categoria_id is not None:
            query = query.filter(Servico.categoria_id == categoria_id)
        return query.order_by(Servico.nome).offset(skip).limit(limit).all()
    except Exception as e:
        import traceback
        with open("/tmp/opencode/catalogo_500.txt", "w") as f:
            f.write(traceback.format_exc())
        raise


@router.get("/portfolio/produtos", response_model=List[ServicoOut])
def listar_produtos_para_portfolio(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "leitura")),
    categoria_id: Optional[int] = None,
    apenas_com_imagem: bool = False,
    limit: int = Query(500, ge=1, le=500),
):
    """Lista produtos ativos para montagem visual do portfólio (grade de seleção)."""
    query = (
        db.query(Servico)
        .options(joinedload(Servico.categoria))
        .filter(
            Servico.empresa_id == usuario.empresa_id,
            Servico.ativo == True,
        )
    )
    if categoria_id is not None:
        query = query.filter(Servico.categoria_id == categoria_id)
    if apenas_com_imagem:
        query = query.filter(
            Servico.imagem_url.isnot(None),
            Servico.imagem_url != "",
        )
    return query.order_by(Servico.categoria_id, Servico.nome).limit(limit).all()


@router.get("/{servico_id}", response_model=ServicoOut)
def obter_servico(
    servico_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "leitura")),
):
    """Retorna um único serviço pelo ID."""
    srv = (
        db.query(Servico)
        .options(joinedload(Servico.categoria))
        .filter(
            Servico.id == servico_id,
            Servico.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not srv:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return srv


@router.post("/", response_model=ServicoOut, status_code=status.HTTP_201_CREATED)
def criar_servico(
    dados: ServicoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "escrita")),
):
    """Cria um novo serviço no catálogo."""
    servico = Servico(
        empresa_id=usuario.empresa_id,
        nome=dados.nome,
        descricao=dados.descricao,
        preco_padrao=dados.preco_padrao,
        preco_custo=dados.preco_custo,
        unidade=dados.unidade,
        categoria_id=dados.categoria_id,
        ativo=True,
    )
    db.add(servico)
    db.commit()
    db.refresh(servico)
    return servico


@router.put("/{servico_id}", response_model=ServicoOut)
def atualizar_servico(
    servico_id: int,
    dados: ServicoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "escrita")),
):
    """Atualiza os dados de um serviço existente."""
    srv = (
        db.query(Servico)
        .filter(
            Servico.id == servico_id,
            Servico.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not srv:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(srv, campo, valor)

    db.commit()
    db.refresh(srv)
    return srv


@router.patch("/{servico_id}", response_model=ServicoOut)
def patch_servico(
    servico_id: int,
    dados: ServicoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "escrita")),
):
    """Atualização parcial de um serviço (ex: reativar item)."""
    srv = (
        db.query(Servico)
        .filter(
            Servico.id == servico_id,
            Servico.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not srv:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(srv, campo, valor)

    db.commit()
    db.refresh(srv)
    return srv


@router.delete("/{servico_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_servico(
    servico_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "admin")),
):
    """Desativa um serviço (soft delete)."""
    srv = (
        db.query(Servico)
        .filter(
            Servico.id == servico_id,
            Servico.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not srv:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    # Soft delete — preserva histórico de orçamentos
    srv.ativo = False
    db.commit()


@router.post("/{servico_id}/imagem", response_model=ServicoOut)
async def upload_imagem_servico(
    servico_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "escrita")),
):
    """Faz upload de imagem para um serviço."""
    srv = (
        db.query(Servico)
        .filter(
            Servico.id == servico_id,
            Servico.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not srv:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não permitido. Use: {', '.join(EXTENSOES_PERMITIDAS)}",
        )

    # Remove imagem anterior se existir
    if srv.imagem_url:
        r2_service.delete_file(srv.imagem_url)

    # Upload para R2
    mime_type = file.content_type or "image/jpeg"
    file_url = r2_service.upload_file(
        file_obj=file.file,
        empresa_id=usuario.empresa_id,
        tipo="catalogo",
        extensao=ext,
        content_type=mime_type,
    )

    srv.imagem_url = file_url
    db.commit()
    db.refresh(srv)
    return srv


@router.delete("/{servico_id}/imagem", response_model=ServicoOut)
def remover_imagem_servico(
    servico_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "escrita")),
):
    """Remove a imagem de um serviço."""
    srv = (
        db.query(Servico)
        .filter(
            Servico.id == servico_id,
            Servico.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not srv:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    if srv.imagem_url:
        r2_service.delete_file(srv.imagem_url)
        srv.imagem_url = None
        db.commit()
        db.refresh(srv)
    return srv


@router.post("/analisar-importacao", status_code=200)
async def analisar_importacao(
    payload: dict,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "escrita")),
):
    """Analisa texto colado para importação de catálogo."""
    _checar_rate_limit_ia(usuario.empresa_id)
    texto = payload.get("texto", "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Texto da tabela vazio")

    items = await interpretar_tabela_catalogo(texto)
    return _enriquecer_com_duplicatas(items, db, usuario.empresa_id)


def _enriquecer_com_duplicatas(items: list[dict], db: Session, empresa_id: int) -> dict:
    """Comum entre analisar-importacao e analisar-arquivo."""
    nomes_existentes = {
        s.nome.lower()
        for s in db.query(Servico.nome).filter(Servico.empresa_id == empresa_id).all()
    }
    categorias = {
        c.nome.lower(): c.id
        for c in db.query(CategoriaCatalogo).filter(CategoriaCatalogo.empresa_id == empresa_id).all()
    }
    items_com_status = []
    for item in items:
        duplicado = item["nome"].lower() in nomes_existentes
        sugestao = item.get("categoria_sugerida", "")
        categoria_sugerida_id = None
        if sugestao:
            categoria_sugerida_id = categorias.get(sugestao.lower().strip())
        items_com_status.append({
            **item,
            "duplicado": duplicado,
            "selecionado": not duplicado,
            "categoria_sugerida_id": categoria_sugerida_id,
            "categoria_sugerida_nome": sugestao if sugestao else None,
        })
    return {"items": items_com_status, "total": len(items_com_status)}


@router.post("/analisar-arquivo", status_code=200)
async def analisar_arquivo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "escrita")),
):
    """Analisa arquivo (CSV/XLSX/PDF) para importação."""
    _checar_rate_limit_ia(usuario.empresa_id)
    MAX_SIZE = 5 * 1024 * 1024  # 5MB
    filename = (file.filename or "").lower()
    conteudo = await file.read()
    if len(conteudo) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="Arquivo muito grande. Máximo permitido: 5MB")

    if filename.endswith(".csv"):
        try:
            texto_decodificado = conteudo.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto_decodificado = conteudo.decode("latin-1")
        reader = csv.reader(io.StringIO(texto_decodificado))
        linhas = ["\t".join(row) for row in reader if any(c.strip() for c in row)]
        texto = "\n".join(linhas)

    elif filename.endswith((".xlsx", ".xls")):
        try:
            import openpyxl

            wb = openpyxl.load_workbook(
                io.BytesIO(conteudo), read_only=True, data_only=True
            )
            ws = wb.active
            linhas = []
            for row in ws.iter_rows(values_only=True):
                valores = [str(c) if c is not None else "" for c in row]
                if any(v.strip() for v in valores):
                    linhas.append("\t".join(valores))
            texto = "\n".join(linhas)
            wb.close()
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Erro ao ler arquivo Excel: {e}"
            )
    elif filename.endswith(".pdf"):
        try:
            import pdfplumber

            linhas = []
            with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
                for page in pdf.pages:
                    # Tenta extrair tabelas estruturadas primeiro
                    tabelas = page.extract_tables()
                    if tabelas:
                        for tabela in tabelas:
                            for row in tabela:
                                valores = [str(c) if c is not None else "" for c in row]
                                if any(v.strip() for v in valores):
                                    linhas.append("\t".join(valores))
                    else:
                        # Fallback: extrai texto livre da página
                        t = page.extract_text()
                        if t:
                            linhas.extend(t.splitlines())
            texto = "\n".join(linhas)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erro ao ler PDF: {e}")
    else:
        raise HTTPException(
            status_code=400, detail="Formato não suportado. Use .csv, .xlsx ou .pdf"
        )

    if not texto.strip():
        raise HTTPException(status_code=400, detail="Arquivo vazio ou sem dados")

    items = await interpretar_tabela_catalogo(texto)
    return _enriquecer_com_duplicatas(items, db, usuario.empresa_id)


@router.post("/importar-lote", status_code=201)
def importar_lote(
    payload: dict,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "admin")),
):
    """Importa lista de serviços em lote para o catálogo."""
    items_dados = payload.get("items", [])
    if not items_dados:
        raise HTTPException(status_code=400, detail="Nenhum item para importar")

    criados = []
    nomes_existentes = {
        s.nome.lower()
        for s in db.query(Servico.nome)
        .filter(Servico.empresa_id == usuario.empresa_id)
        .all()
    }

    for item_data in items_dados:
        nome = item_data.get("nome", "").strip()
        if not nome or nome.lower() in nomes_existentes:
            continue  # skip duplicatas

        categoria_id = item_data.get("categoria_id")
        if not categoria_id:
            raise HTTPException(status_code=400, detail=f"O produto '{nome}' requer uma categoria. Seleção obrigatória.")

        try:
            preco = float(item_data.get("preco_padrao", 0.0))
        except (ValueError, TypeError):
            preco = 0.0

        try:
            preco_custo = float(item_data.get("preco_custo", 0.0)) if item_data.get("preco_custo") else None
        except (ValueError, TypeError):
            preco_custo = None

        servico = Servico(
            empresa_id=usuario.empresa_id,
            nome=nome,
            descricao=item_data.get("descricao"),
            preco_padrao=preco,
            preco_custo=preco_custo,
            unidade=item_data.get("unidade", "un"),
            categoria_id=categoria_id,
            ativo=True,
        )
        db.add(servico)
        nomes_existentes.add(nome.lower())

    db.commit()

    # Retorna lista de items criados
    items_novos = (
        db.query(Servico)
        .filter(
            Servico.empresa_id == usuario.empresa_id,
            Servico.nome.in_([item["nome"] for item in items_dados]),
        )
        .all()
    )

    return {
        "criados": len(items_novos),
        "items": [ServicoOut.from_orm(s) for s in items_novos],
    }


# ── TEMPLATES DE SEGMENTO ─────────────────────────────────────────────────────


@router.get("/templates/segmentos", status_code=200)
def get_segmentos(
    usuario: Usuario = Depends(exigir_permissao("catalogo", "leitura")),
):
    """Lista segmentos disponíveis para importação de template."""
    return listar_segmentos()


@router.get("/templates/{segmento}", status_code=200)
def get_template(
    segmento: str,
    usuario: Usuario = Depends(exigir_permissao("catalogo", "leitura")),
):
    """Retorna o template completo de um segmento."""
    template = obter_template(segmento)
    if not template:
        raise HTTPException(status_code=404, detail="Segmento não encontrado")
    return template


@router.post("/templates/{segmento}/importar", status_code=201)
def importar_template(
    segmento: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "admin")),
):
    """Importa categorias e serviços de um template para a empresa."""
    resultado = importar_template_para_empresa(segmento, usuario.empresa_id, db)
    if "erro" in resultado:
        raise HTTPException(status_code=404, detail=resultado["erro"])
    db.commit()
    return resultado


# ── DADOS FISCAIS ────────────────────────────────────────────────────────────


@router.get("/{servico_id}/sugerir-fiscal", response_model=FiscalSugestaoOut)
async def sugerir_fiscal_servico(
    servico_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "leitura")),
):
    """Usa IA para sugerir NCM, CFOP, CSOSN e unidade para um produto do catálogo."""
    _checar_rate_limit_ia(usuario.empresa_id)

    servico = (
        db.query(Servico)
        .options(joinedload(Servico.categoria))
        .filter(Servico.id == servico_id, Servico.empresa_id == usuario.empresa_id)
        .first()
    )
    if not servico:
        raise HTTPException(404, "Produto não encontrado")

    categoria = servico.categoria.nome if servico.categoria else None
    preco = float(servico.preco_padrao) if servico.preco_padrao else None
    descricao = servico.descricao or servico.nome

    dados = await sugerir_dados_fiscais(descricao, categoria, preco)
    return FiscalSugestaoOut(**dados)


@router.patch("/{servico_id}/fiscal", response_model=ServicoOut)
def salvar_fiscal_servico(
    servico_id: int,
    dados: FiscalUpdateRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "escrita")),
):
    """Salva dados fiscais (NCM, CFOP, CSOSN, origem, unidade_fiscal) em um produto."""
    servico = (
        db.query(Servico)
        .filter(Servico.id == servico_id, Servico.empresa_id == usuario.empresa_id)
        .first()
    )
    if not servico:
        raise HTTPException(404, "Produto não encontrado")

    if dados.ncm is not None:
        servico.ncm = dados.ncm
    if dados.cfop is not None:
        servico.cfop = dados.cfop
    if dados.csosn is not None:
        servico.csosn = dados.csosn
    if dados.origem is not None:
        servico.origem = dados.origem
    if dados.unidade_fiscal is not None:
        servico.unidade_fiscal = dados.unidade_fiscal
    if dados.dados_fiscais_ok is not None:
        servico.dados_fiscais_ok = dados.dados_fiscais_ok

    db.commit()
    db.refresh(servico)
    return servico

from app.schemas.schemas import PortfolioGenerateRequest, PortfolioSendRequest, PortfolioLinkOut
from app.services.pdf_service import gerar_html_portfolio, gerar_pdf_portfolio
from app.services.ia_service import ia_service
from app.services.whatsapp_service import enviar_mensagem_texto
from app.core.cache import CacheManager
from fastapi.responses import HTMLResponse, Response
from fastapi import BackgroundTasks
import json

cache = CacheManager()

_TEMAS_PORTFOLIO_VALIDOS = {"classico", "escuro", "corporativo", "elegante", "natureza", "sunset", "grafite", "meia-noite", "minimalista"}

def _normalizar_tema_portfolio(tema: Optional[str]) -> str:
    t = (tema or "").strip().lower()
    if t in ("moderno", "dark"):
        return "escuro"
    if t in _TEMAS_PORTFOLIO_VALIDOS:
        return t
    return "classico"

def _gerar_texto_capa_fallback(
    empresa_dict: dict,
    nomes_categorias: list[str],
    tom_voz: str,
    objetivo: str,
) -> str:
    inicio_por_tom = {
        "consultivo": "Apresentamos um portfólio construído para apoiar decisões com clareza e resultado.",
        "premium": "Apresentamos um portfólio com curadoria especializada, foco em excelência e alto padrão de entrega.",
        "tecnico": "Apresentamos um portfólio estruturado com soluções objetivas, confiáveis e orientadas por desempenho.",
        "acolhedor": "Apresentamos um portfólio pensado para oferecer atendimento próximo, confiança e qualidade em cada etapa.",
        "profissional": "Apresentamos um portfólio com soluções selecionadas para gerar valor real ao seu negócio.",
    }
    inicio = inicio_por_tom.get((tom_voz or "profissional").strip().lower(), inicio_por_tom["profissional"])
    nome_empresa = empresa_dict.get("nome") or "Nossa empresa"
    categorias_txt = ", ".join([n for n in nomes_categorias if n]) or "diversas categorias"
    objetivo_txt = f" {objetivo.strip()}" if (objetivo or "").strip() else ""
    return (
        f"{nome_empresa}: {inicio} "
        f"Atuamos com {categorias_txt}, priorizando qualidade, agilidade e parceria comercial.{objetivo_txt}"
    ).strip()

def _empresa_para_portfolio_dict(empresa: Empresa) -> dict:
    endereco_partes = [
        (empresa.endereco_logradouro or "").strip(),
        (empresa.endereco_numero or "").strip(),
        (empresa.endereco_bairro or "").strip(),
        (empresa.endereco_cidade or "").strip(),
        (empresa.endereco_uf or "").strip(),
    ]
    endereco = ", ".join([p for p in endereco_partes if p])
    return {
        "nome": empresa.nome,
        "logo_url": empresa.logo_url,
        "capa_portfolio_url": getattr(empresa, "capa_portfolio_url", None),
        "capa_slogan": getattr(empresa, "capa_slogan", None) or "",
        "cor_primaria": getattr(empresa, "cor_primaria", None) or "#00e5a0",
        "telefone": empresa.telefone,
        "email": empresa.email,
        "descricao_publica_empresa": empresa.descricao_publica_empresa,
        "endereco_apresentacao": endereco or None,
    }

def _build_portfolio_dict(db: Session, req: PortfolioGenerateRequest, empresa_id: int) -> dict:
    categorias: list = []

    if req.servicos_ids is not None:
        ids_unicos = list(dict.fromkeys(req.servicos_ids))
        servicos_db = (
            db.query(Servico)
            .options(joinedload(Servico.categoria))
            .filter(
                Servico.id.in_(ids_unicos),
                Servico.empresa_id == empresa_id,
                Servico.ativo == True,
            )
            .all()
        )
        id_map = {s.id: s for s in servicos_db}
        servicos_ordenados = [id_map[i] for i in ids_unicos if i in id_map]

        por_categoria: dict = {}
        for s in servicos_ordenados:
            cat_key = s.categoria_id if s.categoria_id is not None else -1
            if cat_key not in por_categoria:
                cat_nome = s.categoria.nome if s.categoria else "Sem categoria"
                por_categoria[cat_key] = {
                    "id": s.categoria_id,
                    "nome": cat_nome,
                    "itens": [],
                }
            item_dict = {
                "id": s.id,
                "nome": s.nome,
                "descricao": s.descricao or "",
                "preco": float(s.preco_padrao),
                "unidade": (s.unidade or "un"),
                "imagem_url": s.imagem_url,
                "mostrar_preco_venda": req.exibir_preco_venda,
                "mostrar_custo": req.incluir_custo,
            }
            if req.incluir_custo:
                item_dict["custo"] = float(s.preco_custo or 0)
            por_categoria[cat_key]["itens"].append(item_dict)

        categorias = list(por_categoria.values())
    else:
        query = db.query(CategoriaCatalogo).filter(
            CategoriaCatalogo.empresa_id == empresa_id
        )
        if req.categorias_ids:
            query = query.filter(CategoriaCatalogo.id.in_(req.categorias_ids))
        categorias_db = query.options(joinedload(CategoriaCatalogo.servicos)).all()

        for c in categorias_db:
            itens = []
            for s in c.servicos:
                if not s.ativo or s.empresa_id != empresa_id:
                    continue

                item_dict = {
                    "id": s.id,
                    "nome": s.nome,
                    "descricao": s.descricao or "",
                    "preco": float(s.preco_padrao),
                    "unidade": (s.unidade or "un"),
                    "imagem_url": s.imagem_url,
                    "mostrar_preco_venda": req.exibir_preco_venda,
                    "mostrar_custo": req.incluir_custo,
                }
                if req.incluir_custo:
                    item_dict["custo"] = float(s.preco_custo or 0)

                itens.append(item_dict)

            if itens:
                categorias.append({"id": c.id, "nome": c.nome, "itens": itens})

    layout = (getattr(req, "layout", None) or "compacto").strip().lower()
    if layout not in ("compacto", "galeria"):
        layout = "compacto"

    return {
        "titulo": req.titulo,
        "descricao": req.descricao,
        "tema": _normalizar_tema_portfolio(req.tema),
        "layout": layout,
        "categorias": categorias,
        "exibir_preco_venda": req.exibir_preco_venda,
        "incluir_custo": req.incluir_custo,
        "incluir_apresentacao_primeira_folha": req.incluir_apresentacao_primeira_folha,
        "exibir_categorias": req.exibir_categorias,
        "exibir_logo": req.exibir_logo,
        "dados_empresa_personalizados": req.dados_empresa_personalizados,
        "segmento_empresa": req.segmento_empresa,
        "tom_voz_capa": req.tom_voz_capa or "profissional",
        "objetivo_capa": req.objetivo_capa,
    }

@router.post("/portfolio/html")
def preview_portfolio_html(
    req: PortfolioGenerateRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "leitura"))
):
    empresa_dict = _empresa_para_portfolio_dict(usuario.empresa)

    portfolio_dict = _build_portfolio_dict(db, req, usuario.empresa_id)
    portfolio_dict["layout"] = req.layout
    html_str = gerar_html_portfolio(portfolio_dict, empresa_dict)
    return HTMLResponse(content=html_str)

@router.post("/portfolio/pdf")
def download_portfolio_pdf(
    req: PortfolioGenerateRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "leitura"))
):
    empresa_dict = _empresa_para_portfolio_dict(usuario.empresa)

    portfolio_dict = _build_portfolio_dict(db, req, usuario.empresa_id)
    portfolio_dict["layout"] = req.layout
    pdf_bytes = gerar_pdf_portfolio(portfolio_dict, empresa_dict)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=portfolio.pdf"}
    )

@router.post("/portfolio/link", response_model=PortfolioLinkOut)
def gerar_link_efemero_portfolio(
    req: PortfolioGenerateRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "leitura"))
):
    """Gera um link público efêmero armazenando o state da geração no cache."""
    import uuid
    # Store config with 7 days TTL
    link_uuid = str(uuid.uuid4())
    cache.set(f"portfolio_link:{link_uuid}", {"req": req.model_dump(), "empresa_id": usuario.empresa_id}, ttl=86400 * 7)
    
    # Returning relative link. The frontend should prepend window.location.origin
    return {"link": f"/p/cat-{link_uuid}", "uuid": link_uuid}

@router.post("/portfolio/sugerir-descricao-ia")
def sugerir_descricao_ia(
    req: PortfolioGenerateRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "leitura"))
):
    empresa_dict = _empresa_para_portfolio_dict(usuario.empresa)
    portfolio_dict = _build_portfolio_dict(db, req, usuario.empresa_id)
    
    nomes_categorias = [c["nome"] for c in portfolio_dict["categorias"]]
    segmento = (req.segmento_empresa or "").strip() or "não informado"
    tom_voz = (req.tom_voz_capa or "").strip() or "profissional"
    objetivo = (req.objetivo_capa or "").strip()
    dados_empresa = [
        f"Empresa: {empresa_dict.get('nome') or 'não informado'}",
        f"Telefone: {empresa_dict.get('telefone') or 'não informado'}",
        f"E-mail: {empresa_dict.get('email') or 'não informado'}",
        f"Endereço: {empresa_dict.get('endereco_apresentacao') or 'não informado'}",
        f"Descrição institucional atual: {empresa_dict.get('descricao_publica_empresa') or 'não informado'}",
    ]
    objetivo_linha = f"Objetivo da capa: {objetivo}. " if objetivo else ""
    
    prompt = (
        "Crie um texto institucional curto para a capa de apresentação da empresa "
        "em um portfólio comercial (máximo 3 frases, português do Brasil). "
        f"Segmento da empresa: {segmento}. "
        f"Tom de voz desejado: {tom_voz}. "
        f"{objetivo_linha}"
        f"Categorias incluídas no portfólio: {', '.join(nomes_categorias) or 'não informado'}. "
        f"Dados da empresa para contexto: {' | '.join(dados_empresa)}. "
        "Regras: texto objetivo, comercial, sem emoji, sem listas e sem marcadores. "
        "Apenas retorne o texto final."
    )
    
    try:
        resp = ia_service.chat_sync(messages=[{"role": "user", "content": prompt}])
        texto = (resp.get("content", "") if isinstance(resp, dict) else "").strip()
    except Exception:
        texto = ""

    if not texto:
        texto = _gerar_texto_capa_fallback(
            empresa_dict=empresa_dict,
            nomes_categorias=nomes_categorias,
            tom_voz=tom_voz,
            objetivo=objetivo,
        )

    return {"descricao": texto}

@router.post("/portfolio/sugerir-slogan-ia")
def sugerir_slogan_ia(
    req: SloganIARequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "leitura")),
):
    """Gera uma tagline curta (1 linha, máx 80 chars) para o banner de capa."""
    empresa = usuario.empresa
    segmento = (req.segmento or "").strip() or "não informado"
    nome = empresa.nome or "Empresa"
    descricao = (empresa.descricao_publica_empresa or "").strip()

    prompt = (
        "Crie uma tagline comercial curta para o banner de capa de um portfólio de produtos. "
        f"Empresa: {nome}. Segmento: {segmento}. "
        f"{'Descrição: ' + descricao + '. ' if descricao else ''}"
        "Regras: máximo 80 caracteres, português do Brasil, sem emoji, "
        "sem aspas, sem ponto final obrigatório, tom profissional e direto. "
        "Retorne APENAS a tagline, sem explicações."
    )

    try:
        resp = ia_service.chat_sync(messages=[{"role": "user", "content": prompt}])
        slogan = (resp.get("content", "") if isinstance(resp, dict) else "").strip()
        slogan = slogan.strip('"\'').strip()[:80]
    except Exception:
        slogan = ""

    if not slogan:
        slogan = f"{nome} — qualidade e confiança."

    return {"slogan": slogan}

@router.post("/portfolio/enviar")
def enviar_portfolio(
    req: PortfolioSendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "leitura"))
):
    import uuid
    import os
    # To send a mini-site link we need to generate one
    link_uuid = str(uuid.uuid4())
    cache.set(f"portfolio_link:{link_uuid}", {"req": req.model_dump(), "empresa_id": usuario.empresa_id}, ttl=86400 * 7)
    
    from app.models.models import Empresa
    from sqlalchemy.orm import joinedload
    empresa = db.query(Empresa).options(
        joinedload(Empresa.pacote).joinedload("modulos")
    ).filter(Empresa.id == usuario.empresa_id).first()
    
    if req.telefone_whatsapp:
        # Background task para enviar PDF ou link pelo wpp
        # Enviaremos link efêmero preferencialmente. Se quiser PDF, precisará mudar ou adicionar opção no modal.
        # Aqui enviamos o link.
        msg = f"Olá! Veja nosso portfólio atualizado: {req.titulo}\nAcesse o link: {os.getenv('APP_URL', 'https://cotte.app')}/p/cat-{link_uuid}"
        
        # Call whatsapp_service
        background_tasks.add_task(
            whatsapp_service.enviar_mensagem_texto,
            req.telefone_whatsapp,
            msg,
            empresa=empresa
        )
        
    return {"sucesso": True, "link": f"/p/cat-{link_uuid}"}
