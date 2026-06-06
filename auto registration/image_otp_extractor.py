#!/usr/bin/env python3
"""
Image OTP Extractor Module v1.0
Extracts OTP codes from images using OCR (Tesseract)
Author: vinayakkumar9000
"""

# Standard library imports
import re
import base64
import io
from typing import Optional, List
from pathlib import Path

# Third-party imports
try:
    from PIL import Image
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from rich.console import Console

console = Console()

# ============================================================================
# OCR CONFIGURATION
# ============================================================================

# Tesseract configuration for better digit recognition
TESSERACT_CONFIG = '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789'

# OTP patterns (4-8 digits)
OTP_PATTERNS = [
    r'\b\d{8}\b',  # 8-digit codes
    r'\b\d{6}\b',  # 6-digit codes (most common)
    r'\b\d{5}\b',  # 5-digit codes
    r'\b\d{4}\b',  # 4-digit codes
]

COMPILED_PATTERNS = [re.compile(pattern) for pattern in OTP_PATTERNS]


# ============================================================================
# IMAGE PREPROCESSING
# ============================================================================

def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Preprocess image for better OCR accuracy.
    
    Args:
        image: PIL Image object
    
    Returns:
        Image.Image: Preprocessed image
    """
    # Convert to grayscale
    image = image.convert('L')
    
    # Increase contrast
    from PIL import ImageEnhance
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)
    
    # Increase sharpness
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2.0)
    
    # Resize if too small (OCR works better on larger images)
    width, height = image.size
    if width < 300 or height < 100:
        scale = max(300 / width, 100 / height)
        new_size = (int(width * scale), int(height * scale))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    return image


# ============================================================================
# OTP EXTRACTION FROM IMAGES
# ============================================================================

def extract_otp_from_image(image_data: bytes, verbose: bool = True) -> Optional[str]:
    """
    Extract OTP from image using OCR.
    
    Args:
        image_data: Raw image bytes
        verbose: Whether to print console messages
    
    Returns:
        Optional[str]: Extracted OTP or None if not found
    """
    if not TESSERACT_AVAILABLE:
        if verbose:
            console.print("[red]✗[/red] Tesseract OCR not available. Install: pip install pytesseract pillow")
        return None
    
    try:
        # Load image
        image = Image.open(io.BytesIO(image_data))
        
        # Preprocess for better OCR
        processed_image = preprocess_image_for_ocr(image)
        
        # Extract text using Tesseract
        text = pytesseract.image_to_string(processed_image, config=TESSERACT_CONFIG)
        
        if verbose:
            console.print(f"[cyan]OCR extracted text:[/cyan] {text[:100]}...")
        
        # Search for OTP patterns
        for pattern in COMPILED_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                otp = matches[0]
                if verbose:
                    console.print(f"[green]✓[/green] OTP extracted from image: {otp}")
                return otp
        
        if verbose:
            console.print("[yellow]⚠[/yellow] No OTP pattern found in OCR text")
        return None
    
    except Exception as e:
        if verbose:
            console.print(f"[red]✗[/red] Image OCR failed: {e}")
        return None


def extract_otp_from_base64_image(base64_data: str, verbose: bool = True) -> Optional[str]:
    """
    Extract OTP from base64-encoded image.
    
    Args:
        base64_data: Base64-encoded image string (with or without data URI prefix)
        verbose: Whether to print console messages
    
    Returns:
        Optional[str]: Extracted OTP or None if not found
    """
    try:
        # Remove data URI prefix if present
        if ',' in base64_data:
            base64_data = base64_data.split(',', 1)[1]
        
        # Decode base64
        image_bytes = base64.b64decode(base64_data)
        
        return extract_otp_from_image(image_bytes, verbose)
    
    except Exception as e:
        if verbose:
            console.print(f"[red]✗[/red] Base64 decode failed: {e}")
        return None


def extract_otp_from_image_file(file_path: str, verbose: bool = True) -> Optional[str]:
    """
    Extract OTP from image file.
    
    Args:
        file_path: Path to image file
        verbose: Whether to print console messages
    
    Returns:
        Optional[str]: Extracted OTP or None if not found
    """
    try:
        with open(file_path, 'rb') as f:
            image_bytes = f.read()
        
        return extract_otp_from_image(image_bytes, verbose)
    
    except Exception as e:
        if verbose:
            console.print(f"[red]✗[/red] Failed to read image file: {e}")
        return None


# ============================================================================
# EMAIL IMAGE EXTRACTION
# ============================================================================

def extract_images_from_email_html(html_content: str) -> List[str]:
    """
    Extract base64-encoded images from HTML email content.
    
    Args:
        html_content: HTML email content
    
    Returns:
        List[str]: List of base64-encoded images
    """
    images = []
    
    # Pattern for base64 images in img tags
    img_pattern = r'<img[^>]+src=["\']data:image/[^;]+;base64,([^"\']+)["\']'
    matches = re.findall(img_pattern, html_content, re.IGNORECASE)
    images.extend(matches)
    
    # Pattern for base64 images in CSS background
    css_pattern = r'background(?:-image)?:\s*url\(["\']?data:image/[^;]+;base64,([^"\')\s]+)["\']?\)'
    matches = re.findall(css_pattern, html_content, re.IGNORECASE)
    images.extend(matches)
    
    return images


def extract_otp_from_email_images(email_content: str, verbose: bool = True) -> Optional[str]:
    """
    Extract OTP from images embedded in email content.
    
    Args:
        email_content: Email content (HTML or text)
        verbose: Whether to print console messages
    
    Returns:
        Optional[str]: Extracted OTP or None if not found
    """
    if not TESSERACT_AVAILABLE:
        if verbose:
            console.print("[yellow]⚠[/yellow] Tesseract OCR not available, skipping image OTP extraction")
        return None
    
    # Extract images from HTML
    images = extract_images_from_email_html(email_content)
    
    if not images:
        if verbose:
            console.print("[cyan]ℹ[/cyan] No embedded images found in email")
        return None
    
    if verbose:
        console.print(f"[cyan]Found {len(images)} embedded image(s), attempting OCR...[/cyan]")
    
    # Try to extract OTP from each image
    for i, base64_image in enumerate(images, 1):
        if verbose:
            console.print(f"[cyan]Processing image {i}/{len(images)}...[/cyan]")
        
        otp = extract_otp_from_base64_image(base64_image, verbose=False)
        if otp:
            if verbose:
                console.print(f"[green]✓[/green] OTP found in image {i}: {otp}")
            return otp
    
    if verbose:
        console.print("[yellow]⚠[/yellow] No OTP found in any embedded images")
    return None


# ============================================================================
# INSTALLATION CHECK
# ============================================================================

def check_tesseract_installation() -> bool:
    """
    Check if Tesseract OCR is properly installed.
    
    Returns:
        bool: True if Tesseract is available, False otherwise
    """
    if not TESSERACT_AVAILABLE:
        console.print("[red]✗[/red] Python packages missing:")
        console.print("  Install with: pip install pytesseract pillow")
        return False
    
    try:
        pytesseract.get_tesseract_version()
        console.print("[green]✓[/green] Tesseract OCR is installed and working")
        return True
    except Exception as e:
        console.print("[red]✗[/red] Tesseract OCR not found:")
        console.print(f"  Error: {e}")
        console.print("\n  Installation instructions:")
        console.print("  - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
        console.print("  - Linux: sudo apt-get install tesseract-ocr")
        console.print("  - macOS: brew install tesseract")
        return False


# ============================================================================
# TESTING
# ============================================================================

def test_image_otp_extraction():
    """Test image OTP extraction with sample data."""
    console.print("\n=== Testing Image OTP Extraction ===\n")
    
    # Check installation
    if not check_tesseract_installation():
        console.print("\n[yellow]⚠[/yellow] Cannot run tests without Tesseract OCR")
        return
    
    # Test with sample HTML email containing base64 image
    sample_html = """
    <html>
    <body>
        <p>Your verification code is:</p>
        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" alt="OTP">
    </body>
    </html>
    """
    
    console.print("Testing with sample HTML email...")
    otp = extract_otp_from_email_images(sample_html, verbose=True)
    
    if otp:
        console.print(f"\n[green]✓[/green] Test passed: OTP = {otp}")
    else:
        console.print("\n[yellow]⚠[/yellow] Test completed (no OTP found in sample)")


if __name__ == "__main__":
    test_image_otp_extraction()
