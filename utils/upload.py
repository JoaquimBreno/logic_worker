import os
import logging
import subprocess
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

def upload_stems_to_gcp(
    local_folder: str,
    bucket_path: str,
    stems_pattern: str = "*.wav",
    folder_name: str = None
) -> Dict[str, Any]:
    """
    Upload processed stems from local folder to GCP bucket.
    
    Args:
        local_folder: Path to local folder containing stems
        bucket_path: GCP bucket path to upload to (e.g. 'bucket-name/folder')
        stems_pattern: Pattern to match stem files (default: "*.wav")
        
    Returns:
        Dict containing upload status and paths
    """
    try:
        # Ensure local folder exists
        if not os.path.exists(local_folder):
            raise Exception(f"Local folder not found: {local_folder}")
            
        # Find all stem files
        stem_files = list(Path(local_folder).glob(stems_pattern))
        if not stem_files:
            raise Exception(f"No stem files found in {local_folder}")
            
        # Construct gsutil path
        gs_path = f"gs://{bucket_path}"
        
        if folder_name:
            gs_path = f"{gs_path}/{folder_name}"
            
        # Log what we're uploading
        logger.info(f"Found {len(stem_files)} stems to upload:")
        for stem in stem_files:
            logger.info(f"  - {stem.name}")
            
        # Construct upload command
        cmd = ["gsutil", "-m", "cp", "-r", f"{local_folder}", gs_path]
        logger.info(f"Executing upload command: {' '.join(cmd)}")
        
        # Execute upload
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        # Log output
        if result.stdout:
            logger.info(f"gsutil output: {result.stdout}")
        if result.stderr:
            logger.warning(f"gsutil stderr: {result.stderr}")
            
        if result.returncode != 0:
            raise Exception(f"gsutil error (code {result.returncode}): {result.stderr}")
            
        # Return success with paths
        return {
            "status": "success",
            "message": f"Successfully uploaded {len(stem_files)} stems",
            "source_folder": local_folder,
            "destination_bucket": bucket_path,
            "uploaded_files": [stem.name for stem in stem_files],
            "gcp_path": gs_path
        }
        
    except Exception as e:
        logger.error(f"Error uploading stems to GCP: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "source_folder": local_folder,
            "destination_bucket": bucket_path
        }
