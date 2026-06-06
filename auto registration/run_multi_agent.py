#!/usr/bin/env python3
"""
Multi-Agent Registration Runner
Executes registration using the AI-first multi-agent architecture
Author: vinayakkumar9000
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel

from integration_layer import create_integration_layer
from identity_generator import generate_identity
from email_providers import generate_email_with_fallback

console = Console()


async def run_multi_agent_registration(
    url: str,
    session_id: str,
    logger: logging.Logger,
    budget: float = 0.01,
    timeout: int = 180
) -> Dict[str, Any]:
    """
    Execute registration using multi-agent system.
    
    Args:
        url: Registration URL
        session_id: Session identifier
        logger: Logger instance
        budget: Maximum AI budget in dollars
        timeout: Maximum execution time in seconds
    
    Returns:
        Registration result dictionary
    """
    console.print("\n[bold magenta]🤖 MULTI-AGENT MODE ENABLED[/bold magenta]")
    logger.info("="*80)
    logger.info("MULTI-AGENT REGISTRATION STARTED")
    logger.info(f"Session: {session_id}")
    logger.info(f"URL: {url}")
    logger.info(f"Budget: ${budget}")
    logger.info(f"Timeout: {timeout}s")
    logger.info("="*80)
    
    try:
        # Step 1: Generate Identity
        console.print("\n[bold cyan]═══ Step 1: Generate Identity ═══[/bold cyan]")
        logger.info("Generating identity...")
        
        identity = generate_identity()
        logger.info(f"Identity: {identity.full_name}, {identity.gender}, {identity.age}y")
        
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
        
        console.print(Panel(
            f"[bold]Email:[/bold] {email}\n"
            f"[bold]Provider:[/bold] {provider}",
            title="📧 Email Generated",
            border_style="cyan"
        ))
        logger.info(f"Email: {email} (provider: {provider})")
        
        # Step 3: Initialize Multi-Agent System
        console.print("\n[bold cyan]═══ Step 3: Initialize Multi-Agent System ═══[/bold cyan]")
        logger.info("Creating integration layer...")
        
        integration = create_integration_layer(logger=logger)
        console.print("[green]✓[/green] Integration layer initialized")
        logger.info("Integration layer ready")
        
        # Prepare identity data
        identity_data = {
            "email": email,
            "first_name": identity.first_name,
            "last_name": identity.last_name,
            "full_name": identity.full_name,
            "username": email.split("@")[0],
            "password": "SecurePass123!@#",
            "date_of_birth": identity.date_of_birth,
            "phone": identity.phone,
            "address": identity.address,
            "city": identity.city,
            "state": identity.state,
            "zip_code": identity.zip_code,
            "country": identity.country,
            "gender": identity.gender,
            "age": identity.age
        }
        
        # Step 4: Execute Multi-Agent Registration
        console.print("\n[bold cyan]═══ Step 4: Execute Multi-Agent Registration ═══[/bold cyan]")
        logger.info("Starting multi-agent workflow...")
        
        console.print("[cyan]🤖 CoordinatorAgent analyzing site...[/cyan]")
        console.print("[cyan]🤖 PlannerAgent creating strategy...[/cyan]")
        console.print("[cyan]🤖 FormAgent filling fields...[/cyan]")
        console.print("[cyan]🤖 EmailAgent monitoring inbox...[/cyan]")
        
        result = await integration.execute_registration(
            url=url,
            email=email,
            identity_data=identity_data,
            budget=budget,
            timeout=timeout
        )
        
        # Step 5: Display Results
        console.print("\n[bold cyan]═══ Step 5: Results ═══[/bold cyan]")
        
        if result.get("success"):
            console.print(Panel(
                f"[bold green]✓ Registration Successful[/bold green]\n\n"
                f"[bold]Workflow ID:[/bold] {result.get('workflow_id')}\n"
                f"[bold]Execution Time:[/bold] {result.get('execution_time', 0):.2f}s\n"
                f"[bold]AI Cost:[/bold] ${result.get('cost', 0):.6f}\n"
                f"[bold]Confidence:[/bold] {result.get('confidence', 0):.2%}\n"
                f"[bold]Steps:[/bold] {len(result.get('steps_completed', []))}",
                title="🎉 Success",
                border_style="green"
            ))
            logger.info(f"Registration successful: {result.get('workflow_id')}")
        else:
            console.print(Panel(
                f"[bold red]✗ Registration Failed[/bold red]\n\n"
                f"[bold]Error:[/bold] {result.get('error', 'Unknown')}\n"
                f"[bold]Workflow ID:[/bold] {result.get('workflow_id')}\n"
                f"[bold]Execution Time:[/bold] {result.get('execution_time', 0):.2f}s\n"
                f"[bold]AI Cost:[/bold] ${result.get('cost', 0):.6f}",
                title="❌ Failed",
                border_style="red"
            ))
            logger.error(f"Registration failed: {result.get('error')}")
        
        # Display agent statistics
        if hasattr(integration, 'coordinator') and hasattr(integration.coordinator, 'get_stats'):
            stats = integration.coordinator.get_stats()
            console.print("\n[bold cyan]Agent Statistics:[/bold cyan]")
            console.print(f"  Total Agents Used: {stats.get('agents_used', 0)}")
            console.print(f"  Total AI Calls: {stats.get('ai_calls', 0)}")
            console.print(f"  Total Cost: ${stats.get('total_cost', 0):.6f}")
        
        return result
        
    except asyncio.TimeoutError:
        error_msg = f"Multi-agent workflow timed out after {timeout}s"
        console.print(f"\n[red]✗ {error_msg}[/red]")
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "session_id": session_id
        }
        
    except Exception as e:
        error_msg = f"Multi-agent workflow error: {str(e)}"
        console.print(f"\n[red]✗ {error_msg}[/red]")
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id
        }


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Setup logging
    LOG_DIR = Path(__file__).parent / ".logs"
    LOG_DIR.mkdir(exist_ok=True)
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"session_{session_id}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    # Get URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        from rich.prompt import Prompt
        url = Prompt.ask("Enter registration URL")
    
    if not url.startswith("http"):
        console.print("[red]✗[/red] Invalid URL. Must start with http:// or https://")
        sys.exit(1)
    
    # Run multi-agent registration
    try:
        result = asyncio.run(run_multi_agent_registration(
            url=url,
            session_id=session_id,
            logger=logger,
            budget=0.01,
            timeout=180
        ))
        
        if not result.get("success"):
            sys.exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]✗ Fatal error: {e}[/red]")
        sys.exit(1)
