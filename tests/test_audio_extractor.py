"""
Integration tests for the audio extractor module.
Tests the complete flow with mock API responses.
"""
import json
import os
import tempfile
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.audio_extractor import AudioExtractor, AudioExtractionError, extract_audio
from src.models import ChannelConfig, DeepgramConfig, APIConfig, ExportStatus


@pytest.fixture
def sample_config():
    """Create a sample channel configuration for testing."""
    deepgram_config = DeepgramConfig(
        language="multi",
        model="nova-3",
        smart_format=True
    )
    
    api_config = APIConfig(
        base_url="http://test-api.example.com",
        cookie_sid="test_session_id",
        format=11,
        video_is_public=0,
        is_masive=1,
        max_retries=3,
        sleep_seconds=1  # Shorter for tests
    )
    
    return ChannelConfig(
        channel_name="test_channel",
        idemisora=1,
        idprograma=5,
        cortinillas=["test phrase"],
        deepgram_config=deepgram_config,
        api_config=api_config
    )


@pytest.fixture
def mock_session():
    """Create a mock requests session."""
    session = Mock()
    session.cookies = Mock()
    session.headers = {}
    return session


class TestAudioExtractor:
    """Test cases for AudioExtractor class."""
    
    def test_init(self, sample_config):
        """Test AudioExtractor initialization."""
        with patch('src.audio_extractor.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.headers = {}  # Initialize as dict
            mock_session_class.return_value = mock_session
            
            extractor = AudioExtractor(sample_config)
            
            assert extractor.config == sample_config
            assert extractor.session == mock_session
            mock_session.cookies.set.assert_called_once_with('SID', 'test_session_id')
            assert 'User-Agent' in mock_session.headers
            assert 'Referer' in mock_session.headers
    
    @patch('src.audio_extractor.requests.Session')
    def test_store_clip_success(self, mock_session_class, sample_config):
        """Test successful clip storage."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {'id': '12345'}
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response
        
        extractor = AudioExtractor(sample_config)
        start_time = datetime(2025, 1, 1, 10, 0, 0)
        end_time = datetime(2025, 1, 1, 11, 0, 0)
        
        clip_id = extractor.store_clip(start_time, end_time, "test_clip")
        
        assert clip_id == "12345"
        mock_session.post.assert_called_once()
        
        # Verify the call parameters
        call_args = mock_session.post.call_args
        assert "store_clip" in call_args[1]['params']['event']
        assert call_args[1]['data']['nombre'] == "test_clip"
        assert call_args[1]['data']['starttime'] == "2025-01-01 10:00:00"
        assert call_args[1]['data']['endtime'] == "2025-01-01 11:00:00"
    
    @patch('src.audio_extractor.requests.Session')
    def test_store_clip_retry_logic(self, mock_session_class, sample_config):
        """Test retry logic in store_clip."""
        mock_session = Mock()
        mock_session.headers = {}
        mock_session_class.return_value = mock_session
        
        # First call raises exception, second succeeds
        mock_response_success = Mock()
        mock_response_success.json.return_value = {'id': '12345'}
        mock_response_success.raise_for_status.return_value = None
        
        # First call raises RequestException, second returns success
        from requests.exceptions import RequestException
        mock_session.post.side_effect = [RequestException("Network error"), mock_response_success]
        
        extractor = AudioExtractor(sample_config)
        start_time = datetime(2025, 1, 1, 10, 0, 0)
        end_time = datetime(2025, 1, 1, 11, 0, 0)
        
        with patch('time.sleep'):  # Speed up test
            clip_id = extractor.store_clip(start_time, end_time, "test_clip")
        
        assert clip_id == "12345"
        assert mock_session.post.call_count == 2
    
    @patch('src.audio_extractor.requests.Session')
    def test_store_clip_max_retries_exceeded(self, mock_session_class, sample_config):
        """Test store_clip when max retries are exceeded."""
        mock_session = Mock()
        mock_session.headers = {}
        mock_session_class.return_value = mock_session
        
        # All calls fail
        from requests.exceptions import RequestException
        mock_session.post.side_effect = RequestException("Network error")
        
        extractor = AudioExtractor(sample_config)
        start_time = datetime(2025, 1, 1, 10, 0, 0)
        end_time = datetime(2025, 1, 1, 11, 0, 0)
        
        with patch('time.sleep'):  # Speed up test
            with pytest.raises(AudioExtractionError, match="Failed to store clip after 3 attempts"):
                extractor.store_clip(start_time, end_time, "test_clip")
        
        assert mock_session.post.call_count == 3
    
    @patch('src.audio_extractor.requests.Session')
    def test_export_clip_success(self, mock_session_class, sample_config):
        """Test successful clip export."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        
        extractor = AudioExtractor(sample_config)
        extractor.export_clip("12345")
        
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert call_args[1]['params']['event'] == 'export_nodes_uni'
        assert call_args[1]['params']['idclip'] == '12345'
    
    @patch('src.audio_extractor.requests.Session')
    def test_poll_export_status_ready(self, mock_session_class, sample_config):
        """Test polling when export is ready."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.json.return_value = {
            'files': [{'download_path': '/path/to/file.mp3'}]
        }
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        
        extractor = AudioExtractor(sample_config)
        status = extractor.poll_export_status("12345")
        
        assert status.is_ready is True
        assert status.download_path == '/path/to/file.mp3'
        assert status.error_message is None
    
    @patch('src.audio_extractor.requests.Session')
    @patch('time.sleep')
    def test_poll_export_status_not_ready_then_ready(self, mock_sleep, mock_session_class, sample_config):
        """Test polling when export is not ready initially."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # First response: not ready, second response: ready
        mock_response_not_ready = Mock()
        mock_response_not_ready.json.return_value = {'files': []}
        mock_response_not_ready.raise_for_status.return_value = None
        
        mock_response_ready = Mock()
        mock_response_ready.json.return_value = {
            'files': [{'download_path': '/path/to/file.mp3'}]
        }
        mock_response_ready.raise_for_status.return_value = None
        
        mock_session.get.side_effect = [mock_response_not_ready, mock_response_ready]
        
        extractor = AudioExtractor(sample_config)
        status = extractor.poll_export_status("12345")
        
        assert status.is_ready is True
        assert status.download_path == '/path/to/file.mp3'
        assert mock_session.get.call_count == 2
        mock_sleep.assert_called_once_with(1)  # sleep_seconds from config
    
    @patch('src.audio_extractor.requests.Session')
    @patch('time.sleep')
    def test_poll_export_status_timeout(self, mock_sleep, mock_session_class, sample_config):
        """Test polling timeout."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # All responses: not ready
        mock_response = Mock()
        mock_response.json.return_value = {'files': []}
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        
        extractor = AudioExtractor(sample_config)
        status = extractor.poll_export_status("12345")
        
        assert status.is_ready is False
        assert status.download_path is None
        assert "Export not ready after 3 attempts" in status.error_message
        assert mock_session.get.call_count == 3
    
    @patch('src.audio_extractor.requests.Session')
    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('pathlib.Path.mkdir')
    def test_download_audio_success(self, mock_mkdir, mock_getsize, mock_exists, 
                                   mock_open, mock_session_class, sample_config):
        """Test successful audio download."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Mock successful download response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_content.return_value = [b'audio_data_chunk1', b'audio_data_chunk2']
        mock_session.get.return_value = mock_response
        
        # Mock file operations
        mock_exists.return_value = True
        mock_getsize.return_value = 1024  # File size
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        extractor = AudioExtractor(sample_config)
        
        with patch('src.audio_extractor.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20250101_120000"
            
            output_path = extractor.download_audio(
                "/path/to/file.mp3", 
                "/tmp/output", 
                "test_clip"
            )
        
        expected_path = os.path.join("/tmp/output", "test_clip_20250101_120000.mp3")
        assert output_path == expected_path
        
        # Verify file was written
        mock_file.write.assert_any_call(b'audio_data_chunk1')
        mock_file.write.assert_any_call(b'audio_data_chunk2')
    
    @patch('src.audio_extractor.requests.Session')
    def test_cleanup_clip_success(self, mock_session_class, sample_config):
        """Test successful clip cleanup."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        
        extractor = AudioExtractor(sample_config)
        result = extractor.cleanup_clip("12345")
        
        assert result is True
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert call_args[1]['params']['event'] == 'remove_masive_nodes'
        assert call_args[1]['params']['idsnodes'] == '12345'
    
    @patch('src.audio_extractor.requests.Session')
    def test_cleanup_clip_failure(self, mock_session_class, sample_config):
        """Test clip cleanup failure (should not raise exception)."""
        mock_session = Mock()
        mock_session.headers = {}
        mock_session_class.return_value = mock_session
        
        from requests.exceptions import RequestException
        mock_session.get.side_effect = RequestException("Network error")
        
        extractor = AudioExtractor(sample_config)
        
        with patch('time.sleep'):  # Speed up test
            result = extractor.cleanup_clip("12345")
        
        assert result is False  # Should return False but not raise exception
        assert mock_session.get.call_count == 3  # Should retry
    
    @patch('src.audio_extractor.AudioExtractor.store_clip')
    @patch('src.audio_extractor.AudioExtractor.export_clip')
    @patch('src.audio_extractor.AudioExtractor.poll_export_status')
    @patch('src.audio_extractor.AudioExtractor.download_audio')
    @patch('src.audio_extractor.AudioExtractor.cleanup_clip')
    @patch('src.audio_extractor.requests.Session')
    def test_extract_audio_full_flow(self, mock_session_class, mock_cleanup, 
                                    mock_download, mock_poll, mock_export, 
                                    mock_store, sample_config):
        """Test the complete extract_audio flow."""
        # Setup mocks
        mock_store.return_value = "12345"
        mock_export.return_value = None
        mock_poll.return_value = ExportStatus(
            is_ready=True,
            download_path="/path/to/file.mp3",
            error_message=None
        )
        mock_download.return_value = "/tmp/output/test_clip.mp3"
        mock_cleanup.return_value = True
        
        extractor = AudioExtractor(sample_config)
        
        start_time = datetime(2025, 1, 1, 10, 0, 0)
        end_time = datetime(2025, 1, 1, 11, 0, 0)
        
        result = extractor.extract_audio(start_time, end_time, "/tmp/output", "test_clip")
        
        assert result == "/tmp/output/test_clip.mp3"
        
        # Verify all steps were called
        mock_store.assert_called_once_with(start_time, end_time, "test_clip")
        mock_export.assert_called_once_with("12345")
        mock_poll.assert_called_once_with("12345")
        mock_download.assert_called_once_with("/path/to/file.mp3", "/tmp/output", "test_clip")
        mock_cleanup.assert_called_once_with("12345")
    
    @patch('src.audio_extractor.AudioExtractor.store_clip')
    @patch('src.audio_extractor.requests.Session')
    def test_extract_audio_store_failure(self, mock_session_class, mock_store, sample_config):
        """Test extract_audio when store_clip fails."""
        mock_store.side_effect = AudioExtractionError("Store failed")
        
        extractor = AudioExtractor(sample_config)
        
        start_time = datetime(2025, 1, 1, 10, 0, 0)
        end_time = datetime(2025, 1, 1, 11, 0, 0)
        
        with pytest.raises(AudioExtractionError, match="Failed to extract audio"):
            extractor.extract_audio(start_time, end_time, "/tmp/output", "test_clip")
    
    @patch('src.audio_extractor.requests.Session')
    def test_context_manager(self, mock_session_class, sample_config):
        """Test AudioExtractor as context manager."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        with AudioExtractor(sample_config) as extractor:
            assert extractor.session == mock_session
        
        mock_session.close.assert_called_once()


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('src.audio_extractor.AudioExtractor')
    def test_extract_audio_function(self, mock_extractor_class, sample_config):
        """Test the extract_audio convenience function."""
        mock_extractor = Mock()
        mock_extractor_class.return_value.__enter__.return_value = mock_extractor
        mock_extractor.extract_audio.return_value = "/path/to/audio.mp3"
        
        start_time = datetime(2025, 1, 1, 10, 0, 0)
        end_time = datetime(2025, 1, 1, 11, 0, 0)
        
        result = extract_audio(sample_config, start_time, end_time, "/tmp/output", "test")
        
        assert result == "/path/to/audio.mp3"
        mock_extractor.extract_audio.assert_called_once_with(
            start_time, end_time, "/tmp/output", "test"
        )


@pytest.mark.integration
class TestAudioExtractorIntegration:
    """Integration tests with more realistic scenarios."""
    
    def test_url_encoding(self, sample_config):
        """Test URL encoding for download paths with spaces."""
        with patch('src.audio_extractor.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            # Mock response with spaces in path
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.iter_content.return_value = [b'data']
            mock_session.get.return_value = mock_response
            
            extractor = AudioExtractor(sample_config)
            
            with patch('os.path.exists', return_value=True), \
                 patch('os.path.getsize', return_value=100), \
                 patch('builtins.open', create=True), \
                 patch('pathlib.Path.mkdir'), \
                 patch('datetime.datetime') as mock_datetime:
                
                mock_datetime.now.return_value.strftime.return_value = "20250101_120000"
                
                extractor.download_audio(
                    "/path with spaces/file name.mp3",
                    "/tmp/output",
                    "test_clip"
                )
            
            # Verify URL was properly encoded
            call_args = mock_session.get.call_args
            url = call_args[0][0]
            assert "/path%20with%20spaces/file%20name.mp3" in url
    
    def test_error_propagation(self, sample_config):
        """Test that errors are properly propagated through the chain."""
        with patch('src.audio_extractor.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            # Mock store_clip to succeed
            store_response = Mock()
            store_response.json.return_value = {'id': '12345'}
            store_response.raise_for_status.return_value = None
            
            # Mock export_clip to succeed
            export_response = Mock()
            export_response.raise_for_status.return_value = None
            
            # Mock poll to fail
            poll_response = Mock()
            poll_response.json.return_value = {'files': []}
            poll_response.raise_for_status.return_value = None
            
            mock_session.post.return_value = store_response
            mock_session.get.return_value = poll_response
            
            extractor = AudioExtractor(sample_config)
            
            start_time = datetime(2025, 1, 1, 10, 0, 0)
            end_time = datetime(2025, 1, 1, 11, 0, 0)
            
            with patch('time.sleep'):  # Speed up test
                with pytest.raises(AudioExtractionError, match="Export failed"):
                    extractor.extract_audio(start_time, end_time, "/tmp/output")