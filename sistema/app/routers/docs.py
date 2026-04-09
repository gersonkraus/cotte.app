"""
Router para documentação da API.
Fornece endpoints para acessar e explorar a documentação OpenAPI.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse, JSONResponse

from app.core.openapi_docs import create_api_documentation, generate_model_documentation
from app.schemas.schemas import (
    OrcamentoCreate,
    OrcamentoUpdate,
    OrcamentoOut,
    ClienteCreate,
    ClienteUpdate,
    ClienteOut,
    ServicoCreate,
    ServicoUpdate,
    ServicoOut,
)

router = APIRouter(prefix="/docs", tags=["Documentação"])


@router.get("/swagger", include_in_schema=False)
async def swagger_ui():
    """
    Interface Swagger UI personalizada.
    """
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="COTTE API - Documentação",
        swagger_favicon_url="/static/favicon.ico",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )


@router.get("/redoc", include_in_schema=False)
async def redoc_ui():
    """
    Interface ReDoc personalizada.
    """
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="COTTE API - Documentação",
        redoc_favicon_url="/static/favicon.ico",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )


@router.get("/api-info", response_model=Dict[str, Any])
async def get_api_info():
    """
    Obtém informações gerais sobre a API.

    Returns:
        Informações da API incluindo versão, endpoints disponíveis, etc.
    """
    from fastapi import FastAPI
    from app.main import app

    api_docs = create_api_documentation(app)

    return {
        "api": "COTTE API",
        "version": api_docs["version"],
        "description": "Sistema de geração de orçamentos via WhatsApp com IA",
        "endpoints_count": api_docs["endpoints_count"],
        "schemas_count": api_docs["schemas_count"],
        "tags": api_docs["tags"],
    }


@router.get("/models/{model_name}", response_model=Dict[str, Any])
async def get_model_documentation(model_name: str):
    """
    Obtém documentação detalhada de um modelo específico.

    Args:
        model_name: Nome do modelo (ex: OrcamentoCreate, ClienteOut)

    Returns:
        Documentação do modelo com campos, exemplos, etc.
    """
    # Mapeamento de nomes de modelos para classes
    model_classes = {
        "OrcamentoCreate": OrcamentoCreate,
        "OrcamentoUpdate": OrcamentoUpdate,
        "OrcamentoOut": OrcamentoOut,
        "ClienteCreate": ClienteCreate,
        "ClienteUpdate": ClienteUpdate,
        "ClienteOut": ClienteOut,
        "ServicoCreate": ServicoCreate,
        "ServicoUpdate": ServicoUpdate,
        "ServicoOut": ServicoOut,
    }

    if model_name not in model_classes:
        return JSONResponse(
            status_code=404, content={"error": f"Modelo '{model_name}' não encontrado"}
        )

    model_class = model_classes[model_name]
    documentation = generate_model_documentation(model_class)

    return documentation


@router.get("/endpoints", response_model=Dict[str, Any])
async def list_endpoints():
    """
    Lista todos os endpoints disponíveis na API.

    Returns:
        Lista de endpoints agrupados por tag
    """
    from fastapi import FastAPI
    from app.main import app

    openapi_schema = app.openapi()
    endpoints_by_tag = {}

    for path, methods in openapi_schema.get("paths", {}).items():
        for method, details in methods.items():
            tags = details.get("tags", ["default"])

            for tag in tags:
                if tag not in endpoints_by_tag:
                    endpoints_by_tag[tag] = []

                endpoint_info = {
                    "path": path,
                    "method": method.upper(),
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "operation_id": details.get("operationId", ""),
                }

                endpoints_by_tag[tag].append(endpoint_info)

    return {
        "endpoints_by_tag": endpoints_by_tag,
        "total_endpoints": sum(
            len(endpoints) for endpoints in endpoints_by_tag.values()
        ),
    }


@router.get("/search")
async def search_endpoints(q: str = ""):
    """
    Busca endpoints por nome, path, descrição ou tag.

    Args:
        q: Termo de busca (ex: orcamento, cliente, PIX)

    Returns:
        Lista de endpoints que correspondem ao termo de busca
    """
    if not q or len(q.strip()) < 2:
        return JSONResponse(
            status_code=400,
            content={"detail": "Parâmetro 'q' deve ter pelo menos 2 caracteres"},
        )

    from app.main import app

    termo = q.strip().lower()
    openapi_schema = app.openapi()
    resultados = []

    for path, methods in openapi_schema.get("paths", {}).items():
        for method, details in methods.items():
            tags = details.get("tags", [])
            summary = details.get("summary", "")
            description = details.get("description", "")
            operation_id = details.get("operationId", "")

            texto_busca = " ".join(
                [
                    path,
                    summary,
                    description,
                    operation_id,
                    " ".join(tags),
                ]
            ).lower()

            if termo in texto_busca:
                resultados.append(
                    {
                        "path": path,
                        "method": method.upper(),
                        "summary": summary,
                        "description": description,
                        "tags": tags,
                        "operation_id": operation_id,
                    }
                )

    return {
        "query": q,
        "total": len(resultados),
        "results": resultados,
    }


@router.get("/health-check", include_in_schema=False)
async def health_check_detailed():
    """
    Verificação de saúde detalhada da API.

    Returns:
        Status de saúde com informações do sistema
    """
    import psutil
    import platform
    from datetime import datetime

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "api": "COTTE API",
        "version": "1.0.0",
        "system": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent,
        },
    }


@router.get("/examples/{resource}", response_model=Dict[str, Any])
async def get_resource_examples(resource: str):
    """
    Obtém exemplos de uso para um recurso específico.

    Args:
        resource: Nome do recurso (ex: orcamentos, clientes, servicos)

    Returns:
        Exemplos de requisições e respostas para o recurso
    """
    examples = {
        "orcamentos": {
            "create": {
                "description": "Criação de um novo orçamento",
                "request": {
                    "method": "POST",
                    "url": "/orcamentos/",
                    "body": {
                        "cliente_id": 1,
                        "validade_dias": 7,
                        "observacoes": "Orçamento para reforma completa",
                        "itens": [
                            {
                                "servico_id": 1,
                                "quantidade": 2,
                                "valor_unitario": 1500.00,
                                "desconto_percent": 10,
                            }
                        ],
                    },
                },
                "response": {
                    "status": 201,
                    "body": {
                        "id": 123,
                        "numero": "ORC-123-26",
                        "cliente_id": 1,
                        "status": "rascunho",
                        "valor_total": 2700.00,
                        "criado_em": "2026-03-17T12:00:00Z",
                    },
                },
            }
        },
        "clientes": {
            "create": {
                "description": "Criação de um novo cliente",
                "request": {
                    "method": "POST",
                    "url": "/clientes/",
                    "body": {
                        "nome": "Maria Santos",
                        "telefone": "+5511988888888",
                        "email": "maria@email.com",
                        "cep": "04567-890",
                        "logradouro": "Av. Paulista",
                        "numero": "1000",
                        "bairro": "Bela Vista",
                        "cidade": "São Paulo",
                        "estado": "SP",
                    },
                },
                "response": {
                    "status": 201,
                    "body": {
                        "id": 456,
                        "nome": "Maria Santos",
                        "telefone": "+5511988888888",
                        "email": "maria@email.com",
                        "empresa_id": 1,
                        "criado_em": "2026-03-17T12:00:00Z",
                    },
                },
            }
        },
        "servicos": {
            "create": {
                "description": "Criação de um novo serviço no catálogo",
                "request": {
                    "method": "POST",
                    "url": "/servicos/",
                    "body": {
                        "nome": "Instalação de ar condicionado",
                        "descricao": "Instalação completa de ar condicionado split",
                        "preco_padrao": 2500.00,
                        "unidade": "unidade",
                    },
                },
                "response": {
                    "status": 201,
                    "body": {
                        "id": 789,
                        "nome": "Instalação de ar condicionado",
                        "descricao": "Instalação completa de ar condicionado split",
                        "preco_padrao": 2500.00,
                        "unidade": "unidade",
                        "empresa_id": 1,
                        "ativo": True,
                    },
                },
            }
        },
    }

    if resource not in examples:
        return JSONResponse(
            status_code=404,
            content={"error": f"Exemplos para recurso '{resource}' não encontrados"},
        )

    return examples[resource]
