# src/utils/file_manager.py
"""
Gemini File API Manager for uploading and managing PDF files.
Handles upload, polling for processing, and cleanup.

⚠️ DEPRECATION NOTICE:
This module is currently NOT used in the main extraction pipeline.
We now use direct PDF bytes (types.Part.from_bytes()) which is much faster.

This module is kept for:
- Future use cases requiring server-side file caching
- Very large files (>20MB) that exceed request size limits
- Legacy compatibility

For context generation, see context_generator.py which uses direct bytes.
"""
import os
import time
from google import genai
from pathlib import Path
from typing import Optional
from .logging_utils import setup_logger

logger = setup_logger("file_manager")


class GeminiFileManager:
    """
    Manager for Gemini File API operations.
    Handles PDF upload, processing wait, and cleanup.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize File Manager with API key.
        
        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
        """
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment")
        
        self.client = genai.Client(api_key=api_key)
        logger.info("Gemini File Manager initialized")
    
    def upload_pdf(self, pdf_path: str, display_name: Optional[str] = None) -> str:
        """
        Upload PDF file to Gemini File API.
        
        Args:
            pdf_path: Path to PDF file
            display_name: Optional display name for the file
        
        Returns:
            File URI for use in prompts
        
        Raises:
            FileNotFoundError: If PDF doesn't exist
            Exception: If upload fails
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        if display_name is None:
            display_name = pdf_path.stem
        
        logger.info(f"Uploading PDF: {pdf_path.name} ({pdf_path.stat().st_size / 1024 / 1024:.2f} MB)")
        
        try:
            # Upload file to Gemini using new API
            uploaded_file = self.client.files.upload(
                file=str(pdf_path)
            )
            
            logger.info(f"File uploaded successfully: {uploaded_file.name}")
            logger.info(f"File URI: {uploaded_file.uri}")
            
            return uploaded_file.name  # Return file name for later reference
            
        except Exception as e:
            logger.error(f"Failed to upload PDF: {e}")
            raise
    
    def wait_for_file(self, file_name: str, timeout: int = 300, poll_interval: int = 5) -> bool:
        """
        Wait for uploaded file to be processed and ready.
        
        Args:
            file_name: File name returned from upload_pdf()
            timeout: Maximum wait time in seconds
            poll_interval: How often to check status (seconds)
        
        Returns:
            True if file is ready, False if timeout
        
        Raises:
            Exception: If file processing fails
        """
        logger.info(f"Waiting for file to be processed: {file_name}")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                file = self.client.files.get(name=file_name)
                
                if file.state.name == "ACTIVE":
                    logger.info(f"File is ready: {file_name}")
                    return True
                elif file.state.name == "FAILED":
                    raise Exception(f"File processing failed: {file_name}")
                
                # Still processing
                elapsed = time.time() - start_time
                logger.debug(f"File still processing... ({elapsed:.1f}s elapsed)")
                time.sleep(poll_interval)
                
            except Exception as e:
                logger.error(f"Error checking file status: {e}")
                raise
        
        logger.error(f"Timeout waiting for file to be processed: {file_name}")
        return False
    
    def get_file(self, file_name: str):
        """
        Get file object from Gemini API.
        
        Args:
            file_name: File name to retrieve
        
        Returns:
            File object with uri, state, etc.
        """
        try:
            return self.client.files.get(name=file_name)
        except Exception as e:
            logger.error(f"Error retrieving file: {e}")
            raise
    
    def delete_file(self, file_name: str) -> bool:
        """
        Delete uploaded file from Gemini File API.
        
        Args:
            file_name: File name to delete
        
        Returns:
            True if deleted successfully
        """
        try:
            self.client.files.delete(name=file_name)
            logger.info(f"File deleted successfully: {file_name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete file {file_name}: {e}")
            return False
    
    def upload_and_wait(self, pdf_path: str, display_name: Optional[str] = None, 
                       timeout: int = 300) -> tuple[str, str]:
        """
        Convenience method: upload file and wait for it to be ready.
        
        Args:
            pdf_path: Path to PDF file
            display_name: Optional display name
            timeout: Maximum wait time
        
        Returns:
            Tuple of (file_name, file_uri)
        
        Raises:
            Exception: If upload or processing fails
        """
        file_name = self.upload_pdf(pdf_path, display_name)
        
        if not self.wait_for_file(file_name, timeout):
            # Try to cleanup on timeout
            self.delete_file(file_name)
            raise TimeoutError(f"File processing timeout: {pdf_path}")
        
        # Get file object to retrieve URI
        file_obj = self.get_file(file_name)
        
        return file_name, file_obj.uri
