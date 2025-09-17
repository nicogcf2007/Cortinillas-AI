"""
Time Manager Module

Handles Colombian timezone calculations and time range generation for audio extraction.
Implements requirements 7.1, 7.2, 7.3, and 7.4 for Colombian timezone handling.
"""

from datetime import datetime, timedelta
from typing import Tuple
import pytz


# Colombian timezone (UTC-5, no DST)
COLOMBIA_TZ = pytz.timezone('America/Bogota')


def get_previous_hour_range() -> Tuple[datetime, datetime]:
    """
    Get the time range for the previous complete hour in Colombian timezone.
    
    Returns:
        Tuple[datetime, datetime]: Start and end times for the previous hour
        
    Requirements:
        - 7.1: Use Colombian timezone (UTC-5)
        - 7.2: Extract audio from the hour immediately before current hour
    """
    # Get current time in Colombian timezone
    now_colombia = datetime.now(COLOMBIA_TZ)
    
    # Calculate the start of the previous hour
    previous_hour_start = now_colombia.replace(
        minute=0, 
        second=0, 
        microsecond=0
    ) - timedelta(hours=1)
    
    # Calculate the end of the previous hour (start + 1 hour)
    previous_hour_end = previous_hour_start + timedelta(hours=1)
    
    return previous_hour_start, previous_hour_end


def to_colombia_timezone(dt: datetime) -> datetime:
    """
    Convert a datetime to Colombian timezone.
    
    Args:
        dt: Datetime object to convert
        
    Returns:
        datetime: Datetime in Colombian timezone
        
    Requirements:
        - 7.1: Use Colombian timezone (UTC-5)
        - 7.4: Automatically adjust to correct timezone
    """
    if dt.tzinfo is None:
        # If naive datetime, assume it's in UTC
        dt = pytz.UTC.localize(dt)
    
    return dt.astimezone(COLOMBIA_TZ)


def format_for_api(dt: datetime) -> str:
    """
    Format datetime for API compatibility.
    
    Args:
        dt: Datetime object to format
        
    Returns:
        str: Formatted datetime string for API calls
        
    Requirements:
        - 7.3: Use Colombian timezone format in metadata
    """
    # Ensure datetime is in Colombian timezone
    if dt.tzinfo != COLOMBIA_TZ:
        dt = to_colombia_timezone(dt)
    
    # Format as ISO string with timezone info
    return dt.isoformat()


def get_current_colombia_time() -> datetime:
    """
    Get current time in Colombian timezone.
    
    Returns:
        datetime: Current time in Colombian timezone
        
    Requirements:
        - 7.1: Use Colombian timezone (UTC-5)
    """
    return datetime.now(COLOMBIA_TZ)


def format_timestamp_for_filename(dt: datetime) -> str:
    """
    Format timestamp for use in filenames.
    
    Args:
        dt: Datetime object to format
        
    Returns:
        str: Formatted timestamp (YYYY-MM-DD_HH)
        
    Requirements:
        - 7.3: Use Colombian timezone format in metadata
    """
    # Ensure datetime is in Colombian timezone
    if dt.tzinfo != COLOMBIA_TZ:
        dt = to_colombia_timezone(dt)
    
    return dt.strftime("%Y-%m-%d_%H")


def is_dst_active(dt: datetime = None) -> bool:
    """
    Check if Daylight Saving Time is active for the given datetime.
    Note: Colombia does not observe DST, so this always returns False.
    
    Args:
        dt: Datetime to check (defaults to current time)
        
    Returns:
        bool: False (Colombia doesn't observe DST)
        
    Requirements:
        - 7.4: Handle DST changes (Colombia doesn't have DST)
    """
    return False


def get_timezone_offset() -> str:
    """
    Get the current timezone offset for Colombia.
    
    Returns:
        str: Timezone offset (always "-05:00" for Colombia)
        
    Requirements:
        - 7.1: Use Colombian timezone (UTC-5)
    """
    return "-05:00"