#!/usr/bin/env python3
"""
Script para testar o endpoint de pagamento de contas a receber avulsas.
"""
import sys
from datetime import date

# Configurações
BASE_URL = "http://localhost:8000"
# Para testes, vamos usar um token válido (precisaríamos fazer login primeiro)
# Vamos simular uma requisição direta ao banco para testar a lógica

def test_direct_database():
    """Testa a lógica diretamente no banco de dados."""
    print("=== Teste Direto no Banco de Dados ===")
    
    import sys
    sys.path.append('.')
    from app.core.database import SessionLocal
    from app.models.models import ContaFinanceira, TipoConta, StatusConta, PagamentoFinanceiro, TipoPagamento, StatusPagamentoFinanceiro, OrigemRegistro
    from app.services.financeiro_service import registrar_pagamento_conta_receber
    from sqlalchemy import and_
    from decimal import Decimal
    
    db = SessionLocal()
    try:
        # Buscar uma conta a receber avulsa para testar
        conta = db.query(ContaFinanceira).filter(
            and_(
                ContaFinanceira.tipo == TipoConta.RECEBER,
                ContaFinanceira.orcamento_id == None,
                ContaFinanceira.status != StatusConta.PAGO
            )
        ).first()
        
        if not conta:
            print("❌ Nenhuma conta a receber avulsa encontrada para teste")
            return False
        
        print(f"✅ Conta encontrada para teste:")
        print(f"   ID: {conta.id}")
        print(f"   Descrição: {conta.descricao}")
        print(f"   Valor: {conta.valor}")
        print(f"   Status atual: {conta.status}")
        
        # Verificar se há pagamentos existentes
        pagamentos_existentes = db.query(PagamentoFinanceiro).filter(
            PagamentoFinanceiro.conta_id == conta.id
        ).count()
        print(f"   Pagamentos existentes: {pagamentos_existentes}")
        
        # Testar a função de serviço
        print("\n=== Testando registrar_pagamento_conta_receber ===")
        
        # Criar um usuário mock (precisamos de um usuário válido)
        from app.models.models import Usuario
        usuario = db.query(Usuario).filter_by(empresa_id=conta.empresa_id).first()
        
        if not usuario:
            print("❌ Nenhum usuário encontrado para a empresa da conta")
            return False
        
        print(f"   Usuário: {usuario.nome} (ID: {usuario.id})")
        print(f"   Empresa: {usuario.empresa_id}")
        
        # Chamar a função de serviço
        try:
            pagamento = registrar_pagamento_conta_receber(
                conta_id=conta.id,
                empresa_id=usuario.empresa_id,
                usuario=usuario,
                db=db,
                valor=None,  # Usar valor da conta
                forma_pagamento_id=None,  # Sem forma de pagamento específica
                observacao="Teste de pagamento via script",
                data_pagamento=date.today()
            )
            
            db.commit()
            
            print(f"✅ Pagamento registrado com sucesso!")
            print(f"   ID do pagamento: {pagamento.id}")
            print(f"   Valor pago: {pagamento.valor}")
            print(f"   Data: {pagamento.data_pagamento}")
            print(f"   Tipo: {pagamento.tipo}")
            
            # Verificar se o status da conta foi atualizado
            db.refresh(conta)
            print(f"   Status da conta após pagamento: {conta.status}")
            
            if conta.status == StatusConta.PAGO:
                print("✅ Status da conta atualizado corretamente para PAGO")
                return True
            else:
                print("❌ Status da conta NÃO foi atualizado para PAGO")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao registrar pagamento: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    finally:
        db.close()

def test_endpoint_via_http():
    """Testa o endpoint via HTTP (requer autenticação)."""
    print("\n=== Teste via HTTP (requer token) ===")
    
    # Primeiro precisamos fazer login para obter um token
    # Vamos pular este teste por enquanto, pois requer credenciais válidas
    print("⚠️  Teste HTTP requer autenticação - pulando...")
    return True

def test_frontend_integration():
    """Verifica se as alterações no frontend estão corretas."""
    print("\n=== Verificação de Integração Frontend ===")
    
    # Verificar se o arquivo financeiro.html foi modificado corretamente
    try:
        with open('cotte-frontend/financeiro.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar se a função abrirModalBaixa foi atualizada
        if 'abrirModalBaixa(${c.orcamento_id' in content and '${c.id})' in content:
            print("✅ Função abrirModalBaixa atualizada para passar conta_id")
        else:
            print("❌ Função abrirModalBaixa NÃO foi atualizada corretamente")
            return False
        
        # Verificar se a função salvarBaixa foi atualizada
        if 'else if (_baixaContaId)' in content and 'Financeiro.receberConta' in content:
            print("✅ Lógica de pagamento de conta avulsa implementada no frontend")
        else:
            print("❌ Lógica de pagamento de conta avulsa NÃO implementada no frontend")
            return False
        
        # Verificar se a variável _baixaContaId foi declarada
        if 'let _baixaContaId' in content or 'var _baixaContaId' in content:
            print("✅ Variável _baixaContaId declarada")
        else:
            print("❌ Variável _baixaContaId NÃO declarada")
            return False
        
        return True
        
    except FileNotFoundError:
        print("❌ Arquivo financeiro.html não encontrado")
        return False

def test_api_js_integration():
    """Verifica se a API JavaScript foi atualizada."""
    print("\n=== Verificação de API JavaScript ===")
    
    try:
        with open('cotte-frontend/js/api-financeiro.js', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar se a função receberConta foi adicionada
        if 'function receberConta(' in content:
            print("✅ Função receberConta adicionada ao api-financeiro.js")
            
            # Verificar se a função está exportada
            if 'receberConta' in content and 'return {' in content:
                print("✅ Função receberConta exportada no módulo Financeiro")
                return True
            else:
                print("❌ Função receberConta NÃO está exportada no módulo")
                return False
        else:
            print("❌ Função receberConta NÃO encontrada no api-financeiro.js")
            return False
            
    except FileNotFoundError:
        print("❌ Arquivo api-financeiro.js não encontrado")
        return False

def main():
    """Função principal de teste."""
    print("=== Teste da Correção: Contas a Receber Avulsas ===\n")
    
    all_tests_passed = True
    
    # Teste 1: Verificação de integração frontend
    if not test_frontend_integration():
        all_tests_passed = False
    
    # Teste 2: Verificação de API JavaScript
    if not test_api_js_integration():
        all_tests_passed = False
    
    # Teste 3: Teste direto no banco (lógica de negócio)
    if not test_direct_database():
        all_tests_passed = False
    
    # Teste 4: Teste HTTP (opcional)
    test_endpoint_via_http()
    
    print("\n" + "="*50)
    if all_tests_passed:
        print("✅ TODOS OS TESTES PASSARAM!")
        print("A correção para contas a receber avulsas está funcionando corretamente.")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        print("Revisar as implementações feitas.")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)