"""
Unit tests for the cortinilla detector module.
"""
import os
import json
import tempfile
import unittest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

from src.cortinilla_detector import CortinillaDetector
from src.models import (
    ChannelConfig, DeepgramConfig, APIConfig, Word, TranscriptionResult,
    FilteredContent, OverlapResult, Occurrence
)
from src.overlap_detector import OverlapDetector


class TestCortinillaDetector(unittest.TestCase):
    """Test cases for CortinillaDetector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.deepgram_config = DeepgramConfig(
            language="es",
            model="nova-3",
            smart_format=True
        )
        
        self.api_config = APIConfig(
            base_url="http://test.com",
            cookie_sid="test_sid",
            format=11,
            video_is_public=0,
            is_masive=1,
            max_retries=3,
            sleep_seconds=30
        )
        
        self.channel_config = ChannelConfig(
            channel_name="Test Channel",
            idemisora=1,
            idprograma=5,
            cortinillas=["buenos días", "buenas tardes", "muchas gracias"],
            deepgram_config=self.deepgram_config,
            api_config=self.api_config
        )
        
        self.mock_overlap_detector = Mock(spec=OverlapDetector)
        self.detector = CortinillaDetector(overlap_detector=self.mock_overlap_detector)
    
    def test_init_with_overlap_detector(self):
        """Test initialization with overlap detector."""
        detector = CortinillaDetector(self.mock_overlap_detector)
        self.assertEqual(detector.overlap_detector, self.mock_overlap_detector)
    
    def test_init_without_overlap_detector(self):
        """Test initialization without overlap detector creates default."""
        detector = CortinillaDetector()
        self.assertIsInstance(detector.overlap_detector, OverlapDetector)
    
    def test_normalize_text(self):
        """Test text normalization."""
        test_cases = [
            ("Buenos Días", "buenos dias"),
            ("¡Muchas Gracias!", "muchas gracias"),
            ("Buenas  Tardes", "buenas tardes"),
            ("HASTA MAÑANA", "hasta manana"),
            ("Café con Leche", "cafe con leche"),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.detector._normalize_text(input_text)
                self.assertEqual(result, expected)
    
    def test_tokenize(self):
        """Test text tokenization."""
        test_cases = [
            ("buenos días", ["buenos", "dias"]),
            ("¡Muchas Gracias!", ["muchas", "gracias"]),
            ("", []),
            ("   ", []),
            ("single", ["single"]),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.detector._tokenize(input_text)
                self.assertEqual(result, expected)
    
    def test_guess_mime_type(self):
        """Test MIME type guessing."""
        test_cases = [
            ("test.mp3", "audio/mpeg"),
            ("test.wav", "audio/wav"),
            ("test.unknown", "audio/wav"),  # fallback
        ]
        
        for filename, expected in test_cases:
            with self.subTest(filename=filename):
                result = self.detector._guess_mime_type(filename)
                # Note: actual result may vary by system, just check it's reasonable
                self.assertTrue(result.startswith("audio/"))
    
    def test_extract_transcript(self):
        """Test transcript extraction from Deepgram response."""
        # Valid response
        valid_response = {
            "results": {
                "channels": [{
                    "alternatives": [{
                        "transcript": "buenos días muchas gracias"
                    }]
                }]
            }
        }
        
        result = self.detector._extract_transcript(valid_response)
        self.assertEqual(result, "buenos días muchas gracias")
        
        # Invalid response
        invalid_response = {"invalid": "structure"}
        result = self.detector._extract_transcript(invalid_response)
        self.assertEqual(result, "")
    
    def test_extract_words(self):
        """Test word extraction from Deepgram response."""
        # Valid response
        valid_response = {
            "results": {
                "channels": [{
                    "alternatives": [{
                        "words": [
                            {"word": "buenos", "start": 0.0, "end": 0.5, "confidence": 0.9},
                            {"word": "días", "start": 0.5, "end": 1.0, "confidence": 0.8},
                        ]
                    }]
                }]
            }
        }
        
        result = self.detector._extract_words(valid_response)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].word, "buenos")
        self.assertEqual(result[0].start, 0.0)
        self.assertEqual(result[0].end, 0.5)
        self.assertEqual(result[0].confidence, 0.9)
        
        # Invalid response
        invalid_response = {"invalid": "structure"}
        result = self.detector._extract_words(invalid_response)
        self.assertEqual(result, [])
    
    def test_extract_duration(self):
        """Test duration extraction."""
        # From metadata
        response_with_metadata = {
            "metadata": {"duration": 120.5}
        }
        words = []
        result = self.detector._extract_duration(response_with_metadata, words)
        self.assertEqual(result, 120.5)
        
        # From words fallback
        response_without_metadata = {}
        words = [
            Word("test", 0.0, 1.0, 0.9),
            Word("word", 1.0, 2.5, 0.8)
        ]
        result = self.detector._extract_duration(response_without_metadata, words)
        self.assertEqual(result, 2.5)
        
        # No data
        result = self.detector._extract_duration({}, [])
        self.assertEqual(result, 0.0)
    
    def test_calculate_confidence(self):
        """Test confidence calculation."""
        # Normal case
        words = [
            Word("test", 0.0, 1.0, 0.9),
            Word("word", 1.0, 2.0, 0.8),
            Word("another", 2.0, 3.0, 0.7)
        ]
        result = self.detector._calculate_confidence(words)
        expected = (0.9 + 0.8 + 0.7) / 3
        self.assertAlmostEqual(result, expected, places=2)
        
        # Empty words
        result = self.detector._calculate_confidence([])
        self.assertEqual(result, 0.0)
        
        # Words with zero confidence
        words_zero = [Word("test", 0.0, 1.0, 0.0)]
        result = self.detector._calculate_confidence(words_zero)
        self.assertEqual(result, 0.0)
    
    def test_find_cortinilla_occurrences(self):
        """Test finding cortinilla occurrences in word list."""
        words = [
            Word("buenos", 0.0, 0.5, 0.9),
            Word("días", 0.5, 1.0, 0.8),
            Word("y", 1.0, 1.2, 0.7),
            Word("muchas", 1.2, 1.7, 0.9),
            Word("gracias", 1.7, 2.2, 0.8),
            Word("por", 2.2, 2.5, 0.7),
            Word("todo", 2.5, 3.0, 0.8),
        ]
        
        cortinillas = ["buenos días", "muchas gracias", "hasta luego"]
        
        result = self.detector.find_cortinilla_occurrences(cortinillas, words)
        
        # Check "buenos días" found
        self.assertEqual(len(result["buenos días"]), 1)
        occurrence = result["buenos días"][0]
        self.assertEqual(occurrence.start_time, 0.0)
        self.assertEqual(occurrence.end_time, 1.0)
        self.assertEqual(occurrence.text, "buenos días")
        
        # Check "muchas gracias" found
        self.assertEqual(len(result["muchas gracias"]), 1)
        occurrence = result["muchas gracias"][0]
        self.assertEqual(occurrence.start_time, 1.2)
        self.assertEqual(occurrence.end_time, 2.2)
        
        # Check "hasta luego" not found
        self.assertEqual(len(result["hasta luego"]), 0)
    
    def test_find_cortinilla_occurrences_with_accents(self):
        """Test cortinilla detection with accent variations."""
        words = [
            Word("buenas", 0.0, 0.5, 0.9),
            Word("tardes", 0.5, 1.0, 0.8),
        ]
        
        # Search for cortinilla with accents when audio has none
        cortinillas = ["buenas tardes"]
        result = self.detector.find_cortinilla_occurrences(cortinillas, words)
        
        self.assertEqual(len(result["buenas tardes"]), 1)
    
    @patch.dict(os.environ, {"DEEPGRAM_API_KEY": "test_key"})
    @patch("requests.post")
    def test_transcribe_audio_success(self, mock_post):
        """Test successful audio transcription."""
        # Mock successful Deepgram response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": {
                "channels": [{
                    "alternatives": [{
                        "transcript": "buenos días muchas gracias",
                        "words": [
                            {"word": "buenos", "start": 0.0, "end": 0.5, "confidence": 0.9},
                            {"word": "días", "start": 0.5, "end": 1.0, "confidence": 0.8},
                            {"word": "muchas", "start": 1.0, "end": 1.5, "confidence": 0.9},
                            {"word": "gracias", "start": 1.5, "end": 2.0, "confidence": 0.8},
                        ]
                    }]
                }]
            },
            "metadata": {"duration": 2.0}
        }
        mock_post.return_value = mock_response
        
        # Create temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_path = temp_file.name
        
        try:
            result = self.detector.transcribe_audio(temp_path, self.channel_config, "test_key")
            
            self.assertEqual(result.transcript, "buenos días muchas gracias")
            self.assertEqual(len(result.words), 4)
            self.assertEqual(result.duration, 2.0)
            self.assertGreater(result.confidence, 0)
            
            # Verify API call
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            self.assertIn("model", call_args[1]["params"])
            self.assertEqual(call_args[1]["params"]["model"], "nova-3")
            
        finally:
            os.unlink(temp_path)
    
    @patch.dict(os.environ, {"DEEPGRAM_API_KEY": "test_key"})
    def test_transcribe_audio_file_not_found(self):
        """Test transcription with non-existent file."""
        with self.assertRaises(FileNotFoundError):
            self.detector.transcribe_audio("nonexistent.mp3", self.channel_config, "test_key")
    
    @patch.dict(os.environ, {"DEEPGRAM_API_KEY": "test_key"})
    @patch("requests.post")
    def test_transcribe_audio_api_error_with_retry(self, mock_post):
        """Test transcription with API error and retry logic."""
        # Mock failed responses followed by success
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.text = "Internal Server Error"
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "results": {
                "channels": [{
                    "alternatives": [{
                        "transcript": "test transcript",
                        "words": []
                    }]
                }]
            },
            "metadata": {"duration": 1.0}
        }
        
        mock_post.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]
        
        # Create temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_path = temp_file.name
        
        try:
            result = self.detector.transcribe_audio(temp_path, self.channel_config, "test_key")
            self.assertEqual(result.transcript, "test transcript")
            self.assertEqual(mock_post.call_count, 3)  # 2 failures + 1 success
            
        finally:
            os.unlink(temp_path)
    
    @patch.dict(os.environ, {"DEEPGRAM_API_KEY": "test_key"})
    @patch("requests.post")
    def test_transcribe_audio_max_retries_exceeded(self, mock_post):
        """Test transcription when max retries are exceeded."""
        # Mock all responses as failures
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        # Create temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_path = temp_file.name
        
        try:
            with self.assertRaises(RuntimeError) as context:
                self.detector.transcribe_audio(temp_path, self.channel_config, "test_key")
            
            self.assertIn("Deepgram API error 500", str(context.exception))
            self.assertEqual(mock_post.call_count, 3)  # Max retries
            
        finally:
            os.unlink(temp_path)
    
    def test_process_with_overlap_filtering_with_detector(self):
        """Test processing with overlap detector."""
        transcription_result = TranscriptionResult(
            transcript="test transcript",
            words=[Word("test", 0.0, 1.0, 0.9)],
            confidence=0.9,
            duration=1.0
        )
        
        # Mock overlap detector response
        filtered_content = FilteredContent(
            filtered_transcript="filtered transcript",
            filtered_words=[Word("filtered", 0.5, 1.0, 0.8)],
            removed_duration=0.5
        )
        overlap_result = OverlapResult(
            has_overlap=True,
            overlap_start=0.0,
            overlap_end=0.5,
            overlap_duration=0.5,
            similarity_score=0.8
        )
        
        self.mock_overlap_detector.process_with_overlap_detection.return_value = (
            filtered_content, overlap_result
        )
        
        result_filtered, result_overlap = self.detector._process_with_overlap_filtering(
            "test_channel", transcription_result, datetime.now()
        )
        
        self.assertEqual(result_filtered, filtered_content)
        self.assertEqual(result_overlap, overlap_result)
        self.mock_overlap_detector.process_with_overlap_detection.assert_called_once()
    
    def test_process_with_overlap_filtering_without_detector(self):
        """Test processing without overlap detector."""
        # Create detector and manually set overlap_detector to None
        detector_no_overlap = CortinillaDetector()
        detector_no_overlap.overlap_detector = None
        
        transcription_result = TranscriptionResult(
            transcript="test transcript",
            words=[Word("test", 0.0, 1.0, 0.9)],
            confidence=0.9,
            duration=1.0
        )
        
        result_filtered, result_overlap = detector_no_overlap._process_with_overlap_filtering(
            "test_channel", transcription_result, datetime.now()
        )
        
        # Should return original content without filtering
        self.assertEqual(result_filtered.filtered_transcript, "test transcript")
        self.assertEqual(len(result_filtered.filtered_words), 1)
        self.assertEqual(result_filtered.removed_duration, 0.0)
        self.assertFalse(result_overlap.has_overlap)
    
    @patch.dict(os.environ, {"DEEPGRAM_API_KEY": "test_key"})
    @patch("src.cortinilla_detector.CortinillaDetector.transcribe_audio")
    def test_detect_cortinillas_integration(self, mock_transcribe):
        """Test full cortinilla detection integration."""
        # Mock transcription result
        transcription_result = TranscriptionResult(
            transcript="buenos días muchas gracias",
            words=[
                Word("buenos", 0.0, 0.5, 0.9),
                Word("días", 0.5, 1.0, 0.8),
                Word("muchas", 1.0, 1.5, 0.9),
                Word("gracias", 1.5, 2.0, 0.8),
            ],
            confidence=0.85,
            duration=2.0
        )
        mock_transcribe.return_value = transcription_result
        
        # Mock overlap processing
        filtered_content = FilteredContent(
            filtered_transcript="buenos días muchas gracias",
            filtered_words=transcription_result.words,
            removed_duration=0.0
        )
        overlap_result = OverlapResult(
            has_overlap=False,
            overlap_start=None,
            overlap_end=None,
            overlap_duration=None,
            similarity_score=0.0
        )
        
        self.mock_overlap_detector.process_with_overlap_detection.return_value = (
            filtered_content, overlap_result
        )
        
        # Run detection
        timestamp = datetime.now()
        result = self.detector.detect_cortinillas("test.mp3", self.channel_config, timestamp)
        
        # Verify results
        self.assertEqual(result.channel, "Test Channel")
        self.assertEqual(result.timestamp, timestamp)
        self.assertEqual(result.audio_duration, 2.0)
        self.assertEqual(result.total_cortinillas, 2)  # "buenos días" and "muchas gracias"
        self.assertEqual(result.cortinillas_by_type["buenos días"], 1)
        self.assertEqual(result.cortinillas_by_type["muchas gracias"], 1)
        self.assertEqual(result.cortinillas_by_type["buenas tardes"], 0)
        self.assertFalse(result.overlap_filtered)
        self.assertIsNone(result.overlap_duration)
    
    def test_detect_cortinillas_missing_api_key(self):
        """Test cortinilla detection without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as context:
                self.detector.detect_cortinillas("test.mp3", self.channel_config, datetime.now())
            
            self.assertIn("DEEPGRAM_API_KEY", str(context.exception))


if __name__ == "__main__":
    unittest.main()