"""
Cortinilla detection system for Cortinillas AI.

This module handles detection of predefined cortinillas (jingles/bumpers) in TV audio
using Deepgram API, with integration for channel-specific configurations and overlap filtering.
"""
import os
import re
import unicodedata
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime

import requests

try:
    from .models import (
        ChannelConfig, CortinillaResult, CortinillaDetectionResult, TranscriptionResult, Word, Occurrence,
        FilteredContent, OverlapResult
    )
    from .overlap_detector import OverlapDetector
    from .exceptions import TranscriptionError, NetworkError, ValidationError
    from .error_handler import ErrorHandler, create_error_context, safe_execute
except ImportError:
    from models import (
        ChannelConfig, CortinillaResult, CortinillaDetectionResult, TranscriptionResult, Word, Occurrence,
        FilteredContent, OverlapResult
    )
    from overlap_detector import OverlapDetector
    from exceptions import TranscriptionError, NetworkError, ValidationError
    from error_handler import ErrorHandler, create_error_context, safe_execute


logger = logging.getLogger(__name__)


class CortinillaDetector:
    """Detects predefined cortinillas in TV audio using Deepgram API."""
    
    def __init__(self, overlap_detector: Optional[OverlapDetector] = None):
        """
        Initialize the cortinilla detector.
        
        Args:
            overlap_detector: Optional overlap detector for filtering duplicate content
        """
        if overlap_detector is None:
            self.overlap_detector = OverlapDetector()
        else:
            self.overlap_detector = overlap_detector
        
        self.error_handler = ErrorHandler(max_retries=3, base_delay=2.0)
        logger.info("CortinillaDetector initialized")
    
    def detect_cortinillas(
        self, 
        audio_path: str, 
        channel_config: ChannelConfig,
        timestamp: datetime,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> CortinillaDetectionResult:
        """
        Detect cortinillas in audio file using channel-specific configuration.
        
        Args:
            audio_path: Path to the audio file
            channel_config: Channel configuration with cortinillas and API settings
            timestamp: Timestamp of the audio processing
            start_time: Start time of the audio fragment (optional)
            end_time: End time of the audio fragment (optional)
            
        Returns:
            CortinillaDetectionResult with detection results
        """
        context = create_error_context(
            "cortinilla_detection",
            channel=channel_config.channel_name,
            timestamp=timestamp,
            additional_info={"audio_file": os.path.basename(audio_path)}
        )
        
        logger.info(f"Starting cortinilla detection for channel {channel_config.channel_name}")
        
        try:
            # Validate inputs
            self._validate_inputs(audio_path, channel_config)
            
            # Get Deepgram API key from environment
            api_key = os.getenv("DEEPGRAM_API_KEY")
            if not api_key:
                raise ValidationError("DEEPGRAM_API_KEY environment variable not set")
            
            # Transcribe audio with error handling
            transcription_result = self._transcribe_with_error_handling(
                audio_path, channel_config, api_key
            )
            
            # Process with overlap detection if available
            filtered_content, overlap_result = safe_execute(
                self._process_with_overlap_filtering,
                channel_config.channel_name,
                transcription_result,
                timestamp,
                default_return=(
                    FilteredContent(
                        original_words=transcription_result.words,
                        filtered_words=transcription_result.words,
                        removed_words=[],
                        similarity_score=0.0
                    ),
                    OverlapResult(
                        has_overlap=False,
                        similarity_score=0.0,
                        overlapping_content="",
                        overlap_duration_seconds=0.0
                    )
                ),
                error_handler=self.error_handler,
                context=f"{context} | overlap_detection"
            )
            
            # Find cortinilla occurrences in filtered content
            cortinilla_occurrences = safe_execute(
                self.find_cortinilla_occurrences,
                channel_config.cortinillas,
                filtered_content.filtered_words,
                default_return={cortinilla: [] for cortinilla in channel_config.cortinillas},
                error_handler=self.error_handler,
                context=f"{context} | cortinilla_search"
            )
            
            # Calculate totals
            total_cortinillas = sum(len(occurrences) for occurrences in cortinilla_occurrences.values())
            cortinillas_by_type = {
                cortinilla: len(occurrences) 
                for cortinilla, occurrences in cortinilla_occurrences.items()
            }
            
            logger.info(f"Found {total_cortinillas} cortinillas for channel {channel_config.channel_name}")
            
            return CortinillaDetectionResult(
                channel=channel_config.channel_name,
                timestamp=timestamp,
                start_time=start_time or timestamp,
                end_time=end_time or timestamp,
                audio_duration=transcription_result.duration_seconds,
                total_cortinillas=total_cortinillas,
                cortinillas_by_type=cortinillas_by_type,
                cortinillas_details=cortinilla_occurrences,
                overlap_filtered=overlap_result.has_overlap,
                overlap_duration=overlap_result.overlap_duration_seconds
            )
            
        except Exception as e:
            self.error_handler.handle_error(e, context, critical=True)
            if isinstance(e, (TranscriptionError, ValidationError)):
                raise
            else:
                raise TranscriptionError(f"Cortinilla detection failed: {e}") from e
    
    def transcribe_audio(
        self, 
        audio_path: str, 
        channel_config: ChannelConfig,
        api_key: str
    ) -> TranscriptionResult:
        """
        Transcribe audio using Deepgram API with channel-specific configuration.
        
        Args:
            audio_path: Path to the audio file
            channel_config: Channel configuration with Deepgram settings
            api_key: Deepgram API key
            
        Returns:
            TranscriptionResult with transcript and word-level timing
        """
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"Transcribing audio: {os.path.basename(audio_path)}")
        
        # Prepare Deepgram API request
        url = "https://api.deepgram.com/v1/listen"
        
        params = {
            "model": channel_config.deepgram_config.model,
            "language": channel_config.deepgram_config.language,
            "punctuate": "true",
            "smart_format": "true" if channel_config.deepgram_config.smart_format else "false",
            "timestamps": "true",
            "utterances": "true",
        }
        
        # Determine MIME type
        mime_type = self._guess_mime_type(audio_path)
        
        headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": mime_type,
        }
        
        # Send audio to Deepgram with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(audio_path, "rb") as f:
                    data = f.read()
                
                logger.info(f"Sending audio to Deepgram (attempt {attempt + 1}/{max_retries})")
                response = requests.post(
                    url, 
                    params=params, 
                    headers=headers, 
                    data=data, 
                    timeout=600
                )
                
                if response.status_code >= 300:
                    error_msg = f"Deepgram API error {response.status_code}: {response.text[:1000]}"
                    if attempt == max_retries - 1:
                        raise RuntimeError(error_msg)
                    logger.warning(f"{error_msg} - Retrying...")
                    continue
                
                result_json = response.json()
                break
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Failed to connect to Deepgram after {max_retries} attempts: {e}")
                logger.warning(f"Request failed (attempt {attempt + 1}): {e} - Retrying...")
        
        # Extract transcript and words
        transcript = self._extract_transcript(result_json)
        words = self._extract_words(result_json)
        
        # Get duration
        duration = self._extract_duration(result_json, words)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(words)
        
        logger.info(f"Transcription completed: {len(words)} words, {duration:.2f}s duration")
        
        return TranscriptionResult(
            transcript=transcript,
            words=words,
            confidence=confidence,
            duration_seconds=duration,
            raw_response=response
        )
    
    def find_cortinilla_occurrences(
        self, 
        cortinillas: List[str], 
        words: List[Word]
    ) -> Dict[str, List[Occurrence]]:
        """
        Find occurrences of cortinillas in the word list using text alignment.
        
        Args:
            cortinillas: List of cortinilla phrases to search for
            words: List of words with timing information
            
        Returns:
            Dictionary mapping cortinilla phrases to their occurrences
        """
        logger.info(f"Searching for {len(cortinillas)} cortinillas in {len(words)} words")
        
        # Prepare normalized word sequence
        normalized_words = [self._normalize_text(word.word) for word in words]
        
        results: Dict[str, List[Occurrence]] = {cortinilla: [] for cortinilla in cortinillas}
        
        for cortinilla in cortinillas:
            pattern_tokens = self._tokenize(cortinilla)
            if not pattern_tokens:
                continue
            
            pattern_len = len(pattern_tokens)
            
            # Search for pattern in normalized words
            i = 0
            while i <= len(normalized_words) - pattern_len:
                window = normalized_words[i:i + pattern_len]
                
                if window == pattern_tokens:
                    # Found a match - get timing information
                    start_time = words[i].start
                    end_time = words[i + pattern_len - 1].end
                    
                    # Calculate confidence as average of word confidences
                    word_confidences = [words[j].confidence for j in range(i, i + pattern_len)]
                    avg_confidence = sum(word_confidences) / len(word_confidences)
                    
                    # Get original text
                    original_text = ' '.join([words[j].word for j in range(i, i + pattern_len)])
                    
                    # Format times as strings
                    start_time_str = f"{int(start_time//3600):02d}:{int((start_time%3600)//60):02d}:{int(start_time%60):02d}"
                    end_time_str = f"{int(end_time//3600):02d}:{int((end_time%3600)//60):02d}:{int(end_time%60):02d}"
                    
                    occurrence = Occurrence(
                        start_time=start_time_str,
                        end_time=end_time_str,
                        start_seconds=start_time,
                        end_seconds=end_time,
                        confidence=avg_confidence
                    )
                    
                    results[cortinilla].append(occurrence)
                    logger.debug(f"Found '{cortinilla}' at {start_time:.2f}s - {end_time:.2f}s")
                    
                    # Advance by pattern length to avoid overlapping matches
                    i += pattern_len
                else:
                    i += 1
        
        # Log results summary
        total_found = sum(len(occurrences) for occurrences in results.values())
        found_types = sum(1 for occurrences in results.values() if occurrences)
        logger.info(f"Found {total_found} total cortinillas ({found_types} different types)")
        
        return results
    
    def _process_with_overlap_filtering(
        self,
        channel: str,
        transcription_result: TranscriptionResult,
        timestamp: datetime
    ) -> Tuple[FilteredContent, OverlapResult]:
        """
        Process transcription with overlap detection and filtering.
        
        Args:
            channel: Channel identifier
            transcription_result: Transcription result to process
            timestamp: Processing timestamp
            
        Returns:
            Tuple of filtered content and overlap result
        """
        if self.overlap_detector is not None:
            return self.overlap_detector.process_with_overlap_detection(
                channel, transcription_result, timestamp
            )
        else:
            # No overlap detection - return original content
            filtered_content = FilteredContent(
                original_words=transcription_result.words,
                filtered_words=transcription_result.words,
                removed_words=[],
                similarity_score=0.0
            )
            overlap_result = OverlapResult(
                has_overlap=False,
                similarity_score=0.0,
                overlapping_content="",
                overlap_duration_seconds=0.0
            )
            return filtered_content, overlap_result
    
    def _guess_mime_type(self, path: str) -> str:
        """Guess MIME type for audio file."""
        import mimetypes
        guessed, _ = mimetypes.guess_type(path)
        
        # Common corrections
        if not guessed:
            return "audio/wav"
        if guessed == "audio/mp4":
            return "audio/mp4"
        return guessed
    
    def _extract_transcript(self, result_json: Dict) -> str:
        """Extract transcript text from Deepgram response."""
        try:
            return str(
                result_json["results"]["channels"][0]["alternatives"][0]["transcript"]
            )
        except (KeyError, IndexError):
            logger.warning("Could not extract transcript from Deepgram response")
            return ""
    
    def _extract_words(self, result_json: Dict) -> List[Word]:
        """Extract words with timing from Deepgram response."""
        try:
            words_data = result_json["results"]["channels"][0]["alternatives"][0]["words"]
        except (KeyError, IndexError):
            logger.warning("Could not extract words from Deepgram response")
            return []
        
        words = []
        for word_data in words_data or []:
            word = Word(
                word=str(word_data.get("word", "")),
                start=float(word_data.get("start", 0.0)),
                end=float(word_data.get("end", 0.0)),
                confidence=float(word_data.get("confidence", 0.0))
            )
            words.append(word)
        
        return words
    
    def _extract_duration(self, result_json: Dict, words: List[Word]) -> float:
        """Extract audio duration from Deepgram response or calculate from words."""
        try:
            duration = result_json.get("metadata", {}).get("duration")
            if duration is not None:
                return float(duration)
        except (ValueError, TypeError):
            pass
        
        # Fallback to last word end time
        if words:
            return words[-1].end
        return 0.0
    
    def _calculate_confidence(self, words: List[Word]) -> float:
        """Calculate overall confidence from word confidences."""
        if not words:
            return 0.0
        
        confidences = [word.confidence for word in words if word.confidence > 0]
        if not confidences:
            return 0.0
        
        return sum(confidences) / len(confidences)
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison (case-insensitive, accent-insensitive).
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Convert to lowercase
        lowered = text.lower()
        
        # Remove accents
        nfkd = unicodedata.normalize("NFD", lowered)
        no_accents = "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")
        
        # Replace non-alphanumeric characters with space
        normalized = re.sub(r"[^a-z0-9áéíóúñü]+", " ", no_accents)
        
        # Compact multiple spaces
        normalized = re.sub(r"\s+", " ", normalized).strip()
        
        return normalized
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into normalized words.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of normalized tokens
        """
        return [token for token in self._normalize_text(text).split(" ") if token]
    
    def _validate_inputs(self, audio_path: str, channel_config: ChannelConfig) -> None:
        """
        Validate inputs for cortinilla detection.
        
        Args:
            audio_path: Path to audio file
            channel_config: Channel configuration
            
        Raises:
            ValidationError: If inputs are invalid
        """
        if not os.path.isfile(audio_path):
            raise ValidationError(f"Audio file not found: {audio_path}")
        
        if not channel_config.cortinillas:
            raise ValidationError("No cortinillas defined in channel configuration")
        
        if not channel_config.deepgram_config:
            raise ValidationError("Deepgram configuration missing")
        
        # Check file size (reasonable limits)
        file_size = os.path.getsize(audio_path)
        max_size = 500 * 1024 * 1024  # 500MB
        if file_size > max_size:
            raise ValidationError(f"Audio file too large: {file_size} bytes (max: {max_size})")
        
        if file_size == 0:
            raise ValidationError("Audio file is empty")
    
    @ErrorHandler().retry_on_error(
        retryable_exceptions=(NetworkError, requests.RequestException),
        max_retries=3,
        backoff_factor=2.0
    )
    def _transcribe_with_error_handling(
        self, 
        audio_path: str, 
        channel_config: ChannelConfig,
        api_key: str
    ) -> TranscriptionResult:
        """
        Transcribe audio with comprehensive error handling.
        
        Args:
            audio_path: Path to audio file
            channel_config: Channel configuration
            api_key: Deepgram API key
            
        Returns:
            TranscriptionResult
            
        Raises:
            TranscriptionError: If transcription fails
        """
        try:
            return self.transcribe_audio(audio_path, channel_config, api_key)
        except requests.RequestException as e:
            raise NetworkError(f"Network error during transcription: {e}") from e
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}") from e