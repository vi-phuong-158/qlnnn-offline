"""
QLNNN Offline - Text Utilities
Xử lý chuỗi, chuẩn hóa text, remove diacritics
"""

import re
from typing import Optional
from unidecode import unidecode


def normalize_passport(passport: str) -> str:
    """
    Normalize passport number for consistent matching
    - Uppercase
    - Remove spaces and special characters
    - Trim
    
    Args:
        passport: Raw passport string
        
    Returns:
        Normalized passport number
    """
    if not passport:
        return ""
    
    # Convert to uppercase and strip
    result = str(passport).upper().strip()
    
    # Remove common separators
    result = re.sub(r'[\s\-_.]+', '', result)
    
    return result


def remove_diacritics(text: str) -> str:
    """
    Remove Vietnamese diacritics for search matching
    
    Args:
        text: Vietnamese text with diacritics
        
    Returns:
        Text without diacritics
    """
    if not text:
        return ""
    
    return unidecode(text)


def normalize_for_search(text: str) -> str:
    """
    Normalize text for full-text search
    - Remove diacritics
    - Lowercase
    - Remove extra spaces
    
    Args:
        text: Input text
        
    Returns:
        Normalized text for search
    """
    if not text:
        return ""
    
    # Remove diacritics
    result = remove_diacritics(text)
    
    # Lowercase
    result = result.lower()
    
    # Normalize spaces
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result


def normalize_header(header: str) -> str:
    """
    Normalize column header for matching
    - Remove diacritics
    - Lowercase
    - Replace spaces with underscores
    - Remove special characters
    
    Args:
        header: Column header string
        
    Returns:
        Normalized header
    """
    if not header:
        return ""
    
    # Remove diacritics
    result = remove_diacritics(header)
    
    # Lowercase
    result = result.lower()
    
    # Replace spaces with underscores
    result = re.sub(r'\s+', '_', result)
    
    # Remove non-alphanumeric except underscore
    result = re.sub(r'[^a-z0-9_]', '', result)
    
    return result


def clean_csv_value(value: str) -> str:
    """
    Clean and escape string for CSV
    - Remove line breaks
    - Escape quotes
    
    Args:
        value: Raw string value
        
    Returns:
        Cleaned string safe for CSV
    """
    if not value:
        return ""
    
    result = str(value)
    
    # Remove line breaks
    result = re.sub(r'[\r\n]+', ' ', result)
    
    # Escape double quotes
    result = result.replace('"', '""')
    
    return result.strip()


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to max length with suffix
    
    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text or ""
    
    return text[:max_length - len(suffix)] + suffix


def extract_numbers(text: str) -> str:
    """
    Extract only numeric characters from text
    
    Args:
        text: Input text
        
    Returns:
        String containing only digits
    """
    if not text:
        return ""
    
    return re.sub(r'[^0-9]', '', str(text))


def is_valid_passport(passport: str) -> bool:
    """
    Basic validation for passport format
    - At least 5 characters
    - Alphanumeric
    
    Args:
        passport: Passport number to validate
        
    Returns:
        True if valid format
    """
    if not passport:
        return False
    
    normalized = normalize_passport(passport)
    
    # Must be at least 5 characters
    if len(normalized) < 5:
        return False
    
    # Must be alphanumeric
    if not normalized.isalnum():
        return False
    
    return True


def split_passports(text: str) -> list:
    """
    Split text containing multiple passport numbers
    Supports comma, newline, space, tab as separators
    
    Args:
        text: Text containing passport numbers
        
    Returns:
        List of cleaned passport numbers
    """
    if not text:
        return []
    
    # Split by common separators
    parts = re.split(r'[,;\n\r\t]+', text)
    
    # Clean and filter
    result = []
    for part in parts:
        passport = normalize_passport(part)
        if passport and is_valid_passport(passport):
            result.append(passport)
    
    return result
