"""
Utilitários para documentação automática OpenAPI.
Melhora a documentação gerada automaticamente a partir dos schemas Pydantic.
"""
from typing import Dict, Any, List, Optional, Type
from fastapi import FastAPI
from pydantic import BaseModel
import inspect


def enhance_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """
    Melhora o schema OpenAPI gerado automaticamente.
    
    Args:
        app: Aplicação FastAPI
        
    Returns:
        Schema OpenAPI melhorado
    """
    openapi_schema = app.openapi()
    
    # Adiciona informações de contato
    openapi_schema["info"]["contact"] = {
        "name": "Suporte COTTE",
        "email": "suporte@cotte.app",
        "url": "https://cotte.app"
    }
    
    # Adiciona tags para organização
    if "tags" not in openapi_schema:
        openapi_schema["tags"] = []
    
    # Tags padrão
    default_tags = [
        {"name": "Orçamentos", "description": "Operações com orçamentos"},
        {"name": "Clientes", "description": "Gestão de clientes"},
        {"name": "Catálogo", "description": "Serviços e produtos do catálogo"},
        {"name": "Empresa", "description": "Configurações da empresa"},
        {"name": "Autenticação", "description": "Login e gestão de usuários"},
        {"name": "WhatsApp", "description": "Integração com WhatsApp"},
        {"name": "Financeiro", "description": "Gestão financeira"},
        {"name": "Comercial", "description": "CRM e gestão comercial"},
        {"name": "Documentos", "description": "Gestão de documentos"},
        {"name": "Health", "description": "Verificação de saúde da API"},
    ]
    
    # Adiciona tags que não existem
    existing_tags = {tag["name"] for tag in openapi_schema.get("tags", [])}
    for tag in default_tags:
        if tag["name"] not in existing_tags:
            openapi_schema["tags"].append(tag)
    
    # Melhora descrições de schemas
    enhance_schemas_descriptions(openapi_schema)
    
    # Adiciona exemplos para schemas comuns
    add_examples_to_schemas(openapi_schema)
    
    # Adiciona respostas de erro padrão
    add_error_responses(openapi_schema)
    
    return openapi_schema


def enhance_schemas_descriptions(openapi_schema: Dict[str, Any]):
    """
    Melhora as descrições dos schemas no OpenAPI.
    
    Args:
        openapi_schema: Schema OpenAPI
    """
    schemas = openapi_schema.get("components", {}).get("schemas", {})
    
    # Descrições para schemas comuns
    schema_descriptions = {
        "OrcamentoCreate": "Dados para criação de um novo orçamento",
        "OrcamentoUpdate": "Dados para atualização de um orçamento existente",
        "OrcamentoOut": "Representação completa de um orçamento",
        "ClienteCreate": "Dados para criação de um novo cliente",
        "ClienteUpdate": "Dados para atualização de um cliente existente",
        "ClienteOut": "Representação completa de um cliente",
        "ServicoCreate": "Dados para criação de um novo serviço no catálogo",
        "ServicoUpdate": "Dados para atualização de um serviço existente",
        "ServicoOut": "Representação completa de um serviço",
        "UsuarioCreate": "Dados para criação de um novo usuário",
        "UsuarioOut": "Representação completa de um usuário",
        "EmpresaUpdate": "Dados para atualização de uma empresa",
        "EmpresaOut": "Representação completa de uma empresa",
    }
    
    for schema_name, description in schema_descriptions.items():
        if schema_name in schemas:
            if "description" not in schemas[schema_name] or not schemas[schema_name]["description"]:
                schemas[schema_name]["description"] = description


