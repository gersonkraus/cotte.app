from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import os, shutil, uuid, csv, io, time
from collections import defaultdict

from app.core.database import get_db
from app.core.auth import exigir_permissao
from app.core.tenant_context import set_tenant_context
from app.models.models import Servico, Usuario, CategoriaCatalogo
from app.schemas.schemas import (
    ServicoCreate,
    ServicoUpdate,
    ServicoOut,
    CategoriaCatalogoOut,
    CategoriaCatalogoCreate,
    FiscalSugestaoOut,
    FiscalUpdateRequest,
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
    items_com_status = []
    for item in items:
        duplicado = item["nome"].lower() in nomes_existentes
        items_com_status.append(
            {**item, "duplicado": duplicado, "selecionado": not duplicado}
        )
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

        try:
            preco = float(item_data.get("preco_padrao", 0.0))
        except (ValueError, TypeError):
            preco = 0.0

        servico = Servico(
            empresa_id=usuario.empresa_id,
            nome=nome,
            descricao=item_data.get("descricao"),
            preco_padrao=preco,
            unidade=item_data.get("unidade", "un"),
            categoria_id=item_data.get("categoria_id"),
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

    return {
        "titulo": req.titulo,
        "descricao": req.descricao,
        "tema": req.tema or "classico",
        "categorias": categorias,
        "exibir_preco_venda": req.exibir_preco_venda,
        "incluir_custo": req.incluir_custo,
        "incluir_apresentacao_primeira_folha": req.incluir_apresentacao_primeira_folha,
    }

@router.post("/portfolio/html")
def preview_portfolio_html(
    req: PortfolioGenerateRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "leitura"))
):
    empresa = usuario.empresa
    empresa_dict = {"nome": empresa.nome, "logo_url": empresa.logo_url, "telefone": empresa.telefone, "email": empresa.email}
    
    portfolio_dict = _build_portfolio_dict(db, req, usuario.empresa_id)
    html_str = gerar_html_portfolio(portfolio_dict, empresa_dict)
    return HTMLResponse(content=html_str)

@router.post("/portfolio/pdf")
def download_portfolio_pdf(
    req: PortfolioGenerateRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "leitura"))
):
    empresa = usuario.empresa
    empresa_dict = {"nome": empresa.nome, "logo_url": empresa.logo_url, "telefone": empresa.telefone, "email": empresa.email}
    
    portfolio_dict = _build_portfolio_dict(db, req, usuario.empresa_id)
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
    portfolio_dict = _build_portfolio_dict(db, req, usuario.empresa_id)
    
    nomes_categorias = [c["nome"] for c in portfolio_dict["categorias"]]
    
    prompt = (
        f"Crie um parágrafo introdutório persuasivo e atrativo (max 3 frases) para a capa de um portfólio de produtos/serviços. "
        f"As categorias incluídas são: {', '.join(nomes_categorias)}. "
        f"O tom deve ser profissional, convidativo e focado em valor. "
        f"Apenas retorne o texto final."
    )
    
    resp = ia_service.chat_sync(messages=[{"role": "user", "content": prompt}])
    
    return {"descricao": resp.get("content", "").strip()}

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
