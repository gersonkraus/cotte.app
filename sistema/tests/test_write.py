with open('test_result.txt', 'w') as f:
    f.write('Test is working\n')
    try:
        from app.routers.financeiro import listar_categorias
        f.write('Import successful\n')
        f.write(f'Function: {listar_categorias}\n')
    except Exception as e:
        f.write(f'Import failed: {e}\n')
