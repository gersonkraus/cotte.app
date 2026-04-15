import subprocess
import os
from pydantic import BaseModel, Field
from typing import Any

from ._base import ToolSpec

class LerArquivoInput(BaseModel):
    path: str = Field(..., description="Caminho relativo ou absoluto do arquivo no repositório.")
    offset: int = Field(1, description="Linha inicial para leitura (1-indexed).")
    limit: int = Field(500, description="Número máximo de linhas para ler.")

async def handler_ler_arquivo_repositorio(input_data: LerArquivoInput, **kwargs: Any) -> dict[str, Any]:
    """Lê o conteúdo de um arquivo do repositório com suporte a paginação."""
    # Resolvendo o caminho base do projeto de forma dinâmica (4 níveis acima de ai_tools)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    file_path = os.path.abspath(os.path.join(base_dir, input_data.path))
    
    if not file_path.startswith(base_dir):
        return {"error": "Acesso negado: Path traversal detectado."}
        
    sensitive_extensions = ('.env', '.key', '.pem')
    if any(file_path.endswith(ext) or ext in os.path.basename(file_path) for ext in sensitive_extensions):
        return {"error": "Acesso negado: Leitura de arquivos sensíveis não permitida."}
    
    if not os.path.isfile(file_path):
        return {"error": f"Arquivo não encontrado: {file_path}"}
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        start_idx = max(0, input_data.offset - 1)
        end_idx = start_idx + input_data.limit
        
        content = "".join(lines[start_idx:end_idx])
        
        return {
            "path": input_data.path,
            "total_lines": len(lines),
            "offset": input_data.offset,
            "limit": input_data.limit,
            "content": content
        }
    except Exception as e:
        return {"error": f"Erro ao ler arquivo: {str(e)}"}

from html.parser import HTMLParser
from collections import Counter

class LinterHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.ids = []
        self.classes = []
        self.errors = []
        
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        for attr, value in attrs:
            if attr == 'id' and value:
                self.ids.append(value)
            if attr == 'class' and value:
                self.classes.extend(value.split())

    def check(self):
        id_counts = Counter(self.ids)
        dups = {k: v for k, v in id_counts.items() if v > 1}
        if dups:
            self.errors.append(f"IDs duplicados encontrados: {list(dups.keys())}")
        return {
            "tags_totais": len(self.tags),
            "ids_unicos": len(set(self.ids)),
            "ids_duplicados": list(dups.keys()),
            "erros": self.errors
        }

class AnalisarHtmlInput(BaseModel):
    path: str = Field(..., description="Caminho relativo ou absoluto do arquivo HTML no repositório.")

async def handler_analisar_estrutura_html(input_data: AnalisarHtmlInput, **kwargs: Any) -> dict[str, Any]:
    """Analisa a estrutura de um arquivo HTML buscando erros básicos como IDs duplicados."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    file_path = os.path.abspath(os.path.join(base_dir, input_data.path))
    
    if not file_path.startswith(base_dir) or not file_path.endswith('.html'):
        return {"error": "Acesso negado: Path inválido ou não é HTML."}
    
    if not os.path.isfile(file_path):
        return {"error": f"Arquivo HTML não encontrado: {file_path}"}
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        parser = LinterHTML()
        parser.feed(content)
        resultado = parser.check()
        resultado["path"] = input_data.path
        return resultado
    except Exception as e:
        return {"error": f"Erro ao analisar HTML: {str(e)}"}

analisar_estrutura_html = ToolSpec(
    name="analisar_estrutura_html",
    description="Analisa a estrutura DOM de um arquivo HTML, identificando tags e verificando IDs duplicados e possíveis erros.",
    input_model=AnalisarHtmlInput,
    handler=handler_analisar_estrutura_html,
    destrutiva=False,
    permissao_acao="leitura"
)
class BuscarCodigoInput(BaseModel):
    termo: str = Field(..., description="Termo de busca ou regex (grep-like).")
    path: str = Field(".", description="Diretório ou arquivo para buscar (relativo ao repositório).")

async def handler_buscar_codigo_repositorio(input_data: BuscarCodigoInput, **kwargs: Any) -> dict[str, Any]:
    """Busca um termo no repositório usando grep/rg."""
    # Resolvendo o caminho base do projeto de forma dinâmica
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    search_path = os.path.abspath(os.path.join(base_dir, input_data.path))
    
    if not search_path.startswith(base_dir):
        return {"error": "Acesso negado: Path traversal detectado."}
    
    if not os.path.exists(search_path):
        return {"error": f"Caminho não encontrado para busca: {search_path}"}
        
    try:
        # Tenta usar ripgrep se disponível, senão grep
        try:
            result = subprocess.run(
                ["rg", "-n", "--", input_data.termo, search_path],
                capture_output=True,
                text=True,
                timeout=10
            )
        except FileNotFoundError:
            result = subprocess.run(
                ["grep", "-rnE", "--", input_data.termo, search_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
        return {
            "termo": input_data.termo,
            "matches": result.stdout[:4000] + ("\n... truncado" if len(result.stdout) > 4000 else ""),
            "exit_code": result.returncode
        }
    except Exception as e:
        return {"error": f"Erro ao buscar código: {str(e)}"}

ler_arquivo_repositorio = ToolSpec(
    name="ler_arquivo_repositorio",
    description="Lê o conteúdo completo ou parcial de um arquivo no repositório.",
    input_model=LerArquivoInput,
    handler=handler_ler_arquivo_repositorio,
    destrutiva=False,
    permissao_acao="leitura"
)

buscar_codigo_repositorio = ToolSpec(
    name="buscar_codigo_repositorio",
    description="Busca um termo no código do repositório inteiro (equivalente a grep).",
    input_model=BuscarCodigoInput,
    handler=handler_buscar_codigo_repositorio,
    destrutiva=False,
    permissao_acao="leitura"
)