def add_examples_to_schemas(openapi_schema: Dict[str, Any]):
    """
    Adiciona exemplos para schemas comuns.
    
    Args:
        openapi_schema: Schema OpenAPI
    """
    schemas = openapi_schema.get("components", {}).get("schemas", {})
    
    # Exemplo para OrcamentoCreate
    if "OrcamentoCreate" in schemas:
        schemas["OrcamentoCreate"]["example"] = {
            "cliente_id": 1,
            "validade_dias": 7,
            "observacoes": "Orçamento para reforma do banheiro",
            "itens": [
                {
                    "servico_id": 1,
                    "quantidade": 1,
                    "valor_unitario": 1500.00,
                    "desconto_percent": 10
                }
            ]
        }
    
    # Exemplo para ClienteCreate
    if "ClienteCreate" in schemas:
        schemas["ClienteCreate"]["example"] = {
            "nome": "João Silva",
            "telefone": "+5511999999999",
            "email": "joao@email.com",
            "cep": "01234-567",
            "logradouro": "Rua das Flores",
            "numero": "123",
            "bairro": "Centro",
            "cidade": "São Paulo",
            "estado": "SP"
        }
    
    # Exemplo para ServicoCreate
    if "ServicoCreate" in schemas:
        schemas["ServicoCreate"]["example"] = {
            "nome": "Instalação de piso",
            "descricao": "Instalação de piso porcelanato",
            "preco_padrao": 1200.00,
            "unidade": "m²"
        }


