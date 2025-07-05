import os
import tempfile
import logging
import subprocess
import soundfile as sf
from typing import Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class CorruptedWavError(Exception):
    """Exception raised when a WAV file is corrupted"""
    pass

def verify_wav_file(file_path: str) -> Tuple[bool, str]:
    """
    Verify if WAV file is valid and not corrupted.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Try to open and read file info
        with sf.SoundFile(file_path) as wav_file:
            # Check basic properties
            if wav_file.frames == 0:
                return False, "File has 0 frames"
            if wav_file.samplerate <= 0:
                return False, "Invalid sample rate"
            if wav_file.channels <= 0:
                return False, "Invalid channel count"
                
            # Try to read a few frames to verify data
            wav_file.seek(0)
            wav_file.read(min(1000, wav_file.frames))
            
            # Log file info
            logger.info(f"WAV file verified: {os.path.basename(file_path)}")
            logger.info(f"  - Sample rate: {wav_file.samplerate} Hz")
            logger.info(f"  - Channels: {wav_file.channels}")
            logger.info(f"  - Duration: {wav_file.frames / wav_file.samplerate:.2f} seconds")
            
            return True, "File is valid"
            
    except Exception as e:
        return False, f"Error verifying WAV file: {str(e)}"

def download_gcp_folder(
    bucket_path: str
) -> Tuple[str, tempfile.TemporaryDirectory]:
    """
    Download a folder from GCP bucket using gsutil into a temporary directory inside ./temp.
    Only keeps valid *_mix.wav files, removes all others.
    Raises CorruptedWavError if any _mix.wav file is corrupted.
    
    Args:
        bucket_path: Full path to GCP bucket folder (e.g. 'bucket-name/folder/subfolder')
        
    Returns:
        Tuple containing:
        - Path to the downloaded folder
        - TemporaryDirectory object (keep this to ensure cleanup)
        
    Raises:
        CorruptedWavError: If any _mix.wav file is corrupted
    """
    try:
        # Create base temp directory if it doesn't exist
        base_temp = os.path.join(os.getcwd(), 'temp')
        os.makedirs(base_temp, exist_ok=True)
        temp_dir = tempfile.TemporaryDirectory(dir=base_temp)  # Keep this for cleanup tracking
        temp_path = temp_dir.name
        # Construct gsutil path
        gs_path = f"gs://{bucket_path}"
        
        # Construct command
        cmd = ["gsutil", "-m", "cp", "-r", gs_path, temp_path]
        logger.info(f"Executing command: {' '.join(cmd)}")
        logger.info(f"Downloading from {gs_path} to {temp_path}")
        
        # Use gsutil to download
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
        
        # Filter files - keep only valid *_mix.wav
        mix_files = []
        removed_files = []
        corrupted_files = []
        
        for root, dirs, files in os.walk(temp_path):
            for file in files:
                file_path = os.path.join(root, file)
                if file.endswith('_mix.wav'):
                    # Verify WAV file integrity
                    is_valid, error_msg = verify_wav_file(file_path)
                    if is_valid:
                        mix_files.append(file_path)
                    else:
                        os.remove(file_path)
                        corrupted_files.append((file, error_msg))
                else:
                    os.remove(file_path)
                    removed_files.append(file)
        
        # If any corrupted files were found, raise error
        if corrupted_files:
            error_msg = "\n".join([f"  - {f}: {err}" for f, err in corrupted_files])
            raise CorruptedWavError(
                f"Found {len(corrupted_files)} corrupted _mix.wav files:\n{error_msg}"
            )
        
        # Log what we kept and removed
        if mix_files:
            logger.info(f"Kept {len(mix_files)} valid _mix.wav files:")
            for f in mix_files:
                logger.info(f"  - {os.path.basename(f)}")
        else:
            raise Exception("No valid _mix.wav files found in downloaded folder")
            
        if removed_files:
            logger.info(f"Removed {len(removed_files)} non-mix files:")
            for f in removed_files:
                logger.info(f"  - {f}")
        
        folder_name = bucket_path.rstrip('/').split('/')[-1]
        temp_path = os.path.join(temp_path, folder_name)
        return temp_path, temp_dir
        
    except Exception as e:
        logger.error(f"Error downloading from GCP bucket: {str(e)}")
        # If we created temp_dir but failed, clean it up
        if 'temp_dir' in locals():
            temp_dir.cleanup()
        raise

def cleanup_temp(temp_base: str = None):
    """Clean up temporary directory"""
    if temp_base is None:
        temp_base = os.path.join(os.getcwd(), 'temp')
    
    if os.path.exists(temp_base):
        shutil.rmtree(temp_base)
        logger.info(f"Cleaned up temporary directory: {temp_base}")
