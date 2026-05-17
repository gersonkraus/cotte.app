"""Router para gestão da Base de Conhecimento (RAG) da empresa."""

from __future__ import annotations

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import delete

from app.core.database import get_db
from app.core.auth import get_usuario_atual as get_current_user
from app.models.models import Usuario, AIDocumentoConhecimento
from app.ai.rag.service import SemanticRAGService
from app.services.rag.chunking import chunk_text
from app.utils.text_extractor import extract_text_from_pdf, extract_text_from_txt

router = APIRouter(prefix="/ai/rag", tags=["AI Knowledge Base"])

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_knowledge_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Sobe um manual (PDF/TXT), extrai texto, divide em chunks e indexa no pgvector."""
    if not current_user.empresa_id:
        raise HTTPException(status_code=403, detail="Usuário sem empresa vinculada.")

    content = await file.read()
    filename = file.filename
    
    if filename.lower().endswith(".pdf"):
        text = extract_text_from_pdf(content)
    elif filename.lower().endswith(".txt"):
        text = extract_text_from_txt(content)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Formato de arquivo não suportado. Use .pdf ou .txt"
        )
    
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Não foi possível extrair texto do arquivo ou o arquivo está vazio."
        )
    
    # Chunking para evitar limites de tokens e melhorar a granularidade da busca
    chunks = chunk_text(text, chunk_size=1000, overlap=200)
    
    indexed_docs = []
    for i, chunk in enumerate(chunks):
        doc = await SemanticRAGService.index_document(
            db=db,
            empresa_id=current_user.empresa_id,
            conteudo=chunk,
            fonte=filename,
            metadata={
                "filename": filename, 
                "chunk_index": i, 
                "total_chunks": len(chunks),
                "upload_by": current_user.id
            }
        )
        indexed_docs.append(doc.id)
    
    return {
        "success": True, 
        "filename": filename, 
        "chunks_indexed": len(indexed_docs),
        "document_ids": indexed_docs
    }

@router.get("/documents")
async def listar_documentos_conhecimento(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Lista todos os documentos/chunks de conhecimento da empresa."""
    docs = db.query(AIDocumentoConhecimento).filter(
        AIDocumentoConhecimento.empresa_id == current_user.empresa_id
    ).order_by(AIDocumentoConhecimento.criado_em.desc()).all()
    
    return {
        "success": True,
        "total": len(docs),
        "documents": [
            {
                "id": d.id,
                "fonte": d.fonte,
                "conteudo_preview": d.conteudo[:100] + "...",
                "metadata": d.metadata_json,
                "criado_em": d.criado_em.isoformat()
            }
            for d in docs
        ]
    }

@router.delete("/documents/{doc_id}")
async def excluir_documento_conhecimento(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Exclui um chunk/documento específico da base de conhecimento."""
    doc = db.query(AIDocumentoConhecimento).filter(
        AIDocumentoConhecimento.id == doc_id,
        AIDocumentoConhecimento.empresa_id == current_user.empresa_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    
    db.delete(doc)
    db.commit()
    
    return {"success": True, "message": "Documento removido com sucesso."}

@router.delete("/documents/source/{filename}")
async def excluir_todos_por_fonte(
    filename: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Exclui todos os chunks associados a um arquivo (fonte) específico."""
    stmt = delete(AIDocumentoConhecimento).where(
        AIDocumentoConhecimento.empresa_id == current_user.empresa_id,
        AIDocumentoConhecimento.fonte == filename
    )
    result = db.execute(stmt)
    db.commit()
    
    return {"success": True, "removed_count": result.rowcount}
