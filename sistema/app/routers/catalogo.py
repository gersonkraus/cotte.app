from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from typing import List
import os, shutil, uuid, csv, io

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
)
from app.services.ia_service import interpretar_tabela_catalogo
from app.services.r2_service import r2_service
from app.services.catalogo_service import seed_catalogo_padrao
from app.services.template_segmento_service import (
    listar_segmentos,
    obter_template,
    importar_template_para_empresa,
)

router = APIRouter(prefix="/catalogo", tags=["Catálogo"])

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
    seed_catalogo_padrao(usuario.empresa_id, db)
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
):
    """Lista serviços do catálogo da empresa."""
    # Reforça o escopo tenant na sessão desta rota.
    set_tenant_context(
        db,
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        is_superadmin=usuario.is_superadmin,
    )
    seed_catalogo_padrao(usuario.empresa_id, db)
    query = (
        db.query(Servico)
        .options(joinedload(Servico.categoria))
        .filter(Servico.empresa_id == usuario.empresa_id)
    )
    if apenas_ativos:
        query = query.filter(Servico.ativo == True)
    return query.order_by(Servico.nome).all()


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
        unidade=dados.unidade,
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
    filename = (file.filename or "").lower()
    conteudo = await file.read()

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
