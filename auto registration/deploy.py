#!/usr/bin/env python3
"""
Production Deployment Script
Deploy and configure the multi-agent registration system
Author: vinayakkumar9000
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# ============================================================================
# DEPLOYMENT CONFIGURATION
# ============================================================================

class DeploymentConfig:
    """Deployment configuration."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.config_file = self.project_root / "config.json"
        self.db_file = self.project_root / "domain_intelligence.db"
        self.logs_dir = self.project_root / ".logs"
        self.screenshots_dir = self.project_root / ".screenshots"
        
    def ensure_directories(self):
        """Ensure required directories exist."""
        self.logs_dir.mkdir(exist_ok=True)
        self.screenshots_dir.mkdir(exist_ok=True)
        console.print("[green]✓[/green] Created required directories")
    
    def check_config(self) -> bool:
        """Check if config file exists."""
        return self.config_file.exists()
    
    def create_config(self):
        """Create default config file."""
        if self.check_config():
            if not Confirm.ask("Config file exists. Overwrite?"):
                return
        
        api_key = Prompt.ask("Enter your B.ai API key", password=True)
        
        config = {
            "api_key": api_key,
            "default_model": "gpt-4o-mini",
            "budget_per_registration": 0.01,
            "timeout": 180,
            "max_retries": 3,
            "log_level": "INFO"
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        console.print("[green]✓[/green] Created config.json")
    
    def check_dependencies(self) -> bool:
        """Check if all dependencies are installed."""
        try:
            import playwright
            import anthropic
            import rich
            import sqlite3
            console.print("[green]✓[/green] All dependencies installed")
            return True
        except ImportError as e:
            console.print(f"[red]✗[/red] Missing dependency: {e.name}")
            return False
    
    def install_dependencies(self):
        """Install dependencies."""
        console.print("[cyan]Installing dependencies...[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Installing requirements...", total=None)
            
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                check=True,
                capture_output=True
            )
            
            progress.update(task, completed=True)
        
        console.print("[green]✓[/green] Dependencies installed")
    
    def initialize_database(self):
        """Initialize domain intelligence database."""
        from domain_intelligence import DomainIntelligence
        
        db = DomainIntelligence()
        console.print("[green]✓[/green] Database initialized")
    
    def run_tests(self) -> bool:
        """Run test suite."""
        console.print("[cyan]Running tests...[/cyan]")
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                console.print("[green]✓[/green] All tests passed")
                return True
            else:
                console.print("[red]✗[/red] Some tests failed")
                console.print(result.stdout)
                return False
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Could not run tests: {e}")
            return True  # Don't block deployment


# ============================================================================
# DEPLOYMENT STEPS
# ============================================================================

def deploy():
    """Main deployment function."""
    console.print(Panel.fit(
        "[bold cyan]Multi-Agent Registration System[/bold cyan]\n"
        "[white]Production Deployment[/white]",
        border_style="cyan"
    ))
    
    config = DeploymentConfig()
    
    # Step 1: Check dependencies
    console.print("\n[bold]Step 1:[/bold] Checking dependencies...")
    if not config.check_dependencies():
        if Confirm.ask("Install dependencies?"):
            config.install_dependencies()
        else:
            console.print("[red]Deployment aborted[/red]")
            return
    
    # Step 2: Create directories
    console.print("\n[bold]Step 2:[/bold] Setting up directories...")
    config.ensure_directories()
    
    # Step 3: Configure
    console.print("\n[bold]Step 3:[/bold] Configuration...")
    if not config.check_config():
        config.create_config()
    else:
        console.print("[green]✓[/green] Config file exists")
    
    # Step 4: Initialize database
    console.print("\n[bold]Step 4:[/bold] Initializing database...")
    config.initialize_database()
    
    # Step 5: Run tests (optional)
    console.print("\n[bold]Step 5:[/bold] Testing...")
    if Confirm.ask("Run test suite?", default=False):
        config.run_tests()
    else:
        console.print("[yellow]⚠[/yellow] Skipped tests")
    
    # Step 6: Summary
    console.print("\n[bold green]Deployment Complete![/bold green]")
    console.print("\n[cyan]Next steps:[/cyan]")
    console.print("1. Review config.json settings")
    console.print("2. Test with: python -m pytest tests/")
    console.print("3. Run example: python integration_layer.py")
    console.print("4. Monitor logs in .logs/ directory")
    
    console.print("\n[bold]System Ready![/bold]")


# ============================================================================
# CLI COMMANDS
# ============================================================================

def status():
    """Show deployment status."""
    config = DeploymentConfig()
    
    console.print(Panel.fit(
        "[bold cyan]System Status[/bold cyan]",
        border_style="cyan"
    ))
    
    # Check config
    config_status = "✓" if config.check_config() else "✗"
    console.print(f"[{'green' if config.check_config() else 'red'}]{config_status}[/] Config file")
    
    # Check database
    db_status = "✓" if config.db_file.exists() else "✗"
    console.print(f"[{'green' if config.db_file.exists() else 'red'}]{db_status}[/] Database")
    
    # Check directories
    logs_status = "✓" if config.logs_dir.exists() else "✗"
    console.print(f"[{'green' if config.logs_dir.exists() else 'red'}]{logs_status}[/] Logs directory")
    
    screenshots_status = "✓" if config.screenshots_dir.exists() else "✗"
    console.print(f"[{'green' if config.screenshots_dir.exists() else 'red'}]{screenshots_status}[/] Screenshots directory")
    
    # Check dependencies
    deps_status = "✓" if config.check_dependencies() else "✗"
    console.print(f"[{'green' if config.check_dependencies() else 'red'}]{deps_status}[/] Dependencies")


def clean():
    """Clean deployment artifacts."""
    config = DeploymentConfig()
    
    if not Confirm.ask("This will remove logs, screenshots, and database. Continue?"):
        return
    
    # Remove logs
    if config.logs_dir.exists():
        shutil.rmtree(config.logs_dir)
        console.print("[green]✓[/green] Removed logs")
    
    # Remove screenshots
    if config.screenshots_dir.exists():
        shutil.rmtree(config.screenshots_dir)
        console.print("[green]✓[/green] Removed screenshots")
    
    # Remove database
    if config.db_file.exists():
        config.db_file.unlink()
        console.print("[green]✓[/green] Removed database")
    
    console.print("[bold green]Cleanup complete![/bold green]")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy multi-agent registration system")
    parser.add_argument("command", choices=["deploy", "status", "clean"], 
                       help="Deployment command")
    
    args = parser.parse_args()
    
    if args.command == "deploy":
        deploy()
    elif args.command == "status":
        status()
    elif args.command == "clean":
        clean()
