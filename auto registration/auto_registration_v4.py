#!/usr/bin/env python3
"""
Auto Registration Workflow v3.1.2 - AI-Free Production Release
Universal, robust automation with advanced form detection
Integrates: FormDetectionEngine, FieldHandlers, DynamicFormSupport
Author: vinayakkumar9000
"""

import asyncio
import html
import json
import re
import sys
import time
import random
import string
import logging
from pathlib import Path
from typing import Optional, Tuple, Callable, Any
from datetime import datetime

import requests
from playwright.async_api import async_playwright, Page, Browser
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "tempmail"))
sys.path.insert(0, str(Path(__file__).parent.parent / "identity"))

from identity_generator import generate_identity
from integration_layer import UnifiedFormFiller
from form_detection_engine import FormDetectionEngine

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

def get_api_key() -> str:
    """Get API key from config or prompt user."""
    config = load_config()
    if "freemodel_api_key" in config and config["freemodel_api_key"]:
        return config["freemodel_api_key"]
    
    console.print("\n[cyan]FreeModel API Key Required[/cyan]")
    console.print("Get your key from: https://freemodel.dev")
    api_key = Prompt.ask("Enter your FreeModel API key", password=True)
    
    config["freemodel_api_key"] = api_key
    save_config(config)
    return api_key

# ============================================================================
# RETRY HELPERS
# ============================================================================

async def retry_async(fn: Callable, retries: int = 3, delay: float = 1.5, label: str = "step", logger: Optional[logging.Logger] = None) -> Any:
    """Retry async function with logging."""
    for attempt in range(retries):
        try:
            return await fn()
        except Exception as e:
            if logger:
                logger.warning(f"Retry {label} (attempt {attempt + 1}/{retries}): {e}")
            if attempt == retries - 1:
                raise
            console.print(f"[yellow]Retry {label} ({attempt + 1}/{retries}): {e}[/yellow]")
            await asyncio.sleep(delay)

def retry_sync(fn: Callable, retries: int = 3, delay: float = 1.5, label: str = "step", logger: Optional[logging.Logger] = None) -> Any:
    """Retry sync function with logging."""
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if logger:
                logger.warning(f"Retry {label} (attempt {attempt + 1}/{retries}): {e}")
            if attempt == retries - 1:
                raise
            console.print(f"[yellow]Retry {label} ({attempt + 1}/{retries}): {e}[/yellow]")
            time.sleep(delay)

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

# ============================================================================
# EMAIL PROVIDER: MAIL.TM
# ============================================================================

def generate_mailtm_email() -> Tuple[str, str, str]:
    """Generate mail.tm email. Returns: (email, password, auth_token)"""
    BASE = "https://api.mail.tm"
    
    domains_res = requests.get(f"{BASE}/domains?page=1", timeout=15)
    domains_res.raise_for_status()
    domain = domains_res.json()["hydra:member"][0]["domain"]
    
    local_part = _rand_string(10)
    address = f"{local_part}@{domain}"
    password = _rand_string(12)
    
    account_res = requests.post(f"{BASE}/accounts", json={"address": address, "password": password}, timeout=15)
    account_res.raise_for_status()
    
    token_res = requests.post(f"{BASE}/token", json={"address": address, "password": password}, timeout=15)
    token_res.raise_for_status()
    auth = token_res.json()["token"]
    
    return address, password, auth

def check_mailtm_inbox(auth_token: str) -> Optional[str]:
    """Check mail.tm inbox once. Returns email content or None."""
    BASE = "https://api.mail.tm"
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    inbox_res = requests.get(f"{BASE}/messages", headers=headers, timeout=15)
    inbox_res.raise_for_status()
    messages = inbox_res.json()["hydra:member"]
    
    if messages:
        message_id = messages[0]["id"]
        full_res = requests.get(f"{BASE}/messages/{message_id}", headers=headers, timeout=15)
        full_res.raise_for_status()
        data = full_res.json()
        content = data.get("text") or data.get("html") or ""
        if content and "<" in content:
            content = html.unescape(re.sub(r'<[^>]+>', ' ', content))
        return content
    return None

# ============================================================================
# EMAIL PROVIDER: GUERRILLAMAIL
# ============================================================================

