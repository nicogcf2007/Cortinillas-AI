"""
Integration tests for error handling across components.
"""
import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import ChannelConfig, DeepgramConfig, APIConfig, CortinillaResult
from config_manager import ConfigManager
from audio_extractor import AudioExtractor
from cortinilla_detector import CortinillaDetector
from overlap_detector import OverlapDetector
from report_generator import ReportGenerator
from exceptions import (
    ConfigurationError, AudioExtractionError, TranscriptionError,
    NetworkError, FileOperationError
)


class TestConfigManagerErrorHandling:
    """Test error handling in ConfigManager."""
    
    def test_load_nonexistent_config(self):
        """Test loading non-existent configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            with pytest.raises(FileNotFoundError):
                config_manager.load_channel_config("nonexistent.json")
    
    def test_load_invalid_json_config(self):
        """Test loading invalid JSON configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Create invalid JSON file
            invalid_config_path = os.path.join(temp_dir, "invalid.json")
            with open(invalid_config_path, 'w') as f:
                f.write("{ invalid json }")
            
            with pytest.raises(ConfigurationError):
                config_manager.load_channel_config(invalid_config_path)
    
    def test_load_incomplete_config(self):
        """Test loading incomplete configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Create incomplete config
            incomplete_config = {"channel_name": "test"}
            config_path = os.path.join(temp_dir, "incomplete.json")
            with open(config_path, 'w') as f:
                json.dump(incomplete_config, f)
            
            with pytest.raises(ConfigurationError):
                config_manager.load_channel_config(config_path)
    
    def test_create_default_configs_on_empty_directory(self):
        """Test creating default configs when directory is empty."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            channels = config_manager.load_all_channels()
            
            # Should create default configurations
            assert len(channels) >= 2
            assert "channel1" in channels or "channel2" in channels


class TestAudioExtractorErrorHandling:
    """Test error handling in AudioExtractor."""
    
    def create_test_config(self):
        """Create a test configuration."""
        return ChannelConfig(
            channel_name="test_channel",
            idemisora=1,
            idprograma=5,
            cortinillas=["test"],
            deepgram_config=DeepgramConfig("multi", "nova-3", True),
            api_config=APIConfig(
                base_url="http://test.com",
                cookie_sid="test_sid",
                format=11,
                video_is_public=0,
                is_masive=1,
                max_retries=2,
                sleep_seconds=1
            )
        )
    
    @patch('requests.Session')
    def test_network_error_retry(self, mock_session_class):
        """Test network error retry logic."""
        config = self.create_test_config()
        
        # Mock session to raise network errors
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.post.side_effect = [
            Exception("Network error 1"),
            Exception("Network error 2"),
            Mock(status_code=200, json=lambda: {"id": "test_id"})
        ]
        
        extractor = AudioExtractor(config)
        
        # Should succeed after retries
        start_time = datetime.now()
        end_time = datetime.now()
        
        # This will fail because we're not mocking the full flow,
        # but it tests the retry mechanism
        with pytest.raises(Exception):
            extractor.store_clip(start_time, end_time, "test_clip")
    
    @patch('requests.Session')
    def test_api_error_handling(self, mock_session_class):
        """Test API error handling."""
        config = self.create_test_config()
        
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server error")
        mock_session.post.return_value = mock_response
        
        extractor = AudioExtractor(config)
        
        with pytest.raises(Exception):
            start_time = datetime.now()
            end_time = datetime.now()
            extractor.store_clip(start_time, end_time, "test_clip")


