"""
Tests for custom exceptions.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from exceptions import (
    TVAudioMonitorError, ConfigurationError, AudioExtractionError,
    TranscriptionError, OverlapDetectionError, ReportGenerationError,
    APIConnectionError, FileOperationError, ValidationError,
    RetryableError, NetworkError, TemporaryServiceError
)


class TestExceptionHierarchy:
    """Test exception hierarchy and inheritance."""
    
    def test_base_exception(self):
        """Test base TVAudioMonitorError."""
        error = TVAudioMonitorError("Base error")
        assert str(error) == "Base error"
        assert isinstance(error, Exception)
    
    def test_configuration_error(self):
        """Test ConfigurationError inheritance."""
        error = ConfigurationError("Config error")
        assert isinstance(error, TVAudioMonitorError)
        assert isinstance(error, Exception)
    
    def test_audio_extraction_error(self):
        """Test AudioExtractionError inheritance."""
        error = AudioExtractionError("Extraction error")
        assert isinstance(error, TVAudioMonitorError)
        assert isinstance(error, Exception)
    
    def test_transcription_error(self):
        """Test TranscriptionError inheritance."""
        error = TranscriptionError("Transcription error")
        assert isinstance(error, TVAudioMonitorError)
        assert isinstance(error, Exception)
    
    def test_overlap_detection_error(self):
        """Test OverlapDetectionError inheritance."""
        error = OverlapDetectionError("Overlap error")
        assert isinstance(error, TVAudioMonitorError)
        assert isinstance(error, Exception)
    
    def test_report_generation_error(self):
        """Test ReportGenerationError inheritance."""
        error = ReportGenerationError("Report error")
        assert isinstance(error, TVAudioMonitorError)
        assert isinstance(error, Exception)
    
    def test_api_connection_error(self):
        """Test APIConnectionError inheritance."""
        error = APIConnectionError("API error")
        assert isinstance(error, TVAudioMonitorError)
        assert isinstance(error, Exception)
    
    def test_file_operation_error(self):
        """Test FileOperationError inheritance."""
        error = FileOperationError("File error")
        assert isinstance(error, TVAudioMonitorError)
        assert isinstance(error, Exception)
    
    def test_validation_error(self):
        """Test ValidationError inheritance."""
        error = ValidationError("Validation error")
        assert isinstance(error, TVAudioMonitorError)
        assert isinstance(error, Exception)


class TestRetryableExceptions:
    """Test retryable exception hierarchy."""
    
    def test_retryable_error_base(self):
        """Test RetryableError base class."""
        error = RetryableError("Retryable error")
        assert isinstance(error, TVAudioMonitorError)
        assert isinstance(error, Exception)
    
    def test_network_error(self):
        """Test NetworkError inheritance."""
        error = NetworkError("Network error")
        assert isinstance(error, RetryableError)
        assert isinstance(error, TVAudioMonitorError)
        assert isinstance(error, Exception)
    
    def test_temporary_service_error(self):
        """Test TemporaryServiceError inheritance."""
        error = TemporaryServiceError("Service error")
        assert isinstance(error, RetryableError)
        assert isinstance(error, TVAudioMonitorError)
        assert isinstance(error, Exception)


class TestExceptionMessages:
    """Test exception message handling."""
    
    def test_exception_with_message(self):
        """Test exception with custom message."""
        message = "Custom error message"
        error = ConfigurationError(message)
        assert str(error) == message
    
    def test_exception_without_message(self):
        """Test exception without message."""
        error = ConfigurationError()
        assert str(error) == ""
    
    def test_exception_with_cause(self):
        """Test exception chaining."""
        original_error = ValueError("Original error")
        
        try:
            try:
                raise original_error
            except ValueError as e:
                raise ConfigurationError("Wrapped error") from e
        except ConfigurationError as chained_error:
            assert chained_error.__cause__ is original_error


class TestExceptionUsage:
    """Test practical exception usage scenarios."""
    
    def test_catching_specific_exception(self):
        """Test catching specific exception types."""
        def function_that_raises_config_error():
            raise ConfigurationError("Config problem")
        
        with pytest.raises(ConfigurationError) as exc_info:
            function_that_raises_config_error()
        
        assert "Config problem" in str(exc_info.value)
    
    def test_catching_base_exception(self):
        """Test catching base exception type."""
        def function_that_raises_specific_error():
            raise AudioExtractionError("Extraction problem")
        
        with pytest.raises(TVAudioMonitorError) as exc_info:
            function_that_raises_specific_error()
        
        assert isinstance(exc_info.value, AudioExtractionError)
    
    def test_catching_retryable_exceptions(self):
        """Test catching retryable exception types."""
        def function_that_raises_network_error():
            raise NetworkError("Network problem")
        
        with pytest.raises(RetryableError) as exc_info:
            function_that_raises_network_error()
        
        assert isinstance(exc_info.value, NetworkError)
    
    def test_exception_in_try_except_chain(self):
        """Test exception handling in try-except chains."""
        def process_with_multiple_error_types():
            try:
                # Simulate configuration loading
                raise FileNotFoundError("Config file missing")
            except FileNotFoundError as e:
                raise ConfigurationError("Failed to load config") from e
        
        with pytest.raises(ConfigurationError) as exc_info:
            process_with_multiple_error_types()
        
        assert isinstance(exc_info.value.__cause__, FileNotFoundError)


if __name__ == "__main__":
    pytest.main([__file__])