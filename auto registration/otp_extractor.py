#!/usr/bin/env python3
"""
Local-Only OTP Extraction Module
No AI, no API calls, pure regex-based extraction
Author: vinayakkumar9000
Version: 1.0.0
"""

import re
from typing import Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class OTPMatch:
    """Represents a potential OTP match with confidence score."""
    code: str
    confidence: int
    pattern_name: str
    context: str


# ============================================================================
# ENHANCED OTP PATTERNS WITH CONFIDENCE SCORING
# ============================================================================

# Pattern format: (regex, confidence_score, pattern_name)
OTP_PATTERNS = [
    # High confidence - explicit context with 6 digits
    (r'(?:verification|verify|confirmation|confirm)\s*code[\s:]*(\d{6})', 100, 'verify_6digit'),
    (r'(?:otp|one[\s-]?time[\s-]?password)[\s:]*(\d{6})', 100, 'otp_6digit'),
    (r'(?:authentication|auth)\s*code[\s:]*(\d{6})', 100, 'auth_6digit'),
    (r'(?:security|access)\s*code[\s:]*(\d{6})', 95, 'security_6digit'),
    
    # High confidence - explicit context with 4 digits
    (r'(?:verification|verify|confirmation|confirm)\s*code[\s:]*(\d{4})', 95, 'verify_4digit'),
    (r'(?:otp|one[\s-]?time[\s-]?password)[\s:]*(\d{4})', 95, 'otp_4digit'),
    (r'(?:pin|personal\s*identification)[\s:]*(\d{4})', 95, 'pin_4digit'),
    
    # High confidence - explicit context with 8 digits
    (r'(?:verification|verify|confirmation|confirm)\s*code[\s:]*(\d{8})', 90, 'verify_8digit'),
    (r'(?:otp|one[\s-]?time[\s-]?password)[\s:]*(\d{8})', 90, 'otp_8digit'),
    
    # Medium confidence - keyword followed by digits within 50 chars
    (r'(?:code|otp|verif|pin|token)[\s\S]{0,50}?(\d{6})', 85, 'keyword_6digit'),
    (r'(?:code|otp|verif|pin|token)[\s\S]{0,50}?(\d{4})', 80, 'keyword_4digit'),
    (r'(?:code|otp|verif|pin|token)[\s\S]{0,50}?(\d{8})', 75, 'keyword_8digit'),
    
    # Medium confidence - "your code is" patterns
    (r'your\s+(?:verification|confirmation|security|access)?\s*code\s+is[\s:]*(\d{4,8})', 90, 'your_code_is'),
    (r'code\s+is[\s:]*(\d{4,8})', 85, 'code_is'),
    
    # Medium confidence - HTML/email specific patterns
    (r'<strong[^>]*>(\d{6})</strong>', 85, 'html_strong_6digit'),
    (r'<b[^>]*>(\d{6})</b>', 85, 'html_bold_6digit'),
    (r'<span[^>]*>(\d{6})</span>', 80, 'html_span_6digit'),
    
    # Medium confidence - formatted codes
    (r'(\d{3}[\s-]\d{3})', 80, 'formatted_6digit'),  # 123-456 or 123 456
    (r'(\d{4}[\s-]\d{4})', 75, 'formatted_8digit'),  # 1234-5678
    
    # Lower confidence - standalone digits (prefer 6-digit)
    (r'\b(\d{6})\b', 70, 'standalone_6digit'),
    (r'\b(\d{4})\b', 60, 'standalone_4digit'),
    (r'\b(\d{8})\b', 55, 'standalone_8digit'),
    
    # Lower confidence - digits in brackets or quotes
    (r'["\'](\d{6})["\']', 75, 'quoted_6digit'),
    (r'\[(\d{6})\]', 75, 'bracketed_6digit'),
    (r'\((\d{6})\)', 75, 'parenthesized_6digit'),
]

