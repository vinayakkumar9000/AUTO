#!/usr/bin/env python3
"""
Auto Registration Workflow v4.1.0 - Production-Ready Release
Universal automation with magic link support, OCR, and enhanced framework compatibility
Integrates: FormDetectionEngine, FieldHandlers, DynamicFormSupport, MagicLinkHandler, ImageOCR
Author: vinayakkumar9000
"""

# Standard library imports
import asyncio
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Third-party imports
import requests
from playwright.async_api import async_playwright, Page
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "tempmail"))
sys.path.insert(0, str(Path(__file__).parent.parent / "identity"))

# Local module imports
from email_providers import generate_email_with_fallback, smart_poll_inbox_async
from form_detection_engine import FormDetectionEngine
from identity_generator import generate_identity
from integration_layer import UnifiedFormFiller
from magic_link_handler import extract_magic_link_with_context, extract_domain_from_url
from image_otp_extractor import extract_otp_from_email_images
from retry_utils import retry_async, retry_sync

# AI integration (optional)
try:
    from ai_form_analyzer import AIFormHelper
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    AIFormHelper = None

console = Console()
CONFIG_FILE = Path(__file__).parent / "config.json"
LOG_DIR = Path(__file__).parent / ".logs"
SCREENSHOT_DIR = Path(__file__).parent / ".screenshots"

# Create directories
LOG_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR.mkdir(exist_ok=True)

# ============================================================================
# STRUCTURED LOGGING SETUP
# ============================================================================

def setup_logging(session_id: str) -> logging.Logger:
    """Setup structured logging with file output."""
    log_file = LOG_DIR / f"session_{session_id}.log"
    
    logger = logging.getLogger(f"auto_reg_{session_id}")
    logger.setLevel(logging.DEBUG)
    
    # File handler with detailed format
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger

# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================

def load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(config: dict) -> None:
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass





# ============================================================================
# SCREENSHOT CAPTURE
# ============================================================================

async def capture_screenshot(page: Page, session_id: str, stage: str, logger: Optional[logging.Logger] = None) -> str:
    """Capture screenshot for debugging."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{session_id}_{stage}_{timestamp}.png"
        filepath = SCREENSHOT_DIR / filename
        
        await page.screenshot(path=str(filepath), full_page=True)
        
        if logger:
            logger.info(f"Screenshot captured: {filename}")
        
        return str(filepath)
    except Exception as e:
        if logger:
            logger.error(f"Failed to capture screenshot: {e}")
        return ""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _rand_string(length: int) -> str:
    """Generate random string."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))





def extract_otp(email_content: str, api_key: str = None, logger: Optional[logging.Logger] = None) -> Optional[str]:
    """Extract OTP using local-only regex patterns (no AI)."""
    from otp_extractor import extract_otp as extract_otp_local
    
    otp = extract_otp_local(email_content, preferred_length=6, min_confidence=60, verbose=False)
    if otp:
        console.print(f"[green]✓[/green] OTP extracted: {otp}")
        if logger:
            logger.info(f"OTP extracted: {otp}")
        return otp
    
    console.print("[red]✗[/red] No OTP found in email")
    if logger:
        logger.error("No OTP found in email")
    return None

# ============================================================================
# FIELD VALIDATION
# ============================================================================

async def validate_field_filled(locator, expected_value: str, field_name: str, logger: Optional[logging.Logger] = None) -> bool:
    """Validate that field was filled correctly."""
    try:
        actual_value = await locator.input_value()
        
        if actual_value == expected_value:
            if logger:
                logger.info(f"✓ {field_name} validation passed: {expected_value}")
            return True
        else:
            if logger:
                logger.warning(f"✗ {field_name} validation failed. Expected: {expected_value}, Got: {actual_value}")
            return False
    except Exception as e:
        if logger:
            logger.error(f"✗ {field_name} validation error: {e}")
        return False

# ============================================================================
# MAIN AUTOMATION WORKFLOW - ENHANCED
# ============================================================================

