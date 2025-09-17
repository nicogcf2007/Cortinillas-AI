"""
Unit tests for time_manager module.

Tests Colombian timezone calculations and time range generation.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
import pytz

from src.time_manager import (
    get_previous_hour_range,
    to_colombia_timezone,
    format_for_api,
    get_current_colombia_time,
    format_timestamp_for_filename,
    is_dst_active,
    get_timezone_offset,
    COLOMBIA_TZ
)


class TestTimeManager(unittest.TestCase):
    """Test cases for time manager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Fixed test time: 2024-03-15 14:30:45 Colombia time
        self.test_time_colombia = COLOMBIA_TZ.localize(
            datetime(2024, 3, 15, 14, 30, 45)
        )
        
        # Expected previous hour range
        self.expected_start = COLOMBIA_TZ.localize(
            datetime(2024, 3, 15, 13, 0, 0)
        )
        self.expected_end = COLOMBIA_TZ.localize(
            datetime(2024, 3, 15, 14, 0, 0)
        )

    @patch('src.time_manager.datetime')
    def test_get_previous_hour_range_basic(self, mock_datetime):
        """Test basic previous hour range calculation."""
        # Mock current time
        mock_datetime.now.return_value = self.test_time_colombia
        
        start, end = get_previous_hour_range()
        
        self.assertEqual(start, self.expected_start)
        self.assertEqual(end, self.expected_end)
        self.assertEqual(str(start.tzinfo), str(COLOMBIA_TZ))
        self.assertEqual(str(end.tzinfo), str(COLOMBIA_TZ))

    @patch('src.time_manager.datetime')
    def test_get_previous_hour_range_edge_cases(self, mock_datetime):
        """Test previous hour range calculation at edge cases."""
        # Test at midnight (00:30)
        midnight_time = COLOMBIA_TZ.localize(datetime(2024, 3, 15, 0, 30, 0))
        mock_datetime.now.return_value = midnight_time
        
        start, end = get_previous_hour_range()
        
        expected_start = COLOMBIA_TZ.localize(datetime(2024, 3, 14, 23, 0, 0))
        expected_end = COLOMBIA_TZ.localize(datetime(2024, 3, 15, 0, 0, 0))
        
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)

    @patch('src.time_manager.datetime')
    def test_get_previous_hour_range_exact_hour(self, mock_datetime):
        """Test previous hour range when current time is exactly on the hour."""
        # Test at exactly 14:00:00
        exact_hour = COLOMBIA_TZ.localize(datetime(2024, 3, 15, 14, 0, 0))
        mock_datetime.now.return_value = exact_hour
        
        start, end = get_previous_hour_range()
        
        expected_start = COLOMBIA_TZ.localize(datetime(2024, 3, 15, 13, 0, 0))
        expected_end = COLOMBIA_TZ.localize(datetime(2024, 3, 15, 14, 0, 0))
        
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)

    def test_to_colombia_timezone_utc_input(self):
        """Test conversion from UTC to Colombian timezone."""
        utc_time = pytz.UTC.localize(datetime(2024, 3, 15, 19, 30, 45))  # UTC
        colombia_time = to_colombia_timezone(utc_time)
        
        expected = COLOMBIA_TZ.localize(datetime(2024, 3, 15, 14, 30, 45))  # UTC-5
        self.assertEqual(colombia_time, expected)
        self.assertEqual(str(colombia_time.tzinfo), str(COLOMBIA_TZ))

    def test_to_colombia_timezone_naive_input(self):
        """Test conversion from naive datetime (assumed UTC) to Colombian timezone."""
        naive_time = datetime(2024, 3, 15, 19, 30, 45)
        colombia_time = to_colombia_timezone(naive_time)
        
        expected = COLOMBIA_TZ.localize(datetime(2024, 3, 15, 14, 30, 45))  # UTC-5
        self.assertEqual(colombia_time, expected)
        self.assertEqual(str(colombia_time.tzinfo), str(COLOMBIA_TZ))

    def test_to_colombia_timezone_already_colombia(self):
        """Test conversion when datetime is already in Colombian timezone."""
        colombia_time = to_colombia_timezone(self.test_time_colombia)
        
        self.assertEqual(colombia_time, self.test_time_colombia)
        self.assertEqual(str(colombia_time.tzinfo), str(COLOMBIA_TZ))

    def test_format_for_api_colombia_timezone(self):
        """Test API formatting with Colombian timezone datetime."""
        formatted = format_for_api(self.test_time_colombia)
        
        expected = "2024-03-15T14:30:45-05:00"
        self.assertEqual(formatted, expected)

    def test_format_for_api_utc_input(self):
        """Test API formatting with UTC input (should convert to Colombia)."""
        utc_time = pytz.UTC.localize(datetime(2024, 3, 15, 19, 30, 45))
        formatted = format_for_api(utc_time)
        
        expected = "2024-03-15T14:30:45-05:00"
        self.assertEqual(formatted, expected)

    def test_format_for_api_naive_input(self):
        """Test API formatting with naive datetime input."""
        naive_time = datetime(2024, 3, 15, 19, 30, 45)
        formatted = format_for_api(naive_time)
        
        expected = "2024-03-15T14:30:45-05:00"
        self.assertEqual(formatted, expected)

    @patch('src.time_manager.datetime')
    def test_get_current_colombia_time(self, mock_datetime):
        """Test getting current time in Colombian timezone."""
        mock_datetime.now.return_value = self.test_time_colombia
        
        current_time = get_current_colombia_time()
        
        self.assertEqual(current_time, self.test_time_colombia)
        self.assertEqual(str(current_time.tzinfo), str(COLOMBIA_TZ))

    def test_format_timestamp_for_filename_colombia_timezone(self):
        """Test filename timestamp formatting with Colombian timezone."""
        formatted = format_timestamp_for_filename(self.test_time_colombia)
        
        expected = "2024-03-15_14"
        self.assertEqual(formatted, expected)

    def test_format_timestamp_for_filename_utc_input(self):
        """Test filename timestamp formatting with UTC input."""
        utc_time = pytz.UTC.localize(datetime(2024, 3, 15, 19, 30, 45))
        formatted = format_timestamp_for_filename(utc_time)
        
        expected = "2024-03-15_14"  # Converted to Colombia time
        self.assertEqual(formatted, expected)

    def test_is_dst_active(self):
        """Test DST check (Colombia doesn't observe DST)."""
        # Test with current time
        self.assertFalse(is_dst_active())
        
        # Test with specific time
        self.assertFalse(is_dst_active(self.test_time_colombia))
        
        # Test with summer time (still no DST in Colombia)
        summer_time = COLOMBIA_TZ.localize(datetime(2024, 7, 15, 14, 30, 45))
        self.assertFalse(is_dst_active(summer_time))

    def test_get_timezone_offset(self):
        """Test timezone offset retrieval."""
        offset = get_timezone_offset()
        self.assertEqual(offset, "-05:00")

    def test_hour_range_duration(self):
        """Test that the hour range is exactly one hour."""
        with patch('src.time_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = self.test_time_colombia
            
            start, end = get_previous_hour_range()
            duration = end - start
            
            self.assertEqual(duration, timedelta(hours=1))

    def test_timezone_consistency(self):
        """Test that all functions maintain timezone consistency."""
        with patch('src.time_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = self.test_time_colombia
            
            # Get previous hour range
            start, end = get_previous_hour_range()
            
            # Format for API
            start_formatted = format_for_api(start)
            end_formatted = format_for_api(end)
            
            # Format for filename
            start_filename = format_timestamp_for_filename(start)
            
            # All should maintain Colombian timezone
            self.assertTrue(start_formatted.endswith("-05:00"))
            self.assertTrue(end_formatted.endswith("-05:00"))
            self.assertEqual(start_filename, "2024-03-15_13")

    def test_month_boundary(self):
        """Test previous hour calculation across month boundary."""
        # Test at 00:30 on the first day of month
        first_day = COLOMBIA_TZ.localize(datetime(2024, 4, 1, 0, 30, 0))
        
        with patch('src.time_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = first_day
            
            start, end = get_previous_hour_range()
            
            # Should go to previous month
            expected_start = COLOMBIA_TZ.localize(datetime(2024, 3, 31, 23, 0, 0))
            expected_end = COLOMBIA_TZ.localize(datetime(2024, 4, 1, 0, 0, 0))
            
            self.assertEqual(start, expected_start)
            self.assertEqual(end, expected_end)

    def test_year_boundary(self):
        """Test previous hour calculation across year boundary."""
        # Test at 00:30 on January 1st
        new_year = COLOMBIA_TZ.localize(datetime(2024, 1, 1, 0, 30, 0))
        
        with patch('src.time_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = new_year
            
            start, end = get_previous_hour_range()
            
            # Should go to previous year
            expected_start = COLOMBIA_TZ.localize(datetime(2023, 12, 31, 23, 0, 0))
            expected_end = COLOMBIA_TZ.localize(datetime(2024, 1, 1, 0, 0, 0))
            
            self.assertEqual(start, expected_start)
            self.assertEqual(end, expected_end)


if __name__ == '__main__':
    unittest.main()