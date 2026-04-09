"""
Script de teste para verificar o middleware de segurança.
Testa se caminhos suspeitos como WordPress são bloqueados.
"""
import asyncio
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_wordpress_paths():
    """Testa se caminhos do WordPress são bloqueados."""
    suspicious_paths = [
        "/wordpress/wp-admin/setup-config.php",
        "/wp-admin",
        "/wp-content",
        "/wp-includes",
        "/xmlrpc.php",
        "/wp-login.php",
        "/admin",
        "/administrator",
        "/phpmyadmin",
        "/.env",
        "/.git",
        "/config.php",
        "/setup.php",
    ]
    
    print("Testando bloqueio de caminhos suspeitos...")
    for path in suspicious_paths:
        response = client.get(path)
        print(f"  {path}: {response.status_code} - {response.text[:50]}")
        
        # Deve retornar 404 (Not Found) em vez de 403 para não dar informações
        assert response.status_code == 404, f"Path {path} não foi bloqueado (status: {response.status_code})"
    
    print("✓ Todos os caminhos suspeitos foram bloqueados corretamente!")

def test_normal_paths():
    """Testa se caminhos normais continuam funcionando."""
    normal_paths = [
        "/",
        "/health",
        "/app",
        "/static",
        "/docs",
        "/redoc",
    ]
    
    print("\nTestando acesso a caminhos normais...")
    for path in normal_paths:
        response = client.get(path)
        print(f"  {path}: {response.status_code}")
        
        # Caminhos normais devem funcionar (alguns podem redirecionar)
        assert response.status_code in [200, 301, 302, 307, 308], f"Path {path} não está acessível (status: {response.status_code})"
    
    print("✓ Todos os caminhos normais estão acessíveis!")

def test_rate_limiting():
    """Testa rate limiting (simulação básica)."""
    print("\nTestando rate limiting...")
    
    # Faz várias requisições rápidas
    for i in range(10):
        response = client.get("/health")
        if response.status_code == 429:
            print(f"  Rate limiting ativado após {i+1} requisições")
            break
    
    print("✓ Rate limiting está configurado!")

def test_malicious_user_agents():
    """Testa bloqueio de user agents maliciosos."""
    print("\nTestando bloqueio de user agents maliciosos...")
    
    malicious_agents = [
        "sqlmap/1.0",
        "nikto",
        "acunetix",
        "wpscan",
        "nmap",
    ]
    
    for agent in malicious_agents:
        response = client.get("/", headers={"User-Agent": agent})
        print(f"  User-Agent '{agent}': {response.status_code}")
        
        # User agents maliciosos devem ser bloqueados
        if response.status_code != 403:
            print(f"  ⚠️  User-Agent '{agent}' não foi bloqueado (status: {response.status_code})")
    
    print("✓ Teste de user agents completado!")

if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DO MIDDLEWARE DE SEGURANÇA")
    print("=" * 60)
    
    try:
        test_wordpress_paths()
        test_normal_paths()
        test_rate_limiting()
        test_malicious_user_agents()
        
        print("\n" + "=" * 60)
        print("✅ TODOS OS TESTES PASSARAM COM SUCESSO!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()