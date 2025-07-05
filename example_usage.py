#!/usr/bin/env python3
"""
Example usage of the Logic Worker API with GCP bucket paths
"""

import asyncio
import aiohttp
import json
from datetime import datetime

API_BASE_URL = "http://localhost:3000"

async def create_job(input_bucket_path: str, output_bucket_path: str, callback_url=None):
    """Create a new processing job using GCP bucket paths"""
    async with aiohttp.ClientSession() as session:
        data = {
            "input_bucket_path": input_bucket_path,
            "output_bucket_path": output_bucket_path,
            "callback_url": callback_url
        }
        
        async with session.post(f"{API_BASE_URL}/process", json=data) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Job created successfully!")
                print(f"   Execution ID: {result['execution_id']}")
                print(f"   Status: {result['status']}")
                print(f"   Folder: {result['folder_name']}")
                print(f"   Input bucket: {result['input_bucket_path']}")
                print(f"   Output bucket: {result['output_bucket_path']}")
                return result['execution_id']
            else:
                error = await response.text()
                print(f"❌ Error creating job: {error}")
                return None

async def check_status(execution_id):
    """Check status of a job"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/status/{execution_id}") as response:
            if response.status == 200:
                result = await response.json()
                print(f"📊 Status of Job {execution_id}:")
                print(f"   Status: {result['status']}")
                print(f"   Folder: {result['folder_name']}")
                print(f"   Errors: {len(result['errors'])}")
                print(f"   Created at: {result['created_at']}")
                
                if result.get('processed_stems_path'):
                    print(f"   Processed stems: {result['processed_stems_path']}")
                
                if result['results']:
                    for res in result['results']:
                        if 'uploaded_stems' in res:
                            upload_info = res['uploaded_stems']
                            print(f"   Upload status: {upload_info['status']}")
                            if upload_info['status'] == 'success':
                                print(f"   Uploaded files: {len(upload_info['uploaded_files'])}")
                                for file in upload_info['uploaded_files']:
                                    print(f"     - {file}")
                
                return result
            else:
                error = await response.text()
                print(f"❌ Error checking status: {error}")
                return None

async def scan_folder(bucket_path: str):
    """Scan a GCP bucket folder to check if it can be processed"""
    async with aiohttp.ClientSession() as session:
        params = {"bucket_path": bucket_path}
        async with session.get(f"{API_BASE_URL}/scan", params=params) as response:
            if response.status == 200:
                result = await response.json()
                print(f"🔍 Scan of bucket folder {bucket_path}:")
                print(f"   Status: {result['status']}")
                print(f"   Processable: {'✅ Yes' if result.get('processable') else '❌ No'}")
                
                if result.get('folder_info'):
                    folder = result['folder_info']
                    print(f"   Folder name: {folder['name']}")
                    print(f"   _mix.wav files: {len(folder['mix_files'])}")
                    print(f"   Total .wav files: {folder['total_wav_files']}")
                
                return result
            else:
                error = await response.text()
                print(f"❌ Error scanning folder: {error}")
                return None

async def health_check():
    """Check if the API is running"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/health") as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ API is running: {result['message']}")
                return True
            else:
                print(f"❌ API is not responding")
                return False

async def monitor_job(execution_id, interval=10):
    """Monitor a job until completion"""
    print(f"🔄 Monitoring job {execution_id}...")
    
    while True:
        status = await check_status(execution_id)
        
        if not status:
            break
            
        if status['status'] in ['completed', 'completed_with_errors', 'error']:
            print(f"🏁 Job completed with status: {status['status']}")
            
            if status['errors']:
                print("⚠️ Errors found:")
                for error in status['errors']:
                    print(f"   - {error}")
            
            # Check if stems were processed and uploaded
            if status.get('processed_stems_path'):
                print(f"✅ Stems available at: {status['processed_stems_path']}")
            else:
                print("❌ No processed stems path available")
            
            break
            
        await asyncio.sleep(interval)

async def example_workflow():
    """Complete example workflow"""
    print("🎵 Logic Worker API Example with GCP")
    print("====================================")
    
    # 1. Check if API is running
    if not await health_check():
        return
    
    # 2. Example bucket paths (adjust as needed)
    input_bucket = "your-bucket/input/track-to-process"
    output_bucket = "your-bucket/output/processed-stems"
    callback_url = "https://your-callback-url.com/webhook"  # Optional
    
    # 3. Scan bucket folder first
    print("\n1. Scanning bucket folder...")
    scan_result = await scan_folder(input_bucket)
    
    if not scan_result or not scan_result.get('processable'):
        print("❌ Folder cannot be processed")
        return
    
    # 4. Create job
    print("\n2. Creating job...")
    execution_id = await create_job(input_bucket, output_bucket, callback_url)
    
    if not execution_id:
        return
    
    # 5. Monitor job
    print("\n3. Monitoring progress...")
    await monitor_job(execution_id)
    
    print("\n✅ Workflow completed!")

if __name__ == "__main__":
    # Basic example
    asyncio.run(example_workflow())
    
    # Or use individual functions:
    # asyncio.run(health_check())
    # asyncio.run(scan_folder("your-bucket/input/folder"))
    # execution_id = asyncio.run(create_job("input-bucket/folder", "output-bucket/folder"))
    # asyncio.run(check_status(execution_id)) 