# Patterns to EXCLUDE (these are NOT OTPs)
EXCLUSION_PATTERNS = [
    r'\b\d{4}[-/]\d{2}[-/]\d{2}\b',  # Dates (YYYY-MM-DD)
    r'\b\d{2}[-/]\d{2}[-/]\d{4}\b',  # Dates (DD-MM-YYYY)
    r'\b\d{10,}\b',                   # Phone numbers (10+ digits)
    r'\$\d+',                         # Prices
    r'#\d+',                          # Order/ticket numbers
    r'order[\s#]*\d+',                # Order numbers
    r'invoice[\s#]*\d+',              # Invoice numbers
    r'ticket[\s#]*\d+',               # Ticket numbers
    r'transaction[\s#]*\d+',          # Transaction IDs
    r'reference[\s#]*\d+',            # Reference numbers
    r'\d+\s*(?:am|pm|AM|PM)',         # Times
    r'\d+\s*(?:years?|months?|days?|hours?|minutes?|seconds?)',  # Durations
]


# ============================================================================
# OTP EXTRACTION ENGINE
# ============================================================================

class OTPExtractor:
    """Local-only OTP extraction using enhanced regex patterns."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), confidence, name)
            for pattern, confidence, name in OTP_PATTERNS
        ]
        self.compiled_exclusions = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in EXCLUSION_PATTERNS
        ]
    
    def log(self, message: str):
        """Log debug messages if verbose enabled."""
        if self.verbose:
            print(f"[OTP] {message}")
    
    def _is_excluded(self, text: str, code: str) -> bool:
        """Check if the code matches any exclusion pattern."""
        # Check if code appears in excluded context
        for exclusion_pattern in self.compiled_exclusions:
            if exclusion_pattern.search(text):
                # Check if our code is part of the excluded match
                for match in exclusion_pattern.finditer(text):
                    if code in match.group(0):
                        return True
        return False
    
    def _clean_code(self, code: str) -> str:
        """Clean and normalize extracted code."""
        # Remove spaces, hyphens, and other separators
        cleaned = re.sub(r'[\s\-]', '', code)
        return cleaned
    
    def extract_all_candidates(self, email_content: str) -> List[OTPMatch]:
        """
        Extract all potential OTP candidates with confidence scores.
        
        Args:
            email_content: Email text content
        
        Returns:
            List of OTPMatch objects sorted by confidence (highest first)
        """
        candidates = []
        seen_codes = set()
        
        # Normalize content (remove excessive whitespace)
        content = re.sub(r'\s+', ' ', email_content)
        
        for pattern, confidence, name in self.compiled_patterns:
            for match in pattern.finditer(content):
                code = match.group(1)
                cleaned_code = self._clean_code(code)
                
                # Skip if already seen
                if cleaned_code in seen_codes:
                    continue
                
                # Skip if excluded
                if self._is_excluded(content, cleaned_code):
                    self.log(f"Excluded: {cleaned_code} (matched exclusion pattern)")
                    continue
                
                # Get surrounding context (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)
                context = content[start:end]
                
                candidates.append(OTPMatch(
                    code=cleaned_code,
                    confidence=confidence,
                    pattern_name=name,
                    context=context
                ))
                
                seen_codes.add(cleaned_code)
                self.log(f"Found candidate: {cleaned_code} (confidence={confidence}, pattern={name})")
        
        # Sort by confidence (highest first)
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        
        return candidates
    
    def extract_best(self, email_content: str, min_confidence: int = 60) -> Optional[str]:
        """
        Extract the most likely OTP code.
        
        Args:
            email_content: Email text content
            min_confidence: Minimum confidence threshold (0-100)
        
        Returns:
            OTP code string or None if not found
        """
        candidates = self.extract_all_candidates(email_content)
        
        if not candidates:
            self.log("No OTP candidates found")
            return None
        
        # Get highest confidence candidate
        best = candidates[0]
        
        if best.confidence < min_confidence:
            self.log(f"Best candidate confidence ({best.confidence}) below threshold ({min_confidence})")
            return None
        
        self.log(f"Selected OTP: {best.code} (confidence={best.confidence}, pattern={best.pattern_name})")
        return best.code
    
    def extract_with_fallback(
        self,
        email_content: str,
        preferred_length: int = 6,
        min_confidence: int = 60
    ) -> Optional[str]:
        """
        Extract OTP with preference for specific length.
        
        Args:
            email_content: Email text content
            preferred_length: Preferred OTP length (4, 6, or 8)
            min_confidence: Minimum confidence threshold
        
        Returns:
            OTP code string or None if not found
        """
        candidates = self.extract_all_candidates(email_content)
        
        if not candidates:
            return None
        
        # First, try to find preferred length with high confidence
        for candidate in candidates:
            if len(candidate.code) == preferred_length and candidate.confidence >= min_confidence:
                self.log(f"Found preferred length OTP: {candidate.code}")
                return candidate.code
        
        # Fallback to highest confidence regardless of length
        best = candidates[0]
        if best.confidence >= min_confidence:
            self.log(f"Using best candidate: {best.code} (length={len(best.code)})")
            return best.code
        
        return None


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def extract_otp(
    email_content: str,
    preferred_length: int = 6,
    min_confidence: int = 60,
    verbose: bool = False
) -> Optional[str]:
    """
    Extract OTP from email content (convenience function).
    
    Args:
        email_content: Email text content
        preferred_length: Preferred OTP length (4, 6, or 8)
        min_confidence: Minimum confidence threshold (0-100)
        verbose: Enable debug logging
    
    Returns:
        OTP code string or None if not found
    
    Example:
        >>> otp = extract_otp(email_text)
        >>> print(otp)  # "123456"
    """
    extractor = OTPExtractor(verbose=verbose)
    return extractor.extract_with_fallback(email_content, preferred_length, min_confidence)


def extract_otp_all_candidates(
    email_content: str,
    verbose: bool = False
) -> List[Tuple[str, int, str]]:
    """
    Extract all OTP candidates with confidence scores.
    
    Args:
        email_content: Email text content
        verbose: Enable debug logging
    
    Returns:
        List of (code, confidence, pattern_name) tuples
    
    Example:
        >>> candidates = extract_otp_all_candidates(email_text)
        >>> for code, conf, pattern in candidates:
        ...     print(f"{code}: {conf}% ({pattern})")
    """
    extractor = OTPExtractor(verbose=verbose)
    matches = extractor.extract_all_candidates(email_content)
    return [(m.code, m.confidence, m.pattern_name) for m in matches]


# ============================================================================
# CLI TESTING INTERFACE
# ============================================================================

def main():
    """CLI interface for testing OTP extraction."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python otp_extractor.py <email_file>")
        print("   or: python otp_extractor.py --test")
        sys.exit(1)
    
    if sys.argv[1] == "--test":
        # Run test cases
        test_cases = [
            ("Your verification code is 123456", "123456"),
            ("OTP: 987654", "987654"),
            ("Your code is 4321", "4321"),
            ("Confirmation code: 12345678", "12345678"),
            ("<strong>567890</strong>", "567890"),
            ("Order #123456 has been placed", None),  # Should be excluded
        ]
        
        print("Running test cases...\n")
        extractor = OTPExtractor(verbose=True)
        
        for content, expected in test_cases:
            print(f"Input: {content}")
            result = extractor.extract_best(content)
            status = "✓" if result == expected else "✗"
            print(f"Result: {result} (expected: {expected}) {status}\n")
    else:
        # Extract from file
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            content = f.read()
        
        extractor = OTPExtractor(verbose=True)
        otp = extractor.extract_best(content)
        
        if otp:
            print(f"\n✓ Extracted OTP: {otp}")
        else:
            print("\n✗ No OTP found")
            print("\nAll candidates:")
            candidates = extractor.extract_all_candidates(content)
            for match in candidates:
                print(f"  {match.code}: {match.confidence}% ({match.pattern_name})")


if __name__ == "__main__":
    main()
