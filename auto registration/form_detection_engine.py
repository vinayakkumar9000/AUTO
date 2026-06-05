#!/usr/bin/env python3
"""
Advanced Universal Form Detection Engine v1.1
Multi-context form discovery with iframe and Shadow DOM support
ENHANCED: iframe interaction support, Shadow DOM pierce selectors
Author: vinayakkumar9000
"""

import asyncio
import re
from typing import List, Dict, Optional, Any, Tuple
from playwright.async_api import Page, Locator, Frame, ElementHandle


# ============================================================================
# FIELD TYPE PATTERNS - Enhanced for scoring
# ============================================================================

FIELD_PATTERNS = {
    "email": [
        (r'\bemail\b', 100),
        (r'\be[\-_]?mail\b', 95),
        (r'\bmail\b', 70),
        (r'\bcontact\b', 40),
    ],
    "username": [
        (r'\busername\b', 100),
        (r'\buser[\-_]?name\b', 95),
        (r'\blogin\b', 80),
        (r'\bhandle\b', 75),
        (r'\baccount\b', 60),
    ],
    "display_name": [
        (r'\bdisplay[\-_]?name\b', 100),
        (r'\bnickname\b', 90),
        (r'\bscreen[\-_]?name\b', 85),
        (r'\bpublic[\-_]?name\b', 80),
    ],
    "password": [
        (r'\bpassword\b', 100),
        (r'\bpasswd\b', 95),
        (r'\bpwd\b', 90),
        (r'\bsecret\b', 70),
    ],
    "confirm_password": [
        (r'\bconfirm[\s\-_]*password\b', 100),
        (r'\bpassword[\s\-_]*confirm\b', 100),
        (r'\bre[\s\-_]*enter[\s\-_]*password\b', 100),
        (r'\bverify[\s\-_]*password\b', 100),
        (r'\bpassword[\s\-_]*2\b', 95),
        (r'\bconfirm[\s\-_]*pwd\b', 95),
        (r'\brepeat[\s\-_]*password\b', 95),
    ],
    "otp": [
        (r'\botp\b', 100),
        (r'\bverification[\s\-_]*code\b', 100),
        (r'\bverify[\s\-_]*code\b', 100),
        (r'\bcode\b', 95),
        (r'\bverif', 95),
        (r'\b2fa\b', 90),
        (r'\bmfa\b', 90),
        (r'\bone[\s\-_]*time\b', 90),
        (r'\bauth[\s\-_]*code\b', 95),
        (r'\bpin\b', 85),
        (r'\btoken\b', 85),
    ],
    "first_name": [
        (r'\bfirst[\s\-_]*name\b', 100),
        (r'\bgiven[\s\-_]*name\b', 95),
        (r'\bfname\b', 90),
        (r'\bforename\b', 85),
    ],
    "last_name": [
        (r'\blast[\s\-_]*name\b', 100),
        (r'\bsurname\b', 95),
        (r'\bfamily[\s\-_]*name\b', 90),
        (r'\blname\b', 85),
    ],
    "full_name": [
        (r'\bfull[\s\-_]*name\b', 100),
        (r'\bname\b', 80),
        (r'\bcomplete[\s\-_]*name\b', 90),
    ],
    "date_of_birth": [
        (r'\bdate[\s\-_]*of[\s\-_]*birth\b', 100),
        (r'\bdob\b', 95),
        (r'\bbirthday\b', 90),
        (r'\bbirth[\s\-_]*date\b', 95),
        (r'\bage\b', 70),
    ],
    "gender": [
        (r'\bgender\b', 100),
        (r'\bsex\b', 90),
    ],
    "country": [
        (r'\bcountry\b', 100),
        (r'\bnation\b', 80),
        (r'\blocation\b', 60),
    ],
    "phone": [
        (r'\bphone\b', 100),
        (r'\bmobile\b', 95),
        (r'\btel\b', 90),
        (r'\bcontact\b', 70),
    ],
}


# ============================================================================
# FIELD DISCOVERY RESULT
# ============================================================================

class FieldCandidate:
    """Represents a discovered form field with metadata."""
    
    def __init__(
        self,
        locator: Locator,
        field_type: str,
        confidence: int,
        context: str,
        frame_path: List[str],
        attributes: Dict[str, str],
        surrounding_text: str = "",
        frame_context: Optional[Any] = None,
        shadow_host_selector: Optional[str] = None
    ):
        self.locator = locator
        self.field_type = field_type
        self.confidence = confidence
        self.context = context  # "main", "iframe", "shadow"
        self.frame_path = frame_path
        self.attributes = attributes
        self.surrounding_text = surrounding_text
        self.frame_context = frame_context  # Store frame reference for iframe fields
        self.shadow_host_selector = shadow_host_selector  # Store shadow host selector
    
    def __repr__(self):
        return f"FieldCandidate(type={self.field_type}, confidence={self.confidence}, context={self.context})"


