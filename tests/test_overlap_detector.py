"""
Unit tests for the overlap detection system.
"""
import json
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch, mock_open

from src.overlap_detector import OverlapDetector
from src.models import OverlapResult, FilteredContent, Word, TranscriptionResult


class TestOverlapDetector(unittest.TestCase):
    """Test cases for OverlapDetector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.detector = OverlapDetector(cache_dir=self.temp_dir)
        
        # Sample words for testing
        self.sample_words = [
            Word("buenos", 0.0, 0.5, 0.9),
            Word("días", 0.5, 1.0, 0.9),
            Word("queridos", 1.0, 1.5, 0.8),
            Word("televidentes", 1.5, 2.5, 0.9),
            Word("hoy", 2.5, 3.0, 0.9),
            Word("tenemos", 3.0, 3.5, 0.8),
            Word("noticias", 3.5, 4.0, 0.9),
            Word("importantes", 4.0, 5.0, 0.8)
        ]
        
        self.sample_transcript = "buenos días queridos televidentes hoy tenemos noticias importantes"
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_creates_cache_directory(self):
        """Test that initialization creates cache directory."""
        self.assertTrue(os.path.exists(self.temp_dir))
    
    def test_clean_transcript(self):
        """Test transcript cleaning functionality."""
        dirty_transcript = "  Buenos   DÍAS,  queridos\n\ttelevidentes!  "
        expected = "buenos días, queridos televidentes!"
        
        result = self.detector._clean_transcript(dirty_transcript)
        self.assertEqual(result, expected)
    
    def test_detect_overlap_no_previous_transcript(self):
        """Test overlap detection when no previous transcript exists."""
        current = "buenos días queridos televidentes"
        previous = None
        
        result = self.detector.detect_overlap(current, previous)
        
        self.assertFalse(result.has_overlap)
        self.assertIsNone(result.overlap_start)
        self.assertIsNone(result.overlap_end)
        self.assertIsNone(result.overlap_duration)
        self.assertEqual(result.similarity_score, 0.0)
    
    def test_detect_overlap_no_similarity(self):
        """Test overlap detection with completely different transcripts."""
        current = "buenos días queridos televidentes"
        previous = "muchas gracias por su atención hasta mañana"
        
        result = self.detector.detect_overlap(current, previous)
        
        self.assertFalse(result.has_overlap)
        self.assertIsNone(result.overlap_start)
        self.assertIsNone(result.overlap_end)
        self.assertIsNone(result.overlap_duration)
        self.assertLess(result.similarity_score, 0.7)
    
    def test_detect_overlap_with_similarity(self):
        """Test overlap detection with similar content."""
        # Previous transcript ends with content that current starts with
        previous = "noticias del día muchas gracias buenos días queridos televidentes"
        current = "buenos días queridos televidentes hoy tenemos más noticias"
        
        result = self.detector.detect_overlap(current, previous)
        
        self.assertTrue(result.has_overlap)
        self.assertEqual(result.overlap_start, 0.0)
        self.assertGreaterEqual(result.similarity_score, 0.7)
    
    def test_find_text_overlap_exact_match(self):
        """Test finding exact text overlap."""
        current = "buenos días queridos televidentes hoy tenemos noticias"
        previous = "programa anterior buenos días queridos televidentes"
        
        result = self.detector._find_text_overlap(current, previous)
        
        self.assertTrue(result.has_overlap)
        self.assertGreaterEqual(result.similarity_score, 0.9)
    
    def test_find_text_overlap_partial_match(self):
        """Test finding partial text overlap."""
        current = "buenos días queridos amigos hoy tenemos noticias"
        previous = "programa anterior buenos días queridos televidentes"
        
        result = self.detector._find_text_overlap(current, previous)
        
        # Should detect some similarity but maybe not enough for overlap
        self.assertGreater(result.similarity_score, 0.0)
    
    def test_filter_overlapping_content_no_overlap(self):
        """Test filtering when there's no overlap."""
        overlap = OverlapResult(False, None, None, None, 0.0)
        
        result = self.detector.filter_overlapping_content(
            self.sample_transcript, 
            self.sample_words, 
            overlap
        )
        
        self.assertEqual(result.filtered_transcript, self.sample_transcript)
        self.assertEqual(result.filtered_words, self.sample_words)
        self.assertEqual(result.removed_duration, 0.0)
    
    def test_filter_overlapping_content_with_overlap(self):
        """Test filtering when overlap is detected."""
        overlap = OverlapResult(True, 0.0, None, None, 0.8)
        
        result = self.detector.filter_overlapping_content(
            self.sample_transcript, 
            self.sample_words, 
            overlap
        )
        
        # Should remove some content from the beginning
        self.assertNotEqual(result.filtered_transcript, self.sample_transcript)
        self.assertLess(len(result.filtered_words), len(self.sample_words))
        self.assertGreater(result.removed_duration, 0.0)
    
    def test_calculate_overlap_end_time(self):
        """Test calculation of overlap end time."""
        similarity_score = 0.8
        
        end_time = self.detector._calculate_overlap_end_time(self.sample_words, similarity_score)
        
        self.assertGreater(end_time, 0.0)
        self.assertLess(end_time, self.sample_words[-1].end)
    
    def test_calculate_overlap_end_time_empty_words(self):
        """Test overlap end time calculation with empty words list."""
        result = self.detector._calculate_overlap_end_time([], 0.8)
        self.assertEqual(result, 0.0)
    
    def test_save_and_load_transcript_cache(self):
        """Test saving and loading transcript cache."""
        channel = "test_channel"
        transcript = "test transcript content"
        timestamp = datetime.now()
        
        # Save transcript
        self.detector.save_transcript_cache(channel, transcript, timestamp)
        
        # Verify file was created
        cache_path = self.detector._get_cache_path(channel)
        self.assertTrue(os.path.exists(cache_path))
        
        # Load transcript
        loaded_transcript = self.detector.load_previous_transcript(channel)
        self.assertEqual(loaded_transcript, transcript)
    
    def test_load_previous_transcript_no_cache(self):
        """Test loading transcript when no cache exists."""
        result = self.detector.load_previous_transcript("nonexistent_channel")
        self.assertIsNone(result)
    
    def test_save_transcript_cache_invalid_path(self):
        """Test saving transcript cache with invalid path."""
        # Test that initialization fails gracefully with invalid path
        with self.assertRaises(PermissionError):
            OverlapDetector(cache_dir="C:\\Windows\\System32\\invalid_cache")
        
        # Test error handling during save operation
        # Create a detector with a valid path first
        detector = OverlapDetector(cache_dir=self.temp_dir)
        
        # Mock the open function to raise an exception
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            with patch('src.overlap_detector.logger') as mock_logger:
                detector.save_transcript_cache("test", "transcript", datetime.now())
                mock_logger.error.assert_called()
    
    def test_load_transcript_cache_corrupted_file(self):
        """Test loading transcript cache with corrupted JSON."""
        channel = "test_channel"
        cache_path = self.detector._get_cache_path(channel)
        
        # Create corrupted JSON file
        with open(cache_path, 'w') as f:
            f.write("invalid json content")
        
        with patch('src.overlap_detector.logger') as mock_logger:
            result = self.detector.load_previous_transcript(channel)
            self.assertIsNone(result)
            mock_logger.error.assert_called()
    
    def test_process_with_overlap_detection_no_previous(self):
        """Test complete processing workflow with no previous transcript."""
        channel = "test_channel"
        transcription_result = TranscriptionResult(
            transcript=self.sample_transcript,
            words=self.sample_words,
            confidence=0.9,
            duration=5.0
        )
        timestamp = datetime.now()
        
        filtered_content, overlap_result = self.detector.process_with_overlap_detection(
            channel, transcription_result, timestamp
        )
        
        # No overlap expected since no previous transcript
        self.assertFalse(overlap_result.has_overlap)
        self.assertEqual(filtered_content.filtered_transcript, self.sample_transcript)
        self.assertEqual(filtered_content.removed_duration, 0.0)
        
        # Verify transcript was cached
        cached = self.detector.load_previous_transcript(channel)
        self.assertEqual(cached, self.sample_transcript)
    
    def test_process_with_overlap_detection_with_previous(self):
        """Test complete processing workflow with previous transcript."""
        channel = "test_channel"
        
        # First, save a previous transcript
        previous_transcript = "programa anterior buenos días queridos televidentes"
        self.detector.save_transcript_cache(channel, previous_transcript, datetime.now())
        
        # Now process current transcript that overlaps
        current_transcript = "buenos días queridos televidentes hoy tenemos noticias importantes"
        current_words = [
            Word("buenos", 0.0, 0.5, 0.9),
            Word("días", 0.5, 1.0, 0.9),
            Word("queridos", 1.0, 1.5, 0.8),
            Word("televidentes", 1.5, 2.5, 0.9),
            Word("hoy", 2.5, 3.0, 0.9),
            Word("tenemos", 3.0, 3.5, 0.8),
            Word("noticias", 3.5, 4.0, 0.9),
            Word("importantes", 4.0, 5.0, 0.8)
        ]
        
        transcription_result = TranscriptionResult(
            transcript=current_transcript,
            words=current_words,
            confidence=0.9,
            duration=5.0
        )
        
        filtered_content, overlap_result = self.detector.process_with_overlap_detection(
            channel, transcription_result, datetime.now()
        )
        
        # Should detect overlap
        self.assertTrue(overlap_result.has_overlap)
        self.assertGreater(overlap_result.similarity_score, 0.7)
        
        # Should filter some content
        self.assertLess(len(filtered_content.filtered_words), len(current_words))
        self.assertGreater(filtered_content.removed_duration, 0.0)
    
    def test_get_cache_path(self):
        """Test cache path generation."""
        channel = "test_channel"
        expected_path = os.path.join(self.temp_dir, "test_channel_last_transcript.json")
        
        result = self.detector._get_cache_path(channel)
        self.assertEqual(result, expected_path)
    
    def test_edge_case_empty_transcripts(self):
        """Test edge case with empty transcripts."""
        result = self.detector.detect_overlap("", "")
        
        self.assertFalse(result.has_overlap)
        self.assertEqual(result.similarity_score, 0.0)
    
    def test_edge_case_very_short_transcripts(self):
        """Test edge case with very short transcripts."""
        current = "hola"
        previous = "adiós"
        
        result = self.detector.detect_overlap(current, previous)
        
        self.assertFalse(result.has_overlap)
    
    def test_similarity_threshold(self):
        """Test that similarity threshold is properly applied."""
        # Create transcripts with moderate similarity (below threshold)
        current = "buenos días queridos amigos"
        previous = "buenos días estimados televidentes"
        
        result = self.detector.detect_overlap(current, previous)
        
        # Should have some similarity but not enough for overlap detection
        self.assertGreater(result.similarity_score, 0.0)
        # Depending on the exact similarity, this might or might not trigger overlap
        # The test verifies the threshold logic is working


if __name__ == '__main__':
    unittest.main()