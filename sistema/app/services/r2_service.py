import boto3
import uuid
import logging
from typing import BinaryIO, Optional
from botocore.exceptions import ClientError
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


class R2Service:
    """Serviço para gerenciar uploads no Cloudflare R2 (compatível S3)."""

    def __init__(self):
        if not all(
            [
                settings.R2_ACCOUNT_ID,
                settings.R2_ACCESS_KEY_ID,
                settings.R2_SECRET_ACCESS_KEY,
                settings.R2_BUCKET_NAME,
            ]
        ):
            logger.warning("R2 não configurado. Uploads serão desabilitados.")
            self.client = None
            self.bucket_name = None
            self.public_url = None
            return

        endpoint_url = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
        self.bucket_name = settings.R2_BUCKET_NAME
        self.public_url = (
            settings.R2_PUBLIC_URL.rstrip("/") if settings.R2_PUBLIC_URL else None
        )

    def _check_configured(self):
        if not self.client:
            raise HTTPException(
                status_code=503,
                detail="Armazenamento de arquivos não configurado. Contate o administrador.",
            )

    def upload_file(
        self,
        file_obj: BinaryIO,
        empresa_id: int,
        tipo: str,
        extensao: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Faz upload de um arquivo para o R2.

        Args:
            file_obj: Objeto de arquivo binário
            empresa_id: ID da empresa (para organização)
            tipo: Tipo do arquivo (catalogo, logos, documentos)
            extensao: Extensão do arquivo (com ponto, ex: .jpg)
            content_type: MIME type do arquivo

        Returns:
            URL pública do arquivo
        """
        self._check_configured()

        filename = f"{uuid.uuid4().hex}{extensao}"
        key = f"empresas/{empresa_id}/{tipo}/{filename}"

        try:
            logger.info(
                "Tentando upload para R2: bucket=%s, key=%s", self.bucket_name, key
            )
            self.client.upload_fileobj(
                file_obj,
                self.bucket_name,
                key,
                ExtraArgs={
                    "ContentType": content_type,
                    "CacheControl": "public, max-age=31536000",
                },
            )

            if self.public_url:
                url = f"{self.public_url}/{key}"
            else:
                url = f"https://{self.bucket_name}.r2.dev/{key}"

            logger.info("Upload concluído com sucesso: %s", url)
            return url

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))

            logger.error(
                "Erro ao fazer upload para R2 - Code: %s, Message: %s, Bucket: %s, Key: %s",
                error_code,
                error_msg,
                self.bucket_name,
                key,
            )

            if error_code == "AccessDenied":
                raise HTTPException(
                    status_code=500,
                    detail="Erro de permissão no R2. Verifique as credenciais e permissões do API Token.",
                )
            elif error_code == "NoSuchBucket":
                raise HTTPException(
                    status_code=500,
                    detail=f"Bucket '{self.bucket_name}' não encontrado no R2.",
                )
            else:
                raise HTTPException(
                    status_code=500, detail=f"Falha ao fazer upload: {error_msg}"
                )

    def delete_file(self, file_url: str) -> bool:
        """
        Deleta um arquivo do R2 a partir da URL pública.

        Args:
            file_url: URL pública do arquivo

        Returns:
            True se deletado com sucesso, False caso contrário
        """
        self._check_configured()

        try:
            if self.public_url and file_url.startswith(self.public_url):
                key = file_url.replace(f"{self.public_url}/", "")
            elif f"{self.bucket_name}.r2.dev" in file_url:
                key = file_url.split(f"{self.bucket_name}.r2.dev/", 1)[1]
            else:
                logger.warning("URL não reconhecida para deleção: %s", file_url)
                return False

            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info("Arquivo deletado do R2: %s", key)
            return True

        except ClientError as e:
            logger.exception("Erro ao deletar arquivo do R2: %s", e)
            return False

    def get_public_url(self, key: str) -> str:
        """
        Retorna a URL pública de um arquivo.

        Args:
            key: Chave do arquivo no R2 (ex: empresas/1/logos/abc.png)

        Returns:
            URL pública do arquivo
        """
        if self.public_url:
            return f"{self.public_url}/{key}"
        else:
            return f"https://{self.bucket_name}.r2.dev/{key}"

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Gera URL temporária (presigned) para acesso a arquivo privado.

        Args:
            key: Chave do arquivo no R2
            expires_in: Tempo de validade em segundos (padrão 1 hora)

        Returns:
            URL temporária signed
        """
        if not self.client:
            raise HTTPException(
                status_code=503, detail="Armazenamento não configurado."
            )

        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            logger.error("Erro ao gerar presigned URL: %s", e)
            raise HTTPException(status_code=500, detail="Erro ao gerar URL temporária")


r2_service = R2Service()
