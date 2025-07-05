#!/usr/bin/env python3
import os
import json
import uuid
import asyncio
import logging
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError
import aiohttp
from utils.download import download_gcp_folder
from utils.upload import upload_stems_to_gcp
# Import the robot
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from robot.logic import LogicRobot

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(config['log_folder'], 'worker.log')),
        logging.StreamHandler()
    ]
)

@dataclass
class ProcessingJob:
    execution_id: str
    input_bucket_path: str
    output_bucket_path: str
    callback_url: Optional[str]
    created_at: datetime
    status: str = "pending"
    folder_name: str = ""
    errors: List[Dict[str, Any]] = None
    results: List[Dict[str, Any]] = None
    processed_stems_path: Optional[str] = None
    temp_dir: Optional[Any] = None  # TemporaryDirectory instance

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.results is None:
            self.results = []

class LogicWorker:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.redis = None
        self.pool = None
        self.robot = LogicRobot()
        self.jobs_status = {}  # In-memory job status tracking
        
    async def initialize(self):
        """Initialize Redis connection pool"""
        try:
            self.pool = ConnectionPool.from_url(
                config['redis_url'],
                max_connections=10,
                decode_responses=True
            )
            self.redis = Redis(connection_pool=self.pool)
            self.logger.info("Worker initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize worker: {str(e)}")
            raise

    async def cleanup_logic_folder(self):
        """Clean up Logic folder in case of errors"""
        try:
            cleanup_folder = config['cleanup_folder']
            if os.path.exists(cleanup_folder):
                shutil.rmtree(cleanup_folder)
                os.makedirs(cleanup_folder)
                self.logger.info(f"Cleaned up folder: {cleanup_folder}")
        except Exception as e:
            self.logger.error(f"Error cleaning up folder: {str(e)}")

    def scan_input_folder(self, folder_path: str) -> Dict[str, Any]:
        """Scan input folder and return information about _mix.wav files"""
        try:
            if not os.path.exists(folder_path):
                return {
                    "status": "error",
                    "error": "Input folder does not exist",
                    "processable": False,
                    "folder_info": None
                }
            
            # Check if this folder directly contains a _mix.wav file
            mix_files = [f for f in os.listdir(folder_path) if f.endswith('_mix.wav')]
            
            if mix_files:
                # This is the folder we want to process
                folder_name = os.path.basename(folder_path)
                wav_files = [f for f in os.listdir(folder_path) if f.endswith('.wav')]
                
                folder_info = {
                    "path": folder_path,
                    "name": folder_name,
                    "mix_files": mix_files,
                    "total_wav_files": len(wav_files),
                    "should_process": len(wav_files) == len(mix_files)  # Only process if only _mix.wav files
                }
                
                return {
                    "status": "success",
                    "processable": folder_info["should_process"],
                    "folder_info": folder_info,
                    "scanned_at": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "error": "No _mix.wav file found in the specified folder",
                    "processable": False,
                    "folder_info": None
                }
            
        except Exception as e:
            self.logger.error(f"Error scanning input folder: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "processable": False,
                "folder_info": None
            }

    async def send_callback(self, callback_url: str, data: Dict[str, Any]):
        """Send callback to the provided URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(callback_url, json=data) as response:
                    if response.status == 200:
                        self.logger.info(f"Callback sent successfully to {callback_url}")
                    else:
                        self.logger.error(f"Callback failed with status {response.status}")
        except Exception as e:
            self.logger.error(f"Error sending callback: {str(e)}")

    async def process_job(self, job_data: Dict[str, Any]):
        """Process a single job from the queue"""
        temp_dir = None
        try:
            execution_id = job_data['execution_id']
            input_bucket_path = job_data['input_bucket_path']
            output_bucket_path = job_data['output_bucket_path']
            callback_url = job_data.get('callback_url')
            
            self.logger.info(f"Processing job {execution_id} from bucket: {input_bucket_path}")
            
            # Update job status
            processing_job = ProcessingJob(
                execution_id=execution_id,
                input_bucket_path=input_bucket_path,
                output_bucket_path=output_bucket_path,
                callback_url=callback_url,
                created_at=datetime.now(),
                status="processing"
            )
            self.jobs_status[execution_id] = processing_job
            
            # Download from GCP bucket
            try:
                folder_name, temp_path, temp_dir = download_gcp_folder(input_bucket_path)
                processing_job.temp_dir = temp_dir
                print(f"Temp dir: {temp_dir}")
                print(f"Temp path: {temp_path}")
                self.logger.info(f"Downloaded files to temp folder: {temp_path}")
            except Exception as e:
                processing_job.status = "error"
                processing_job.errors.append({
                    "error": f"Failed to download from GCP: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
                if callback_url:
                    await self.send_callback(callback_url, {
                        "execution_id": execution_id,
                        "status": "error",
                        "error": f"Download failed: {str(e)}"
                    })
                return
            
            # Scan the downloaded folder
            scan_result = self.scan_input_folder(temp_path)
            
            if scan_result["status"] == "error":
                processing_job.status = "error"
                processing_job.errors.append({
                    "error": scan_result["error"],
                    "timestamp": datetime.now().isoformat()
                })
                
                if callback_url:
                    await self.send_callback(callback_url, {
                        "execution_id": execution_id,
                        "status": "error",
                        "error": scan_result["error"]
                    })
                return
            
            folder_info = scan_result["folder_info"]
            
            if not folder_info or not folder_info["should_process"]:
                processing_job.status = "error"
                processing_job.errors.append({
                    "error": "No processable folder found or folder contains other .wav files",
                    "timestamp": datetime.now().isoformat()
                })
                
                if callback_url:
                    await self.send_callback(callback_url, {
                        "execution_id": execution_id,
                        "status": "error",
                        "error": "No processable folder found"
                    })
                return
            
            # Save folder name for control
            processing_job.folder_name = folder_info["name"]
            self.logger.info(f"Processing folder: {folder_info['name']}")
            
            # Process the folder
            try:
                result = await self.robot.process_folder(folder_info["path"], folder_info["name"])
                processing_job.results.append(result)
                
                if result["status"] == "error":
                    processing_job.errors.append({
                        "folder": folder_info["name"],
                        "error": result.get("error", "Unknown error"),
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # If any error occurs, cleanup
                    await self.cleanup_logic_folder()
                    
                else:
                    # If processing was successful, move stems to temp folder and upload
                    try:   
                        # Move stems from Logic folder to temp folder
                        logic_folder = config['cleanup_folder']
                        temp_stems_folder = os.path.join(temp_path, 'stems')
                        os.makedirs(temp_stems_folder, exist_ok=True)
                        
                        # Move all wav files
                        for file in os.listdir(logic_folder):
                            if file.endswith('.wav'):
                                src = os.path.join(logic_folder, file)
                                dst = os.path.join(temp_stems_folder, file)
                                shutil.move(src, dst)
                        
                        # Upload stems to GCP
                        upload_result = upload_stems_to_gcp(
                            local_folder=temp_stems_folder,
                            bucket_path=output_bucket_path,
                            folder_name=folder_name
                        )
                        
                        if upload_result["status"] == "success":
                            processing_job.processed_stems_path = upload_result["gcp_path"]
                            result["uploaded_stems"] = upload_result
                        else:
                            processing_job.errors.append({
                                "folder": folder_info["name"],
                                "error": f"Failed to upload stems: {upload_result['message']}",
                                "timestamp": datetime.now().isoformat()
                            })
                        
                    except Exception as e:
                        self.logger.error(f"Error handling stems: {str(e)}")
                        processing_job.errors.append({
                            "folder": folder_info["name"],
                            "error": f"Failed to handle stems: {str(e)}",
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    # Cleanup Logic folder
                    await self.cleanup_logic_folder()
                    
            except Exception as e:
                self.logger.error(f"Error processing folder {folder_info['name']}: {str(e)}")
                processing_job.errors.append({
                    "folder": folder_info["name"],
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                
                # Cleanup on error
                await self.cleanup_logic_folder()
            
            # Update final status
            if processing_job.errors:
                processing_job.status = "completed_with_errors"
            else:
                processing_job.status = "completed"
            
            self.logger.info(f"Job {execution_id} completed with status: {processing_job.status}")
            
            # Send callback if provided
            if callback_url:
                callback_data = {
                    "execution_id": execution_id,
                    "status": processing_job.status,
                    "folder_name": processing_job.folder_name,
                    "errors": processing_job.errors,
                    "results": processing_job.results,
                    "processed_stems_path": processing_job.processed_stems_path,
                    "completed_at": datetime.now().isoformat()
                }
                await self.send_callback(callback_url, callback_data)
            
        except Exception as e:
            self.logger.error(f"Critical error in job processing: {str(e)}")
            execution_id = job_data.get('execution_id', 'unknown')
            
            if execution_id in self.jobs_status:
                self.jobs_status[execution_id].status = "error"
                self.jobs_status[execution_id].errors.append({
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
            
            # Cleanup on critical error
            await self.cleanup_logic_folder()
            
            # Send error callback
            callback_url = job_data.get('callback_url')
            if callback_url:
                await self.send_callback(callback_url, {
                    "execution_id": execution_id,
                    "status": "error",
                    "error": str(e)
                })
        finally:
            # Always cleanup temp directory if it exists
            if temp_dir:
                temp_dir.cleanup()

    async def create_job(
        self, 
        input_bucket_path: str,
        output_bucket_path: str,
        callback_url: Optional[str] = None
    ) -> str:
        """Create a new processing job"""
        try:
            execution_id = str(uuid.uuid4())
            
            # Create job in queue
            job_data = {
                "execution_id": execution_id,
                "input_bucket_path": input_bucket_path,
                "output_bucket_path": output_bucket_path,
                "callback_url": callback_url,
                "created_at": datetime.now().isoformat()
            }
            
            # Add job to Redis list
            await self.redis.lpush("logic-processing", json.dumps(job_data))
            
            # Initialize job status
            processing_job = ProcessingJob(
                execution_id=execution_id,
                input_bucket_path=input_bucket_path,
                output_bucket_path=output_bucket_path,
                callback_url=callback_url,
                created_at=datetime.now(),
                status="queued"
            )
            self.jobs_status[execution_id] = processing_job
            
            self.logger.info(f"Created job {execution_id} for bucket path: {input_bucket_path}")
            
            return execution_id
            
        except Exception as e:
            self.logger.error(f"Error creating job: {str(e)}")
            raise

    def get_job_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a job by execution ID"""
        if execution_id not in self.jobs_status:
            return None
        
        job = self.jobs_status[execution_id]
        return {
            "execution_id": job.execution_id,
            "status": job.status,
            "input_bucket_path": job.input_bucket_path,
            "output_bucket_path": job.output_bucket_path,
            "folder_name": job.folder_name,
            "errors": job.errors,
            "results": job.results,
            "created_at": job.created_at.isoformat(),
            "callback_url": job.callback_url,
            "processed_stems_path": job.processed_stems_path
        }

    async def process_queue(self):
        """Process jobs from the queue"""
        while True:
            try:
                # Get job from Redis list
                job_data = await self.redis.brpop("logic-processing", timeout=1)
                if job_data:
                    _, job_json = job_data
                    job = json.loads(job_json)
                    await self.process_job(job)
            except Exception as e:
                self.logger.error(f"Error processing queue: {str(e)}")
                await asyncio.sleep(1)

    async def start_worker(self):
        """Start the worker"""
        try:
            await self.initialize()
            self.logger.info("Worker started and waiting for jobs...")
            await self.process_queue()
        except Exception as e:
            self.logger.error(f"Error starting worker: {str(e)}")
            raise

    async def stop_worker(self):
        """Stop the worker"""
        try:
            if self.redis:
                await self.redis.close()
            if self.pool:
                await self.pool.disconnect()
            self.logger.info("Worker stopped")
        except Exception as e:
            self.logger.error(f"Error stopping worker: {str(e)}")

# Global worker instance
worker_instance = LogicWorker()

async def main():
    """Main function to run the worker"""
    try:
        await worker_instance.start_worker()
    except KeyboardInterrupt:
        print("\nShutting down worker...")
        await worker_instance.stop_worker()
    except Exception as e:
        logging.error(f"Worker error: {str(e)}")
        await worker_instance.stop_worker()

if __name__ == "__main__":
    asyncio.run(main())
