#!/usr/bin/env python3
"""
Magic Link Handler Module v1.0
Detects and handles magic link verification emails
Author: vinayakkumar9000
"""

# Standard library imports
import re
from typing import Optional, Tuple
from urllib.parse import urlparse

# Third-party imports
from rich.console import Console

console = Console()

# ============================================================================
# MAGIC LINK DETECTION PATTERNS
# ============================================================================

MAGIC_LINK_PATTERNS = [
    # Standard verification links
    r'https?://[^\s<>"]+/verify[^\s<>"]*',
    r'https?://[^\s<>"]+/confirm[^\s<>"]*',
    r'https?://[^\s<>"]+/activate[^\s<>"]*',
    r'https?://[^\s<>"]+/validation[^\s<>"]*',
    r'https?://[^\s<>"]+/authentication[^\s<>"]*',
    
    # Token-based links
    r'https?://[^\s<>"]+[?&]token=[^\s<>"&]+',
    r'https?://[^\s<>"]+[?&]code=[^\s<>"&]+',
    r'https?://[^\s<>"]+[?&]key=[^\s<>"&]+',
    r'https?://[^\s<>"]+[?&]verification=[^\s<>"&]+',
    
    # Email-specific verification
    r'https?://[^\s<>"]+/email[/-]verify[^\s<>"]*',
    r'https?://[^\s<>"]+/email[/-]confirm[^\s<>"]*',
    
    # Common SaaS patterns
    r'https?://[^\s<>"]+\.notion\.so/[^\s<>"]+',
    r'https?://[^\s<>"]+\.slack\.com/[^\s<>"]+',
    r'https?://github\.com/[^\s<>"]+/verify[^\s<>"]*',
]

# Compile patterns for performance
COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in MAGIC_LINK_PATTERNS]

# Patterns to exclude (tracking, unsubscribe, etc.)
EXCLUDE_PATTERNS = [
    r'unsubscribe',
    r'preferences',
    r'settings',
    r'privacy',
    r'terms',
    r'help',
    r'support',
    r'contact',
    r'about',
    r'tracking',
    r'pixel',
    r'beacon',
]

COMPILED_EXCLUDE = [re.compile(pattern, re.IGNORECASE) for pattern in EXCLUDE_PATTERNS]


# ============================================================================
# MAGIC LINK DETECTION
# ============================================================================

def extract_magic_link(email_content: str, registration_domain: Optional[str] = None) -> Optional[str]:
    """
    Extract magic link from email content.
    
    Args:
        email_content: Raw email content (text or HTML)
        registration_domain: Optional domain to match against (e.g., "example.com")
    
    Returns:
        Optional[str]: Magic link URL or None if not found
    """
    if not email_content:
        return None
    
    # Find all potential links
    potential_links = []
    
    for pattern in COMPILED_PATTERNS:
        matches = pattern.findall(email_content)
        potential_links.extend(matches)
    
    if not potential_links:
        return None
    
    # Filter out excluded links
    filtered_links = []
    for link in potential_links:
        is_excluded = False
        for exclude_pattern in COMPILED_EXCLUDE:
            if exclude_pattern.search(link):
                is_excluded = True
                break
        
        if not is_excluded:
            filtered_links.append(link)
    
    if not filtered_links:
        return None
    
    # If registration domain provided, prefer links from same domain
    if registration_domain:
        domain_links = []
        for link in filtered_links:
            parsed = urlparse(link)
            if registration_domain in parsed.netloc:
                domain_links.append(link)
        
        if domain_links:
            return domain_links[0]  # Return first matching domain link
    
    # Return first filtered link
    return filtered_links[0]


def detect_verification_type(email_content: str) -> str:
    """
    Detect whether email contains magic link or OTP.
    
    Args:
        email_content: Raw email content
    
    Returns:
        str: "magic_link", "otp", or "unknown"
    """
    if not email_content:
        return "unknown"
    
    # Check for magic link
    magic_link = extract_magic_link(email_content)
    if magic_link:
        return "magic_link"
    
    # Check for OTP patterns
    otp_patterns = [
        r'\b\d{4,8}\b',  # 4-8 digit codes
        r'code[:\s]+\d{4,8}',
        r'otp[:\s]+\d{4,8}',
        r'verification[:\s]+\d{4,8}',
    ]
    
    for pattern in otp_patterns:
        if re.search(pattern, email_content, re.IGNORECASE):
            return "otp"
    
    return "unknown"


