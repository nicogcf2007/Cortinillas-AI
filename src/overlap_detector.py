"""
Overlap detection system for Cortinillas AI.

This module handles detection of overlapping content between consecutive audio segments
to avoid counting duplicate cortinillas in overlapping portions.
"""
import json
import os
import logging
from datetime import datetime
from typing import List, Optional, Tuple
from difflib import SequenceMatcher

try:
    from .models import OverlapResult, FilteredContent, Word, TranscriptionResult
    from .exceptions import OverlapDetectionError, FileOperationError
    from .error_handler import ErrorHandler, create_error_context, safe_execute
except ImportError:
    from models import OverlapResult, FilteredContent, Word, TranscriptionResult
    from exceptions import OverlapDetectionError, FileOperationError
    from error_handler import ErrorHandler, create_error_context, safe_execute


logger = logging.getLogger(__name__)


class OverlapDetector:
    """Detects and handles overlapping content between consecutive audio segments."""
    
    def __init__(self, cache_dir: str = "data/transcript_cache"):
        """
        Initialize the overlap detector.
        
        Args:
            cache_dir: Directory to store transcript cache files
        """
        self.cache_dir = cache_dir
        self.error_handler = ErrorHandler(max_retries=2, base_delay=1.0)
        self._ensure_cache_dir()
        logger.info(f"OverlapDetector initialized with cache dir: {cache_dir}")
    
    def _ensure_cache_dir(self) -> None:
        """Ensure the cache directory exists."""
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_path(self, channel: str) -> str:
        """Get the cache file path for a channel."""
        return os.path.join(self.cache_dir, f"{channel.lower()}_last_transcript.json")
    
    def detect_overlap(self, current_transcript: str, previous_transcript: str) -> OverlapResult:
        """
        Detect overlap between current and previous transcripts.
        
        Args:
            current_transcript: Current audio transcript
            previous_transcript: Previous audio transcript
            
        Returns:
            OverlapResult with overlap information
        """
        if not previous_transcript or not current_transcript:
            logger.info("🔍 OVERLAP ANALYSIS - No previous transcript available for comparison")
            return OverlapResult(
                has_overlap=False,
                similarity_score=0.0,
                overlapping_content="",
                overlap_duration_seconds=0.0
            )
        
        logger.info("🔍 OVERLAP ANALYSIS - Comparing transcripts:")
        logger.info(f"   📄 Previous transcript length: {len(previous_transcript)} chars")
        logger.info(f"   📄 Current transcript length: {len(current_transcript)} chars")
        
        # Show preview of transcripts being compared
        prev_preview = previous_transcript[-200:] if len(previous_transcript) > 200 else previous_transcript
        curr_preview = current_transcript[:200] if len(current_transcript) > 200 else current_transcript
        
        logger.info(f"   📝 Previous transcript (end): '...{prev_preview}'")
        logger.info(f"   📝 Current transcript (start): '{curr_preview}...'")
        
        # Clean and normalize transcripts for comparison
        current_clean = self._clean_transcript(current_transcript)
        previous_clean = self._clean_transcript(previous_transcript)
        
        # Find overlap at the beginning of current transcript with end of previous
        overlap_info = self._find_text_overlap(current_clean, previous_clean)
        
        if overlap_info.has_overlap:
            logger.info(f"   ✅ OVERLAP FOUND - Similarity: {overlap_info.similarity_score:.2f}")
            logger.info(f"   📝 Overlapping content: '{overlap_info.overlapping_content}'")
        else:
            logger.info(f"   ❌ NO OVERLAP - Best similarity: {overlap_info.similarity_score:.2f}")
        
        return overlap_info
    
    def _clean_transcript(self, transcript: str) -> str:
        """
        Clean transcript for comparison by normalizing whitespace and case.
        
        Args:
            transcript: Raw transcript text
            
        Returns:
            Cleaned transcript
        """
        return ' '.join(transcript.lower().split())
    
    def _find_text_overlap(self, current: str, previous: str) -> OverlapResult:
        """
        Find overlapping text between current and previous transcripts.
        
        Uses sliding window approach to find the best match between the beginning
        of current transcript and the end of previous transcript.
        
        Args:
            current: Current transcript (cleaned)
            previous: Previous transcript (cleaned)
            
        Returns:
            OverlapResult with overlap details
        """
        # Split into words for better matching
        current_words = current.split()
        previous_words = previous.split()
        
        if not current_words or not previous_words:
            return OverlapResult(
                has_overlap=False,
                similarity_score=0.0,
                overlapping_content="",
                overlap_duration_seconds=0.0
            )
        
        best_similarity = 0.0
        best_overlap_length = 0
        
        # Check different window sizes for overlap detection
        min_window = min(3, len(current_words), len(previous_words))  # Start with smaller windows
        max_window = min(len(current_words), len(previous_words), 20)  # Reasonable upper limit
        
        if max_window < min_window:
            return OverlapResult(
                has_overlap=False,
                similarity_score=0.0,
                overlapping_content="",
                overlap_duration_seconds=0.0
            )
        
        for window_size in range(min_window, max_window + 1):
            # Get beginning of current transcript
            current_start = ' '.join(current_words[:window_size])
            
            # Check against end portions of previous transcript
            # Look at the last portion of previous transcript
            for i in range(max(0, len(previous_words) - window_size - 5), len(previous_words) - window_size + 1):
                if i < 0:
                    continue
                    
                previous_end = ' '.join(previous_words[i:i + window_size])
                
                # Calculate similarity
                similarity = SequenceMatcher(None, current_start, previous_end).ratio()
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_overlap_length = window_size
        
        # Also check for exact substring matches
        for window_size in range(min_window, max_window + 1):
            current_start = ' '.join(current_words[:window_size])
            if current_start in previous:
                # Found exact match
                best_similarity = max(best_similarity, 1.0)
                best_overlap_length = window_size
                break
        
        if best_similarity > 0.7:  # 70% similarity threshold
            overlapping_content = ' '.join(current_words[:best_overlap_length])
            logger.info(f"   🎯 MATCH FOUND:")
            logger.info(f"      - Words matched: {best_overlap_length}")
            logger.info(f"      - Similarity score: {best_similarity:.2f}")
            logger.info(f"      - Overlapping text: '{overlapping_content}'")
            
            return OverlapResult(
                has_overlap=True,
                similarity_score=best_similarity,
                overlapping_content=overlapping_content,
                overlap_duration_seconds=0.0  # Will be calculated later if needed
            )
        
        return OverlapResult(
            has_overlap=False,
            similarity_score=best_similarity,
            overlapping_content="",
            overlap_duration_seconds=0.0
        )
    
    def filter_overlapping_content(
        self, 
        transcript: str, 
        words: List[Word], 
        overlap: OverlapResult
    ) -> FilteredContent:
        """
        Filter out overlapping content from transcript and words.
        
        Args:
            transcript: Original transcript
            words: List of words with timing information
            overlap: Overlap detection result
            
        Returns:
            FilteredContent with overlapping portions removed
        """
        if not overlap.has_overlap or not words:
            logger.info("No overlap detected or no words to filter")
            return FilteredContent(
                original_words=words,
                filtered_words=words,
                removed_words=[],
                similarity_score=0.0
            )
        
        # Find the overlap end time based on similarity analysis
        overlap_end_time = self._calculate_overlap_end_time(words, overlap.similarity_score)
        
        # Calculate removed words first to show detailed logs
        removed_words = [word for word in words if word.start < overlap_end_time]
        
        if removed_words:
            # Log detailed information about what will be removed
            start_time = removed_words[0].start
            end_time = removed_words[-1].end
            removed_duration = end_time - start_time
            removed_text = ' '.join([word.word for word in removed_words])
            
            logger.info(f"🔍 OVERLAP DETECTION - Removing overlapping content:")
            logger.info(f"   📍 Time range: {start_time:.2f}s - {end_time:.2f}s ({removed_duration:.2f}s duration)")
            logger.info(f"   📝 Removed text: '{removed_text[:200]}{'...' if len(removed_text) > 200 else ''}'")
            logger.info(f"   🎯 Similarity score: {overlap.similarity_score:.2f}")
            logger.info(f"   📊 Words removed: {len(removed_words)} out of {len(words)} total words")
            
            # Show time breakdown
            logger.info(f"   ⏰ Detailed timing:")
            logger.info(f"      - Original audio duration: {words[-1].end:.2f}s")
            logger.info(f"      - Overlap duration removed: {removed_duration:.2f}s")
            logger.info(f"      - Remaining audio duration: {words[-1].end - removed_duration:.2f}s")
            
            # Show first few and last few words being removed
            if len(removed_words) > 6:
                first_words = ' '.join([word.word for word in removed_words[:3]])
                last_words = ' '.join([word.word for word in removed_words[-3:]])
                logger.info(f"   🔤 First words removed: '{first_words}'")
                logger.info(f"   🔤 Last words removed: '{last_words}'")
            
        # Filter words that fall within the overlap period
        filtered_words = [word for word in words if word.start >= overlap_end_time]
        
        if filtered_words:
            remaining_text = ' '.join([word.word for word in filtered_words[:10]])
            logger.info(f"   ✅ Remaining content starts with: '{remaining_text}{'...' if len(filtered_words) > 10 else ''}'")
        else:
            logger.warning("   ⚠️  All content was removed as overlap!")
        
        return FilteredContent(
            original_words=words,
            filtered_words=filtered_words,
            removed_words=removed_words,
            similarity_score=overlap.similarity_score
        )
    
    def _calculate_overlap_end_time(self, words: List[Word], similarity_score: float) -> float:
        """
        Calculate the end time of overlapping content based on word analysis.
        
        Args:
            words: List of words with timing
            similarity_score: Similarity score from overlap detection
            
        Returns:
            End time of overlap in seconds
        """
        if not words:
            logger.info("   ⚠️  No words available for overlap calculation")
            return 0.0
        
        # Estimate overlap duration based on similarity score and word distribution
        # Higher similarity suggests longer overlap
        total_duration = words[-1].end if words else 0.0
        
        # Use similarity score to estimate overlap percentage (with reasonable bounds)
        overlap_percentage = min(0.3, max(0.05, similarity_score * 0.4))
        estimated_overlap_duration = total_duration * overlap_percentage
        
        logger.info(f"   🧮 OVERLAP CALCULATION:")
        logger.info(f"      - Total audio duration: {total_duration:.2f}s")
        logger.info(f"      - Similarity score: {similarity_score:.2f}")
        logger.info(f"      - Calculated overlap percentage: {overlap_percentage:.1%}")
        logger.info(f"      - Estimated overlap duration: {estimated_overlap_duration:.2f}s")
        
        # Find the word that corresponds to this estimated duration
        for i, word in enumerate(words):
            if word.end >= estimated_overlap_duration:
                logger.info(f"      - Overlap end time set to: {word.end:.2f}s (word #{i+1}: '{word.word}')")
                return word.end
        
        # Fallback: use first 10% of audio or first 30 seconds, whichever is smaller
        fallback_duration = min(30.0, total_duration * 0.1)
        logger.info(f"      - Using fallback duration: {fallback_duration:.2f}s")
        
        for word in words:
            if word.end >= fallback_duration:
                logger.info(f"      - Fallback overlap end time: {word.end:.2f}s (word: '{word.word}')")
                return word.end
        
        logger.info("      - No suitable overlap end time found, returning 0.0s")
        return 0.0
    
    def save_transcript_cache(self, channel: str, transcript: str, timestamp: datetime) -> None:
        """
        Save transcript to cache for future overlap detection.
        
        Args:
            channel: Channel identifier
            transcript: Transcript text to cache
            timestamp: Timestamp of the audio
        """
        context = create_error_context(
            "save_transcript_cache",
            channel=channel,
            timestamp=timestamp
        )
        
        cache_path = self._get_cache_path(channel)
        
        cache_data = {
            "transcript": transcript,
            "timestamp": timestamp.isoformat(),
            "channel": channel
        }
        
        try:
            # Ensure directory exists before writing
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            
            # Write with atomic operation (write to temp file first)
            temp_path = cache_path + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            # Atomic rename
            os.replace(temp_path, cache_path)
            logger.info(f"Saved transcript cache for channel {channel}")
            
        except (OSError, IOError) as e:
            self.error_handler.handle_error(
                FileOperationError(f"Failed to save transcript cache: {e}"),
                context
            )
        except Exception as e:
            self.error_handler.handle_error(e, context)
    
    def load_previous_transcript(self, channel: str) -> Optional[str]:
        """
        Load previous transcript from cache.
        
        Args:
            channel: Channel identifier
            
        Returns:
            Previous transcript text or None if not available
        """
        context = create_error_context("load_previous_transcript", channel=channel)
        cache_path = self._get_cache_path(channel)
        
        if not os.path.exists(cache_path):
            logger.info(f"No previous transcript cache found for channel {channel}")
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Validate cache data
            if not isinstance(cache_data, dict) or "transcript" not in cache_data:
                logger.warning(f"Invalid cache data format for channel {channel}")
                return None
            
            transcript = cache_data.get("transcript")
            if not isinstance(transcript, str):
                logger.warning(f"Invalid transcript type in cache for channel {channel}")
                return None
            
            logger.info(f"Loaded previous transcript for channel {channel} from {cache_data.get('timestamp')}")
            return transcript
        
        except (json.JSONDecodeError, OSError, IOError) as e:
            self.error_handler.handle_error(
                FileOperationError(f"Failed to load previous transcript: {e}"),
                context
            )
            return None
        except Exception as e:
            self.error_handler.handle_error(e, context)
            return None
    
    def process_with_overlap_detection(
        self, 
        channel: str, 
        transcription_result: TranscriptionResult,
        timestamp: datetime
    ) -> Tuple[FilteredContent, OverlapResult]:
        """
        Process transcription with overlap detection and filtering.
        
        Args:
            channel: Channel identifier
            transcription_result: Current transcription result
            timestamp: Current audio timestamp
            
        Returns:
            Tuple of (filtered_content, overlap_result)
        """
        # Check if audio duration is long enough to warrant overlap detection
        # Only process overlap if audio is longer than 1 hour and 3 seconds (3603 seconds)
        audio_duration = transcription_result.duration_seconds
        min_duration_for_overlap = 3603  # 1 hour and 3 seconds
        
        if audio_duration <= min_duration_for_overlap:
            logger.info(f"🔍 OVERLAP ANALYSIS - Audio duration ({audio_duration:.0f}s) is too short for overlap detection (minimum: {min_duration_for_overlap}s)")
            logger.info("   ⏭️  Skipping overlap detection - returning original content")
            
            # Return original content without overlap processing
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
            
            # Still save transcript for future comparisons
            self.save_transcript_cache(channel, transcription_result.transcript, timestamp)
            return filtered_content, overlap_result
        
        logger.info(f"🔍 OVERLAP ANALYSIS - Audio duration ({audio_duration:.0f}s) is sufficient for overlap detection")
        
        # Load previous transcript for comparison
        previous_transcript = self.load_previous_transcript(channel)
        
        # Detect overlap
        overlap_result = self.detect_overlap(transcription_result.transcript, previous_transcript)
        
        # Filter overlapping content
        filtered_content = self.filter_overlapping_content(
            transcription_result.transcript,
            transcription_result.words,
            overlap_result
        )
        
        # Update overlap result with calculated duration
        if overlap_result.has_overlap and len(filtered_content.removed_words) > 0:
            # Calculate duration from removed words
            if filtered_content.removed_words:
                overlap_duration = filtered_content.removed_words[-1].end - filtered_content.removed_words[0].start
                overlap_result.overlap_duration_seconds = overlap_duration
        
        # Save current transcript for next comparison
        self.save_transcript_cache(channel, transcription_result.transcript, timestamp)
        
        return filtered_content, overlap_result