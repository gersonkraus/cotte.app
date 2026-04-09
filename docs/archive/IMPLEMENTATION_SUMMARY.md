---
title: Implementation Summary
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Implementation Summary
tags:
  - documentacao
prioridade: media
status: documentado
---
# Fix for /financeiro/categorias 404 Error

## Problem
The frontend was making requests to `/financeiro/categorias` but this endpoint was commented out in the router, causing 404 errors.

## Solution Implemented

### 1. Added Missing Imports (financeiro.py)
```python
from app.models.models import CategoriaFinanceira
from app.schemas.financeiro import (
    CategoriaFinanceiraCreate,
    CategoriaFinanceiraOut, 
    CategoriaFinanceiraUpdate,
    TipoCategoria,
)
```

### 2. Created Sync Service Function (financeiro_service.py)
```python
def listar_categorias_sync(
    empresa_id: int,
    db: Session,
    tipo: Optional[str] = None,
    ativas: bool = True,
) -> List[CategoriaFinanceira]:
    """Lista categorias financeiras customizáveis da empresa (versão sync)."""
    query = db.query(CategoriaFinanceira).filter_by(empresa_id=empresa_id)
    
    if ativas:
        query = query.filter(CategoriaFinanceira.ativo == True)
    
    if tipo:
        query = query.filter(CategoriaFinanceira.tipo == tipo)
    
    return query.order_by(CategoriaFinanceira.ordem, CategoriaFinanceira.nome).all()
```

### 3. Implemented Endpoint (financeiro.py)
```python
@router.get("/categorias", response_model=List[CategoriaFinanceiraOut])
def listar_categorias(
    tipo: Optional[str] = Query(None, description="Tipo de categoria: receita, despesa ou ambos"),
    ativas: bool = Query(True, description="Apenas categorias ativas"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Lista categorias financeiras da empresa."""
    categorias = svc.listar_categorias_sync(
        empresa_id=usuario.empresa_id,
        db=db,
        tipo=tipo,
        ativas=ativas,
    )
    return [
        CategoriaFinanceiraOut(
            id=c.id,
            empresa_id=c.empresa_id,
            nome=c.nome,
            tipo=TipoCategoria(c.tipo),  # Convert string to enum
            cor=c.cor,
            icone=c.icone,
            ativo=c.ativo,
            ordem=c.ordem,
            criado_em=c.criado_em,
        )
        for c in categorias
    ]
```

## Features
- ✅ Lists categories by company (empresa_id)
- ✅ Filter by type (receita, despesa, ambos)
- ✅ Filter by active status
- ✅ Proper authentication required
- ✅ Returns ordered list (by ordem, then nome)
- ✅ Uses existing CategoriaFinanceira model and schemas

## Testing
The endpoint should now respond to:
- `GET /financeiro/categorias` - all active categories
- `GET /financeiro/categorias?tipo=receita` - only income categories  
- `GET /financeiro/categorias?ativas=false` - include inactive categories

## Frontend Compatibility
The response format matches what the frontend expects in `api-financeiro.js`:
```javascript
function listarCategorias(forceFetch = false) {
    if (_categoriasCache && !forceFetch) return Promise.resolve(_categoriasCache);
    return apiRequest('GET', '/financeiro/categorias').then(cats => {
        _categoriasCache = cats;
        return cats;
    });
}
```
