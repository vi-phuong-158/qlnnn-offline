"""
QLNNN Offline - Security Utilities
Password hashing, verification
"""

import bcrypt
import hashlib
from typing import Optional


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        password: Plain text password to verify
        password_hash: Stored hash to compare against
        
    Returns:
        True if password matches
    """
    if not password or not password_hash:
        return False
    
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            password_hash.encode('utf-8')
        )
    except Exception:
        return False


def hash_sha256(text: str) -> str:
    """
    Compute SHA-256 hash of text
    
    Args:
        text: Input text
        
    Returns:
        Hex-encoded SHA-256 hash
    """
    if not text:
        return ""
    
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def is_strong_password(password: str, min_length: int = 6) -> tuple:
    """
    Check if password meets strength requirements
    
    Args:
        password: Password to check
        min_length: Minimum required length
        
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    if not password:
        return False, "Mật khẩu không được để trống"
    
    if len(password) < min_length:
        return False, f"Mật khẩu phải có ít nhất {min_length} ký tự"
    
    # Optional: Add more requirements
    # has_upper = any(c.isupper() for c in password)
    # has_lower = any(c.islower() for c in password)
    # has_digit = any(c.isdigit() for c in password)
    
    return True, "Mật khẩu hợp lệ"


def mask_sensitive(text: str, show_chars: int = 4) -> str:
    """
    Mask sensitive information (e.g., email, phone)
    
    Args:
        text: Sensitive text to mask
        show_chars: Number of characters to show at start and end
        
    Returns:
        Masked string
    """
    if not text or len(text) <= show_chars * 2:
        return "*" * len(text) if text else ""
    
    start = text[:show_chars]
    end = text[-show_chars:]
    middle = "*" * (len(text) - show_chars * 2)
    
    return f"{start}{middle}{end}"
