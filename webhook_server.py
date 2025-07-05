#!/usr/bin/env python3
import json
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from worker.logic_worker import worker_instance

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('webhook_server.log'),
        logging.StreamHandler()
    ]
)

app = FastAPI(title="Logic Worker API", version="1.0.0")

class ProcessingRequest(BaseModel):
    input_bucket_path: str = Field(..., description="GCP bucket path containing the _mix.wav file (e.g. 'bucket-name/folder')")
    output_bucket_path: str = Field(..., description="GCP bucket path where processed stems should be uploaded")
    callback_url: Optional[str] = Field(None, description="Optional callback URL to notify when processing is complete")

class ProcessingResponse(BaseModel):
    execution_id: str
    status: str
    message: str
    folder_name: str
    input_bucket_path: str
    output_bucket_path: str

class StatusResponse(BaseModel):
    execution_id: str
    status: str
    input_bucket_path: str
    output_bucket_path: str
    folder_name: str
    errors: list
    results: list
    created_at: str
    callback_url: Optional[str]
    processed_stems_path: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Initialize the worker when the server starts"""
    try:
        await worker_instance.initialize()
        logging.info("Worker initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize worker: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up when the server shuts down"""
    try:
        await worker_instance.stop_worker()
        logging.info("Worker stopped successfully")
    except Exception as e:
        logging.error(f"Error stopping worker: {str(e)}")

@app.post("/process", response_model=ProcessingResponse)
async def create_processing_job(request: ProcessingRequest):
    """
    Create a new processing job
    
    This endpoint accepts:
    - input_bucket_path: GCP bucket path containing the _mix.wav file
    - output_bucket_path: GCP bucket path where processed stems should be uploaded
    - callback_url: Optional URL for status updates
    """
    try:
        # Create the job with bucket paths
        execution_id = await worker_instance.create_job(
            input_bucket_path=request.input_bucket_path,
            output_bucket_path=request.output_bucket_path,
            callback_url=request.callback_url
        )
        
        # Get initial job status
        job_status = worker_instance.get_job_status(execution_id)
        
        return ProcessingResponse(
            execution_id=execution_id,
            status="queued",
            message=f"Job created successfully. Will process from bucket: {request.input_bucket_path}",
            folder_name=job_status['folder_name'] if job_status.get('folder_name') else '',
            input_bucket_path=request.input_bucket_path,
            output_bucket_path=request.output_bucket_path
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating processing job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{execution_id}", response_model=StatusResponse)
async def get_job_status(execution_id: str):
    """
    Get the status of a processing job by execution ID
    
    This endpoint allows you to check the current status of a job,
    including progress, errors, and results.
    """
    try:
        job_status = worker_instance.get_job_status(execution_id)
        
        if job_status is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return StatusResponse(**job_status)
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting job status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scan")
async def scan_folder(bucket_path: str):
    """
    Scan a GCP bucket folder to see if it can be processed
    
    This is a utility endpoint to preview if a folder can be processed
    without actually creating a job.
    """
    try:
        from utils.download import download_gcp_folder
        
        # Download files to temp directory
        temp_path, temp_dir = download_gcp_folder(bucket_path)
        
        try:
            scan_result = worker_instance.scan_input_folder(temp_path)
            return scan_result
        finally:
            temp_dir.cleanup()
        
    except Exception as e:
        logging.error(f"Error scanning folder: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "message": "Logic Worker API is running"}

@app.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "message": "Logic Worker API",
        "version": "1.0.0",
        "endpoints": {
            "POST /process": "Create a new processing job",
            "GET /status/{execution_id}": "Get job status",
            "GET /scan": "Scan GCP bucket folder for processable files",
            "GET /health": "Health check"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "webhook_server:app",
        host="0.0.0.0",
        port=config["webhook_port"],
        log_level="info"
    ) 