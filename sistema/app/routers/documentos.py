from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import get_usuario_atual, exigir_permissao
from app.core.database import get_db
from app.models.models import (
    DocumentoEmpresa,
    StatusDocumentoEmpresa,
    TipoDocumentoEmpresa,
    TipoConteudoDocumento,
    Usuario,
)
from app.schemas.schemas import DocumentoEmpresaOut, DocumentoEmpresaUpdate
from app.services.documentos_service import (
    gerar_slug_documento,
    montar_nome_download,
    resolver_arquivo_path,
    salvar_upload_documento,
)


router = APIRouter(prefix="/documentos", tags=["Documentos"])


@router.get("/", response_model=List[DocumentoEmpresaOut])
def listar_documentos(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("documentos", "leitura")),
    q: Optional[str] = None,
    tipo: Optional[TipoDocumentoEmpresa] = None,
    status_filtro: Optional[StatusDocumentoEmpresa] = None,
    incluir_arquivados: bool = True,
):
    """Lista documentos da empresa com filtros opcionais."""
    query = db.query(DocumentoEmpresa).filter(
        DocumentoEmpresa.empresa_id == usuario.empresa_id,
        DocumentoEmpresa.deletado_em.is_(None),
    )
    if q:
        query = query.filter(DocumentoEmpresa.nome.ilike(f"%{q.strip()}%"))
    if tipo:
        query = query.filter(DocumentoEmpresa.tipo == tipo)
    if status_filtro:
        query = query.filter(DocumentoEmpresa.status == status_filtro)
    if not incluir_arquivados:
        query = query.filter(
            DocumentoEmpresa.status != StatusDocumentoEmpresa.ARQUIVADO
        )
    return query.order_by(
        DocumentoEmpresa.atualizado_em.desc(), DocumentoEmpresa.criado_em.desc()
    ).all()


