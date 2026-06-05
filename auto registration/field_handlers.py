#!/usr/bin/env python3
"""
Field Handlers Module v1.0
Password, username, DOB, checkbox, and dropdown automation
Author: vinayakkumar9000
"""

import random
import string
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from playwright.async_api import Locator


# ============================================================================
# PASSWORD GENERATION
# ============================================================================

def generate_password(length: int = 16, require_all_types: bool = True) -> str:
    """
    Generate a secure password with mixed character types.
    
    Args:
        length: Password length (12-20 recommended)
        require_all_types: Ensure at least one of each type (upper, lower, digit, symbol)
    
    Returns:
        Secure password string
    """
    if length < 12:
        length = 12
    if length > 20:
        length = 20
    
    # Character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    symbols = "!@#$%^&*"
    
    # Combine all
    all_chars = uppercase + lowercase + digits + symbols
    
    if require_all_types:
        # Ensure at least one of each type
        password = [
            random.choice(uppercase),
            random.choice(lowercase),
            random.choice(digits),
            random.choice(symbols)
        ]
        
        # Fill remaining length
        remaining = length - 4
        password.extend(random.choices(all_chars, k=remaining))
        
        # Shuffle to avoid predictable pattern
        random.shuffle(password)
        return ''.join(password)
    else:
        return ''.join(random.choices(all_chars, k=length))


class PasswordManager:
    """Manages password generation and storage for reuse."""
    
    def __init__(self):
        self.generated_password: Optional[str] = None
    
    def get_or_generate(self, length: int = 16) -> str:
        """Get existing password or generate new one."""
        if not self.generated_password:
            self.generated_password = generate_password(length)
        return self.generated_password
    
    def reset(self):
        """Clear stored password."""
        self.generated_password = None


# ============================================================================
# USERNAME GENERATION
# ============================================================================

def generate_username(first_name: str, last_name: str, add_numbers: bool = True) -> str:
    """
    Generate username from identity.
    
    Args:
        first_name: User's first name
        last_name: User's last name
        add_numbers: Add random numbers at end
    
    Returns:
        Username string (e.g., "rahulsharma847")
    """
    # Clean names (remove spaces, special chars)
    first = re.sub(r'[^a-zA-Z]', '', first_name).lower()
    last = re.sub(r'[^a-zA-Z]', '', last_name).lower()
    
    # Combine
    username = f"{first}{last}"
    
    # Add random numbers if requested
    if add_numbers:
        numbers = ''.join(random.choices(string.digits, k=3))
        username += numbers
    
    return username


class UsernameManager:
    """Manages username generation and storage."""
    
    def __init__(self):
        self.generated_username: Optional[str] = None
    
    def get_or_generate(self, first_name: str, last_name: str) -> str:
        """Get existing username or generate new one."""
        if not self.generated_username:
            self.generated_username = generate_username(first_name, last_name)
        return self.generated_username
    
    def reset(self):
        """Clear stored username."""
        self.generated_username = None


# ============================================================================
# DATE OF BIRTH HANDLER
# ============================================================================

