"""
QLNNN Offline - Date Utilities
Port từ SharedUtils.gs - formatDateVN, parseDateVN, formatDateForBQ
"""

from datetime import datetime, date
from typing import Union, Optional
import re


def format_date_vn(date_input: Union[datetime, date, str, None]) -> str:
    """
    Format date to Vietnamese format (DD/MM/YYYY)
    
    Args:
        date_input: Date object, datetime, or string
        
    Returns:
        Formatted date string DD/MM/YYYY or empty string
    """
    if date_input is None:
        return ""
    
    # If already a string, try to parse and reformat
    if isinstance(date_input, str):
        parsed = parse_date_vn(date_input)
        if parsed:
            return parsed.strftime("%d/%m/%Y")
        return date_input  # Return as-is if can't parse
    
    # If datetime or date object
    if isinstance(date_input, (datetime, date)):
        return date_input.strftime("%d/%m/%Y")
    
    return ""


def parse_date_vn(date_str: str) -> Optional[date]:
    """
    Parse Vietnamese date format (DD/MM/YYYY) or other common formats to date object
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        Date object or None if invalid
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    date_str = date_str.strip()
    
    if not date_str:
        return None
    
    # Try various formats
    formats = [
        "%d/%m/%Y",     # DD/MM/YYYY (Vietnamese)
        "%d-%m-%Y",     # DD-MM-YYYY
        "%Y-%m-%d",     # YYYY-MM-DD (ISO)
        "%Y/%m/%d",     # YYYY/MM/DD
        "%d.%m.%Y",     # DD.MM.YYYY
        "%m/%d/%Y",     # MM/DD/YYYY (US)
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    # Try to extract date parts using regex
    # Pattern: any 1-2 digit / 1-2 digit / 2-4 digit
    match = re.match(r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})', date_str)
    if match:
        day, month, year = match.groups()
        day = int(day)
        month = int(month)
        year = int(year)
        
        # Handle 2-digit year
        if year < 100:
            year += 2000 if year < 50 else 1900
        
        try:
            return date(year, month, day)
        except ValueError:
            # Maybe day and month are swapped
            try:
                return date(year, day, month)
            except ValueError:
                pass
    
    return None


def format_date_for_db(date_input: Union[datetime, date, str, None]) -> str:
    """
    Format date for database storage (YYYY-MM-DD)
    
    Args:
        date_input: Date in various formats
        
    Returns:
        Date string in YYYY-MM-DD format or empty string
    """
    if date_input is None:
        return ""
    
    # If already a date/datetime object
    if isinstance(date_input, (datetime, date)):
        return date_input.strftime("%Y-%m-%d")
    
    # If string, parse first
    if isinstance(date_input, str):
        parsed = parse_date_vn(date_input)
        if parsed:
            return parsed.strftime("%Y-%m-%d")
    
    return ""


def days_between(date1: Union[date, str], date2: Union[date, str] = None) -> int:
    """
    Calculate days between two dates
    
    Args:
        date1: First date
        date2: Second date (defaults to today)
        
    Returns:
        Number of days (positive if date2 > date1)
    """
    if date2 is None:
        date2 = date.today()
    
    # Convert to date objects if needed
    if isinstance(date1, str):
        date1 = parse_date_vn(date1)
    if isinstance(date2, str):
        date2 = parse_date_vn(date2)
    
    if date1 is None or date2 is None:
        return 0
    
    return (date2 - date1).days


def is_valid_date(date_str: str) -> bool:
    """
    Check if a string is a valid date
    
    Args:
        date_str: Date string to check
        
    Returns:
        True if valid date
    """
    return parse_date_vn(date_str) is not None
