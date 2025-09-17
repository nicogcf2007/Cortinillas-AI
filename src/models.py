"""
Data models for the Cortinillas_IA system.

This module defines the core data structures used throughout the system
for configuration, results, and data processing.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class DeepgramConfig:
    """Configuration for Deepgram speech-to-text service."""
    language: str = "multi"
    model: str = "nova-3"
    smart_format: bool = True


@dataclass
class APIConfig:
    """Configuration for TV API backend."""
    base_url: str
    cookie_sid: str
    format: int = 11
    video_is_public: int = 0
    is_masive: int = 1
    max_retries: int = 3
    sleep_seconds: int = 30


@dataclass
class ChannelConfig:
    """Configuration for a TV channel."""
    channel_name: str
    idemisora: int
    idprograma: int
    cortinillas: List[str]
    deepgram_config: DeepgramConfig
    api_config: APIConfig


@dataclass
class Occurrence:
    """Represents a single occurrence of a cortinilla in audio."""
    start_time: str
    end_time: str
    start_seconds: float
    end_seconds: float
    confidence: float = 1.0


@dataclass
class CortinillaResult:
    """Results of cortinilla detection for a specific phrase."""
    phrase: str
    occurrences: List[Occurrence]
    total_count: int = 0

    def __post_init__(self):
        self.total_count = len(self.occurrences)


@dataclass
class Word:
    """Represents a single word from transcription with timing."""
    word: str
    start: float
    end: float
    confidence: float = 1.0


@dataclass
class FilteredContent:
    """Content that has been filtered for overlaps."""
    original_words: List[Word]
    filtered_words: List[Word]
    removed_words: List[Word]
    similarity_score: float


@dataclass
class TranscriptionResult:
    """Results from Deepgram speech-to-text processing."""
    transcript: str
    confidence: float
    duration_seconds: float
    words: List[Dict[str, Any]]
    raw_response: Dict[str, Any]


@dataclass
class OverlapResult:
    """Results of overlap detection between audio segments."""
    has_overlap: bool
    similarity_score: float
    overlapping_content: str
    overlap_duration_seconds: float = 0.0


@dataclass
class ProcessingExecution:
    """Represents a single execution of the cortinilla detection process."""
    timestamp: str
    time_range: str
    audio_file_path: str
    audio_duration_seconds: float
    cortinillas_found: int
    cortinillas: Dict[str, List[Dict[str, Any]]]
    processing_time_seconds: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    overlap_filtered: bool = False
    overlap_duration: float = 0.0


@dataclass
class ClipParams:
    """Parameters for audio clip extraction."""
    start_time: str
    end_time: str
    format: int = 11
    video_is_public: int = 0
    is_masive: int = 1


@dataclass
class ExportStatus:
    """Status of audio export operation."""
    success: bool
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    is_ready: bool = False
    status: Optional[str] = None
    progress: Optional[float] = None


@dataclass
class CortinillaDetectionResult:
    """Results of cortinilla detection for a channel."""
    channel: str
    timestamp: datetime
    start_time: datetime
    end_time: datetime
    audio_duration: float
    total_cortinillas: int
    cortinillas_by_type: Dict[str, int]
    cortinillas_details: Dict[str, List[Occurrence]]
    overlap_filtered: bool = False
    overlap_duration: float = 0.0


@dataclass
class ProcessingResult:
    """Results of a complete processing execution."""
    channel_name: str
    success: bool
    execution_time_seconds: float
    cortinillas_found: int
    audio_file_path: Optional[str] = None
    error_message: Optional[str] = None
    cortinilla_results: List[CortinillaResult] = None
    
    def __post_init__(self):
        if self.cortinilla_results is None:
            self.cortinilla_results = []


@dataclass
class AccumulatedResults:
    """Accumulated results for a channel over time."""
    channel_name: str
    total_executions: int
    total_cortinillas_found: int
    last_execution: Optional[str]
    executions: List[ProcessingExecution]
    
    def __post_init__(self):
        if not self.executions:
            self.executions = []


@dataclass
class ChannelReport:
    """Complete report for a channel with historical data."""
    channel_name: str
    metadata: Dict[str, Any]
    executions: List[ProcessingExecution]
    
    def __post_init__(self):
        """Update metadata based on executions."""
        if not self.metadata:
            self.metadata = {}
        
        self.metadata.update({
            "total_executions": len(self.executions),
            "total_cortinillas_found": sum(exec.cortinillas_found for exec in self.executions),
            "last_execution": self.executions[-1].timestamp if self.executions else None,
            "success_rate": len([e for e in self.executions if e.success]) / len(self.executions) if self.executions else 0
        })


# Utility functions for model conversion
def occurrence_to_dict(occurrence: Occurrence) -> Dict[str, Any]:
    """Convert Occurrence to dictionary."""
    return {
        "start_time": occurrence.start_time,
        "end_time": occurrence.end_time,
        "start_seconds": occurrence.start_seconds,
        "end_seconds": occurrence.end_seconds,
        "confidence": occurrence.confidence
    }


def dict_to_occurrence(data: Dict[str, Any]) -> Occurrence:
    """Convert dictionary to Occurrence."""
    return Occurrence(
        start_time=data["start_time"],
        end_time=data["end_time"],
        start_seconds=data["start_seconds"],
        end_seconds=data["end_seconds"],
        confidence=data.get("confidence", 1.0)
    )


def cortinilla_result_to_dict(result: CortinillaResult) -> Dict[str, Any]:
    """Convert CortinillaResult to dictionary."""
    return {
        "phrase": result.phrase,
        "total_count": result.total_count,
        "occurrences": [occurrence_to_dict(occ) for occ in result.occurrences]
    }


def dict_to_cortinilla_result(data: Dict[str, Any]) -> CortinillaResult:
    """Convert dictionary to CortinillaResult."""
    occurrences = [dict_to_occurrence(occ) for occ in data.get("occurrences", [])]
    return CortinillaResult(
        phrase=data["phrase"],
        occurrences=occurrences,
        total_count=data.get("total_count", len(occurrences))
    )


def execution_to_dict(execution: ProcessingExecution) -> Dict[str, Any]:
    """Convert ProcessingExecution to dictionary."""
    return {
        "timestamp": execution.timestamp,
        "time_range": execution.time_range,
        "audio_file_path": execution.audio_file_path,
        "audio_duration_seconds": execution.audio_duration_seconds,
        "cortinillas_found": execution.cortinillas_found,
        "cortinillas": execution.cortinillas,
        "processing_time_seconds": execution.processing_time_seconds,
        "success": execution.success,
        "error_message": execution.error_message
    }


def dict_to_execution(data: Dict[str, Any]) -> ProcessingExecution:
    """Convert dictionary to ProcessingExecution."""
    return ProcessingExecution(
        timestamp=data["timestamp"],
        time_range=data["time_range"],
        audio_file_path=data["audio_file_path"],
        audio_duration_seconds=data["audio_duration_seconds"],
        cortinillas_found=data["cortinillas_found"],
        cortinillas=data["cortinillas"],
        processing_time_seconds=data.get("processing_time_seconds", 0.0),
        success=data.get("success", True),
        error_message=data.get("error_message")
    )


def channel_report_to_dict(report: ChannelReport) -> Dict[str, Any]:
    """Convert ChannelReport to dictionary."""
    return {
        "channel_name": report.channel_name,
        "metadata": report.metadata,
        "executions": [execution_to_dict(exec) for exec in report.executions]
    }


def dict_to_channel_report(data: Dict[str, Any]) -> ChannelReport:
    """Convert dictionary to ChannelReport."""
    executions = [dict_to_execution(exec) for exec in data.get("executions", [])]
    return ChannelReport(
        channel_name=data["channel_name"],
        metadata=data.get("metadata", {}),
        executions=executions
    )