def generate_guerrillamail_email() -> Tuple[str, str, str]:
    """Generate guerrillamail email. Returns: (email, sid_token, email_timestamp_str)"""
    BASE = "https://api.guerrillamail.com/ajax.php"
    
    response = requests.get(BASE, params={"f": "get_email_address"}, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    return data["email_addr"], data["sid_token"], str(data["email_timestamp"])

def check_guerrillamail_inbox(sid_token: str, email_timestamp: str) -> Optional[str]:
    """Check guerrillamail inbox once. Returns email content or None."""
    BASE = "https://api.guerrillamail.com/ajax.php"
    
    response = requests.get(BASE, params={"f": "check_email", "sid_token": sid_token, "seq": email_timestamp}, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    if data.get("list") and len(data["list"]) > 0:
        email_id = data["list"][0]["mail_id"]
        full_response = requests.get(BASE, params={"f": "fetch_email", "sid_token": sid_token, "email_id": email_id}, timeout=15)
        full_response.raise_for_status()
        mail_body = full_response.json().get("mail_body", "")
        clean_body = html.unescape(re.sub(r'<[^>]+>', ' ', mail_body))
        return clean_body
    return None

# ============================================================================
# MULTI-PROVIDER EMAIL WITH FALLBACK
# ============================================================================

def generate_email_with_fallback(logger: Optional[logging.Logger] = None) -> Tuple[str, str, str, str]:
    """
    Try mail.tm first, fallback to guerrillamail.
    Returns: (email_address, auth_data, provider_name, extra_data)
    """
    try:
        console.print("[cyan]Trying mail.tm...[/cyan]")
        if logger:
            logger.info("Attempting mail.tm email generation")
        
        email, password, auth = retry_sync(generate_mailtm_email, label="mail.tm generation", logger=logger)
        console.print(f"[green]✓[/green] mail.tm succeeded: {email}")
        
        if logger:
            logger.info(f"mail.tm email generated: {email}")
        
        return email, auth, "mail.tm", password
    except Exception as e:
        console.print(f"[yellow]mail.tm failed: {e}[/yellow]")
        if logger:
            logger.warning(f"mail.tm failed: {e}")
        
        console.print("[cyan]Falling back to guerrillamail...[/cyan]")
        try:
            email, sid, timestamp = retry_sync(generate_guerrillamail_email, label="guerrillamail generation", logger=logger)
            console.print(f"[green]✓[/green] guerrillamail succeeded: {email}")
            
            if logger:
                logger.info(f"guerrillamail email generated: {email}")
            
            return email, f"{sid}|{timestamp}", "guerrillamail", ""
        except Exception as e2:
            if logger:
                logger.error(f"All email providers failed. mail.tm: {e}, guerrillamail: {e2}")
            raise Exception(f"All email providers failed. mail.tm: {e}, guerrillamail: {e2}")

async def smart_poll_inbox_async(provider: str, auth_data: str, timeout: int = 60, logger: Optional[logging.Logger] = None) -> Optional[str]:
    """Smart async polling for email."""
    start_time = asyncio.get_running_loop().time()
    
    if logger:
        logger.info(f"Starting email polling (provider={provider}, timeout={timeout}s)")
    
    while True:
        elapsed = asyncio.get_running_loop().time() - start_time
        
        if elapsed >= timeout:
            console.print(f"[red]✗[/red] No email after {timeout}s" + " " * 20)
            if logger:
                logger.warning(f"Email polling timeout after {timeout}s")
            return None
        
        try:
            console.print(f"[dim]Checking inbox... ({int(elapsed)}s elapsed)[/dim]", end="\r")
            
            loop = asyncio.get_running_loop()
            if provider == "mail.tm":
                content = await loop.run_in_executor(None, check_mailtm_inbox, auth_data)
            elif provider == "guerrillamail":
                sid, timestamp = auth_data.split("|")
                content = await loop.run_in_executor(None, check_guerrillamail_inbox, sid, timestamp)
            else:
                return None
            
            if content:
                console.print(f"[green]✓[/green] Email received after {int(elapsed)}s" + " " * 20)
                if logger:
                    logger.info(f"Email received after {int(elapsed)}s")
                return content
            
            await asyncio.sleep(2)
        except Exception as e:
            if logger:
                logger.debug(f"Email check error: {e}")
            await asyncio.sleep(2)

# ============================================================================
# OTP EXTRACTION
# ============================================================================

OTP_CONTEXT_REGEX = re.compile(r'(?:code|otp|verif|pin)[\s\S]{0,50}?(\d{4,8})', re.IGNORECASE)
OTP_FALLBACK_REGEX = re.compile(r'\b(\d{6})\b')

def extract_otp_regex(email_content: str, logger: Optional[logging.Logger] = None) -> Optional[str]:
    """Extract OTP using regex."""
    context_match = OTP_CONTEXT_REGEX.search(email_content)
    if context_match:
        otp = context_match.group(1)
        if logger:
            logger.info(f"OTP extracted via context regex: {otp}")
        return otp
    
    fallback_match = OTP_FALLBACK_REGEX.search(email_content)
    if fallback_match:
        otp = fallback_match.group(1)
        if logger:
            logger.info(f"OTP extracted via fallback regex: {otp}")
        return otp
    
    return None

def extract_otp_ai(email_content: str, api_key: str, logger: Optional[logging.Logger] = None) -> Optional[str]:
    """Extract OTP using AI."""
    API_URL = "https://api.freemodel.dev/v1/chat/completions"
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-5.4-mini",
        "max_completion_tokens": 10,
        "messages": [
            {"role": "system", "content": "Extract the OTP verification code from the email. Return only the digits of the verification code, nothing else."},
            {"role": "user", "content": email_content[:1000]}
        ]
    }
    
    response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    otp = response.json()["choices"][0]["message"]["content"].strip()
    
    otp_digits = re.sub(r'\D', '', otp)
    
    if otp_digits and 4 <= len(otp_digits) <= 8:
        if logger:
            logger.info(f"OTP extracted via AI: {otp_digits}")
        return otp_digits
    
    return None

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
        email, auth_data, provider, _ = generate_email_with_fallback(logger)
        
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
            email_content = await smart_poll_inbox_async(provider, auth_data, timeout=60, logger=logger)
            
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