async def run_automation(url: str, api_key: str) -> None:
    """Main automation workflow with advanced detection and AI fallbacks."""
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger = setup_logging(session_id)
    
    logger.info("="*80)
    logger.info(f"NEW SESSION STARTED: {session_id}")
    logger.info(f"Target URL: {url}")
    logger.info("="*80)
    
    # Initialize AI helper (optional)
    ai_helper = None
    if AI_AVAILABLE:
        try:
            ai_helper = AIFormHelper()
            if ai_helper.enabled:
                console.print("[cyan]🤖 AI features enabled[/cyan]")
                logger.info("AI helper initialized successfully")
            else:
                console.print("[yellow]⚠ AI features disabled (no API key)[/yellow]")
                logger.info("AI helper disabled - no API key configured")
        except Exception as e:
            console.print(f"[yellow]⚠ AI initialization failed: {e}[/yellow]")
            logger.warning(f"AI helper initialization failed: {e}")
    
    try:
        # Step 1: Generate Identity
        console.print("\n[bold cyan]═══ Step 1: Generate Identity ═══[/bold cyan]")
        logger.info("Generating identity...")
        
        identity = generate_identity()
        logger.info(f"Identity generated: {identity.full_name}, {identity.gender}, {identity.age}y, {identity.city}")
        
        console.print(Panel(
            f"[bold]Name:[/bold] {identity.full_name}\n"
            f"[bold]Gender:[/bold] {identity.gender.capitalize()}\n"
            f"[bold]Age:[/bold] {identity.age}\n"
            f"[bold]Location:[/bold] {identity.city}, {identity.state}",
            title="✨ Generated Identity",
            border_style="cyan"
        ))
        
        # Step 2: Generate Email
        console.print("\n[bold cyan]═══ Step 2: Generate Email ═══[/bold cyan]")
        email, auth_data, provider, _ = generate_email_with_fallback()
        
        # Step 3: Launch Browser
        console.print("\n[bold cyan]═══ Step 3: Launch Browser ═══[/bold cyan]")
        logger.info("Launching browser...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Step 4: Navigate
            console.print(f"[cyan]Navigating to {url}...[/cyan]")
            logger.info(f"Navigating to {url}")
            
            await retry_async(
                lambda: page.goto(url, wait_until="domcontentloaded", timeout=30000),
                label="page load"
            )
            console.print("[green]✓[/green] Page loaded")
            logger.info("Page loaded successfully")
            
            # Capture initial screenshot
            await capture_screenshot(page, session_id, "01_initial", logger)
            
            # Step 4.5: Wait for dynamic content to load
            console.print("\n[bold cyan]═══ Step 4: Wait for Dynamic Content ═══[/bold cyan]")
            logger.info("Waiting for page to fully load (dynamic content)...")
            
            try:
                # Wait for network to be idle (all resources loaded)
                await page.wait_for_load_state("networkidle", timeout=10000)
                console.print("[green]✓[/green] Network idle detected")
                logger.info("Network idle state reached")
            except Exception as e:
                logger.warning(f"Network idle timeout: {e}")
                console.print("[yellow]⚠[/yellow] Network idle timeout, continuing...")
            
            # Additional wait for React/dynamic forms to render
            console.print("[cyan]Waiting 7 seconds for dynamic forms to render...[/cyan]")
            await asyncio.sleep(7)
            logger.info("Dynamic content wait completed")
            
            # Step 5: ADVANCED FORM DETECTION AND FILLING
            console.print("\n[bold cyan]═══ Step 5: Advanced Form Detection ═══[/bold cyan]")
            logger.info("Starting advanced form detection...")
            
            filler = UnifiedFormFiller(page, identity, verbose=True, ai_helper=ai_helper)
            filled_fields = await filler.discover_and_fill_all(email)
            
            logger.info(f"Form filling results: {filled_fields}")
            
            # Validate email field
            if filled_fields.get("email"):
                console.print("[green]✓[/green] Email field filled and validated")
            else:
                logger.error("Email field filling failed")
                await capture_screenshot(page, session_id, "02_email_failed", logger)
                raise Exception("Failed to fill email field")
            
            await asyncio.sleep(0.5)
            await capture_screenshot(page, session_id, "03_form_filled", logger)
            
            # Step 6: Find and Click Next/Continue/Submit Button (AI-Enhanced)
            console.print("\n[bold cyan]═══ Step 6: Navigate Form ═══[/bold cyan]")
            logger.info("Looking for next action button...")
            
            try:
                # Get all visible buttons
                all_buttons = await page.locator('button, [role="button"], input[type="submit"]').all()
                button_texts = []
                button_map = {}
                
                for btn in all_buttons:
                    try:
                        if await btn.is_visible() and await btn.is_enabled():
                            text = await btn.inner_text()
                            text = text.strip()
                            if text:
                                button_texts.append(text)
                                button_map[text] = btn
                    except:
                        continue
                
                logger.info(f"Found {len(button_texts)} visible buttons: {button_texts}")
                
                button_clicked = False
                clicked_button = None
                
                # Try regex patterns first (deterministic)
                for text, btn in button_map.items():
                    if re.search(r'(next|continue|submit|verify|send|get|proceed|start|begin)[\s\-_]*(code|otp|email|step)?', text, re.IGNORECASE):
                        try:
                            await btn.click()
                            console.print(f"[green]✓[/green] Clicked button: {text}")
                            logger.info(f"Button clicked (regex): {text}")
                            button_clicked = True
                            clicked_button = text
                            break
                        except:
                            continue
                
                # AI FALLBACK: If no button clicked and AI available
                if not button_clicked and ai_helper and ai_helper.enabled and button_texts:
                    console.print("[cyan]🤖 Using AI to determine next button...[/cyan]")
                    logger.info("Using AI navigation agent")
                    
                    # Get page context
                    try:
                        page_title = await page.title()
                    except:
                        page_title = "Registration Form"
                    
                    completed_fields = [k for k, v in filled_fields.items() if v]
                    
                    ai_button = ai_helper.get_next_button(button_texts, page_title, completed_fields)
                    
                    if ai_button and ai_button in button_map:
                        try:
                            await button_map[ai_button].click()
                            console.print(f"[green]✓[/green] AI clicked button: {ai_button}")
                            logger.info(f"Button clicked (AI): {ai_button}")
                            button_clicked = True
                            clicked_button = ai_button
                        except Exception as e:
                            logger.error(f"AI button click failed: {e}")
                
                if not button_clicked:
                    console.print("[yellow]⚠[/yellow] No action button found, continuing...")
                    logger.warning("No action button found")
                
                await asyncio.sleep(2)
                await capture_screenshot(page, session_id, "04_code_sent", logger)
            
            except Exception as e:
                logger.warning(f"Send code button error: {e}")
                console.print("[yellow]⚠[/yellow] Send code step skipped")
            
            # Step 7: Wait for Email (Extended timeout for delayed emails)
            console.print("\n[bold cyan]═══ Step 7: Wait for Email ═══[/bold cyan]")
            email_content = await smart_poll_inbox_async(provider, auth_data, timeout=180)
            
            if not email_content:
                logger.error("No email received within timeout")
                await capture_screenshot(page, session_id, "05_no_email", logger)
                raise Exception("No email received within 180 seconds")
            
            logger.info(f"Email received, length: {len(email_content)} chars")
            
            # Step 8: Check for Magic Link or OTP
            console.print("\n[bold cyan]═══ Step 8: Detect Verification Type ═══[/bold cyan]")
            registration_domain = extract_domain_from_url(url)
            magic_link, verification_type = extract_magic_link_with_context(
                email_content, 
                registration_domain, 
                verbose=True
            )
            
            # AI FALLBACK: If magic link detection is ambiguous, use AI
            if not magic_link and ai_helper and ai_helper.enabled:
                console.print("[cyan]🤖 Using AI to identify verification link...[/cyan]")
                logger.info("Attempting AI-based magic link detection")
                
                # Extract all links from email
                import re as regex_module
                links = regex_module.findall(r'https?://[^\s<>"]+', email_content)
                
                if links:
                    try:
                        # Get email subject if available
                        subject_match = regex_module.search(r'Subject:\s*(.+)', email_content)
                        email_subject = subject_match.group(1) if subject_match else "Verification Email"
                        
                        ai_magic_link = ai_helper.find_magic_link(email_subject, email_content, links)
                        
                        if ai_magic_link:
                            magic_link = ai_magic_link
                            verification_type = "magic_link"
                            console.print(f"[green]✓[/green] AI identified magic link")
                            logger.info(f"AI magic link: {magic_link}")
                    except Exception as e:
                        logger.error(f"AI magic link detection failed: {e}")
            
            if verification_type == "magic_link" and magic_link:
                # Handle magic link verification
                console.print(f"[cyan]Opening magic link...[/cyan]")
                logger.info(f"Magic link detected: {magic_link}")
                
                current_url = page.url
                await page.goto(magic_link, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
                
                new_url = page.url
                if new_url != current_url:
                    console.print(f"[green]✓[/green] Magic link verified (URL changed)")
                    logger.info(f"Magic link verification successful: {new_url}")
                    await capture_screenshot(page, session_id, "09_magic_link_verified", logger)
                    
                    # Success - skip OTP steps
                    console.print("\n[bold green]═══════════════════════════════════[/bold green]")
                    console.print("[bold green]    ✓ REGISTRATION COMPLETED    [/bold green]")
                    console.print("[bold green]═══════════════════════════════════[/bold green]\n")
                    
                    console.print(Panel(
                        f"[bold]URL:[/bold] {url}\n"
                        f"[bold]Email:[/bold] {email}\n"
                        f"[bold]Provider:[/bold] {provider}\n"
                        f"[bold]Identity:[/bold] {identity.full_name}\n"
                        f"[bold]Verification:[/bold] Magic Link\n"
                        f"[bold]Final URL:[/bold] {new_url}",
                        title="📋 Registration Summary",
                        border_style="green"
                    ))
                    return
                else:
                    logger.warning("Magic link did not change URL, falling back to OTP")
                    console.print("[yellow]⚠[/yellow] Magic link did not redirect, trying OTP...")
            
            # Step 9: Extract OTP (fallback or primary method)
            console.print("\n[bold cyan]═══ Step 9: Extract OTP ═══[/bold cyan]")
            otp = extract_otp(email_content, api_key, logger)
            
            # Fallback 1: Try image OCR if text extraction failed
            if not otp:
                console.print("[yellow]⚠[/yellow] Text OTP extraction failed, trying image OCR...")
                logger.info("Attempting image-based OTP extraction")
                otp = extract_otp_from_email_images(email_content, verbose=True)
                
                if otp:
                    console.print(f"[green]✓[/green] OTP extracted from image: {otp}")
                    logger.info(f"OTP extracted from image: {otp}")
            
            # Fallback 2: AI OTP extraction (last resort)
            if not otp and ai_helper and ai_helper.enabled:
                console.print("[cyan]🤖 Using AI to extract OTP...[/cyan]")
                logger.info("Attempting AI-based OTP extraction")
                otp = ai_helper.extract_otp(email_content)
                
                if otp:
                    console.print(f"[green]✓[/green] OTP extracted by AI: {otp}")
                    logger.info(f"OTP extracted by AI: {otp}")
            
            if not otp:
                logger.error("Failed to extract OTP from email (all methods: regex, image OCR, AI)")
                logger.debug(f"Email content preview: {email_content[:500]}")
                await capture_screenshot(page, session_id, "06_otp_extract_failed", logger)
                raise Exception("Failed to extract OTP from email using all available methods")
            
            # Step 10: Wait for OTP Field (Dynamic Form Support)
            console.print("\n[bold cyan]═══ Step 10: Enter OTP ═══[/bold cyan]")
            logger.info("Waiting for OTP field...")
            
            otp_field = await filler.wait_for_otp_field(timeout=15)
            
            if not otp_field:
                logger.error("OTP field not found")
                await capture_screenshot(page, session_id, "07_otp_field_missing", logger)
                raise Exception("OTP field did not appear")
            
            await otp_field.fill(otp)
            console.print(f"[green]✓[/green] OTP entered: {otp}")
            logger.info(f"OTP entered: {otp}")
            
            # Validate OTP field
            is_valid = await validate_field_filled(otp_field, otp, "OTP", logger)
            if not is_valid:
                logger.warning("OTP validation failed, retrying...")
                await otp_field.clear()
                await otp_field.fill(otp)
            
            await asyncio.sleep(0.5)
            await capture_screenshot(page, session_id, "08_otp_entered", logger)
            
            # Step 11: Submit
            console.print("\n[bold cyan]═══ Step 11: Submit Form ═══[/bold cyan]")
            logger.info("Looking for submit button...")
            
            submit_buttons = await page.locator('button, [role="button"], input[type="submit"]').all()
            
            for btn in submit_buttons:
                try:
                    if not await btn.is_visible() or not await btn.is_enabled():
                        continue
                    
                    text = await btn.inner_text()
                    if re.search(r'(submit|verify|confirm|continue|next|proceed)', text, re.IGNORECASE):
                        await btn.click()
                        console.print("[green]✓[/green] Form submitted")
                        logger.info(f"Submit button clicked: {text}")
                        break
                except:
                    continue
            
            await asyncio.sleep(3)
            await capture_screenshot(page, session_id, "09_submitted", logger)
            
            current_url = page.url
            logger.info(f"Final URL: {current_url}")
            
            # Success Summary
            console.print("\n[bold green]═══════════════════════════════════[/bold green]")
            console.print("[bold green]    ✓ REGISTRATION COMPLETED    [/bold green]")
            console.print("[bold green]═══════════════════════════════════[/bold green]\n")
            
            logger.info("REGISTRATION COMPLETED SUCCESSFULLY")
            logger.info(f"Session ID: {session_id}")
            logger.info(f"Log file: {LOG_DIR / f'session_{session_id}.log'}")
            
            console.print(Panel(
                f"[bold]URL:[/bold] {url}\n"
                f"[bold]Email:[/bold] {email}\n"
                f"[bold]Provider:[/bold] {provider}\n"
                f"[bold]Identity:[/bold] {identity.full_name}\n"
                f"[bold]OTP:[/bold] {otp}\n"
                f"[bold]Password:[/bold] {filler.get_generated_password() or 'N/A'}\n"
                f"[bold]Username:[/bold] {filler.get_generated_username() or 'N/A'}\n"
                f"[bold]Final URL:[/bold] {current_url}\n"
                f"[bold]Session ID:[/bold] {session_id}\n"
                f"[bold]Log:[/bold] .logs/session_{session_id}.log",
                title="📋 Registration Summary",
                border_style="green"
            ))
    
    except Exception as e:
        console.print(f"\n[red]✗ Error:[/red] {e}")
        logger.error(f"REGISTRATION FAILED: {e}", exc_info=True)
        
        # Capture error screenshot
        try:
            async with async_playwright() as p:
                if 'page' in locals():
                    await capture_screenshot(page, session_id, "99_error", logger)
        except:
            pass
        
        raise

# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Main CLI entry point."""
    console.print("\n[bold cyan]╔═══════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║   Auto Registration Workflow v4.0    ║[/bold cyan]")
    console.print("[bold cyan]║        ENHANCED EDITION              ║[/bold cyan]")
    console.print("[bold cyan]╚═══════════════════════════════════════╝[/bold cyan]\n")
    
    # Get URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = Prompt.ask("Enter registration URL")
    
    if not url.startswith("http"):
        console.print("[red]✗[/red] Invalid URL. Must start with http:// or https://")
        return
    
    # Run automation (AI-free, no API key needed)
    try:
        asyncio.run(run_automation(url, api_key=""))
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Aborted by user[/yellow]")
        sys.exit(130)
