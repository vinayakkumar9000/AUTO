#!/usr/bin/env python3
"""
Dynamic Form Support Module v1.0
MutationObserver and periodic rescanning for dynamically rendered forms
Author: vinayakkumar9000
"""

import asyncio
from typing import Optional, Callable, Any
from playwright.async_api import Page


# ============================================================================
# MUTATION OBSERVER SUPPORT
# ============================================================================

class DynamicFormWatcher:
    """Watches for dynamically rendered form fields using MutationObserver."""
    
    def __init__(self, page: Page, verbose: bool = True):
        self.page = page
        self.verbose = verbose
        self.observer_active = False
    
    def log(self, message: str):
        """Log debug messages if verbose mode enabled."""
        if self.verbose:
            print(f"[DYNAMIC] {message}")
    
    async def start_observer(self, callback_js: str = ""):
        """
        Start MutationObserver to watch for DOM changes.
        
        Args:
            callback_js: Optional JavaScript code to execute when mutation detected
        """
        try:
            self.log("Starting MutationObserver...")
            
            await self.page.evaluate(f"""
                () => {{
                    if (window.__formObserver) {{
                        window.__formObserver.disconnect();
                    }}
                    
                    window.__formMutationDetected = false;
                    
                    const observer = new MutationObserver((mutations) => {{
                        // Check if any mutations added input/select/textarea elements
                        for (let mutation of mutations) {{
                            if (mutation.addedNodes.length > 0) {{
                                for (let node of mutation.addedNodes) {{
                                    if (node.nodeType === 1) {{ // Element node
                                        const hasFormElements = 
                                            node.matches && node.matches('input, select, textarea') ||
                                            node.querySelector && node.querySelector('input, select, textarea');
                                        
                                        if (hasFormElements) {{
                                            window.__formMutationDetected = true;
                                            {callback_js}
                                            break;
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                    
                    observer.observe(document.body, {{
                        childList: true,
                        subtree: true,
                        attributes: false
                    }});
                    
                    window.__formObserver = observer;
                }}
            """)
            
            self.observer_active = True
            self.log("MutationObserver started")
        
        except Exception as e:
            self.log(f"Error starting MutationObserver: {e}")
    
    async def stop_observer(self):
        """Stop the MutationObserver."""
        try:
            if self.observer_active:
                await self.page.evaluate("""
                    () => {
                        if (window.__formObserver) {
                            window.__formObserver.disconnect();
                            delete window.__formObserver;
                            delete window.__formMutationDetected;
                        }
                    }
                """)
                self.observer_active = False
                self.log("MutationObserver stopped")
        
        except Exception as e:
            self.log(f"Error stopping MutationObserver: {e}")
    
    async def check_mutation_detected(self) -> bool:
        """Check if any form-related mutations were detected."""
        try:
            detected = await self.page.evaluate("""
                () => window.__formMutationDetected || false
            """)
            
            if detected:
                # Reset flag
                await self.page.evaluate("""
                    () => { window.__formMutationDetected = false; }
                """)
                self.log("Form mutation detected!")
            
            return detected
        
        except Exception:
            return False


# ============================================================================
# PERIODIC RESCANNING
# ============================================================================

