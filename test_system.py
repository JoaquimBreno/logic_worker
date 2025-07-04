#!/usr/bin/env python3
"""
Teste simples para verificar o funcionamento do sistema
"""

import asyncio
import aiohttp
import tempfile
import os
import json

API_BASE_URL = "http://localhost:3000"

async def test_api_health():
    """Teste de health check"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/health") as response:
                if response.status == 200:
                    result = await response.json()
                    print("✅ API Health Check: PASS")
                    return True
                else:
                    print(f"❌ API Health Check: FAIL - Status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ API Health Check: FAIL - {str(e)}")
        return False

async def test_scan_nonexistent_folder():
    """Teste de scan de pasta que não existe"""
    try:
        async with aiohttp.ClientSession() as session:
            params = {"folder_path": "/nonexistent/folder"}
            async with session.get(f"{API_BASE_URL}/scan", params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    if result["status"] == "error":
                        print("✅ Scan Nonexistent Folder: PASS")
                        return True
                    else:
                        print("❌ Scan Nonexistent Folder: FAIL - Should return error")
                        return False
                else:
                    print(f"❌ Scan Nonexistent Folder: FAIL - Status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Scan Nonexistent Folder: FAIL - {str(e)}")
        return False

async def test_scan_empty_folder():
    """Teste de scan de pasta vazia"""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            async with aiohttp.ClientSession() as session:
                params = {"folder_path": temp_dir}
                async with session.get(f"{API_BASE_URL}/scan", params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result["status"] == "success" and result["total_files"] == 0:
                            print("✅ Scan Empty Folder: PASS")
                            return True
                        else:
                            print("❌ Scan Empty Folder: FAIL - Unexpected result")
                            return False
                    else:
                        print(f"❌ Scan Empty Folder: FAIL - Status {response.status}")
                        return False
    except Exception as e:
        print(f"❌ Scan Empty Folder: FAIL - {str(e)}")
        return False

async def test_scan_folder_with_mix_files():
    """Teste de scan de pasta com arquivos _mix.wav"""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Criar subpasta com arquivo _mix.wav
            sub_folder = os.path.join(temp_dir, "test_song")
            os.makedirs(sub_folder)
            
            # Criar arquivo _mix.wav falso
            mix_file = os.path.join(sub_folder, "test_song_mix.wav")
            with open(mix_file, 'w') as f:
                f.write("fake wav content")
            
            async with aiohttp.ClientSession() as session:
                params = {"folder_path": temp_dir}
                async with session.get(f"{API_BASE_URL}/scan", params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result["status"] == "success" and result["total_files"] == 1:
                            print("✅ Scan Folder with Mix Files: PASS")
                            return True
                        else:
                            print(f"❌ Scan Folder with Mix Files: FAIL - {result}")
                            return False
                    else:
                        print(f"❌ Scan Folder with Mix Files: FAIL - Status {response.status}")
                        return False
    except Exception as e:
        print(f"❌ Scan Folder with Mix Files: FAIL - {str(e)}")
        return False

async def test_create_job_invalid_folder():
    """Teste de criação de job com pasta inválida"""
    try:
        async with aiohttp.ClientSession() as session:
            data = {"input_folder": "/nonexistent/folder"}
            async with session.post(f"{API_BASE_URL}/process", json=data) as response:
                if response.status == 400:
                    print("✅ Create Job Invalid Folder: PASS")
                    return True
                else:
                    print(f"❌ Create Job Invalid Folder: FAIL - Status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Create Job Invalid Folder: FAIL - {str(e)}")
        return False

async def test_status_nonexistent_job():
    """Teste de status de job inexistente"""
    try:
        async with aiohttp.ClientSession() as session:
            fake_id = "nonexistent-job-id"
            async with session.get(f"{API_BASE_URL}/status/{fake_id}") as response:
                if response.status == 404:
                    print("✅ Status Nonexistent Job: PASS")
                    return True
                else:
                    print(f"❌ Status Nonexistent Job: FAIL - Status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Status Nonexistent Job: FAIL - {str(e)}")
        return False

async def run_all_tests():
    """Executar todos os testes"""
    print("🧪 Executando testes do sistema...")
    print("=" * 50)
    
    tests = [
        test_api_health,
        test_scan_nonexistent_folder,
        test_scan_empty_folder,
        test_scan_folder_with_mix_files,
        test_create_job_invalid_folder,
        test_status_nonexistent_job
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if await test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: EXCEPTION - {str(e)}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Resultados dos testes:")
    print(f"   ✅ Passou: {passed}")
    print(f"   ❌ Falhou: {failed}")
    print(f"   📈 Taxa de sucesso: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 Todos os testes passaram!")
    else:
        print(f"\n⚠️ {failed} teste(s) falharam")

if __name__ == "__main__":
    asyncio.run(run_all_tests()) 