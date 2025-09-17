"""
Audio extraction module for TV API backend.
Handles the complete flow of extracting audio clips from TV backend API.
Based on the original .bat script logic.
"""
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import quote

import requests

try:
    from .models import ChannelConfig, ClipParams, ExportStatus
    from .exceptions import AudioExtractionError, NetworkError, APIConnectionError
    from .error_handler import ErrorHandler, create_error_context
except ImportError:
    from models import ChannelConfig, ClipParams, ExportStatus
    from exceptions import AudioExtractionError, NetworkError, APIConnectionError
    from error_handler import ErrorHandler, create_error_context


logger = logging.getLogger(__name__)


class AudioExtractor:
    """Handles audio extraction from TV API backend."""
    
    def __init__(self, config: ChannelConfig):
        """
        Initialize the audio extractor with channel configuration.
        
        Args:
            config: Channel configuration containing API settings
        """
        self.config = config
        self.session = requests.Session()
        self.error_handler = ErrorHandler(
            max_retries=config.api_config.max_retries,
            base_delay=2.0
        )
        
        # Set up session with cookie
        self.session.cookies.set('SID', config.api_config.cookie_sid)
        
        # Set default headers and cookies
        self.session.headers.update({
            'User-Agent': 'TV-Audio-Monitor/1.0',
            'Referer': f"{config.api_config.base_url}/"
        })
        
        # Set session cookie
        self.session.cookies.set('SID', config.api_config.cookie_sid)
        
        logger.info(f"AudioExtractor initialized for channel {config.channel_name}")
    
    def extract_audio(self, start_time: datetime, end_time: datetime, 
                     output_dir: str, clip_name: Optional[str] = None) -> str:
        """
        Extract audio clip from TV backend API.
        
        Args:
            start_time: Start time for the clip
            end_time: End time for the clip
            output_dir: Directory to save the audio file
            clip_name: Optional name for the clip
            
        Returns:
            str: Path to the downloaded audio file
            
        Raises:
            AudioExtractionError: If extraction fails at any step
        """
        if not clip_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clip_name = f"audio_clip_{timestamp}"
        
        context = create_error_context(
            "audio_extraction",
            channel=self.config.channel_name,
            timestamp=start_time,
            additional_info={"clip_name": clip_name}
        )
        
        logger.info(f"Starting audio extraction: {clip_name}")
        logger.info(f"Time range: {start_time} to {end_time}")
        
        clip_id = None
        try:
            # Step 1: Store clip
            clip_id = self._store_clip_with_retry(start_time, end_time, clip_name)
            logger.info(f"Clip created with ID: {clip_id}")
            
            # Step 2: Export clip
            self._export_clip_with_retry(clip_id)
            logger.info("Export initiated")
            
            # Step 3: Poll for export completion
            export_status = self._poll_export_with_retry(clip_id)
            if not export_status.is_ready or not export_status.file_path:
                raise AudioExtractionError(f"Export failed: {export_status.error_message}")
            
            logger.info("Export completed, download ready")
            
            # Step 4: Download audio file
            output_path = self._download_audio_with_retry(export_status.file_path, output_dir, clip_name)
            logger.info(f"Audio downloaded to: {output_path}")
            
            # Step 5: Cleanup clip from server (best effort)
            try:
                self.cleanup_clip(clip_id)
                logger.info(f"Clip {clip_id} cleaned up from server")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup clip {clip_id}: {cleanup_error}")
            
            return output_path
            
        except Exception as e:
            self.error_handler.handle_error(e, context, critical=True)
            
            # Attempt cleanup if we have a clip_id
            if clip_id:
                try:
                    self.cleanup_clip(clip_id)
                    logger.info(f"Emergency cleanup of clip {clip_id} successful")
                except Exception as cleanup_error:
                    logger.warning(f"Emergency cleanup failed for clip {clip_id}: {cleanup_error}")
            
            if isinstance(e, AudioExtractionError):
                raise
            else:
                raise AudioExtractionError(f"Failed to extract audio: {e}") from e
    
    def store_clip(self, start_time: datetime, end_time: datetime, clip_name: str) -> str:
        """
        Create a clip on the TV backend.
        
        Args:
            start_time: Start time for the clip
            end_time: End time for the clip
            clip_name: Name for the clip
            
        Returns:
            str: Clip ID
            
        Raises:
            AudioExtractionError: If clip creation fails
        """
        url = f"{self.config.api_config.base_url}/pl-v2/Clips.pl"
        
        # Format times as required by the API
        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
        
        params = {
            'event': 'store_clip',
            'program': '1'
        }
        
        data = {
            'comentario': '',
            'endtime': end_str,
            'idemisora': str(self.config.idemisora),
            'idprograma': str(self.config.idprograma),
            'nombre': clip_name,
            'starttime': start_str
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        for attempt in range(self.config.api_config.max_retries):
            try:
                logger.debug(f"Store clip attempt {attempt + 1}/{self.config.api_config.max_retries}")
                
                response = self.session.post(
                    url, 
                    params=params, 
                    data=data, 
                    headers=headers,
                    timeout=30
                )
                response.raise_for_status()
                
                # Parse JSON response to get clip ID
                result = response.json()
                clip_id = result.get('id')
                
                if not clip_id:
                    raise AudioExtractionError("No clip ID returned from store_clip")
                
                return str(clip_id)
                
            except requests.RequestException as e:
                logger.warning(f"Store clip attempt {attempt + 1} failed: {e}")
                if attempt == self.config.api_config.max_retries - 1:
                    raise AudioExtractionError(f"Failed to store clip after {self.config.api_config.max_retries} attempts: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
            
            except (json.JSONDecodeError, KeyError) as e:
                raise AudioExtractionError(f"Invalid response from store_clip: {e}")
    
    def export_clip(self, clip_id: str) -> None:
        """
        Initiate export of the clip.
        
        Args:
            clip_id: ID of the clip to export
            
        Raises:
            AudioExtractionError: If export initiation fails
        """
        url = f"{self.config.api_config.base_url}/Procesos.pl"
        
        params = {
            'event': 'export_nodes_uni',
            'idclip': clip_id,
            'format': str(self.config.api_config.format),
            'videoIsPublic': str(self.config.api_config.video_is_public),
            'isMasive': str(self.config.api_config.is_masive)
        }
        
        for attempt in range(self.config.api_config.max_retries):
            try:
                logger.debug(f"Export clip attempt {attempt + 1}/{self.config.api_config.max_retries}")
                
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                return  # Export initiated successfully
                
            except requests.RequestException as e:
                logger.warning(f"Export clip attempt {attempt + 1} failed: {e}")
                if attempt == self.config.api_config.max_retries - 1:
                    raise AudioExtractionError(f"Failed to export clip after {self.config.api_config.max_retries} attempts: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def poll_export_status(self, clip_id: str) -> ExportStatus:
        """
        Poll the export status until ready or timeout.
        
        Args:
            clip_id: ID of the clip being exported
            
        Returns:
            ExportStatus: Status of the export
            
        Raises:
            AudioExtractionError: If polling fails or times out
        """
        url = f"{self.config.api_config.base_url}/pl-v2/Clips.pl"
        
        params = {
            'event': 'fetch_exported_clips',
            'idclip': clip_id
        }
        
        max_attempts = self.config.api_config.max_retries
        sleep_seconds = self.config.api_config.sleep_seconds
        
        for attempt in range(max_attempts):
            try:
                logger.debug(f"Polling export status attempt {attempt + 1}/{max_attempts}")
                
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                files = result.get('files', [])
                
                if files and len(files) > 0:
                    file_info = files[0]
                    download_path = file_info.get('download_path')
                    
                    if download_path:
                        return ExportStatus(
                            success=True,
                            is_ready=True,
                            file_path=download_path,
                            error_message=None
                        )
                
                # Not ready yet, wait and retry
                if attempt < max_attempts - 1:
                    logger.debug(f"Export not ready, waiting {sleep_seconds} seconds...")
                    time.sleep(sleep_seconds)
                
            except requests.RequestException as e:
                logger.warning(f"Poll attempt {attempt + 1} failed: {e}")
                if attempt == self.config.api_config.max_retries - 1:
                    return ExportStatus(
                        success=False,
                        is_ready=False,
                        file_path=None,
                        error_message=f"Polling failed after {max_attempts} attempts: {e}"
                    )
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except (json.JSONDecodeError, KeyError) as e:
                return ExportStatus(
                    success=False,
                    is_ready=False,
                    file_path=None,
                    error_message=f"Invalid response from fetch_exported_clips: {e}"
                )
        
        return ExportStatus(
            success=False,
            is_ready=False,
            file_path=None,
            error_message=f"Export not ready after {max_attempts} attempts"
        )
    
    def download_audio(self, download_path: str, output_dir: str, clip_name: str) -> str:
        """
        Download the exported audio file.
        
        Args:
            download_path: Path returned by the export API
            output_dir: Directory to save the file
            clip_name: Base name for the output file
            
        Returns:
            str: Path to the downloaded file
            
        Raises:
            AudioExtractionError: If download fails
        """
        # Construct full download URL (like the .bat script)
        # Replace spaces with %20 for URL encoding
        encoded_path = download_path.replace(' ', '%20')
        full_url = f"{self.config.api_config.base_url}{encoded_path}"
        
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Determine file extension (default to mp3 for audio)
        file_extension = "mp3"
        if '.' in download_path:
            file_extension = download_path.split('.')[-1]
        
        # Create output file path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{clip_name}_{timestamp}.{file_extension}"
        output_path = os.path.join(output_dir, output_filename)
        
        for attempt in range(self.config.api_config.max_retries):
            try:
                logger.debug(f"Download attempt {attempt + 1}/{self.config.api_config.max_retries}")
                logger.debug(f"Downloading from: {full_url}")
                
                response = self.session.get(
                    full_url,
                    stream=True,
                    timeout=300,  # 5 minutes for download
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # Write file in chunks
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # Verify file was downloaded
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info(f"Successfully downloaded {os.path.getsize(output_path)} bytes")
                    return output_path
                else:
                    raise AudioExtractionError("Downloaded file is empty or missing")
                
            except requests.RequestException as e:
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                if attempt == self.config.api_config.max_retries - 1:
                    raise AudioExtractionError(f"Failed to download audio after {self.config.api_config.max_retries} attempts: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
            
            except IOError as e:
                raise AudioExtractionError(f"Failed to write downloaded file: {e}")
    
    @ErrorHandler().retry_on_error(
        retryable_exceptions=(NetworkError, APIConnectionError, requests.RequestException),
        max_retries=3
    )
    def _store_clip_with_retry(self, start_time: datetime, end_time: datetime, clip_name: str) -> str:
        """Store clip with retry logic."""
        try:
            return self.store_clip(start_time, end_time, clip_name)
        except requests.RequestException as e:
            raise NetworkError(f"Network error during store_clip: {e}") from e
        except Exception as e:
            raise APIConnectionError(f"API error during store_clip: {e}") from e
    
    @ErrorHandler().retry_on_error(
        retryable_exceptions=(NetworkError, APIConnectionError, requests.RequestException),
        max_retries=3
    )
    def _export_clip_with_retry(self, clip_id: str) -> None:
        """Export clip with retry logic."""
        try:
            self.export_clip(clip_id)
        except requests.RequestException as e:
            raise NetworkError(f"Network error during export_clip: {e}") from e
        except Exception as e:
            raise APIConnectionError(f"API error during export_clip: {e}") from e
    
    @ErrorHandler().retry_on_error(
        retryable_exceptions=(NetworkError, APIConnectionError, requests.RequestException),
        max_retries=5,  # More retries for polling
        backoff_factor=1.5
    )
    def _poll_export_with_retry(self, clip_id: str):
        """Poll export status with retry logic."""
        try:
            return self.poll_export_status(clip_id)
        except requests.RequestException as e:
            raise NetworkError(f"Network error during poll_export: {e}") from e
        except Exception as e:
            raise APIConnectionError(f"API error during poll_export: {e}") from e
    
    @ErrorHandler().retry_on_error(
        retryable_exceptions=(NetworkError, APIConnectionError, requests.RequestException),
        max_retries=3
    )
    def _download_audio_with_retry(self, download_path: str, output_dir: str, clip_name: str) -> str:
        """Download audio with retry logic."""
        try:
            return self.download_audio(download_path, output_dir, clip_name)
        except requests.RequestException as e:
            raise NetworkError(f"Network error during download: {e}") from e
        except Exception as e:
            raise APIConnectionError(f"API error during download: {e}") from e

    def cleanup_clip(self, clip_id: str) -> bool:
        """
        Delete the clip from the server.
        
        Args:
            clip_id: ID of the clip to delete
            
        Returns:
            bool: True if cleanup was successful
            
        Raises:
            AudioExtractionError: If cleanup fails
        """
        url = f"{self.config.api_config.base_url}/Nodes.pl"
        
        params = {
            'event': 'remove_masive_nodes',
            'idsnodes': clip_id
        }
        
        for attempt in range(self.config.api_config.max_retries):
            try:
                logger.debug(f"Cleanup attempt {attempt + 1}/{self.config.api_config.max_retries}")
                
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                return True
                
            except requests.RequestException as e:
                logger.warning(f"Cleanup attempt {attempt + 1} failed: {e}")
                if attempt == self.config.api_config.max_retries - 1:
                    # Don't raise exception for cleanup failures, just log
                    logger.error(f"Failed to cleanup clip {clip_id} after {self.config.api_config.max_retries} attempts: {e}")
                    return False
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return False
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.session.close()


# Convenience functions for backward compatibility
def extract_audio(config: ChannelConfig, start_time: datetime, end_time: datetime, 
                 output_dir: str, clip_name: Optional[str] = None) -> str:
    """
    Extract audio clip using the AudioExtractor.
    
    Args:
        config: Channel configuration
        start_time: Start time for the clip
        end_time: End time for the clip
        output_dir: Directory to save the audio file
        clip_name: Optional name for the clip
        
    Returns:
        str: Path to the downloaded audio file
    """
    with AudioExtractor(config) as extractor:
        return extractor.extract_audio(start_time, end_time, output_dir, clip_name)


def store_clip(config: ChannelConfig, params: ClipParams) -> str:
    """
    Store a clip on the TV backend.
    
    Args:
        config: Channel configuration
        params: Clip parameters
        
    Returns:
        str: Clip ID
    """
    with AudioExtractor(config) as extractor:
        start_time = datetime.strptime(params.start_time, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(params.end_time, "%Y-%m-%d %H:%M:%S")
        return extractor.store_clip(start_time, end_time, f"clip_{params.idemisora}_{params.idprograma}")


def poll_export_status(config: ChannelConfig, clip_id: str) -> ExportStatus:
    """
    Poll export status for a clip.
    
    Args:
        config: Channel configuration
        clip_id: ID of the clip
        
    Returns:
        ExportStatus: Status of the export
    """
    with AudioExtractor(config) as extractor:
        return extractor.poll_export_status(clip_id)


def download_audio(config: ChannelConfig, download_path: str, output_dir: str) -> str:
    """
    Download audio from the given path.
    
    Args:
        config: Channel configuration
        download_path: Path to download from
        output_dir: Directory to save the file
        
    Returns:
        str: Path to the downloaded file
    """
    with AudioExtractor(config) as extractor:
        return extractor.download_audio(download_path, output_dir, "downloaded_audio")


def cleanup_clip(config: ChannelConfig, clip_id: str) -> bool:
    """
    Cleanup a clip from the server.
    
    Args:
        config: Channel configuration
        clip_id: ID of the clip to cleanup
        
    Returns:
        bool: True if cleanup was successful
    """
    with AudioExtractor(config) as extractor:
        return extractor.cleanup_clip(clip_id)