class DOBHandler:
    """Handles date of birth field filling in various formats."""
    
    def __init__(self, birth_year: int, birth_month: int, birth_day: int):
        self.year = birth_year
        self.month = birth_month
        self.day = birth_day
    
    def get_formatted(self, format_type: str = "auto") -> str:
        """
        Get formatted DOB string.
        
        Args:
            format_type: "iso" (YYYY-MM-DD), "us" (MM/DD/YYYY), "eu" (DD/MM/YYYY), "auto"
        
        Returns:
            Formatted date string
        """
        if format_type == "iso":
            return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"
        elif format_type == "us":
            return f"{self.month:02d}/{self.day:02d}/{self.year:04d}"
        elif format_type == "eu":
            return f"{self.day:02d}/{self.month:02d}/{self.year:04d}"
        else:  # auto - prefer ISO
            return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"
    
    async def fill_date_input(self, locator: Locator, verbose: bool = True) -> bool:
        """
        Fill a date input field (input[type=date]).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            input_type = await locator.get_attribute('type')
            
            if input_type == 'date':
                # Use ISO format for date inputs
                date_str = self.get_formatted("iso")
                await locator.fill(date_str)
                if verbose:
                    print(f"[FILL] DOB filled (date input): {date_str}")
                return True
            else:
                # Try common text formats
                for fmt in ["iso", "us", "eu"]:
                    try:
                        date_str = self.get_formatted(fmt)
                        await locator.fill(date_str)
                        if verbose:
                            print(f"[FILL] DOB filled (text input, {fmt}): {date_str}")
                        return True
                    except:
                        continue
                
                return False
        
        except Exception as e:
            if verbose:
                print(f"[FILL] Error filling DOB: {e}")
            return False
    
    async def fill_dropdown_selects(
        self,
        day_locator: Optional[Locator],
        month_locator: Optional[Locator],
        year_locator: Optional[Locator],
        verbose: bool = True
    ) -> bool:
        """
        Fill separate day/month/year dropdown selects.
        
        Returns:
            True if all successful, False otherwise
        """
        success = True
        
        try:
            if day_locator:
                await day_locator.select_option(str(self.day))
                if verbose:
                    print(f"[FILL] Day selected: {self.day}")
            
            if month_locator:
                # Try both numeric and name formats
                try:
                    await month_locator.select_option(str(self.month))
                except:
                    # Try month name
                    month_names = [
                        "January", "February", "March", "April", "May", "June",
                        "July", "August", "September", "October", "November", "December"
                    ]
                    await month_locator.select_option(month_names[self.month - 1])
                
                if verbose:
                    print(f"[FILL] Month selected: {self.month}")
            
            if year_locator:
                await year_locator.select_option(str(self.year))
                if verbose:
                    print(f"[FILL] Year selected: {self.year}")
        
        except Exception as e:
            if verbose:
                print(f"[FILL] Error filling DOB dropdowns: {e}")
            success = False
        
        return success


# ============================================================================
# CHECKBOX INTELLIGENCE
# ============================================================================

class CheckboxHandler:
    """Intelligent checkbox detection and auto-checking."""
    
    # Safe patterns to auto-check
    SAFE_PATTERNS = [
        (r'\bterms\b.*\bconditions\b', 95),
        (r'\bterms\b.*\bservice\b', 95),
        (r'\bprivacy\b.*\bpolicy\b', 90),
        (r'\baccept\b.*\bterms\b', 95),
        (r'\bagree\b.*\bterms\b', 95),
        (r'\b(over|above)\s+18\b', 85),
        (r'\b(over|above)\s+13\b', 85),
        (r'\bage\b.*\bverif', 80),
        (r'\bconsent\b.*\bprocess', 75),
    ]
    
    # Unsafe patterns to NEVER auto-check
    UNSAFE_PATTERNS = [
        r'\bnewsletter\b',
        r'\bmarketing\b',
        r'\bpromotion',
        r'\bemail\b.*\boffer',
        r'\bthird[\s\-]?party\b',
        r'\bshare\b.*\binformation\b',
        r'\bsend\b.*\bemail\b',
        r'\bsubscribe\b',
    ]
    
    @staticmethod
    async def should_check(locator: Locator, verbose: bool = True) -> bool:
        """
        Determine if checkbox should be auto-checked.
        
        Returns:
            True if safe to check, False otherwise
        """
        try:
            # Get associated text
            text = await locator.evaluate("""
                el => {
                    let text = '';
                    
                    // Check label
                    if (el.id) {
                        const label = document.querySelector(`label[for="${el.id}"]`);
                        if (label) text += label.textContent + ' ';
                    }
                    
                    // Check parent
                    if (el.parentElement) {
                        text += el.parentElement.textContent + ' ';
                    }
                    
                    // Check next sibling
                    if (el.nextElementSibling) {
                        text += el.nextElementSibling.textContent + ' ';
                    }
                    
                    return text.toLowerCase();
                }
            """)
            
            # Check unsafe patterns first
            for pattern in CheckboxHandler.UNSAFE_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    if verbose:
                        print(f"[CHECKBOX] Unsafe pattern detected, skipping: {pattern}")
                    return False
            
            # Check safe patterns
            max_confidence = 0
            matched_pattern = None
            
            for pattern, confidence in CheckboxHandler.SAFE_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    if confidence > max_confidence:
                        max_confidence = confidence
                        matched_pattern = pattern
            
            if max_confidence >= 80:
                if verbose:
                    print(f"[CHECKBOX] Safe to check (confidence={max_confidence}): {matched_pattern}")
                return True
            
            if verbose:
                print(f"[CHECKBOX] Confidence too low ({max_confidence}), skipping")
            return False
        
        except Exception as e:
            if verbose:
                print(f"[CHECKBOX] Error analyzing checkbox: {e}")
            return False
    
    @staticmethod
    async def auto_check_safe_boxes(locators: List[Locator], verbose: bool = True) -> int:
        """
        Auto-check all safe checkboxes.
        
        Returns:
            Number of checkboxes checked
        """
        checked_count = 0
        
        for locator in locators:
            try:
                # Check if already checked
                is_checked = await locator.is_checked()
                if is_checked:
                    continue
                
                # Determine if safe to check
                if await CheckboxHandler.should_check(locator, verbose):
                    await locator.check()
                    checked_count += 1
                    if verbose:
                        print(f"[CHECKBOX] ✓ Checked")
            
            except Exception as e:
                if verbose:
                    print(f"[CHECKBOX] Error checking box: {e}")
                continue
        
        return checked_count


# ============================================================================
# DROPDOWN AUTOMATION
# ============================================================================

class DropdownHandler:
    """Handles dropdown/select field automation."""
    
    def __init__(self, identity: Any):
        """
        Initialize with identity data.
        
        Args:
            identity: Identity object with gender, country, etc.
        """
        self.identity = identity
    
    async def fill_gender(self, locator: Locator, verbose: bool = True) -> bool:
        """Fill gender dropdown."""
        try:
            gender = getattr(self.identity, 'gender', 'Male')
            
            # Try exact match first
            try:
                await locator.select_option(label=gender)
                if verbose:
                    print(f"[DROPDOWN] Gender selected: {gender}")
                return True
            except:
                pass
            
            # Try value match
            try:
                await locator.select_option(value=gender.lower())
                if verbose:
                    print(f"[DROPDOWN] Gender selected: {gender}")
                return True
            except:
                pass
            
            # Try first letter
            try:
                await locator.select_option(value=gender[0].upper())
                if verbose:
                    print(f"[DROPDOWN] Gender selected: {gender}")
                return True
            except:
                pass
            
            return False
        
        except Exception as e:
            if verbose:
                print(f"[DROPDOWN] Error filling gender: {e}")
            return False
    
    async def fill_country(self, locator: Locator, verbose: bool = True) -> bool:
        """Fill country dropdown."""
        try:
            country = getattr(self.identity, 'country', 'India')
            
            # Try exact match
            try:
                await locator.select_option(label=country)
                if verbose:
                    print(f"[DROPDOWN] Country selected: {country}")
                return True
            except:
                pass
            
            # Try value match
            try:
                await locator.select_option(value=country)
                if verbose:
                    print(f"[DROPDOWN] Country selected: {country}")
                return True
            except:
                pass
            
            # Try country code (IN for India)
            country_codes = {
                'India': 'IN',
                'United States': 'US',
                'United Kingdom': 'GB',
            }
            
            if country in country_codes:
                try:
                    await locator.select_option(value=country_codes[country])
                    if verbose:
                        print(f"[DROPDOWN] Country selected: {country}")
                    return True
                except:
                    pass
            
            return False
        
        except Exception as e:
            if verbose:
                print(f"[DROPDOWN] Error filling country: {e}")
            return False
    
    async def fill_state(self, locator: Locator, verbose: bool = True) -> bool:
        """Fill state dropdown."""
        try:
            state = getattr(self.identity, 'state', 'Maharashtra')
            
            # Try exact match
            try:
                await locator.select_option(label=state)
                if verbose:
                    print(f"[DROPDOWN] State selected: {state}")
                return True
            except:
                pass
            
            # Try value match
            try:
                await locator.select_option(value=state)
                if verbose:
                    print(f"[DROPDOWN] State selected: {state}")
                return True
            except:
                pass
            
            return False
        
        except Exception as e:
            if verbose:
                print(f"[DROPDOWN] Error filling state: {e}")
            return False
    
    async def auto_fill_dropdown(self, locator: Locator, field_type: str, verbose: bool = True) -> bool:
        """
        Auto-fill dropdown based on field type.
        
        Args:
            locator: Dropdown locator
            field_type: "gender", "country", "state", etc.
            verbose: Enable logging
        
        Returns:
            True if successful, False otherwise
        """
        if field_type == "gender":
            return await self.fill_gender(locator, verbose)
        elif field_type == "country":
            return await self.fill_country(locator, verbose)
        elif field_type == "state":
            return await self.fill_state(locator, verbose)
        else:
            if verbose:
                print(f"[DROPDOWN] Unknown field type: {field_type}")
            return False