def add_error_responses(openapi_schema: Dict[str, Any]):
    """
    Adiciona respostas de erro padrão aos paths.
    
    Args:
        openapi_schema: Schema OpenAPI
    """
    paths = openapi_schema.get("paths", {})
    
    error_responses = {
        "400": {
            "description": "Requisição inválida - Erro de validação",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "object",
                                "properties": {
                                    "code": {"type": "string", "example": "VALIDATION_ERROR"},
                                    "message": {"type": "string", "example": "Campo 'email' é obrigatório"},
                                    "details": {"type": "object", "example": {"field": "email"}}
                                }
                            }
                        }
                    }
                }
            }
        },
        "401": {
            "description": "Não autorizado - Token inválido ou ausente",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "object",
                                "properties": {
                                    "code": {"type": "string", "example": "UNAUTHORIZED"},
                                    "message": {"type": "string", "example": "Acesso não autorizado"},
                                    "details": {"type": "object", "example": {}}
                                }
                            }
                        }
                    }
                }
            }
        },
        "403": {
            "description": "Acesso proibido - Permissões insuficientes",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "object",
                                "properties": {
                                    "code": {"type": "string", "example": "FORBIDDEN"},
                                    "message": {"type": "string", "example": "Acesso proibido"},
                                    "details": {"type": "object", "example": {}}
                                }
                            }
                        }
                    }
                }
            }
        },
        "404": {
            "description": "Recurso não encontrado",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "object",
                                "properties": {
                                    "code": {"type": "string", "example": "NOT_FOUND"},
                                    "message": {"type": "string", "example": "Recurso não encontrado"},
                                    "details": {"type": "object", "example": {"resource": "Orcamento", "identifier": 123}}
                                }
                            }
                        }
                    }
                }
            }
        },
        "409": {
            "description": "Conflito - Recurso já existe",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "object",
                                "properties": {
                                    "code": {"type": "string", "example": "CONFLICT"},
                                    "message": {"type": "string", "example": "Recurso já existe"},
                                    "details": {"type": "object", "example": {"resource": "Cliente"}}
                                }
                            }
                        }
                    }
                }
            }
        },
        "422": {
            "description": "Entidade não processável - Erro de regra de negócio",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "object",
                                "properties": {
                                    "code": {"type": "string", "example": "BUSINESS_RULE_VIOLATION"},
                                    "message": {"type": "string", "example": "Limite de orçamentos excedido"},
                                    "details": {"type": "object", "example": {"rule": "LIMITE_ORCAMENTOS"}}
                                }
                            }
                        }
                    }
                }
            }
        },
        "429": {
            "description": "Muitas requisições - Limite de rate atingido",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "object",
                                "properties": {
                                    "code": {"type": "string", "example": "RATE_LIMIT_EXCEEDED"},
                                    "message": {"type": "string", "example": "Limite de requisições excedido"},
                                    "details": {"type": "object", "example": {}}
                                }
                            }
                        }
                    }
                }
            }
        },
        "500": {
            "description": "Erro interno do servidor",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "object",
                                "properties": {
                                    "code": {"type": "string", "example": "INTERNAL_SERVER_ERROR"},
                                    "message": {"type": "string", "example": "Erro interno do servidor"},
                                    "details": {"type": "object", "example": {}}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    # Adiciona respostas de erro a todos os endpoints
    for path, methods in paths.items():
        for method, details in methods.items():
            if "responses" not in details:
                details["responses"] = {}
            
            # Adiciona respostas de erro que não existem
            for status_code, response in error_responses.items():
                if status_code not in details["responses"]:
                    details["responses"][status_code] = response


def generate_model_documentation(model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Gera documentação detalhada para um modelo Pydantic.
    
    Args:
        model: Modelo Pydantic
        
    Returns:
        Dicionário com documentação do modelo
    """
    schema = model.schema()
    
    # Extrai informações dos campos
    fields_docs = []
    for field_name, field_info in schema.get("properties", {}).items():
        field_doc = {
            "name": field_name,
            "type": field_info.get("type", "string"),
            "required": field_name in schema.get("required", []),
            "description": field_info.get("description", ""),
            "example": field_info.get("example")
        }
        
        # Adiciona enum values se existir
        if "enum" in field_info:
            field_doc["enum"] = field_info["enum"]
        
        fields_docs.append(field_doc)
    
    return {
        "name": model.__name__,
        "description": schema.get("description", ""),
        "fields": fields_docs,
        "example": get_model_example(model)
    }


def get_model_example(model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Gera um exemplo para um modelo Pydantic.
    
    Args:
        model: Modelo Pydantic
        
    Returns:
        Exemplo do modelo
    """
    # Tenta usar Config.schema_extra se existir
    if hasattr(model.Config, "schema_extra"):
        example = model.Config.schema_extra.get("example", {})
        if example:
            return example
    
    # Gera exemplo básico baseado nos tipos
    example = {}
    schema = model.schema()
    
    for field_name, field_info in schema.get("properties", {}).items():
        field_type = field_info.get("type")
        
        if field_type == "string":
            if "enum" in field_info:
                example[field_name] = field_info["enum"][0] if field_info["enum"] else ""
            elif field_name == "email":
                example[field_name] = "usuario@exemplo.com"
            elif field_name == "telefone":
                example[field_name] = "+5511999999999"
            elif field_name == "nome":
                example[field_name] = "João Silva"
            else:
                example[field_name] = f"Exemplo {field_name}"
        
        elif field_type == "integer":
            example[field_name] = 1
        
        elif field_type == "number":
            example[field_name] = 100.50
        
        elif field_type == "boolean":
            example[field_name] = True
        
        elif field_type == "array":
            example[field_name] = []
    
    return example


def create_api_documentation(app: FastAPI) -> Dict[str, Any]:
    """
    Cria documentação completa da API.
    
    Args:
        app: Aplicação FastAPI
        
    Returns:
        Documentação completa da API
    """
    # Obtém schema OpenAPI melhorado
    openapi_schema = enhance_openapi_schema(app)
    
    # Extrai informações dos endpoints
    endpoints = []
    for path, methods in openapi_schema.get("paths", {}).items():
        for method, details in methods.items():
            endpoint = {
                "path": path,
                "method": method.upper(),
                "summary": details.get("summary", ""),
                "description": details.get("description", ""),
                "tags": details.get("tags", []),
                "parameters": details.get("parameters", []),
                "responses": list(details.get("responses", {}).keys())
            }
            endpoints.append(endpoint)
    
    # Extrai informações dos schemas
    schemas_info = []
    for schema_name, schema_details in openapi_schema.get("components", {}).get("schemas", {}).items():
        schema_info = {
            "name": schema_name,
            "description": schema_details.get("description", ""),
            "properties": list(schema_details.get("properties", {}).keys())
        }
        schemas_info.append(schema_info)
    
    return {
        "info": openapi_schema.get("info", {}),
        "version": openapi_schema.get("openapi", ""),
        "endpoints_count": len(endpoints),
        "schemas_count": len(schemas_info),
        "tags": openapi_schema.get("tags", []),
        "endpoints": endpoints[:10],  # Limita para não ficar muito grande
        "schemas": schemas_info[:10]   # Limita para não ficar muito grande
    }