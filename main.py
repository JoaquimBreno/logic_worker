#!/usr/bin/env python3
"""
Logic Worker - Automated Music Processing System
Main entry point for the system
"""

import asyncio
import logging
import signal
import sys
from worker.logic_worker import worker_instance
from webhook_server import app
import uvicorn
import json
import multiprocessing
import os

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('main.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_worker():
    """Run the worker process"""
    asyncio.run(worker_instance.start_worker())

def run_webhook_server():
    """Run the webhook server"""
    uvicorn.run(
        "webhook_server:app",
        host="0.0.0.0",
        port=config["webhook_port"],
        log_level="info"
    )

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Shutdown signal received. Stopping services...")
    sys.exit(0)

def main():
    """Main function to start both services"""
    print("🎵 Logic Worker - Automated Music Processing System")
    print("=" * 60)
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start worker process
        logger.info("Starting worker process...")
        worker_process = multiprocessing.Process(target=run_worker)
        worker_process.start()
        
        # Start webhook server process
        logger.info("Starting webhook server...")
        server_process = multiprocessing.Process(target=run_webhook_server)
        server_process.start()
        
        print(f"✅ System started successfully!")
        print(f"🌐 API available at: http://localhost:{config['webhook_port']}")
        print(f"📚 Documentation: http://localhost:{config['webhook_port']}/docs")
        print(f"🔧 Worker running in background")
        print(f"📝 Logs available in: ./logs/")
        print(f"")
        print(f"Press Ctrl+C to stop all services")
        
        # Wait for processes
        worker_process.join()
        server_process.join()
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
        
        # Terminate processes
        if 'worker_process' in locals():
            worker_process.terminate()
            worker_process.join()
            
        if 'server_process' in locals():
            server_process.terminate()
            server_process.join()
            
        logger.info("All services stopped")
        
    except Exception as e:
        logger.error(f"Error running system: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