# ============================================================================
# MAGIC LINK VALIDATION
# ============================================================================

def is_valid_magic_link(url: str, registration_domain: Optional[str] = None) -> bool:
    """
    Validate if URL is a legitimate magic link.
    
    Args:
        url: URL to validate
        registration_domain: Optional domain to match against
    
    Returns:
        bool: True if valid magic link, False otherwise
    """
    if not url or not url.startswith(('http://', 'https://')):
        return False
    
    try:
        parsed = urlparse(url)
        
        # Must have valid domain
        if not parsed.netloc:
            return False
        
        # Check against exclude patterns
        for pattern in COMPILED_EXCLUDE:
            if pattern.search(url):
                return False
        
        # If registration domain provided, must match
        if registration_domain and registration_domain not in parsed.netloc:
            return False
        
        return True
    
    except Exception:
        return False


# ============================================================================
# MAGIC LINK EXTRACTION WITH CONTEXT
# ============================================================================

def extract_magic_link_with_context(
    email_content: str,
    registration_domain: Optional[str] = None,
    verbose: bool = True
) -> Tuple[Optional[str], str]:
    """
    Extract magic link with detection context.
    
    Args:
        email_content: Raw email content
        registration_domain: Optional domain to match
        verbose: Whether to print console messages
    
    Returns:
        Tuple[Optional[str], str]: (magic_link, verification_type)
    """
    verification_type = detect_verification_type(email_content)
    
    if verification_type == "magic_link":
        magic_link = extract_magic_link(email_content, registration_domain)
        
        if magic_link and is_valid_magic_link(magic_link, registration_domain):
            if verbose:
                console.print(f"[green]✓[/green] Magic link detected: {magic_link[:60]}...")
            return magic_link, "magic_link"
    
    if verbose and verification_type == "otp":
        console.print("[cyan]ℹ[/cyan] OTP-based verification detected")
    
    return None, verification_type


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_domain_from_url(url: str) -> Optional[str]:
    """
    Extract domain from URL.
    
    Args:
        url: Full URL
    
    Returns:
        Optional[str]: Domain or None if invalid
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return None


def clean_magic_link(url: str) -> str:
    """
    Clean magic link by removing tracking parameters.
    
    Args:
        url: Raw magic link URL
    
    Returns:
        str: Cleaned URL
    """
    # Remove common tracking parameters
    tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']
    
    try:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Remove tracking parameters
        cleaned_params = {k: v for k, v in query_params.items() if k not in tracking_params}
        
        # Rebuild URL
        cleaned_query = urlencode(cleaned_params, doseq=True)
        cleaned_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            cleaned_query,
            parsed.fragment
        ))
        
        return cleaned_url
    
    except Exception:
        return url  # Return original if cleaning fails


# ============================================================================
# TESTING
# ============================================================================

def test_magic_link_detection():
    """Test magic link detection with sample emails."""
    
    test_cases = [
        # Magic link email
        """
        Welcome to Example!
        
        Click here to verify your email:
        https://example.com/verify?token=abc123xyz
        
        This link expires in 24 hours.
        """,
        
        # OTP email
        """
        Your verification code is: 123456
        
        Enter this code to complete registration.
        """,
        
        # Mixed email (magic link + OTP)
        """
        Verification Code: 789012
        
        Or click here: https://example.com/email-verify/abc123
        """,
    ]
    
    for i, email in enumerate(test_cases, 1):
        print(f"\n=== Test Case {i} ===")
        magic_link, verification_type = extract_magic_link_with_context(email, verbose=True)
        print(f"Type: {verification_type}")
        if magic_link:
            print(f"Link: {magic_link}")


if __name__ == "__main__":
    test_magic_link_detection()
