"""
Tests for error handling and recovery mechanisms.
"""
import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from error_handler import ErrorHandler, safe_execute, categorize_error, create_error_context
from exceptions import (
    TVAudioMonitorError, RetryableError, NetworkError, 
    TemporaryServiceError, APIConnectionError
)


class TestErrorHandler:
    """Test cases for ErrorHandler class."""
    
    def test_initialization(self):
        """Test ErrorHandler initialization."""
        handler = ErrorHandler(max_retries=5, base_delay=2.0)
        assert handler.max_retries == 5
        assert handler.base_delay == 2.0
        assert handler.error_counts == {}
        assert handler.last_errors == {}
    
    def test_retry_decorator_success(self):
        """Test retry decorator with successful function."""
        handler = ErrorHandler(max_retries=3)
        
        @handler.retry_on_error()
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
    
    def test_retry_decorator_with_retryable_error(self):
        """Test retry decorator with retryable errors."""
        handler = ErrorHandler(max_retries=2, base_delay=0.1)
        call_count = 0
        
        @handler.retry_on_error(retryable_exceptions=(NetworkError,))
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Network failure")
            return "success"
        
        result = failing_function()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_decorator_exhausted_retries(self):
        """Test retry decorator when all retries are exhausted."""
        handler = ErrorHandler(max_retries=2, base_delay=0.1)
        
        @handler.retry_on_error(retryable_exceptions=(NetworkError,))
        def always_failing_function():
            raise NetworkError("Persistent network failure")
        
        with pytest.raises(NetworkError):
            always_failing_function()
    
    def test_retry_decorator_non_retryable_error(self):
        """Test retry decorator with non-retryable errors."""
        handler = ErrorHandler(max_retries=3)
        
        @handler.retry_on_error(retryable_exceptions=(NetworkError,))
        def function_with_non_retryable_error():
            raise ValueError("Non-retryable error")
        
        with pytest.raises(ValueError):
            function_with_non_retryable_error()
    
    def test_handle_error(self):
        """Test error handling and tracking."""
        handler = ErrorHandler()
        error = NetworkError("Test error")
        context = "test_context"
        
        handler.handle_error(error, context)
        
        assert context in handler.error_counts
        assert handler.error_counts[context] == 1
        assert context in handler.last_errors
        assert handler.last_errors[context]['error_type'] == 'NetworkError'
    
    def test_get_error_summary(self):
        """Test error summary generation."""
        handler = ErrorHandler()
        
        # Add some errors
        handler.handle_error(NetworkError("Error 1"), "context1")
        handler.handle_error(APIConnectionError("Error 2"), "context2")
        handler.handle_error(NetworkError("Error 3"), "context1")
        
        summary = handler.get_error_summary()
        
        assert summary['total_errors'] == 3
        assert summary['error_counts']['context1'] == 2
        assert summary['error_counts']['context2'] == 1
        assert len(summary['last_errors']) == 2
    
    def test_reset_error_tracking(self):
        """Test error tracking reset."""
        handler = ErrorHandler()
        
        # Add some errors
        handler.handle_error(NetworkError("Error"), "context")
        assert len(handler.error_counts) > 0
        
        # Reset
        handler.reset_error_tracking()
        assert len(handler.error_counts) == 0
        assert len(handler.last_errors) == 0


class TestSafeExecute:
    """Test cases for safe_execute function."""
    
    def test_safe_execute_success(self):
        """Test safe_execute with successful function."""
        def successful_function(x, y):
            return x + y
        
        result = safe_execute(successful_function, 2, 3)
        assert result == 5
    
    def test_safe_execute_with_error(self):
        """Test safe_execute with error and default return."""
        def failing_function():
            raise ValueError("Test error")
        
        result = safe_execute(failing_function, default_return="default")
        assert result == "default"
    
    def test_safe_execute_with_custom_error_handler(self):
        """Test safe_execute with custom error handler."""
        handler = ErrorHandler()
        
        def failing_function():
            raise NetworkError("Test error")
        
        result = safe_execute(
            failing_function,
            default_return="default",
            error_handler=handler,
            context="test_context"
        )
        
        assert result == "default"
        assert "test_context" in handler.error_counts


