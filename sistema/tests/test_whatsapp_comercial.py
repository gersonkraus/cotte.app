"""
Script de Testes para Envio de WhatsApp no Comercial

Uso:
    cd sistema
    ../venv/bin/python test_whatsapp_comercial.py

Pré-requisitos:
    - Servidor backend rodando em localhost:8000
    - Token JWT de superadmin configurado
    - WhatsApp conectado (ou mock)
"""
import asyncio
import sys
import os

# Adicionar o diretório do sistema ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from datetime import datetime

BASE_URL = "http://localhost:8000"
# Token de superadmin - substitua pelo seu token real ou use login
TOKEN = os.getenv("COMERCIAL_TEST_TOKEN", "")

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}"
}


def log(msg, tipo="INFO"):
    """Log formatado."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    emoji = {"INFO": "📋", "OK": "✅", "WARN": "⚠️", "ERROR": "❌", "TEST": "🧪"}.get(tipo, "📋")
    print(f"[{timestamp}] {emoji} {msg}")


async def esperar_token():
    """Obtém token via login se não definido."""
    global TOKEN, HEADERS
    
    if TOKEN:
        return True
    
    print("\n" + "="*60)
    print("🔐 TESTE DE WHATSAPP COMERCIAL - COTTE")
    print("="*60 + "\n")
    
    # Tentar login padrão
    email = input("📧 E-mail do superadmin: ").strip()
    senha = input("🔑 Senha: ").strip()
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/auth/login",
                json={"email": email, "senha": senha}
            )
            
            if response.status_code == 200:
                data = response.json()
                TOKEN = data.get("access_token", "")
                HEADERS["Authorization"] = f"Bearer {TOKEN}"
                log("Login realizado com sucesso!", "OK")
                return True
            else:
                log(f"Erro no login: {response.status_code} - {response.text}", "ERROR")
                return False
    except Exception as e:
        log(f"Erro ao conectar: {e}", "ERROR")
        return False


async def test_dashboard():
    """Testa endpoint do dashboard."""
    log("Testando GET /comercial/dashboard", "TEST")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/comercial/dashboard",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            log(f"  Total de leads: {data.get('total_leads', 0)}", "OK")
            log(f"  Novos: {data.get('novos', 0)}", "OK")
            return True
        else:
            log(f"  Erro: {response.status_code} - {response.text[:100]}", "ERROR")
            return False


async def test_criar_lead():
    """Testa criação de lead."""
    log("Testando POST /comercial/leads (criar lead)", "TEST")
    
    # Gerar dados únicos para evitar duplicatas
    timestamp = datetime.now().strftime("%H%M%S")
    
    lead_data = {
        "nome_responsavel": f"Teste Bot {timestamp}",
        "nome_empresa": f"Empresa Teste {timestamp} Ltda",
        "whatsapp": f"4899999{timestamp[-4:]}",
        "email": f"teste{timestamp}@empresateste.com.br",
        "cidade": "Florianópolis",
        "segmento_id": None,
        "origem_lead_id": None,
        "interesse_plano": "pro",
        "valor_proposto": 299.90
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/comercial/leads",
            json=lead_data,
            headers=HEADERS
        )
        
        if response.status_code == 201:
            data = response.json()
            lead_id = data.get("id")
            log(f"  Lead criado com ID: {lead_id}", "OK")
            log(f"  Nome: {data.get('nome_responsavel')}", "OK")
            log(f"  WhatsApp: {data.get('whatsapp')}", "OK")
            return lead_id
        else:
            log(f"  Erro: {response.status_code} - {response.text[:150]}", "ERROR")
            return None


async def test_listar_leads():
    """Testa listagem de leads."""
    log("Testando GET /comercial/leads", "TEST")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/comercial/leads?per_page=5",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            total = data.get("total", 0)
            log(f"  Total de leads: {total}", "OK")
            log(f"  Retornados: {len(items)}", "OK")
            
            if items:
                # Mostrar o primeiro lead
                lead = items[0]
                log(f"  Primeiro lead: {lead.get('nome_empresa')} (ID: {lead.get('id')})", "OK")
                return lead.get("id")
            return None
        else:
            log(f"  Erro: {response.status_code} - {response.text[:100]}", "ERROR")
            return None


async def test_detalhe_lead(lead_id):
    """Testa detalhes de um lead."""
    if not lead_id:
        log("Pulando teste de detalhe (sem lead_id)", "WARN")
        return None
    
    log(f"Testando GET /comercial/leads/{lead_id}", "TEST")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/comercial/leads/{lead_id}",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            log(f"  Nome: {data.get('nome_empresa')}", "OK")
            log(f"  Status: {data.get('status_pipeline')}", "OK")
            log(f"  Score: {data.get('lead_score')}", "OK")
            return True
        else:
            log(f"  Erro: {response.status_code}", "ERROR")
            return False


async def test_enviar_whatsapp(lead_id):
    """Testa envio de WhatsApp individual."""
    if not lead_id:
        log("Pulando teste de WhatsApp (sem lead_id)", "WARN")
        return None
    
    log(f"Testando POST /comercial/leads/{lead_id}/whatsapp", "TEST")
    
    mensagem = f"""👋 Olá! Este é um mensagem de teste do COTTE.
    
