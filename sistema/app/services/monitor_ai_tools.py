import os
import logging
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool
from sqlalchemy import create_engine, inspect
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_openai import ChatOpenAI
from app.services.code_rag_service import build_code_context

logger = logging.getLogger(__name__)

# Configuração do banco para o SQL Toolkit
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///test_cotte.db")

# Cria a engine e a conexão SQL Database para o Langchain (Read-Only seria ideal, mas SQLDatabase do Langchain já restringe um pouco)
db_engine = create_engine(DATABASE_URL)
db = SQLDatabase(db_engine, lazy_table_reflection=True)


def get_sql_toolkit(llm: ChatOpenAI) -> SQLDatabaseToolkit:
    """Retorna o toolkit SQL configurado com o LLM."""
    return SQLDatabaseToolkit(db=db, llm=llm)


@tool
def log_reader_tool(linhas: int = 50, nivel: str = "ERROR") -> str:
    """
    Lê os arquivos de log do sistema para análise.
    Útil para diagnosticar problemas e verificar mensagens de erro ou avisos.

    Args:
        linhas: Número de linhas para ler do final do log. (padrão: 50)
        nivel: Filtra por nível de log (ex: ERROR, WARNING, INFO). (padrão: ERROR)
    """
    log_file_path = os.getenv("LOG_FILE_PATH", "debug_output.txt")
    if not os.path.exists(log_file_path):
        return f"Arquivo de log {log_file_path} não encontrado."

    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Filtra pelo nível, se não for None
        if nivel:
            lines = [line for line in lines if nivel in line]

        # Pega as últimas N linhas
        recent_lines = lines[-linhas:]
        if not recent_lines:
            return "Nenhuma linha encontrada para este filtro."

        return "".join(recent_lines)
    except Exception as e:
        return f"Erro ao ler log: {str(e)}"


@tool
def schema_inspector_tool(table_name: str) -> str:
    """
    Retorna colunas, tipos e relações de uma tabela requisitada usando SQLAlchemy Inspector.
    Útil para entender a estrutura do banco de dados antes de gerar queries.

    Args:
        table_name: Nome da tabela a ser inspecionada.
    """
    try:
        inspector = inspect(db_engine)
        if table_name not in inspector.get_table_names():
            return f"Tabela '{table_name}' não encontrada no banco de dados."

        columns = inspector.get_columns(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)

        output = [f"Schema para a tabela '{table_name}':", "Colunas:"]
        for col in columns:
            output.append(f"  - {col['name']} ({col['type']})")

        if foreign_keys:
            output.append("Chaves Estrangeiras:")
            for fk in foreign_keys:
                output.append(
                    f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}"
                )

        return "\n".join(output)
    except Exception as e:
        return f"Erro ao inspecionar schema: {str(e)}"


@tool
def code_rag_tool(query: str) -> str:
    """
    Pesquisa e recupera trechos de código do projeto com base em uma query.
    Útil para entender como uma funcionalidade está implementada no código-fonte.

    Args:
        query: Termos de pesquisa ou descrição do que procurar no código.
    """
    try:
        result = build_code_context(query=query, top_k=5)
        context = result.get("context", "")
        if not context:
            return "Nenhum trecho de código relevante encontrado para esta query."
        return context
    except Exception as e:
        return f"Erro ao pesquisar no código: {str(e)}"


# Retorna a lista de tools personalizadas (exceto as do SQL Toolkit, que são geradas dinamicamente)
def get_custom_tools() -> List[Any]:
    return [log_reader_tool, schema_inspector_tool, code_rag_tool]