class TestErrorCategorization:
    """Test cases for error categorization."""
    
    def test_categorize_network_errors(self):
        """Test categorization of network errors."""
        import requests
        
        assert categorize_error(ConnectionError()) == "network"
        assert categorize_error(requests.ConnectionError()) == "network"
    
    def test_categorize_timeout_errors(self):
        """Test categorization of timeout errors."""
        import requests
        
        assert categorize_error(TimeoutError()) == "timeout"
        assert categorize_error(requests.Timeout()) == "timeout"
    
    def test_categorize_file_errors(self):
        """Test categorization of file errors."""
        assert categorize_error(FileNotFoundError()) == "file_not_found"
        assert categorize_error(PermissionError()) == "permission"
    
    def test_categorize_validation_errors(self):
        """Test categorization of validation errors."""
        assert categorize_error(ValueError()) == "validation"
        assert categorize_error(TypeError()) == "validation"
        assert categorize_error(KeyError()) == "missing_data"
    
    def test_categorize_application_errors(self):
        """Test categorization of application errors."""
        assert categorize_error(TVAudioMonitorError()) == "application"
        assert categorize_error(NetworkError()) == "application"
    
    def test_categorize_unknown_errors(self):
        """Test categorization of unknown errors."""
        assert categorize_error(RuntimeError()) == "unknown"


class TestErrorContext:
    """Test cases for error context creation."""
    
    def test_create_basic_context(self):
        """Test basic error context creation."""
        context = create_error_context("test_operation")
        assert context == "test_operation"
    
    def test_create_context_with_channel(self):
        """Test error context with channel."""
        context = create_error_context("test_operation", channel="channel1")
        assert context == "test_operation | channel=channel1"
    
    def test_create_context_with_timestamp(self):
        """Test error context with timestamp."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        context = create_error_context("test_operation", timestamp=timestamp)
        assert context == "test_operation | time=2023-01-01 12:00:00"
    
    def test_create_context_with_additional_info(self):
        """Test error context with additional information."""
        additional_info = {"file": "test.mp3", "size": "10MB"}
        context = create_error_context(
            "test_operation",
            additional_info=additional_info
        )
        assert "test_operation" in context
        assert "file=test.mp3" in context
        assert "size=10MB" in context
    
    def test_create_full_context(self):
        """Test error context with all parameters."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        additional_info = {"file": "test.mp3"}
        
        context = create_error_context(
            "test_operation",
            channel="channel1",
            timestamp=timestamp,
            additional_info=additional_info
        )
        
        assert "test_operation" in context
        assert "channel=channel1" in context
        assert "time=2023-01-01 12:00:00" in context
        assert "file=test.mp3" in context


class TestRetryLogic:
    """Test cases for retry logic and backoff."""
    
    def test_exponential_backoff(self):
        """Test exponential backoff timing."""
        handler = ErrorHandler(max_retries=3, base_delay=0.1)
        call_times = []
        
        @handler.retry_on_error(
            retryable_exceptions=(NetworkError,),
            backoff_factor=2.0
        )
        def failing_function():
            call_times.append(time.time())
            raise NetworkError("Test error")
        
        start_time = time.time()
        
        with pytest.raises(NetworkError):
            failing_function()
        
        # Check that delays increase exponentially
        assert len(call_times) == 4  # Initial call + 3 retries
        
        # Verify approximate timing (allowing for some variance)
        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            assert 0.08 <= delay1 <= 0.15  # ~0.1 seconds
        
        if len(call_times) >= 3:
            delay2 = call_times[2] - call_times[1]
            assert 0.18 <= delay2 <= 0.25  # ~0.2 seconds
    
    def test_max_delay_limit(self):
        """Test maximum delay limit."""
        handler = ErrorHandler(max_retries=2, base_delay=10.0)
        call_times = []
        
        @handler.retry_on_error(
            retryable_exceptions=(NetworkError,),
            max_delay=0.2  # Very low max delay
        )
        def failing_function():
            call_times.append(time.time())
            raise NetworkError("Test error")
        
        with pytest.raises(NetworkError):
            failing_function()
        
        # Check that delay doesn't exceed max_delay
        if len(call_times) >= 2:
            delay = call_times[1] - call_times[0]
            assert delay <= 0.25  # Should be capped at max_delay


if __name__ == "__main__":
    pytest.main([__file__])