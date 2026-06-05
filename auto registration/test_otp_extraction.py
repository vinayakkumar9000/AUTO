#!/usr/bin/env python3
"""
Unit Tests for OTP Extraction
Tests all 30+ regex patterns against various email formats
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from otp_extractor import extract_otp

# ============================================================================
# TEST CASES
# ============================================================================

TEST_CASES = [
    # Standard formats
    {
        "name": "Standard - Your code is",
        "email": "Your verification code is: 123456. Please enter it to continue.",
        "expected": "123456"
    },
    {
        "name": "Standard - Code:",
        "email": "Code: 789012\nValid for 10 minutes.",
        "expected": "789012"
    },
    {
        "name": "Standard - OTP:",
        "email": "Your OTP: 456789",
        "expected": "456789"
    },
    
    # HTML formats
    {
        "name": "HTML - Strong tag",
        "email": "<div>Your verification code is <strong>234567</strong></div>",
        "expected": "234567"
    },
    {
        "name": "HTML - Bold tag",
        "email": "<p>Code: <b>345678</b></p>",
        "expected": "345678"
    },
    {
        "name": "HTML - Span with class",
        "email": '<span class="otp-code">567890</span>',
        "expected": "567890"
    },
    {
        "name": "HTML - Complex structure",
        "email": """
        <html>
            <body>
                <div class="email-content">
                    <p>Hello,</p>
                    <p>Your verification code is:</p>
                    <h2 style="color: blue;">678901</h2>
                    <p>Please enter this code to verify your account.</p>
                </div>
            </body>
        </html>
        """,
        "expected": "678901"
    },
    
    # Obfuscated formats
    {
        "name": "Obfuscated - Spaced digits",
        "email": "Your code: 1 2 3 4 5 6",
        "expected": "123456"
    },
    {
        "name": "Obfuscated - Hyphenated",
        "email": "Verification code: 7-8-9-0-1-2",
        "expected": "789012"
    },
    {
        "name": "Obfuscated - Mixed spacing",
        "email": "Code is 4 5 6 7 8 9. Enter it now.",
        "expected": "456789"
    },
    
    # Multi-language
    {
        "name": "Spanish",
        "email": "Tu código de verificación es: 234567",
        "expected": "234567"
    },
    {
        "name": "French",
        "email": "Votre code de vérification: 345678",
        "expected": "345678"
    },
    {
        "name": "German",
        "email": "Ihr Bestätigungscode: 567890",
        "expected": "567890"
    },
    
    # Edge cases
    {
        "name": "Edge - Parentheses",
        "email": "Please enter code (678901) to continue",
        "expected": "678901"
    },
    {
        "name": "Edge - Brackets",
        "email": "Your code [789012] expires in 5 minutes",
        "expected": "789012"
    },
    {
        "name": "Edge - Quotes",
        "email": 'Enter code "456789" to verify',
        "expected": "456789"
    },
    {
        "name": "Edge - Multiple codes (should get first)",
        "email": "Your code is 123456. If that doesn't work, try 789012.",
        "expected": "123456"
    },
    
    # 4-digit codes
    {
        "name": "4-digit code",
        "email": "Your PIN: 1234",
        "expected": "1234"
    },
    
    # 8-digit codes
    {
        "name": "8-digit code",
        "email": "Verification code: 12345678",
        "expected": "12345678"
    },
    
    # Real-world examples
    {
        "name": "Real - Gmail style",
        "email": """
        Hi there,
        
        Your Google verification code is 234567
        
        This code will expire in 10 minutes.
        
        If you didn't request this code, you can safely ignore this email.
        """,
        "expected": "234567"
    },
    {
        "name": "Real - GitHub style",
        "email": """
        [GitHub] Please verify your device
        
        Enter this code: 345678
        
        This code expires in 15 minutes.
        """,
        "expected": "345678"
    },
    {
        "name": "Real - Microsoft style",
        "email": """
        Microsoft account security code
        
        Your security code is: 567890
        
        Use this code to verify your identity.
        """,
        "expected": "567890"
    },
    {
        "name": "Real - Banking style",
        "email": """
        One-Time Password (OTP)
        
        Your OTP for transaction verification is 678901
        
        Valid for 5 minutes. Do not share this code.
        """,
        "expected": "678901"
    },
    
    # Tricky cases
    {
        "name": "Tricky - Order number before code",
        "email": "Order #123456. Your verification code is: 789012",
        "expected": "789012"
    },
    {
        "name": "Tricky - Phone number in email",
        "email": "Call us at +1-234-567-8900. Your code: 456789",
        "expected": "456789"
    },
    {
        "name": "Tricky - Date before code",
        "email": "Date: 2026-01-15. Verification code: 234567",
        "expected": "234567"
    },
    
    # Negative cases (should fail)
    {
        "name": "Negative - No code",
        "email": "Please check your email for the verification code.",
        "expected": None
    },
    {
        "name": "Negative - Only 3 digits",
        "email": "Your code is 123",
        "expected": None
    },
    {
        "name": "Negative - Only 9 digits",
        "email": "Your code is 123456789",
        "expected": None
    },
]


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_tests():
    """Run all OTP extraction tests."""
    print("\n" + "="*80)
    print("OTP EXTRACTION UNIT TESTS")
    print("="*80 + "\n")
    
    passed = 0
    failed = 0
    failed_tests = []
    
    for i, test in enumerate(TEST_CASES, 1):
        name = test["name"]
        email = test["email"]
        expected = test["expected"]
        
        # Extract OTP
        result = extract_otp(email, preferred_length=6, min_confidence=60, verbose=False)
        
        # Check result
        if result == expected:
            print(f"✓ Test {i:2d}: {name:<40} PASS")
            passed += 1
        else:
            print(f"✗ Test {i:2d}: {name:<40} FAIL (expected: {expected}, got: {result})")
            failed += 1
            failed_tests.append({
                "name": name,
                "expected": expected,
                "got": result,
                "email": email[:100] + "..." if len(email) > 100 else email
            })
    
    # Summary
    print("\n" + "="*80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(TEST_CASES)} tests")
    print(f"Success Rate: {passed/len(TEST_CASES)*100:.1f}%")
    print("="*80)
    
    # Show failed tests details
    if failed_tests:
        print("\n" + "="*80)
        print("FAILED TESTS DETAILS")
        print("="*80)
        for test in failed_tests:
            print(f"\nTest: {test['name']}")
            print(f"Expected: {test['expected']}")
            print(f"Got: {test['got']}")
            print(f"Email preview: {test['email']}")
    
    return passed, failed


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    passed, failed = run_tests()
    sys.exit(0 if failed == 0 else 1)
