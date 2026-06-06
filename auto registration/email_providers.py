#!/usr/bin/env python3
"""
Email Provider Module
Handles temporary email generation and inbox checking for multiple providers
Supports: mail.tm, guerrillamail with automatic fallback
"""

import html
import random
import re
import string
import time
from typing import Optional, Tuple, Callable, Any

import requests
from rich.console import Console

console = Console()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _rand_string(length: int) -> str:
    """Generate random alphanumeric string."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def retry_sync(fn: Callable, retries: int = 3, delay: float = 1.5, label: str = "step") -> Any:
    """Retry synchronous function with fixed delay."""
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if attempt == retries - 1:
                raise
            console.print(f"[yellow]Retry {label} ({attempt + 1}/{retries}): {e}[/yellow]")
            time.sleep(delay)


# ============================================================================
# EMAIL PROVIDER: MAIL.TM
# ============================================================================

def generate_mailtm_email() -> Tuple[str, str, str]:
    """
    Generate mail.tm email account.
    
    Returns:
        Tuple[str, str, str]: (email_address, password, auth_token)
    
    Raises:
        requests.RequestException: If API request fails
    """
    BASE = "https://api.mail.tm"
    
    # Get available domains
    domains_res = requests.get(f"{BASE}/domains?page=1", timeout=15)
    domains_res.raise_for_status()
    domain = domains_res.json()["hydra:member"][0]["domain"]
    
    # Generate credentials
    local_part = _rand_string(10)
    address = f"{local_part}@{domain}"
    password = _rand_string(12)
    
    # Create account
    account_res = requests.post(
        f"{BASE}/accounts",
        json={"address": address, "password": password},
        timeout=15
    )
    account_res.raise_for_status()
    
    # Get auth token
    token_res = requests.post(
        f"{BASE}/token",
        json={"address": address, "password": password},
        timeout=15
    )
    token_res.raise_for_status()
    auth = token_res.json()["token"]
    
    return address, password, auth


def check_mailtm_inbox(auth_token: str) -> Optional[str]:
    """
    Check mail.tm inbox for new messages.
    
    Args:
        auth_token: Bearer token for authentication
    
    Returns:
        Optional[str]: Email content (text or cleaned HTML) or None if no messages
    
    Raises:
        requests.RequestException: If API request fails
    """
    BASE = "https://api.mail.tm"
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    try:
        # Get inbox messages
        inbox_res = requests.get(f"{BASE}/messages", headers=headers, timeout=15)
        inbox_res.raise_for_status()
        messages = inbox_res.json()["hydra:member"]
        
        if not messages:
            return None
        
        # Get first message content
        message_id = messages[0]["id"]
        full_res = requests.get(f"{BASE}/messages/{message_id}", headers=headers, timeout=15)
        full_res.raise_for_status()
        data = full_res.json()
        
        # Extract content (prefer text, fallback to HTML)
        content = data.get("text") or data.get("html") or ""
        
        # Clean HTML if present
        if content and "<" in content:
            content = html.unescape(re.sub(r'<[^>]+>', ' ', content))
        
        return content
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            console.print(f"\n[red]✗ mail.tm auth failed (401 Unauthorized)[/red]")
        raise
    except Exception as e:
        console.print(f"\n[yellow]⚠ mail.tm error: {e}[/yellow]")
        raise


# ============================================================================
# EMAIL PROVIDER: GUERRILLAMAIL
# ============================================================================

def generate_guerrillamail_email() -> Tuple[str, str, str]:
    """
    Generate guerrillamail email account.
    
    Returns:
        Tuple[str, str, str]: (email_address, sid_token, email_timestamp)
    
    Raises:
        requests.RequestException: If API request fails
    """
    BASE = "https://api.guerrillamail.com/ajax.php"
    
    response = requests.get(BASE, params={"f": "get_email_address"}, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    return data["email_addr"], data["sid_token"], str(data["email_timestamp"])


def check_guerrillamail_inbox(sid_token: str, email_timestamp: str) -> Optional[str]:
    """
    Check guerrillamail inbox for new messages.
    
    Args:
        sid_token: Session ID token
        email_timestamp: Timestamp for checking new messages
    
    Returns:
        Optional[str]: Email content (cleaned HTML) or None if no messages
    
    Raises:
        requests.RequestException: If API request fails
    """
    BASE = "https://api.guerrillamail.com/ajax.php"
    
    # Check for new emails
    response = requests.get(
        BASE,
        params={"f": "check_email", "sid_token": sid_token, "seq": email_timestamp},
        timeout=15
    )
    response.raise_for_status()
    data = response.json()
    
    if not data.get("list") or len(data["list"]) == 0:
        return None
    
    # Fetch first email content
    email_id = data["list"][0]["mail_id"]
    full_response = requests.get(
        BASE,
        params={"f": "fetch_email", "sid_token": sid_token, "email_id": email_id},
        timeout=15
    )
    full_response.raise_for_status()
    mail_body = full_response.json().get("mail_body", "")
    
    # Clean HTML tags
    clean_body = html.unescape(re.sub(r'<[^>]+>', ' ', mail_body))
    
    return clean_body


# ============================================================================
# MULTI-PROVIDER EMAIL WITH AUTOMATIC FALLBACK
# ============================================================================

def generate_email_with_fallback(max_attempts: int = 3) -> Tuple[str, str, str, str]:
    """
    Generate temporary email with automatic provider fallback and retry support.
    Tries mail.tm first, falls back to guerrillamail if it fails.
    Supports multiple generation attempts per provider for reliability.
    
    Args:
        max_attempts: Maximum number of email generation attempts per provider (default: 3)
    
    Returns:
        Tuple[str, str, str, str]: (email_address, auth_data, provider_name, extra_data)
        - email_address: The generated email address
        - auth_data: Authentication data (format depends on provider)
        - provider_name: "mail.tm" or "guerrillamail"
        - extra_data: Additional data (password for mail.tm, empty for guerrillamail)
    
    Raises:
        Exception: If all providers fail after max_attempts
    """
    last_error = None
    
    # Try mail.tm with multiple attempts
    for attempt in range(max_attempts):
        try:
            if attempt == 0:
                console.print("[cyan]Trying mail.tm...[/cyan]")
            else:
                console.print(f"[cyan]Retrying mail.tm (attempt {attempt + 1}/{max_attempts})...[/cyan]")
            
            email, password, auth = retry_sync(generate_mailtm_email, label="mail.tm generation")
            console.print(f"[green]✓[/green] mail.tm succeeded: {email}")
            return email, auth, "mail.tm", password
        except Exception as e:
            last_error = e
            console.print(f"[yellow]mail.tm attempt {attempt + 1} failed: {e}[/yellow]")
            if attempt < max_attempts - 1:
                time.sleep(2)  # Wait before retry
    
    # Fallback to guerrillamail with multiple attempts
    for attempt in range(max_attempts):
        try:
            if attempt == 0:
                console.print("[cyan]Falling back to guerrillamail...[/cyan]")
            else:
                console.print(f"[cyan]Retrying guerrillamail (attempt {attempt + 1}/{max_attempts})...[/cyan]")
            
            email, sid, timestamp = retry_sync(generate_guerrillamail_email, label="guerrillamail generation")
            console.print(f"[green]✓[/green] guerrillamail succeeded: {email}")
            return email, f"{sid}|{timestamp}", "guerrillamail", ""
        except Exception as e2:
            last_error = e2
            console.print(f"[yellow]guerrillamail attempt {attempt + 1} failed: {e2}[/yellow]")
            if attempt < max_attempts - 1:
                time.sleep(2)  # Wait before retry
    
    raise Exception(f"All email providers failed after {max_attempts} attempts. Last error: {last_error}")


def check_inbox(provider: str, auth_data: str) -> Optional[str]:
    """
    Check inbox for the specified provider.
    
    Args:
        provider: Provider name ("mail.tm" or "guerrillamail")
        auth_data: Authentication data (format depends on provider)
    
    Returns:
        Optional[str]: Email content or None if no messages
    
    Raises:
        ValueError: If provider is unknown
        requests.RequestException: If API request fails
    """
    if provider == "mail.tm":
        return check_mailtm_inbox(auth_data)
    elif provider == "guerrillamail":
        sid, timestamp = auth_data.split("|")
        return check_guerrillamail_inbox(sid, timestamp)
    else:
        raise ValueError(f"Unknown provider: {provider}")


# ============================================================================
# SMART POLLING (SYNC VERSION)
# ============================================================================

def smart_poll_inbox(provider: str, auth_data: str, timeout: int = 60, interval: int = 2) -> Optional[str]:
    """
    Smart polling: check inbox every interval seconds, stop immediately when email arrives.
    
    Args:
        provider: Provider name ("mail.tm" or "guerrillamail")
        auth_data: Authentication data
        timeout: Maximum time to wait in seconds (default: 60)
        interval: Check interval in seconds (default: 2)
    
    Returns:
        Optional[str]: Email content or None if timeout reached
    """
    start_time = time.time()
    
    while True:
        elapsed = int(time.time() - start_time)
        
        if elapsed >= timeout:
            console.print(f"[red]✗[/red] No email after {timeout}s" + " " * 20)
            return None
        
        try:
            console.print(f"[dim]Checking inbox... ({elapsed}s elapsed)[/dim]", end="\r")
            
            content = check_inbox(provider, auth_data)
            
            if content:
                console.print(f"[green]✓[/green] Email received after {elapsed}s" + " " * 20)
                return content
            
            time.sleep(interval)
        except Exception:
            time.sleep(interval)


# ============================================================================
# ASYNC VERSION (FOR PLAYWRIGHT INTEGRATION)
# ============================================================================

async def smart_poll_inbox_async(provider: str, auth_data: str, timeout: int = 60, interval: int = 2) -> Optional[str]:
    """
    Async smart polling: check inbox every interval seconds without blocking event loop.
    
    Args:
        provider: Provider name ("mail.tm" or "guerrillamail")
        auth_data: Authentication data
        timeout: Maximum time to wait in seconds (default: 60)
        interval: Check interval in seconds (default: 2)
    
    Returns:
        Optional[str]: Email content or None if timeout reached
    """
    import asyncio
    
    start_time = asyncio.get_running_loop().time()
    
    while True:
        elapsed = asyncio.get_running_loop().time() - start_time
        
        if elapsed >= timeout:
            console.print(f"[red]✗[/red] No email after {timeout}s" + " " * 20)
            return None
        
        try:
            console.print(f"[dim]Checking inbox... ({int(elapsed)}s elapsed)[/dim]", end="\r")
            
            # Run sync email check in executor to avoid blocking
            loop = asyncio.get_running_loop()
            content = await loop.run_in_executor(None, check_inbox, provider, auth_data)
            
            if content:
                console.print(f"[green]✓[/green] Email received after {int(elapsed)}s" + " " * 20)
                return content
            
            await asyncio.sleep(interval)
        except Exception:
            await asyncio.sleep(interval)
