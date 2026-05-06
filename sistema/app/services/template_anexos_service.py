import os
import uuid
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile

from app.services.r2_service import r2_service

UPLOADS_DIR = "uploads"
MAX_TEMPLATE_ANEXO_BYTES = 15 * 1024 * 1024
MIME_PERMITIDOS = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
}
EXTENSOES_PERMITIDAS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
MIME_POR_EXTENSAO = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

def _r2_esta_disponivel() -> bool:
    return bool(r2_service.client)


def validar_template_anexo_path(path: str, empresa_id: int) -> str:
    path_normalizado = (path or "").strip()

    if not _r2_esta_disponivel():
        if path_normalizado.startswith(UPLOADS_DIR):
            return path_normalizado
        prefixo_local = f"{UPLOADS_DIR}/empresas/{empresa_id}/templates-anexos/"
        if prefixo_local not in path_normalizado:
            raise HTTPException(status_code=400, detail="Anexo inválido para este tenant")
        return path_normalizado

    prefixo = f"empresas/{empresa_id}/templates-anexos/"
    parsed = urlparse(path_normalizado)
    host_r2_padrao = f"{r2_service.bucket_name}.r2.dev" if r2_service.bucket_name else None

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Anexo inválido para este tenant")
    if prefixo not in parsed.path.lstrip("/"):
        raise HTTPException(status_code=400, detail="Anexo inválido para este tenant")
    if not r2_service.public_url and not host_r2_padrao:
        raise HTTPException(status_code=400, detail="Anexo inválido para este tenant")
    if r2_service.public_url and not path_normalizado.startswith(f"{r2_service.public_url}/{prefixo}"):
        raise HTTPException(status_code=400, detail="Anexo inválido para este tenant")
    if not r2_service.public_url and host_r2_padrao and parsed.netloc != host_r2_padrao:
        raise HTTPException(status_code=400, detail="Anexo inválido para este tenant")

    return path_normalizado


def _extensao_do_nome(nome: str) -> str:
    _, ext = os.path.splitext(nome or "")
    return (ext or "").lower()


def _resolver_mime(content_type: str, extensao: str) -> str:
    mime = (content_type or "").strip().lower()
    if mime:
        return mime
    return MIME_POR_EXTENSAO.get(extensao, "application/octet-stream")


def _salvar_local(empresa_id: int, ext: str, file: UploadFile) -> str:
    filename = f"{uuid.uuid4().hex}{ext}"
    base = os.path.join(UPLOADS_DIR, "empresas", str(empresa_id), "templates-anexos")
    os.makedirs(base, exist_ok=True)
    caminho = os.path.join(base, filename)
    with open(caminho, "wb") as f:
        f.write(file.file.read())
    return caminho


def salvar_upload_template_anexo(empresa_id: int, file: UploadFile) -> dict:
    original = (file.filename or "").strip()
    if not original:
        raise HTTPException(status_code=400, detail="Arquivo inválido")

    ext = _extensao_do_nome(original)
    if ext not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail="Formato não permitido. Envie PDF ou imagem compatível.",
        )

    mime = _resolver_mime(file.content_type, ext)
    if mime not in MIME_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail="Tipo de arquivo não permitido. Envie PDF ou imagem compatível.",
        )

    file.file.seek(0, 2)
    tamanho = file.file.tell()
    file.file.seek(0)

    if tamanho == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    if tamanho > MAX_TEMPLATE_ANEXO_BYTES:
        raise HTTPException(status_code=400, detail="Arquivo muito grande")

    if _r2_esta_disponivel():
        file_url = r2_service.upload_file(
            file_obj=file.file,
            empresa_id=empresa_id,
            tipo="templates-anexos",
            extensao=ext,
            content_type=mime,
        )
    else:
        file_url = _salvar_local(empresa_id, ext, file)

    return {
        "arquivo_path": file_url,
        "arquivo_nome_original": original,
        "mime_type": mime,
        "tamanho_bytes": int(tamanho),
    }
