"""
Custom exceptions for the Cortinillas AI system.
Provides specific exception types for different error scenarios.
"""


class CortinillasAIError(Exception):
    """Base exception for Cortinillas AI system."""
    pass


class ConfigurationError(TVAudioMonitorError):
    """Raised when configuration is invalid or missing."""
    pass


class AudioExtractionError(TVAudioMonitorError):
    """Raised when audio extraction fails."""
    pass


class TranscriptionError(TVAudioMonitorError):
    """Raised when audio transcription fails."""
    pass


class OverlapDetectionError(TVAudioMonitorError):
    """Raised when overlap detection fails."""
    pass


class ReportGenerationError(TVAudioMonitorError):
    """Raised when report generation fails."""
    pass


class APIConnectionError(TVAudioMonitorError):
    """Raised when API connection fails."""
    pass


class FileOperationError(TVAudioMonitorError):
    """Raised when file operations fail."""
    pass


class ValidationError(TVAudioMonitorError):
    """Raised when data validation fails."""
    pass


class RetryableError(TVAudioMonitorError):
    """Base class for errors that can be retried."""
    pass


class NetworkError(RetryableError):
    """Raised when network operations fail."""
    pass


class TemporaryServiceError(RetryableError):
    """Raised when external services are temporarily unavailable."""
    pass