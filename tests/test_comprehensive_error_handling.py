"""
Comprehensive end-to-end tests for error handling system.
"""
import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import CortinillasAI
from models import ChannelConfig, DeepgramConfig, APIConfig
from exceptions import ConfigurationError, AudioExtractionError


class TestComprehensiveErrorHandling:
    """Test comprehensive error handling across the entire system."""
    
    def create_test_config_file(self, temp_dir: str, channel_name: str) -> str:
        """Create a test configuration file."""
        config_data = {
            "channel_name": channel_name,
            "idemisora": 1,
            "idprograma": 5,
            "cortinillas": ["buenos días", "buenas tardes"],
            "deepgram_config": {
                "language": "multi",
                "model": "nova-3",
                "smart_format": True
            },
            "api_config": {
                "base_url": "http://test.com",
                "cookie_sid": "test_sid",
                "format": 11,
                "video_is_public": 0,
                "is_masive": 1,
                "max_retries": 2,
                "sleep_seconds": 1
            }
        }
        
        config_path = os.path.join(temp_dir, f"{channel_name}_config.json")
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        return config_path
    
    def test_system_resilience_with_partial_failures(self):
        """Test system resilience when some components fail."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = os.path.join(temp_dir, "config")
            data_dir = os.path.join(temp_dir, "data")
            temp_audio_dir = os.path.join(temp_dir, "temp")
            log_dir = os.path.join(temp_dir, "logs")
            
            os.makedirs(config_dir)
            
            # Create test configurations
            self.create_test_config_file(config_dir, "channel1")
            self.create_test_config_file(config_dir, "channel2")
            
            # Initialize monitor
            monitor = TVAudioMonitor(
                config_dir=config_dir,
                data_dir=data_dir,
                temp_dir=temp_audio_dir,
                log_dir=log_dir
            )
            
            # Test that monitor initializes correctly
            assert monitor.config_manager is not None
            assert monitor.error_handler is not None
            
            # Test configuration loading
            channels = monitor.load_channel_configurations()
            assert len(channels) >= 2
            
            # Test error summary functionality
            error_summary = monitor.get_error_summary()
            assert isinstance(error_summary, dict)
            assert 'total_errors' in error_summary
            
            # Close logger handlers to release file locks
            for handler in monitor.logger.handlers[:]:
                handler.close()
                monitor.logger.removeHandler(handler)
    
    def test_error_recovery_mechanisms(self):
        """Test error recovery mechanisms."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = os.path.join(temp_dir, "config")
            data_dir = os.path.join(temp_dir, "data")
            
            os.makedirs(config_dir)
            
            # Create a valid config
            self.create_test_config_file(config_dir, "channel1")
            
            # Create an invalid config to test error handling
            invalid_config_path = os.path.join(config_dir, "channel2_config.json")
            with open(invalid_config_path, 'w') as f:
                f.write("{ invalid json")
            
            monitor = TVAudioMonitor(config_dir=config_dir, data_dir=data_dir)
            
            # Should still load valid configurations despite invalid ones
            channels = monitor.load_channel_configurations()
            
            # Should have at least the valid channel
            assert len(channels) >= 1
            
            # Check error tracking
            error_summary = monitor.get_error_summary()
            # May have errors from trying to load invalid config
            assert isinstance(error_summary['total_errors'], int)
            
            # Close logger handlers
            for handler in monitor.logger.handlers[:]:
                handler.close()
                monitor.logger.removeHandler(handler)
    
    def test_logging_and_error_reporting(self):
        """Test comprehensive logging and error reporting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = os.path.join(temp_dir, "config")
            data_dir = os.path.join(temp_dir, "data")
            log_dir = os.path.join(temp_dir, "logs")
            
            os.makedirs(config_dir)
            
            # Create test config
            self.create_test_config_file(config_dir, "test_channel")
            
            monitor = TVAudioMonitor(
                config_dir=config_dir,
                data_dir=data_dir,
                log_dir=log_dir
            )
            
            # Test that logger is properly configured
            assert monitor.logger is not None
            
            # Test error summary logging
            monitor.log_final_summary(True)
            monitor.log_final_summary(False)
            
            # Check that log file was created
            log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
            assert len(log_files) > 0
            
            # Close logger handlers
            for handler in monitor.logger.handlers[:]:
                handler.close()
                monitor.logger.removeHandler(handler)
    
    def test_environment_validation_with_errors(self):
        """Test environment validation with various error conditions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = os.path.join(temp_dir, "config")
            data_dir = os.path.join(temp_dir, "data")
            
            # Don't create config directory to test error handling
            monitor = TVAudioMonitor(config_dir=config_dir, data_dir=data_dir)
            
            # Test validation without Deepgram API key
            with patch.dict(os.environ, {}, clear=True):
                is_valid = monitor.validate_environment()
                assert not is_valid
            
            # Test validation with API key but no configs
            with patch.dict(os.environ, {"DEEPGRAM_API_KEY": "test_key"}):
                is_valid = monitor.validate_environment()
                # Should create default configs and pass validation
                assert is_valid
            
            # Close logger handlers
            for handler in monitor.logger.handlers[:]:
                handler.close()
                monitor.logger.removeHandler(handler)
    
    @patch('src.audio_extractor.AudioExtractor')
    @patch('src.cortinilla_detector.CortinillaDetector')
    def test_processing_with_component_failures(self, mock_detector, mock_extractor):
        """Test processing workflow with component failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = os.path.join(temp_dir, "config")
            data_dir = os.path.join(temp_dir, "data")
            
            os.makedirs(config_dir)
            self.create_test_config_file(config_dir, "test_channel")
            
            # Mock audio extractor to fail
            mock_extractor_instance = Mock()
            mock_extractor_instance.__enter__ = Mock(return_value=mock_extractor_instance)
            mock_extractor_instance.__exit__ = Mock(return_value=None)
            mock_extractor_instance.extract_audio.side_effect = Exception("Audio extraction failed")
            mock_extractor.return_value = mock_extractor_instance
            
            monitor = TVAudioMonitor(config_dir=config_dir, data_dir=data_dir)
            
            # Load configurations
            channels = monitor.load_channel_configurations()
            assert len(channels) > 0
            
            # Test audio extraction with failure
            config = list(channels.values())[0]
            start_time = datetime.now()
            end_time = datetime.now()
            
            audio_path = monitor.extract_channel_audio(config, start_time, end_time)
            assert audio_path is None  # Should handle failure gracefully
            
            # Check that error was tracked
            error_summary = monitor.get_error_summary()
            assert error_summary['total_errors'] > 0
            
            # Close logger handlers
            for handler in monitor.logger.handlers[:]:
                handler.close()
                monitor.logger.removeHandler(handler)
    
    def test_cleanup_on_errors(self):
        """Test that cleanup occurs even when errors happen."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = os.path.join(temp_dir, "config")
            data_dir = os.path.join(temp_dir, "data")
            temp_audio_dir = os.path.join(temp_dir, "temp")
            
            os.makedirs(config_dir)
            self.create_test_config_file(config_dir, "test_channel")
            
            monitor = TVAudioMonitor(
                config_dir=config_dir,
                data_dir=data_dir,
                temp_dir=temp_audio_dir
            )
            
            # Add some fake temp files
            fake_file1 = os.path.join(temp_audio_dir, "fake1.mp3")
            fake_file2 = os.path.join(temp_audio_dir, "fake2.mp3")
            
            os.makedirs(temp_audio_dir, exist_ok=True)
            with open(fake_file1, 'w') as f:
                f.write("fake audio data")
            with open(fake_file2, 'w') as f:
                f.write("fake audio data")
            
            monitor.temp_files = [fake_file1, fake_file2]
            
            # Test cleanup
            monitor.cleanup_temp_files()
            
            # Files should be removed
            assert not os.path.exists(fake_file1)
            assert not os.path.exists(fake_file2)
            assert len(monitor.temp_files) == 0
            
            # Close logger handlers
            for handler in monitor.logger.handlers[:]:
                handler.close()
                monitor.logger.removeHandler(handler)
    
    def test_error_categorization_and_handling(self):
        """Test that different error types are handled appropriately."""
        with tempfile.TemporaryDirectory() as temp_dir:
            monitor = TVAudioMonitor(data_dir=temp_dir)
            
            # Test different error types
            from exceptions import NetworkError, ConfigurationError, ValidationError
            
            # Simulate different types of errors
            monitor.error_handler.handle_error(
                NetworkError("Network connection failed"),
                "test_network_operation"
            )
            
            monitor.error_handler.handle_error(
                ConfigurationError("Invalid configuration"),
                "test_config_operation"
            )
            
            monitor.error_handler.handle_error(
                ValidationError("Data validation failed"),
                "test_validation_operation"
            )
            
            # Check error summary
            error_summary = monitor.get_error_summary()
            assert error_summary['total_errors'] == 3
            assert len(error_summary['error_counts']) == 3
            assert len(error_summary['last_errors']) == 3
            
            # Close logger handlers
            for handler in monitor.logger.handlers[:]:
                handler.close()
                monitor.logger.removeHandler(handler)


if __name__ == "__main__":
    pytest.main([__file__])