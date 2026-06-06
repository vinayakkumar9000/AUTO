#!/usr/bin/env python3
"""
Debug script to inspect IBM Bob trial page structure
"""
from playwright.sync_api import sync_playwright
import time
import json

def inspect_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Navigating to IBM Bob trial page...")
        try:
            page.goto('https://bob.ibm.com/trial', wait_until='load', timeout=60000)
        except Exception as e:
            print(f"Navigation error (continuing anyway): {e}")
        
        print("\n" + "="*80)
        print("WAITING FOR PAGE TO LOAD...")
        print("="*80)
        time.sleep(10)
        
        # Check frames
        frames = page.frames
        print(f"\n{'='*80}")
        print(f"TOTAL FRAMES: {len(frames)}")
        print("="*80)
        for i, frame in enumerate(frames):
            print(f"\nFrame {i}:")
            print(f"  URL: {frame.url}")
            print(f"  Name: {frame.name}")
        
        # Check inputs in main page
        print(f"\n{'='*80}")
        print("INPUTS IN MAIN PAGE")
        print("="*80)
        inputs = page.locator('input').all()
        print(f"Total inputs: {len(inputs)}")
        for i, inp in enumerate(inputs[:20]):
            try:
                input_type = inp.get_attribute('type')
                input_name = inp.get_attribute('name')
                input_id = inp.get_attribute('id')
                input_placeholder = inp.get_attribute('placeholder')
                input_class = inp.get_attribute('class')
                visible = inp.is_visible()
                print(f"\nInput {i}:")
                print(f"  Type: {input_type}")
                print(f"  Name: {input_name}")
                print(f"  ID: {input_id}")
                print(f"  Placeholder: {input_placeholder}")
                print(f"  Class: {input_class}")
                print(f"  Visible: {visible}")
            except Exception as e:
                print(f"  Error: {e}")
        
        # Check for iframes with forms
        print(f"\n{'='*80}")
        print("CHECKING IFRAMES FOR FORMS")
        print("="*80)
        for i, frame in enumerate(frames[1:], 1):  # Skip main frame
            try:
                frame_inputs = frame.locator('input').all()
                if frame_inputs:
                    print(f"\nFrame {i} ({frame.url}):")
                    print(f"  Total inputs: {len(frame_inputs)}")
                    for j, inp in enumerate(frame_inputs[:10]):
                        try:
                            input_type = inp.get_attribute('type')
                            input_name = inp.get_attribute('name')
                            input_id = inp.get_attribute('id')
                            visible = inp.is_visible()
                            print(f"    Input {j}: type={input_type}, name={input_name}, id={input_id}, visible={visible}")
                        except Exception as e:
                            print(f"    Input {j}: Error - {e}")
            except Exception as e:
                print(f"Frame {i}: Error - {e}")
        
        # Check buttons
        print(f"\n{'='*80}")
        print("BUTTONS ON PAGE")
        print("="*80)
        buttons = page.locator('button').all()
        print(f"Total buttons: {len(buttons)}")
        for i, btn in enumerate(buttons[:20]):
            try:
                text = btn.inner_text()
                btn_type = btn.get_attribute('type')
                btn_class = btn.get_attribute('class')
                visible = btn.is_visible()
                print(f"\nButton {i}:")
                print(f"  Text: {text}")
                print(f"  Type: {btn_type}")
                print(f"  Class: {btn_class}")
                print(f"  Visible: {visible}")
            except Exception as e:
                print(f"  Error: {e}")
        
        # Save page HTML
        print(f"\n{'='*80}")
        print("SAVING PAGE HTML")
        print("="*80)
        html = page.content()
        with open('ibm_bob_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("Saved to: ibm_bob_page.html")
        
        print("\n\nPress Enter to close browser...")
        input()
        
        browser.close()

if __name__ == "__main__":
    inspect_page()