class PeriodicScanner:
    """Periodically rescans for form fields with timeout."""
    
    def __init__(self, page: Page, verbose: bool = True):
        self.page = page
        self.verbose = verbose
    
    def log(self, message: str):
        """Log debug messages if verbose mode enabled."""
        if self.verbose:
            print(f"[RESCAN] {message}")
    
    async def wait_for_field(
        self,
        check_function: Callable[[], Any],
        timeout: int = 15,
        interval: float = 1.0,
        field_name: str = "field"
    ) -> Optional[Any]:
        """
        Periodically check for field appearance with timeout.
        
        Args:
            check_function: Async function that returns field or None
            timeout: Maximum seconds to wait
            interval: Seconds between checks
            field_name: Name of field for logging
        
        Returns:
            Field if found, None if timeout
        """
        start_time = asyncio.get_running_loop().time()
        deadline = start_time + timeout
        
        self.log(f"Waiting for {field_name} (timeout={timeout}s)...")
        
        while asyncio.get_running_loop().time() < deadline:
            elapsed = int(asyncio.get_running_loop().time() - start_time)
            
            try:
                # Check if field exists
                result = await check_function()
                
                if result:
                    self.log(f"✓ {field_name} found after {elapsed}s")
                    return result
                
                # Log progress
                if elapsed % 3 == 0:  # Every 3 seconds
                    self.log(f"Still waiting for {field_name}... ({elapsed}s elapsed)")
                
                # Wait before next check
                await asyncio.sleep(interval)
            
            except Exception as e:
                self.log(f"Error checking for {field_name}: {e}")
                await asyncio.sleep(interval)
        
        self.log(f"✗ {field_name} not found after {timeout}s")
        return None
    
    async def wait_for_multiple_fields(
        self,
        check_functions: dict,
        timeout: int = 15,
        interval: float = 1.0,
        require_all: bool = False
    ) -> dict:
        """
        Wait for multiple fields to appear.
        
        Args:
            check_functions: Dict of {field_name: check_function}
            timeout: Maximum seconds to wait
            interval: Seconds between checks
            require_all: If True, wait until all fields found or timeout
        
        Returns:
            Dict of {field_name: field_or_None}
        """
        start_time = asyncio.get_running_loop().time()
        deadline = start_time + timeout
        
        results = {name: None for name in check_functions.keys()}
        found_count = 0
        
        self.log(f"Waiting for {len(check_functions)} fields (timeout={timeout}s)...")
        
        while asyncio.get_running_loop().time() < deadline:
            elapsed = int(asyncio.get_running_loop().time() - start_time)
            
            # Check each field that hasn't been found yet
            for field_name, check_func in check_functions.items():
                if results[field_name] is not None:
                    continue  # Already found
                
                try:
                    result = await check_func()
                    if result:
                        results[field_name] = result
                        found_count += 1
                        self.log(f"✓ {field_name} found ({found_count}/{len(check_functions)})")
                
                except Exception as e:
                    self.log(f"Error checking {field_name}: {e}")
            
            # Check if we can stop early
            if not require_all and found_count > 0:
                self.log(f"Found {found_count} fields, stopping early")
                break
            
            if require_all and found_count == len(check_functions):
                self.log(f"All {len(check_functions)} fields found!")
                break
            
            # Log progress
            if elapsed % 3 == 0:
                self.log(f"Found {found_count}/{len(check_functions)} fields... ({elapsed}s elapsed)")
            
            await asyncio.sleep(interval)
        
        if found_count < len(check_functions):
            self.log(f"Timeout: Found {found_count}/{len(check_functions)} fields")
        
        return results


# ============================================================================
# COMBINED DYNAMIC FORM HANDLER
# ============================================================================

class DynamicFormHandler:
    """
    Combined handler for dynamic forms.
    Uses MutationObserver + periodic rescanning.
    """
    
    def __init__(self, page: Page, verbose: bool = True):
        self.page = page
        self.verbose = verbose
        self.watcher = DynamicFormWatcher(page, verbose)
        self.scanner = PeriodicScanner(page, verbose)
    
    def log(self, message: str):
        """Log debug messages if verbose mode enabled."""
        if self.verbose:
            print(f"[DYNAMIC] {message}")
    
    async def wait_for_field_with_observer(
        self,
        check_function: Callable[[], Any],
        timeout: int = 15,
        field_name: str = "field"
    ) -> Optional[Any]:
        """
        Wait for field using both MutationObserver and periodic scanning.
        More efficient than scanning alone.
        
        Args:
            check_function: Async function that returns field or None
            timeout: Maximum seconds to wait
            field_name: Name of field for logging
        
        Returns:
            Field if found, None if timeout
        """
        # Start observer
        await self.watcher.start_observer()
        
        start_time = asyncio.get_running_loop().time()
        deadline = start_time + timeout
        
        self.log(f"Waiting for {field_name} with observer (timeout={timeout}s)...")
        
        try:
            while asyncio.get_running_loop().time() < deadline:
                elapsed = int(asyncio.get_running_loop().time() - start_time)
                
                # Check if field exists
                result = await check_function()
                if result:
                    self.log(f"✓ {field_name} found after {elapsed}s")
                    return result
                
                # Check if mutation was detected
                mutation_detected = await self.watcher.check_mutation_detected()
                
                if mutation_detected:
                    self.log(f"DOM mutation detected, rescanning...")
                    # Immediate recheck after mutation
                    result = await check_function()
                    if result:
                        self.log(f"✓ {field_name} found after mutation")
                        return result
                
                # Log progress less frequently
                if elapsed % 5 == 0:
                    self.log(f"Still waiting for {field_name}... ({elapsed}s elapsed)")
                
                # Wait before next check (shorter interval for better responsiveness)
                await asyncio.sleep(0.5)
            
            self.log(f"✗ {field_name} not found after {timeout}s")
            return None
        
        finally:
            # Always stop observer
            await self.watcher.stop_observer()
    
    async def smart_wait_for_field(
        self,
        check_function: Callable[[], Any],
        timeout: int = 15,
        field_name: str = "field",
        use_observer: bool = True
    ) -> Optional[Any]:
        """
        Smart wait that chooses best strategy.
        
        Args:
            check_function: Async function that returns field or None
            timeout: Maximum seconds to wait
            field_name: Name of field for logging
            use_observer: If True, use MutationObserver (more efficient)
        
        Returns:
            Field if found, None if timeout
        """
        if use_observer:
            return await self.wait_for_field_with_observer(
                check_function, timeout, field_name
            )
        else:
            return await self.scanner.wait_for_field(
                check_function, timeout, 1.0, field_name
            )