# ============================================================================
# MULTI-CONTEXT SCANNER
# ============================================================================

class FormDetectionEngine:
    """Advanced form detection with iframe and Shadow DOM support."""
    
    def __init__(self, page: Page, verbose: bool = True):
        self.page = page
        self.verbose = verbose
        self.discovered_fields: List[FieldCandidate] = []
    
    def log(self, message: str):
        """Log debug messages if verbose mode enabled."""
        if self.verbose:
            print(f"[SCAN] {message}")
    
    async def discover_all_fields(self) -> List[FieldCandidate]:
        """
        Main entry point: Discover all form fields across all contexts.
        Returns list of FieldCandidate objects sorted by confidence.
        """
        self.discovered_fields = []
        
        # Scan main document
        self.log("Scanning main document...")
        await self._scan_context(self.page, "main", [])
        
        # Scan all iframes recursively
        self.log("Scanning iframes...")
        await self._scan_iframes(self.page, [])
        
        # Scan Shadow DOM trees using pierce selectors
        self.log("Scanning Shadow DOM...")
        await self._scan_shadow_dom_pierce(self.page)
        
        # Sort by confidence (highest first)
        self.discovered_fields.sort(key=lambda x: x.confidence, reverse=True)
        
        self.log(f"Total fields discovered: {len(self.discovered_fields)}")
        return self.discovered_fields
    
    async def _scan_context(self, context: Page | Frame, context_type: str, frame_path: List[str]):
        """Scan a specific context (page or frame) for form fields."""
        try:
            # Get all input, select, textarea elements
            inputs = await context.locator('input, select, textarea').all()
            
            for inp in inputs:
                try:
                    # Check visibility
                    if not await inp.is_visible():
                        continue
                    
                    # Get all attributes
                    attributes = await self._get_element_attributes(inp)
                    
                    # Get surrounding text
                    surrounding_text = await self._get_surrounding_text(inp)
                    
                    # Classify field
                    field_type, confidence = self._classify_field(attributes, surrounding_text)
                    
                    if field_type and confidence > 50:  # Minimum confidence threshold
                        candidate = FieldCandidate(
                            locator=inp,
                            field_type=field_type,
                            confidence=confidence,
                            context=context_type,
                            frame_path=frame_path,
                            attributes=attributes,
                            surrounding_text=surrounding_text,
                            frame_context=context if context_type == "iframe" else None
                        )
                        self.discovered_fields.append(candidate)
                        self.log(f"Found {field_type} field (confidence={confidence}, context={context_type})")
                
                except Exception as e:
                    if self.verbose:
                        print(f"[SCAN] Error processing input: {e}")
                    continue
        
        except Exception as e:
            if self.verbose:
                print(f"[SCAN] Error scanning context: {e}")
    
    async def _scan_iframes(self, context: Page | Frame, parent_path: List[str]):
        """Recursively scan all iframes."""
        try:
            frames = context.frames if hasattr(context, 'frames') else []
            
            for i, frame in enumerate(frames):
                if frame == context:  # Skip self
                    continue
                
                frame_path = parent_path + [f"iframe_{i}"]
                self.log(f"Scanning iframe: {' > '.join(frame_path)}")
                
                # Scan this iframe
                await self._scan_context(frame, "iframe", frame_path)
                
                # Recursively scan nested iframes
                await self._scan_iframes(frame, frame_path)
        
        except Exception as e:
            if self.verbose:
                print(f"[SCAN] Error scanning iframes: {e}")
    
    async def _scan_shadow_dom_pierce(self, page: Page):
        """Scan Shadow DOM using pierce selectors (Playwright's shadow DOM support)."""
        try:
            # Use pierce selector to find inputs in shadow DOM
            # pierce selector automatically traverses shadow boundaries
            shadow_inputs = await page.locator('pierce/input, pierce/select, pierce/textarea').all()
            
            for inp in shadow_inputs:
                try:
                    # Check if already found in main scan
                    # (pierce also finds regular DOM elements)
                    if not await inp.is_visible():
                        continue
                    
                    # Get attributes
                    attributes = await self._get_element_attributes(inp)
                    
                    # Get surrounding text
                    surrounding_text = await self._get_surrounding_text(inp)
                    
                    # Classify field
                    field_type, confidence = self._classify_field(attributes, surrounding_text)
                    
                    if field_type and confidence > 50:
                        # Check if this field was already found in main scan
                        # by comparing attributes
                        is_duplicate = any(
                            f.attributes.get('name') == attributes.get('name') and
                            f.attributes.get('id') == attributes.get('id') and
                            f.context != "shadow"
                            for f in self.discovered_fields
                        )
                        
                        if not is_duplicate:
                            candidate = FieldCandidate(
                                locator=inp,
                                field_type=field_type,
                                confidence=confidence,
                                context="shadow",
                                frame_path=["shadow_dom"],
                                attributes=attributes,
                                surrounding_text=surrounding_text
                            )
                            self.discovered_fields.append(candidate)
                            self.log(f"Found {field_type} field in Shadow DOM (confidence={confidence})")
                
                except Exception as e:
                    if self.verbose:
                        print(f"[SCAN] Error processing shadow DOM input: {e}")
                    continue
        
        except Exception as e:
            if self.verbose:
                print(f"[SCAN] Error scanning Shadow DOM: {e}")
    
    async def _get_element_attributes(self, element: Locator) -> Dict[str, str]:
        """Extract all relevant attributes from an element."""
        attributes = {}
        
        attr_names = ['name', 'id', 'type', 'placeholder', 'aria-label', 'autocomplete', 'class', 'role']
        
        for attr in attr_names:
            try:
                value = await element.get_attribute(attr)
                if value:
                    attributes[attr] = value
            except:
                pass
        
        # Get data-* attributes
        try:
            data_attrs = await element.evaluate("""
                el => {
                    const data = {};
                    for (let attr of el.attributes) {
                        if (attr.name.startsWith('data-')) {
                            data[attr.name] = attr.value;
                        }
                    }
                    return data;
                }
            """)
            attributes.update(data_attrs)
        except:
            pass
        
        return attributes
    
    async def _get_surrounding_text(self, element: Locator) -> str:
        """Get text from surrounding elements (labels, parent, siblings)."""
        try:
            surrounding = await element.evaluate("""
                el => {
                    let text = '';
                    
                    // Check for associated label
                    if (el.id) {
                        const label = document.querySelector(`label[for="${el.id}"]`);
                        if (label) text += label.textContent + ' ';
                    }
                    
                    // Check parent text
                    if (el.parentElement) {
                        text += el.parentElement.textContent + ' ';
                    }
                    
                    // Check previous sibling
                    if (el.previousElementSibling) {
                        text += el.previousElementSibling.textContent + ' ';
                    }
                    
                    return text.trim();
                }
            """)
            return surrounding[:500]  # Limit length
        except:
            return ""
    
    def _classify_field(self, attributes: Dict[str, str], surrounding_text: str) -> Tuple[Optional[str], int]:
        """
        Classify field type and return confidence score.
        Returns: (field_type, confidence_score)
        """
        scores = {}
        
        # Combine all text to search
        search_text = ' '.join([
            attributes.get('name', ''),
            attributes.get('id', ''),
            attributes.get('placeholder', ''),
            attributes.get('aria-label', ''),
            attributes.get('autocomplete', ''),
            surrounding_text
        ]).lower()
        
        # Score each field type
        for field_type, patterns in FIELD_PATTERNS.items():
            max_score = 0
            for pattern, score in patterns:
                if re.search(pattern, search_text, re.IGNORECASE):
                    max_score = max(max_score, score)
            
            if max_score > 0:
                scores[field_type] = max_score
        
        # Special handling for password vs confirm_password
        if 'password' in scores and 'confirm_password' in scores:
            if scores['confirm_password'] >= scores['password']:
                return 'confirm_password', scores['confirm_password']
            elif scores['password'] > scores['confirm_password'] + 10:
                return 'password', scores['password']
            else:
                return 'confirm_password', scores['confirm_password']
        
        # Return highest scoring field type
        if scores:
            best_type = max(scores, key=scores.get)
            return best_type, scores[best_type]
        
        return None, 0
    
    def get_best_field(self, field_type: str) -> Optional[FieldCandidate]:
        """Get the highest confidence field of a specific type."""
        candidates = [f for f in self.discovered_fields if f.field_type == field_type]
        return candidates[0] if candidates else None
    
    def get_all_fields_by_type(self, field_type: str) -> List[FieldCandidate]:
        """Get all fields of a specific type, sorted by confidence."""
        return [f for f in self.discovered_fields if f.field_type == field_type]


