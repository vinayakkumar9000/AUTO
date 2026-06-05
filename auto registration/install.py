#!/usr/bin/env python3
"""
Installation and Setup Script for Auto Registration Workflow
Automates the installation of dependencies and Playwright browsers
"""

import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run a command and display progress."""
    print(f"\n{'='*60}")
    print(f"📦 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=False,
            text=True
        )
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e}")
        return False

def main():
    """Main installation process."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║     Auto Registration Workflow - Installation Script        ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    script_dir = Path(__file__).parent
    
    # Step 1: Install Python dependencies
    print("\n[1/2] Installing Python dependencies...")
    if not run_command(
        f'"{sys.executable}" -m pip install -r "{script_dir / "requirements.txt"}"',
        "Installing Python packages (requests, rich, playwright)"
    ):
        print("\n⚠️  Failed to install Python dependencies")
        print("Please run manually: pip install -r requirements.txt")
        return False
    
    # Step 2: Install Playwright browsers
    print("\n[2/2] Installing Playwright browsers...")
    if not run_command(
        f'"{sys.executable}" -m playwright install chromium',
        "Installing Chromium browser for Playwright"
    ):
        print("\n⚠️  Failed to install Playwright browsers")
        print("Please run manually: playwright install chromium")
        return False
    
    # Success message
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                  ✓ Installation Complete!                   ║
╚══════════════════════════════════════════════════════════════╝

Next Steps:
-----------
1. Get your FreeModel API key from: https://freemodel.dev
2. Run the automation script:
   
   python auto_registration.py
   
3. Follow the interactive prompts to complete registration

For detailed usage instructions, see README.md

Happy automating! 🚀
    """)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        sys.exit(1)
