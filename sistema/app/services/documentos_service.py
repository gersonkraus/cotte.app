import os
import re
import uuid
from typing import Optional
import logging

from fastapi import HTTPException, UploadFile
from app.services.r2_service import r2_service

logger = logging.getLogger(__name__)


UPLOADS_DIR = "uploads"
MAX_DOCUMENTO_BYTES = 15 * 1024 * 1024
MIME_PERMITIDOS = {"application/pdf"}
EXTENSOES_PERMITIDAS = {".pdf"}


def gerar_slug_documento(nome: str) -> str:
    s = (nome or "").strip().lower()
    s = re.sub(r"[^a-z0-9\\s-]", "", s)
    s = re.sub(r"\\s+", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    s = s.strip("-")
    return s or "documento"


def _extensao_do_nome(nome: str) -> str:
    _, ext = os.path.splitext(nome or "")
    return (ext or "").lower()


def _resolver_caminho_base_empresa(empresa_id: int) -> str:
    base = os.path.join(UPLOADS_DIR, "empresas", f"empresa_{empresa_id}", "documentos")
    os.makedirs(base, exist_ok=True)
    return base


def salvar_upload_documento(empresa_id: int, file: UploadFile) -> dict:
    original = (file.filename or "").strip()
    if not original:
        raise HTTPException(status_code=400, detail="Arquivo inválido")

    ext = _extensao_do_nome(original)
    if ext not in EXTENSOES_PERMITIDAS:
        raise HTTPException(status_code=400, detail="Formato não permitido. Envie PDF.")

    mime = (file.content_type or "").strip().lower()
    if mime and mime not in MIME_PERMITIDOS:
        raise HTTPException(status_code=400, detail="Tipo de arquivo não permitido. Envie PDF.")

    # Validar tamanho antes de fazer upload
    file.file.seek(0, 2)
    tamanho = file.file.tell()
    file.file.seek(0)
    
    if tamanho > MAX_DOCUMENTO_BYTES:
        raise HTTPException(status_code=400, detail="Arquivo muito grande")

    # Upload para R2
    file_url = r2_service.upload_file(
        file_obj=file.file,
        empresa_id=empresa_id,
        tipo="documentos",
        extensao=ext,
        content_type=mime or "application/pdf",
    )

    return {
        "arquivo_path": file_url,
        "arquivo_nome_original": original,
        "mime_type": mime or "application/pdf",
        "tamanho_bytes": int(tamanho),
    }


def resolver_arquivo_path(arquivo_path: str) -> str:
    """
    Retorna a URL do arquivo.
    Para arquivos no R2, retorna a URL diretamente.
    Para arquivos legados no filesystem, retorna o caminho absoluto.
    """
    if not arquivo_path:
        raise HTTPException(status_code=400, detail="Caminho de arquivo inválido")
    
    # Se já é uma URL (R2), retorna diretamente
    if arquivo_path.startswith("http://") or arquivo_path.startswith("https://"):
        return arquivo_path
    
    # Fallback para arquivos legados no filesystem local
    rel = arquivo_path.lstrip("/").replace("\\", "/")
    abs_path = os.path.abspath(rel)
    abs_root = os.path.abspath(UPLOADS_DIR)
    if not (abs_path == abs_root or abs_path.startswith(abs_root + os.sep)):
        raise HTTPException(status_code=400, detail="Caminho de arquivo inválido")
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return abs_path


def montar_nome_download(nome_base: str, versao: Optional[str], ext: str = ".pdf") -> str:
    base = (nome_base or "documento").strip()
    base = re.sub(r"[\\r\\n\\t]", " ", base)
    base = re.sub(r"\\s+", " ", base).strip()
    base = re.sub(r"[^A-Za-z0-9À-ÿ _.-]", "", base)
    base = base[:80].strip() or "documento"
    if versao:
        v = re.sub(r"[^A-Za-z0-9._-]", "", versao.strip())[:20]
        if v:
            base = f"{base}-v{v}"
    if not base.lower().endswith(ext):
        base = base + ext
    return base