# ============================================================================
# FRAMEWORK-AWARE VALUE SETTER WITH IFRAME/SHADOW DOM SUPPORT
# ============================================================================

async def set_field_value(
    locator: Locator,
    value: str,
    verbose: bool = True,
    frame_context: Optional[Frame] = None
) -> bool:
    """
    Set field value with framework-aware fallback chain and robust validation.
    Supports iframe and Shadow DOM fields.
    Tries multiple methods to ensure React/Vue/Angular state updates.
    Returns True if successful, False otherwise.
    
    Args:
        locator: Playwright locator for the field
        value: Value to set
        verbose: Enable logging
        frame_context: Optional frame context for iframe fields
    """
    
    def log(msg: str):
        if verbose:
            print(f"[FILL] {msg}")
    
    # If this is an iframe field, we already have the correct locator from that frame
    # No need to switch contexts - the locator is already bound to the frame
    
    # Escape value for JavaScript to prevent injection issues
    escaped_value = value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")
    
    # Method 1: Playwright fill with validation
    try:
        log(f"Trying fill() method...")
        await locator.clear()
        await asyncio.sleep(0.05)
        await locator.fill(value)
        await asyncio.sleep(0.15)
        
        # Verify it worked
        current_value = await locator.input_value()
        if current_value == value:
            log(f"✓ fill() succeeded")
            return True
        else:
            log(f"fill() validation failed: expected '{value}', got '{current_value}'")
    except Exception as e:
        log(f"fill() failed: {e}")
    
    # Method 2: Type character by character with slower delay
    try:
        log(f"Trying type() method...")
        await locator.clear()
        await asyncio.sleep(0.1)
        await locator.type(value, delay=75)
        await asyncio.sleep(0.15)
        
        current_value = await locator.input_value()
        if current_value == value:
            log(f"✓ type() succeeded")
            return True
        else:
            log(f"type() validation failed: expected '{value}', got '{current_value}'")
    except Exception as e:
        log(f"type() failed: {e}")
    
    # Method 3: JavaScript value injection + comprehensive events
    try:
        log(f"Trying JavaScript injection...")
        await locator.evaluate(f"""
            el => {{
                // Clear first
                el.value = '';
                
                // Set value
                el.value = '{escaped_value}';
                
                // React-specific setter (must be before events)
                try {{
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value'
                    ).set;
                    if (nativeInputValueSetter) {{
                        nativeInputValueSetter.call(el, '{escaped_value}');
                    }}
                }} catch (e) {{}}
                
                // Trigger comprehensive event chain
                el.dispatchEvent(new Event('input', {{ bubbles: true, cancelable: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true, cancelable: true }}));
                el.dispatchEvent(new Event('keydown', {{ bubbles: true, cancelable: true }}));
                el.dispatchEvent(new Event('keyup', {{ bubbles: true, cancelable: true }}));
                el.dispatchEvent(new Event('blur', {{ bubbles: true, cancelable: true }}));
                
                // Vue-specific
                el.dispatchEvent(new Event('update:modelValue', {{ bubbles: true }}));
            }}
        """)
        await asyncio.sleep(0.25)
        
        current_value = await locator.input_value()
        if current_value == value:
            log(f"✓ JavaScript injection succeeded")
            return True
        else:
            log(f"JavaScript validation failed: expected '{value}', got '{current_value}'")
    except Exception as e:
        log(f"JavaScript injection failed: {e}")
    
    # Method 4: Focus + clear + type + blur with validation
    try:
        log(f"Trying focus + type + blur...")
        await locator.focus()
        await asyncio.sleep(0.1)
        
        # Triple-clear to ensure empty
        await locator.press("Control+A")
        await locator.press("Backspace")
        await asyncio.sleep(0.05)
        
        await locator.type(value, delay=100)
        await asyncio.sleep(0.15)
        await locator.blur()
        await asyncio.sleep(0.25)
        
        current_value = await locator.input_value()
        if current_value == value:
            log(f"✓ focus + type + blur succeeded")
            return True
        else:
            log(f"focus+type+blur validation failed: expected '{value}', got '{current_value}'")
    except Exception as e:
        log(f"focus + type + blur failed: {e}")
    
    # Method 5: Last resort - press and fill
    try:
        log(f"Trying press and fill...")
        await locator.click()
        await asyncio.sleep(0.1)
        await locator.press("Control+A")
        await locator.press("Delete")
        await asyncio.sleep(0.05)
        
        for char in value:
            await locator.press(char)
            await asyncio.sleep(0.05)
        
        await asyncio.sleep(0.2)
        
        current_value = await locator.input_value()
        if current_value == value:
            log(f"✓ press and fill succeeded")
            return True
    except Exception as e:
        log(f"press and fill failed: {e}")
    
    log(f"✗ All 5 methods failed to set value")
    return False