Este teste verifica se o fluxo de envio de WhatsApp para leads está funcionando corretamente.

⏰ Enviado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}

Se você recebeu esta mensagem, o sistema está funcionando! 🎉"""
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/comercial/leads/{lead_id}/whatsapp",
            json={"mensagem": mensagem},
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            sucesso = data.get("sucesso", False)
            if sucesso:
                log("  ✅ WhatsApp enviado com sucesso!", "OK")
            else:
                log(f"  ⚠️ WhatsApp pode ter falhado: {data}", "WARN")
            return sucesso
        elif response.status_code == 400:
            data = response.json()
            log(f"  ℹ️ Lead sem WhatsApp ou erro de validação: {data.get('detail', '')}", "WARN")
            return None
        else:
            log(f"  Erro: {response.status_code} - {response.text[:150]}", "ERROR")
            return False


async def test_templates():
    """Testa CRUD de templates."""
    log("Testando CRUD de Templates", "TEST")
    
    # Listar templates existentes
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/comercial/templates",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            templates = response.json()
            log(f"  Templates existentes: {len(templates)}", "OK")
            
            if templates:
                tpl = templates[0]
                log(f"  Primeiro: {tpl.get('nome')} (ID: {tpl.get('id')})", "OK")
                return tpl.get("id")
            else:
                log("  Nenhum template encontrado, criando um...", "WARN")
                
                # Criar template de teste
                timestamp = datetime.now().strftime("%H%M%S")
                tpl_data = {
                    "nome": f"Template Teste {timestamp}",
                    "tipo": "mensagem_inicial",
                    "canal": "whatsapp",
                    "conteudo": f"""Olá {{nome}}! 

Esta é uma mensagem automática da {{empresa}}.

Estamos felizes em falar com você! 🎉

