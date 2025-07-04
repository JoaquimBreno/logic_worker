#!/usr/bin/env python3
"""
Exemplo de uso da API Logic Worker
"""

import asyncio
import aiohttp
import json
from datetime import datetime

API_BASE_URL = "http://localhost:3000"

async def create_job(input_folder, callback_url=None):
    """Criar um novo job de processamento"""
    async with aiohttp.ClientSession() as session:
        data = {
            "input_folder": input_folder,
            "callback_url": callback_url
        }
        
        async with session.post(f"{API_BASE_URL}/process", json=data) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Job criado com sucesso!")
                print(f"   Execution ID: {result['execution_id']}")
                print(f"   Status: {result['status']}")
                print(f"   Pasta: {result['folder_name']}")
                return result['execution_id']
            else:
                error = await response.text()
                print(f"❌ Erro ao criar job: {error}")
                return None

async def check_status(execution_id):
    """Verificar status de um job"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/status/{execution_id}") as response:
            if response.status == 200:
                result = await response.json()
                print(f"📊 Status do Job {execution_id}:")
                print(f"   Status: {result['status']}")
                print(f"   Pasta: {result['folder_name']}")
                print(f"   Erros: {len(result['errors'])}")
                print(f"   Criado em: {result['created_at']}")
                
                if result['results']:
                    for res in result['results']:
                        export_status = "✅ Exportado" if res.get('export_verified') else "❌ Erro na exportação"
                        print(f"   Resultado: {res['status']} - {export_status}")
                
                return result
            else:
                error = await response.text()
                print(f"❌ Erro ao verificar status: {error}")
                return None

async def scan_folder(folder_path):
    """Escanear pasta para ver se pode ser processada"""
    async with aiohttp.ClientSession() as session:
        params = {"folder_path": folder_path}
        async with session.get(f"{API_BASE_URL}/scan", params=params) as response:
            if response.status == 200:
                result = await response.json()
                print(f"🔍 Scan da pasta {folder_path}:")
                print(f"   Status: {result['status']}")
                print(f"   Processável: {'✅ Sim' if result.get('processable') else '❌ Não'}")
                
                if result.get('folder_info'):
                    folder = result['folder_info']
                    print(f"   Nome da pasta: {folder['name']}")
                    print(f"   Arquivos _mix.wav: {len(folder['mix_files'])}")
                    print(f"   Total de .wav: {folder['total_wav_files']}")
                
                return result
            else:
                error = await response.text()
                print(f"❌ Erro ao escanear pasta: {error}")
                return None

async def health_check():
    """Verificar se a API está funcionando"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/health") as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ API está funcionando: {result['message']}")
                return True
            else:
                print(f"❌ API não está respondendo")
                return False

async def monitor_job(execution_id, interval=10):
    """Monitorar um job até sua conclusão"""
    print(f"🔄 Monitorando job {execution_id}...")
    
    while True:
        status = await check_status(execution_id)
        
        if not status:
            break
            
        if status['status'] in ['completed', 'completed_with_errors', 'error']:
            print(f"🏁 Job concluído com status: {status['status']}")
            
            if status['errors']:
                print("⚠️ Erros encontrados:")
                for error in status['errors']:
                    print(f"   - {error}")
            
            # Verificar se exportação foi bem-sucedida
            if status['results']:
                for result in status['results']:
                    if result.get('export_verified'):
                        print("✅ Exportação verificada com sucesso!")
                    else:
                        print("❌ Falha na verificação de exportação")
            
            break
            
        await asyncio.sleep(interval)

async def example_workflow():
    """Exemplo completo de workflow"""
    print("🎵 Exemplo de uso da API Logic Worker")
    print("====================================")
    
    # 1. Verificar se a API está funcionando
    if not await health_check():
        return
    
    # 2. Pasta de exemplo (ajuste conforme necessário)
    input_folder = "/Users/moises/Documents/logic_processa/Tracklib - Won't Be Around_mix"
    callback_url = "https://your-callback-url.com/webhook"  # Opcional
    
    # 3. Escanear pasta primeiro
    print("\n1. Escaneando pasta...")
    scan_result = await scan_folder(input_folder)
    
    if not scan_result or not scan_result.get('processable'):
        print("❌ Pasta não pode ser processada")
        return
    
    # 4. Criar job
    print("\n2. Criando job...")
    execution_id = await create_job(input_folder, callback_url)
    
    if not execution_id:
        return
    
    # 5. Monitorar job
    print("\n3. Monitorando progresso...")
    await monitor_job(execution_id)
    
    print("\n✅ Workflow concluído!")

if __name__ == "__main__":
    # Exemplo básico
    asyncio.run(example_workflow())
    
    # Ou use funções individuais:
    # asyncio.run(health_check())
    # asyncio.run(scan_folder("/path/to/folder"))
    # execution_id = asyncio.run(create_job("/path/to/folder"))
    # asyncio.run(check_status(execution_id)) 