@router.post(
    "/", response_model=DocumentoEmpresaOut, status_code=status.HTTP_201_CREATED
)
def criar_documento(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("documentos", "escrita")),
    nome: str = Form(...),
    tipo: TipoDocumentoEmpresa = Form(TipoDocumentoEmpresa.OUTRO),
    descricao: Optional[str] = Form(None),
    versao: Optional[str] = Form(None),
    status_doc: StatusDocumentoEmpresa = Form(StatusDocumentoEmpresa.ATIVO),
    permite_download: bool = Form(True),
    visivel_no_portal: bool = Form(True),
    slug: Optional[str] = Form(None),
    tipo_conteudo: TipoConteudoDocumento = Form(TipoConteudoDocumento.PDF),
    conteudo_html: Optional[str] = Form(None),
    variaveis_suportadas: Optional[str] = Form(None),
    arquivo: Optional[UploadFile] = File(None),
):
    """Cria um novo documento (PDF ou HTML) para a empresa."""
    # Validação baseada no tipo de conteúdo
    if tipo_conteudo == TipoConteudoDocumento.PDF:
        if not arquivo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo é obrigatório para documentos do tipo PDF",
            )
        meta = salvar_upload_documento(usuario.empresa_id, arquivo)
        arquivo_path = meta["arquivo_path"]
        arquivo_nome_original = meta.get("arquivo_nome_original")
        mime_type = meta.get("mime_type")
        tamanho_bytes = meta.get("tamanho_bytes")
    else:  # HTML
        if not conteudo_html:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conteúdo HTML é obrigatório para documentos do tipo HTML",
            )
        # Para documentos HTML, não há arquivo físico
        arquivo_path = None
        arquivo_nome_original = None
        mime_type = "text/html"
        tamanho_bytes = len(conteudo_html.encode("utf-8"))

    # Processar variáveis suportadas (string JSON para lista)
    variaveis_lista = None
    if variaveis_suportadas:
        try:
            import json

            variaveis_lista = json.loads(variaveis_suportadas)
            if not isinstance(variaveis_lista, list):
                raise ValueError("variaveis_suportadas deve ser uma lista JSON")
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato inválido para variáveis suportadas: {str(e)}",
            )

    slug_final = (slug or "").strip() or gerar_slug_documento(nome)
    existente = (
        db.query(DocumentoEmpresa)
        .filter(
            DocumentoEmpresa.empresa_id == usuario.empresa_id,
            DocumentoEmpresa.slug == slug_final,
            DocumentoEmpresa.deletado_em.is_(None),
        )
        .first()
    )
    if existente:
        slug_final = (
            f"{slug_final}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )

    doc = DocumentoEmpresa(
        empresa_id=usuario.empresa_id,
        criado_por_id=usuario.id,
        nome=nome.strip(),
        slug=slug_final,
        tipo=tipo,
        descricao=(descricao or None),
        versao=(versao or None),
        status=status_doc,
        permite_download=bool(permite_download),
        visivel_no_portal=bool(visivel_no_portal),
        tipo_conteudo=tipo_conteudo,
        conteudo_html=conteudo_html,
        variaveis_suportadas=variaveis_lista,
        arquivo_path=arquivo_path,
        arquivo_nome_original=arquivo_nome_original,
        mime_type=mime_type,
        tamanho_bytes=tamanho_bytes,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{documento_id}", response_model=DocumentoEmpresaOut)
def buscar_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("documentos", "leitura")),
):
    """Busca um documento pelo ID."""
    doc = (
        db.query(DocumentoEmpresa)
        .filter(
            DocumentoEmpresa.id == documento_id,
            DocumentoEmpresa.empresa_id == usuario.empresa_id,
            DocumentoEmpresa.deletado_em.is_(None),
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return doc


@router.put("/{documento_id}", response_model=DocumentoEmpresaOut)
def atualizar_documento(
    documento_id: int,
    dados: DocumentoEmpresaUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("documentos", "escrita")),
):
    """Atualiza os dados de um documento existente."""
    doc = (
        db.query(DocumentoEmpresa)
        .filter(
            DocumentoEmpresa.id == documento_id,
            DocumentoEmpresa.empresa_id == usuario.empresa_id,
            DocumentoEmpresa.deletado_em.is_(None),
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(doc, campo, valor)

    if doc.slug:
        existente = (
            db.query(DocumentoEmpresa)
            .filter(
                DocumentoEmpresa.empresa_id == usuario.empresa_id,
                DocumentoEmpresa.slug == doc.slug,
                DocumentoEmpresa.id != doc.id,
                DocumentoEmpresa.deletado_em.is_(None),
            )
            .first()
        )
        if existente:
            raise HTTPException(status_code=400, detail="Slug já está em uso")

    db.commit()
    db.refresh(doc)
    return doc


@router.put("/{documento_id}/arquivo", response_model=DocumentoEmpresaOut)
def trocar_arquivo_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("documentos", "escrita")),
    arquivo: UploadFile = File(...),
):
    """Substitui o arquivo PDF de um documento existente."""
    doc = (
        db.query(DocumentoEmpresa)
        .filter(
            DocumentoEmpresa.id == documento_id,
            DocumentoEmpresa.empresa_id == usuario.empresa_id,
            DocumentoEmpresa.deletado_em.is_(None),
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    # Verificar se o documento é do tipo PDF (apenas PDFs têm arquivo para trocar)
    if doc.tipo_conteudo == TipoConteudoDocumento.HTML:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Documentos HTML não possuem arquivo físico para trocar. Use a atualização do conteúdo HTML.",
        )

    meta = salvar_upload_documento(usuario.empresa_id, arquivo)
    doc.arquivo_path = meta["arquivo_path"]
    doc.arquivo_nome_original = meta.get("arquivo_nome_original")
    doc.mime_type = meta.get("mime_type")
    doc.tamanho_bytes = meta.get("tamanho_bytes")
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{documento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("documentos", "admin")),
):
    """Exclui (soft-delete) um documento da empresa."""
    doc = (
        db.query(DocumentoEmpresa)
        .filter(
            DocumentoEmpresa.id == documento_id,
            DocumentoEmpresa.empresa_id == usuario.empresa_id,
            DocumentoEmpresa.deletado_em.is_(None),
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    doc.deletado_em = datetime.now(timezone.utc)
    doc.status = StatusDocumentoEmpresa.ARQUIVADO
    db.commit()
    return None


@router.get("/{documento_id}/arquivo")
def baixar_arquivo_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("documentos", "leitura")),
    download: bool = False,
):
    """Baixa ou visualiza o arquivo de um documento."""
    doc = (
        db.query(DocumentoEmpresa)
        .filter(
            DocumentoEmpresa.id == documento_id,
            DocumentoEmpresa.empresa_id == usuario.empresa_id,
            DocumentoEmpresa.deletado_em.is_(None),
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    if download and not doc.permite_download:
        raise HTTPException(
            status_code=403, detail="Download não permitido para este documento"
        )

    # Tratamento diferente para documentos HTML vs PDF
    if doc.tipo_conteudo == TipoConteudoDocumento.HTML:
        # Para documentos HTML, retornamos o conteúdo HTML diretamente
        if not doc.conteudo_html:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conteúdo HTML não encontrado para este documento",
            )

        # Gerar nome do arquivo para download
        filename = montar_nome_download(doc.nome, doc.versao, ext=".html")
        dispo = "attachment" if download else "inline"

        # Retornar o conteúdo HTML como resposta
        from fastapi.responses import Response

        return Response(
            content=doc.conteudo_html,
            media_type="text/html",
            headers={"Content-Disposition": f'{dispo}; filename="{filename}"'},
        )
    else:
        # Documento PDF - comportamento original
        arquivo_path_ou_url = resolver_arquivo_path(doc.arquivo_path)

        # Se é URL do R2, redireciona diretamente
        if arquivo_path_ou_url.startswith("http://") or arquivo_path_ou_url.startswith(
            "https://"
        ):
            return RedirectResponse(url=arquivo_path_ou_url, status_code=302)

        # Fallback: arquivo local legado
        filename = montar_nome_download(doc.nome, doc.versao, ext=".pdf")
        dispo = "attachment" if download else "inline"
        return FileResponse(
            arquivo_path_ou_url,
            media_type=doc.mime_type or "application/pdf",
            filename=filename,
            headers={"Content-Disposition": f'{dispo}; filename="{filename}"'},
        )
