#!/usr/bin/env python3
"""
Retry Utilities Module
Provides retry logic for both synchronous and asynchronous operations
"""

import asyncio
import time
from typing import Callable, Any

from rich.console import Console

console = Console()


# ============================================================================
# SYNCHRONOUS RETRY
# ============================================================================

def retry_sync(
    fn: Callable,
    retries: int = 3,
    delay: float = 1.5,
    label: str = "step"
) -> Any:
    """
    Retry synchronous function with fixed delay between attempts.
    
    Args:
        fn: Function to retry (should be a callable with no arguments)
        retries: Maximum number of attempts (default: 3)
        delay: Delay in seconds between retries (default: 1.5)
        label: Label for logging retry attempts (default: "step")
    
    Returns:
        Any: Return value from successful function call
    
    Raises:
        Exception: Re-raises the last exception if all retries fail
    
    Example:
        >>> result = retry_sync(lambda: risky_operation(), retries=3, delay=2.0, label="API call")
    """
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if attempt == retries - 1:
                # Last attempt failed, re-raise
                raise
            console.print(f"[yellow]Retry {label} ({attempt + 1}/{retries}): {e}[/yellow]")
            time.sleep(delay)


# ============================================================================
# ASYNCHRONOUS RETRY
# ============================================================================

async def retry_async(
    fn: Callable,
    retries: int = 3,
    delay: float = 1.5,
    label: str = "step"
) -> Any:
    """
    Retry asynchronous function with fixed delay between attempts.
    
    Args:
        fn: Async function to retry (should be a callable with no arguments)
        retries: Maximum number of attempts (default: 3)
        delay: Delay in seconds between retries (default: 1.5)
        label: Label for logging retry attempts (default: "step")
    
    Returns:
        Any: Return value from successful function call
    
    Raises:
        Exception: Re-raises the last exception if all retries fail
    
    Example:
        >>> result = await retry_async(lambda: async_operation(), retries=3, delay=2.0, label="page load")
    """
    for attempt in range(retries):
        try:
            return await fn()
        except Exception as e:
            if attempt == retries - 1:
                # Last attempt failed, re-raise
                raise
            console.print(f"[yellow]Retry {label} ({attempt + 1}/{retries}): {e}[/yellow]")
            await asyncio.sleep(delay)


# ============================================================================
# EXPONENTIAL BACKOFF RETRY
# ============================================================================

def retry_exponential(
    fn: Callable,
    retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    label: str = "step"
) -> Any:
    """
    Retry synchronous function with exponential backoff.
    
    Args:
        fn: Function to retry (should be a callable with no arguments)
        retries: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        backoff_factor: Multiplier for delay after each retry (default: 2.0)
        label: Label for logging retry attempts (default: "step")
    
    Returns:
        Any: Return value from successful function call
    
    Raises:
        Exception: Re-raises the last exception if all retries fail
    
    Example:
        >>> result = retry_exponential(lambda: api_call(), retries=4, initial_delay=1.0, backoff_factor=2.0)
        # Delays: 1s, 2s, 4s, 8s
    """
    delay = initial_delay
    
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if attempt == retries - 1:
                # Last attempt failed, re-raise
                raise
            console.print(f"[yellow]Retry {label} ({attempt + 1}/{retries}): {e}[/yellow]")
            console.print(f"[dim]Waiting {delay:.1f}s before retry...[/dim]")
            time.sleep(delay)
            delay *= backoff_factor


async def retry_exponential_async(
    fn: Callable,
    retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    label: str = "step"
) -> Any:
    """
    Retry asynchronous function with exponential backoff.
    
    Args:
        fn: Async function to retry (should be a callable with no arguments)
        retries: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        backoff_factor: Multiplier for delay after each retry (default: 2.0)
        label: Label for logging retry attempts (default: "step")
    
    Returns:
        Any: Return value from successful function call
    
    Raises:
        Exception: Re-raises the last exception if all retries fail
    
    Example:
        >>> result = await retry_exponential_async(lambda: async_api_call(), retries=4)
        # Delays: 1s, 2s, 4s, 8s
    """
    delay = initial_delay
    
    for attempt in range(retries):
        try:
            return await fn()
        except Exception as e:
            if attempt == retries - 1:
                # Last attempt failed, re-raise
                raise
            console.print(f"[yellow]Retry {label} ({attempt + 1}/{retries}): {e}[/yellow]")
            console.print(f"[dim]Waiting {delay:.1f}s before retry...[/dim]")
            await asyncio.sleep(delay)
            delay *= backoff_factor


# ============================================================================
# CONDITIONAL RETRY
# ============================================================================

def retry_on_condition(
    fn: Callable,
    should_retry: Callable[[Exception], bool],
    retries: int = 3,
    delay: float = 1.5,
    label: str = "step"
) -> Any:
    """
    Retry synchronous function only if exception matches condition.
    
    Args:
        fn: Function to retry
        should_retry: Function that takes exception and returns True if should retry
        retries: Maximum number of attempts (default: 3)
        delay: Delay in seconds between retries (default: 1.5)
        label: Label for logging retry attempts (default: "step")
    
    Returns:
        Any: Return value from successful function call
    
    Raises:
        Exception: Re-raises exception if should_retry returns False or all retries fail
    
    Example:
        >>> def is_timeout(e):
        ...     return isinstance(e, TimeoutError)
        >>> result = retry_on_condition(lambda: api_call(), should_retry=is_timeout)
    """
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if not should_retry(e) or attempt == retries - 1:
                # Don't retry this exception or last attempt failed
                raise
            console.print(f"[yellow]Retry {label} ({attempt + 1}/{retries}): {e}[/yellow]")
            time.sleep(delay)


async def retry_on_condition_async(
    fn: Callable,
    should_retry: Callable[[Exception], bool],
    retries: int = 3,
    delay: float = 1.5,
    label: str = "step"
) -> Any:
    """
    Retry asynchronous function only if exception matches condition.
    
    Args:
        fn: Async function to retry
        should_retry: Function that takes exception and returns True if should retry
        retries: Maximum number of attempts (default: 3)
        delay: Delay in seconds between retries (default: 1.5)
        label: Label for logging retry attempts (default: "step")
    
    Returns:
        Any: Return value from successful function call
    
    Raises:
        Exception: Re-raises exception if should_retry returns False or all retries fail
    
    Example:
        >>> def is_network_error(e):
        ...     return "network" in str(e).lower()
        >>> result = await retry_on_condition_async(lambda: fetch_data(), should_retry=is_network_error)
    """
    for attempt in range(retries):
        try:
            return await fn()
        except Exception as e:
            if not should_retry(e) or attempt == retries - 1:
                # Don't retry this exception or last attempt failed
                raise
            console.print(f"[yellow]Retry {label} ({attempt + 1}/{retries}): {e}[/yellow]")
            await asyncio.sleep(delay)
