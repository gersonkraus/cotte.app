#!/usr/bin/env python3
"""Direct test of the categorias functionality"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.routers.financeiro import listar_categorias
from app.schemas.financeiro import TipoCategoria

print("Successfully imported listar_categorias function")
print(f"Function signature: {listar_categorias.__annotations__}")

# Test TipoCategoria enum
try:
    cat = TipoCategoria("despesa")
    print(f"TipoCategoria enum works: {cat}")
except Exception as e:
    print(f"TipoCategoria error: {e}")

print("Direct test completed successfully!")
