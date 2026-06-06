#!/usr/bin/env python3
"""
Auto Registration Workflow v4.0.0 - AI-Free Production Release
Universal, robust automation with advanced form detection
Integrates: FormDetectionEngine, FieldHandlers, DynamicFormSupport
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
from retry_utils import retry_async, retry_sync

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
    """Main automation workflow with advanced detection."""
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger = setup_logging(session_id)
    
    logger.info("="*80)
    logger.info(f"NEW SESSION STARTED: {session_id}")
    logger.info(f"Target URL: {url}")
    logger.info("="*80)
    
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
                label="page load",
                logger=logger
            )
            console.print("[green]✓[/green] Page loaded")
            logger.info("Page loaded successfully")
            
            # Capture initial screenshot
            await capture_screenshot(page, session_id, "01_initial", logger)
            
            # Step 5: ADVANCED FORM DETECTION AND FILLING
            console.print("\n[bold cyan]═══ Step 4: Advanced Form Detection ═══[/bold cyan]")
            logger.info("Starting advanced form detection...")
            
            filler = UnifiedFormFiller(page, identity, verbose=True)
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
            
            # Step 6: Find and Click Send Code Button
            console.print("\n[bold cyan]═══ Step 5: Send Verification Code ═══[/bold cyan]")
            logger.info("Looking for send code button...")
            
            try:
                # Use FormDetectionEngine to find button
                send_buttons = await page.locator('button, [role="button"], input[type="submit"]').all()
                
                send_clicked = False
                for btn in send_buttons:
                    try:
                        if not await btn.is_visible() or not await btn.is_enabled():
                            continue
                        
                        text = await btn.inner_text()
                        if re.search(r'(send|get|request|resend|generate)[\s\-_]*(code|otp|email)', text, re.IGNORECASE):
                            await btn.click()
                            console.print("[green]✓[/green] Send Code clicked")
                            logger.info(f"Send code button clicked: {text}")
                            send_clicked = True
                            break
                    except:
                        continue
                
                if not send_clicked:
                    console.print("[yellow]⚠[/yellow] No Send Code button found, assuming auto-send")
                    logger.warning("No send code button found")
                
                await asyncio.sleep(2)
                await capture_screenshot(page, session_id, "04_code_sent", logger)
            
            except Exception as e:
                logger.warning(f"Send code button error: {e}")
                console.print("[yellow]⚠[/yellow] Send code step skipped")
            
            # Step 7: Wait for Email
            console.print("\n[bold cyan]═══ Step 6: Wait for Email ═══[/bold cyan]")
            email_content = await smart_poll_inbox_async(provider, auth_data, timeout=60)
            
            if not email_content:
                logger.error("No email received within timeout")
                await capture_screenshot(page, session_id, "05_no_email", logger)
                raise Exception("No email received within 60 seconds")
            
            logger.info(f"Email received, length: {len(email_content)} chars")
            
            # Step 8: Extract OTP
            console.print("\n[bold cyan]═══ Step 7: Extract OTP ═══[/bold cyan]")
            otp = extract_otp(email_content, api_key, logger)
            
            if not otp:
                logger.error("Failed to extract OTP from email")
                logger.debug(f"Email content preview: {email_content[:500]}")
                await capture_screenshot(page, session_id, "06_otp_extract_failed", logger)
                raise Exception("Failed to extract OTP from email")
            
            # Step 9: Wait for OTP Field (Dynamic Form Support)
            console.print("\n[bold cyan]═══ Step 8: Enter OTP ═══[/bold cyan]")
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
            
            # Step 10: Submit
            console.print("\n[bold cyan]═══ Step 9: Submit Form ═══[/bold cyan]")
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