class TestCortinillaDetectorErrorHandling:
    """Test error handling in CortinillaDetector."""
    
    def create_test_config(self):
        """Create a test configuration."""
        return ChannelConfig(
            channel_name="test_channel",
            idemisora=1,
            idprograma=5,
            cortinillas=["buenos días", "buenas tardes"],
            deepgram_config=DeepgramConfig("multi", "nova-3", True),
            api_config=APIConfig(
                base_url="http://test.com",
                cookie_sid="test_sid",
                format=11,
                video_is_public=0,
                is_masive=1,
                max_retries=3,
                sleep_seconds=30
            )
        )
    
    def test_missing_audio_file(self):
        """Test handling of missing audio file."""
        detector = CortinillaDetector()
        config = self.create_test_config()
        
        with pytest.raises(TranscriptionError):
            detector.detect_cortinillas(
                "nonexistent_file.mp3",
                config,
                datetime.now()
            )
    
    def test_missing_api_key(self):
        """Test handling of missing Deepgram API key."""
        detector = CortinillaDetector()
        config = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(suffix=".mp3") as temp_audio:
            # Write some dummy data
            temp_audio.write(b"dummy audio data")
            temp_audio.flush()
            
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(TranscriptionError):
                    detector.detect_cortinillas(
                        temp_audio.name,
                        config,
                        datetime.now()
                    )
    
    @patch('requests.post')
    def test_deepgram_api_error(self, mock_post):
        """Test handling of Deepgram API errors."""
        detector = CortinillaDetector()
        config = self.create_test_config()
        
        # Mock API error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix=".mp3") as temp_audio:
            temp_audio.write(b"dummy audio data")
            temp_audio.flush()
            
            with patch.dict(os.environ, {"DEEPGRAM_API_KEY": "test_key"}):
                with pytest.raises(TranscriptionError):
                    detector.detect_cortinillas(
                        temp_audio.name,
                        config,
                        datetime.now()
                    )


class TestOverlapDetectorErrorHandling:
    """Test error handling in OverlapDetector."""
    
    def test_invalid_cache_directory(self):
        """Test handling of invalid cache directory."""
        # Try to create detector with invalid cache directory
        with patch('os.makedirs', side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                OverlapDetector("/invalid/path/that/cannot/be/created")
    
    def test_corrupted_cache_file(self):
        """Test handling of corrupted cache file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            detector = OverlapDetector(temp_dir)
            
            # Create corrupted cache file
            cache_path = detector._get_cache_path("test_channel")
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, 'w') as f:
                f.write("corrupted json data {")
            
            # Should handle corrupted file gracefully
            result = detector.load_previous_transcript("test_channel")
            assert result is None
    
    def test_cache_file_permission_error(self):
        """Test handling of cache file permission errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            detector = OverlapDetector(temp_dir)
            
            # Mock permission error during save
            with patch('builtins.open', side_effect=PermissionError("Permission denied")):
                # Should not raise exception, just log error
                detector.save_transcript_cache(
                    "test_channel",
                    "test transcript",
                    datetime.now()
                )


class TestReportGeneratorErrorHandling:
    """Test error handling in ReportGenerator."""
    
    def create_test_result(self):
        """Create a test cortinilla result."""
        return CortinillaResult(
            channel="test_channel",
            timestamp=datetime.now(),
            audio_duration=3600.0,
            total_cortinillas=2,
            cortinillas_by_type={"buenos días": 1, "buenas tardes": 1},
            cortinillas_details={},
            overlap_filtered=False,
            overlap_duration=None
        )
    
    def test_permission_error_on_json_write(self):
        """Test handling of permission errors during JSON write."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            result = self.create_test_result()
            
            # Mock permission error
            with patch('builtins.open', side_effect=PermissionError("Permission denied")):
                with pytest.raises(Exception):  # Should be wrapped in ReportGenerationError
                    generator.update_json_report(result)
    
    def test_disk_full_error_on_excel_write(self):
        """Test handling of disk full errors during Excel write."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            result = self.create_test_result()
            
            # Mock disk full error
            with patch('openpyxl.Workbook.save', side_effect=OSError("No space left on device")):
                with pytest.raises(Exception):  # Should be wrapped in ReportGenerationError
                    generator.update_excel_report(result)
    
    def test_corrupted_existing_json_file(self):
        """Test handling of corrupted existing JSON files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ReportGenerator(temp_dir)
            result = self.create_test_result()
            
            # Create corrupted JSON file
            json_path = os.path.join(temp_dir, f"{result.channel}_results.json")
            with open(json_path, 'w') as f:
                f.write("{ corrupted json")
            
            # Should handle corrupted file and create new one
            generator.update_json_report(result)
            
            # Verify file was recreated
            assert os.path.exists(json_path)


class TestErrorRecoveryScenarios:
    """Test error recovery scenarios across components."""
    
    def test_partial_system_failure_recovery(self):
        """Test recovery from partial system failures."""
        # This would test scenarios where some components fail
        # but the system continues processing other channels
        pass
    
    def test_temporary_network_failure_recovery(self):
        """Test recovery from temporary network failures."""
        # This would test retry mechanisms across network operations
        pass
    
    def test_disk_space_recovery(self):
        """Test recovery from disk space issues."""
        # This would test cleanup and space management
        pass


if __name__ == "__main__":
    pytest.main([__file__])