Att,
Equipe COTTE"""
                }
                
                response = await client.post(
                    f"{BASE_URL}/api/v1/comercial/templates",
                    json=tpl_data,
                    headers=HEADERS
                )
                
                if response.status_code == 201:
                    tpl = response.json()
                    log(f"  Template criado: {tpl.get('nome')} (ID: {tpl.get('id')})", "OK")
                    return tpl.get("id")
                else:
                    log(f"  Erro ao criar template: {response.status_code}", "ERROR")
                    return None
        else:
            log(f"  Erro ao listar templates: {response.status_code}", "ERROR")
            return None


async def test_enviar_lote(lead_ids, template_id):
    """Testa envio em lote."""
    if not lead_ids or not template_id:
        log("Pulando teste de envio em lote (faltam dados)", "WARN")
        return None
    
    log(f"Testando POST /comercial/leads/enviar-lote", "TEST")
    log(f"  Leads: {lead_ids}", "INFO")
    log(f"  Template: {template_id}", "INFO")
    
    payload = {
        "lead_ids": lead_ids[:3],  # Limitar a 3 para o teste
        "campaign_id": template_id,
        "canal": "whatsapp",
        "delay_min": 2,  # Delay reduzido para teste
        "delay_max": 5
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/comercial/leads/enviar-lote",
            json=payload,
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            log(f"  Total: {data.get('total')}", "OK")
            log(f"  Enviados: {data.get('enviados')}", "OK")
            log(f"  Falhas: {data.get('falhas')}", "OK")
            
            delay = data.get("delay_configurado", {})
            log(f"  Delay configurado: {delay.get('min')}s - {delay.get('max')}s", "OK")
            
            # Mostrar resultados
            resultados = data.get("resultados", [])
            for r in resultados:
                status = r.get("status")
                nome = r.get("nome", "N/A")
                if status == "enviado":
                    log(f"    ✅ {nome}", "OK")
                elif status == "ignorado":
                    log(f"    ⏭️ {nome} (ignorado: {r.get('motivo')})", "WARN")
                else:
                    log(f"    ❌ {nome} ({r.get('motivo', status)})", "ERROR")
            
            return data.get("enviados", 0)
        else:
            log(f"  Erro: {response.status_code} - {response.text[:200]}", "ERROR")
            return None


async def test_preview_template(template_id, lead_id):
    """Testa preview de template."""
    if not template_id or not lead_id:
        log("Pulando teste de preview (faltam dados)", "WARN")
        return
    
    log(f"Testando POST /comercial/templates/{template_id}/preview", "TEST")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/comercial/templates/{template_id}/preview",
            json={"lead_id": lead_id},
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            conteudo = data.get("conteudo", "")[:100]
            log(f"  Preview gerado (primeiros 100 chars):", "OK")
            log(f"  \"{conteudo}...\"", "INFO")
            return True
        else:
            log(f"  Erro: {response.status_code}", "ERROR")
            return False


async def main():
    """Executa todos os testes."""
    print("\n" + "="*60)
    print("🚀 TESTES DE WHATSAPP COMERCIAL")
    print("="*60 + "\n")
    
    # Obter token se necessário
    if not await esperar_token():
        log("Não foi possível obter token de autenticação", "ERROR")
        return
    
    # Suite de testes
    testes = []
    
    # 1. Dashboard
    testes.append(("Dashboard", test_dashboard()))
    
    # 2. Listar leads
    lead_id_existente = await test_listar_leads()
    testes.append(("Listar Leads", lead_id_existente is not None))
    
    # 3. Criar lead de teste
    novo_lead_id = await test_criar_lead()
    if novo_lead_id:
        testes.append(("Criar Lead", True))
        
        # 4. Detalhe do lead criado
        await test_detalhe_lead(novo_lead_id)
        
        # 5. Enviar WhatsApp individual
        await test_enviar_whatsapp(novo_lead_id)
    else:
        testes.append(("Criar Lead", False))
    
    # 6. Templates
    template_id = await test_templates()
    if template_id:
        testes.append(("Templates", True))
        
        # 7. Preview do template
        if lead_id_existente:
            await test_preview_template(template_id, lead_id_existente)
        
        # 8. Envio em lote
        lead_ids_para_lote = [novo_lead_id, lead_id_existente] if novo_lead_id and lead_id_existente else [novo_lead_id] if novo_lead_id else []
        if lead_ids_para_lote:
            await test_enviar_lote(lead_ids_para_lote, template_id)
    else:
        testes.append(("Templates", False))
    
    # Resumo
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    
    for nome, resultado in testes:
        status = "✅ OK" if resultado else "❌ FALHOU"
        print(f"  {status}  {nome}")
    
    # Próximos passos
    print("\n" + "="*60)
    print("📝 PRÓXIMOS PASSOS")
    print("="*60)
    print("""
  1. Verifique se as mensagens foram enviadas pelo WhatsApp
  2. Acesse a interface web: http://localhost:3000/comercial.html
  3. Abra a aba "Leads" e clique em um lead para ver o histórico
  4. Verifique se as interações (WhatsApp/Email) aparecem na timeline

  Para testar via interface:
  - Abra comercial.html
  - Vá na aba "Campanhas"
  - Crie ou selecione um template
  - Importe leads
  - Use o modal de envio em lote
""")


if __name__ == "__main__":
    asyncio.run(main())
