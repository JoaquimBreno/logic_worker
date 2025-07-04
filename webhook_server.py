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
    input_folder: str = Field(..., description="Path to the folder containing a _mix.wav file")
    callback_url: Optional[str] = Field(None, description="Optional callback URL to notify when processing is complete")

class ProcessingResponse(BaseModel):
    execution_id: str
    status: str
    message: str
    folder_name: str

class StatusResponse(BaseModel):
    execution_id: str
    status: str
    input_folder: str
    folder_name: str
    errors: list
    results: list
    created_at: str
    callback_url: Optional[str]

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
    
    This endpoint accepts a folder path and optional callback URL.
    It will scan the folder for a _mix.wav file and create a job in the queue.
    """
    try:
        # Validate input folder first
        scan_result = worker_instance.scan_input_folder(request.input_folder)
        
        if scan_result["status"] == "error":
            raise HTTPException(status_code=400, detail=scan_result["error"])
        
        if not scan_result["processable"]:
            raise HTTPException(
                status_code=400, 
                detail="Folder is not processable - contains other .wav files or no _mix.wav file"
            )
        
        # Create the job
        execution_id = await worker_instance.create_job(
            input_folder=request.input_folder,
            callback_url=request.callback_url
        )
        
        return ProcessingResponse(
            execution_id=execution_id,
            status="queued",
            message=f"Job created successfully. Processing folder: {scan_result['folder_info']['name']}",
            folder_name=scan_result['folder_info']['name']
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
async def scan_folder(folder_path: str):
    """
    Scan a folder to see if it can be processed
    
    This is a utility endpoint to preview if a folder can be processed
    without actually creating a job.
    """
    try:
        scan_result = worker_instance.scan_input_folder(folder_path)
        return scan_result
        
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
            "GET /scan": "Scan folder for processable files",
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