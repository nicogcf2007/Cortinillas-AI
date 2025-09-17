"""
Centralized error handling and recovery mechanisms for Cortinillas AI.
Provides retry logic, error categorization, and recovery strategies.
"""
import functools
import logging
import time
import traceback
from typing import Any, Callable, Optional, Type, Union, List
from datetime import datetime

try:
    from .exceptions import (
        TVAudioMonitorError, RetryableError, NetworkError, 
        TemporaryServiceError, APIConnectionError
    )
except ImportError:
    from exceptions import (
        TVAudioMonitorError, RetryableError, NetworkError, 
        TemporaryServiceError, APIConnectionError
    )


logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling and recovery for Cortinillas AI."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """
        Initialize error handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.error_counts = {}
        self.last_errors = {}
    
    def retry_on_error(
        self,
        retryable_exceptions: Union[Type[Exception], tuple] = (RetryableError,),
        max_retries: Optional[int] = None,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0
    ):
        """
        Decorator for retrying functions on specific exceptions.
        
        Args:
            retryable_exceptions: Exception types that should trigger retries
            max_retries: Maximum retry attempts (uses instance default if None)
            backoff_factor: Exponential backoff multiplier
            max_delay: Maximum delay between retries
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        result = func(*args, **kwargs)
                        
                        # Reset error count on success
                        func_name = f"{func.__module__}.{func.__name__}"
                        if func_name in self.error_counts:
                            del self.error_counts[func_name]
                        
                        return result
                        
                    except retryable_exceptions as e:
                        last_exception = e
                        func_name = f"{func.__module__}.{func.__name__}"
                        
                        # Track error count
                        self.error_counts[func_name] = self.error_counts.get(func_name, 0) + 1
                        self.last_errors[func_name] = {
                            'error': str(e),
                            'timestamp': datetime.now(),
                            'attempt': attempt + 1
                        }
                        
                        if attempt < max_retries:
                            delay = min(
                                self.base_delay * (backoff_factor ** attempt),
                                max_delay
                            )
                            
                            logger.warning(
                                f"Attempt {attempt + 1}/{max_retries + 1} failed for {func_name}: {e}. "
                                f"Retrying in {delay:.2f} seconds..."
                            )
                            time.sleep(delay)
                        else:
                            logger.error(
                                f"All {max_retries + 1} attempts failed for {func_name}. "
                                f"Final error: {e}"
                            )
                    
                    except Exception as e:
                        # Non-retryable exception
                        func_name = f"{func.__module__}.{func.__name__}"
                        logger.error(f"Non-retryable error in {func_name}: {e}")
                        logger.error(traceback.format_exc())
                        raise
                
                # All retries exhausted
                raise last_exception
            
            return wrapper
        return decorator
    
    def handle_error(
        self,
        error: Exception,
        context: str,
        critical: bool = False,
        notify: bool = False
    ) -> None:
        """
        Handle and log errors with appropriate severity and context.
        
        Args:
            error: The exception that occurred
            context: Context description for the error
            critical: Whether this is a critical error
            notify: Whether to send notifications (placeholder for future)
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Log with appropriate level
        if critical:
            logger.critical(f"CRITICAL ERROR in {context}: {error_type}: {error_msg}")
            logger.critical(traceback.format_exc())
        else:
            logger.error(f"ERROR in {context}: {error_type}: {error_msg}")
            logger.debug(traceback.format_exc())
        
        # Track error statistics
        self.error_counts[context] = self.error_counts.get(context, 0) + 1
        self.last_errors[context] = {
            'error_type': error_type,
            'error_message': error_msg,
            'timestamp': datetime.now(),
            'critical': critical
        }
        
        # Future: Send notifications if notify=True
        if notify:
            self._send_error_notification(error, context, critical)
    
    def get_error_summary(self) -> dict:
        """
        Get summary of errors encountered.
        
        Returns:
            Dictionary with error statistics
        """
        return {
            'error_counts': self.error_counts.copy(),
            'last_errors': self.last_errors.copy(),
            'total_errors': sum(self.error_counts.values())
        }
    
    def reset_error_tracking(self) -> None:
        """Reset error tracking counters."""
        self.error_counts.clear()
        self.last_errors.clear()
        logger.info("Error tracking counters reset")
    
    def _send_error_notification(self, error: Exception, context: str, critical: bool) -> None:
        """
        Send error notification (placeholder for future implementation).
        
        Args:
            error: The exception that occurred
            context: Context description
            critical: Whether this is a critical error
        """
        # Placeholder for future notification system
        # Could send emails, Slack messages, etc.
        logger.info(f"Notification placeholder: {context} - {type(error).__name__}")


def safe_execute(
    func: Callable,
    *args,
    default_return: Any = None,
    error_handler: Optional[ErrorHandler] = None,
    context: str = "unknown",
    **kwargs
) -> Any:
    """
    Safely execute a function with error handling.
    
    Args:
        func: Function to execute
        *args: Positional arguments for the function
        default_return: Value to return if function fails
        error_handler: ErrorHandler instance to use
        context: Context description for error logging
        **kwargs: Keyword arguments for the function
    
    Returns:
        Function result or default_return if function fails
    """
    if error_handler is None:
        error_handler = ErrorHandler()
    
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_handler.handle_error(e, context)
        return default_return


def categorize_error(error: Exception) -> str:
    """
    Categorize an error for appropriate handling.
    
    Args:
        error: Exception to categorize
    
    Returns:
        Error category string
    """
    import requests
    
    if isinstance(error, (ConnectionError, requests.ConnectionError)):
        return "network"
    elif isinstance(error, (TimeoutError, requests.Timeout)):
        return "timeout"
    elif isinstance(error, FileNotFoundError):
        return "file_not_found"
    elif isinstance(error, PermissionError):
        return "permission"
    elif isinstance(error, (ValueError, TypeError)):
        return "validation"
    elif isinstance(error, KeyError):
        return "missing_data"
    elif isinstance(error, TVAudioMonitorError):
        return "application"
    else:
        return "unknown"


def create_error_context(
    operation: str,
    channel: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    additional_info: Optional[dict] = None
) -> str:
    """
    Create a standardized error context string.
    
    Args:
        operation: Operation being performed
        channel: Channel being processed (if applicable)
        timestamp: Timestamp of operation (if applicable)
        additional_info: Additional context information
    
    Returns:
        Formatted context string
    """
    context_parts = [operation]
    
    if channel:
        context_parts.append(f"channel={channel}")
    
    if timestamp:
        context_parts.append(f"time={timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if additional_info:
        for key, value in additional_info.items():
            context_parts.append(f"{key}={value}")
    
    return " | ".join(context_parts)


# Global error handler instance
global_error_handler = ErrorHandler()