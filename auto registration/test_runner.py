#!/usr/bin/env python3
"""
Automated Test Runner with Metrics Collection
Tests registration automation against local HTML test pages
Author: vinayakkumar9000
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import statistics

from playwright.async_api import async_playwright, Page, Browser
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "identity"))
from identity_generator import generate_identity
from integration_layer import UnifiedFormFiller

console = Console()

# ============================================================================
# TEST RESULT DATA STRUCTURES
# ============================================================================

@dataclass
class FieldDetectionResult:
    """Result of field detection for a specific field type."""
    field_type: str
    detected: bool
    confidence: int
    time_ms: float
    context: str  # "main", "iframe", "shadow"

@dataclass
class TestResult:
    """Result of a single test run."""
    test_name: str
    url: str
    success: bool
    duration_seconds: float
    error_message: Optional[str]
    fields_detected: List[FieldDetectionResult]
    fields_filled: Dict[str, bool]
    screenshot_path: Optional[str]
    timestamp: str

@dataclass
class TestMetrics:
    """Aggregated metrics across all tests."""
    total_tests: int
    successful_tests: int
    failed_tests: int
    success_rate: float
    avg_duration: float
    field_detection_accuracy: Dict[str, float]
    field_fill_success_rate: Dict[str, float]
    total_duration: float

# ============================================================================
# TEST CONFIGURATION
# ============================================================================

TEST_PAGES = [
    {
        "name": "Basic Email Only",
        "file": "tests/basic_email_only.html",
        "expected_fields": ["email"],
        "requires_otp": False,
        "complexity": "basic"
    },
    {
        "name": "Multi-Step Email + OTP",
        "file": "tests/multistep_email_otp.html",
        "expected_fields": ["email", "otp"],
        "requires_otp": True,
        "complexity": "medium"
    },
    {
        "name": "Complex Full Registration",
        "file": "tests/complex_full_registration.html",
        "expected_fields": ["email", "first_name", "last_name", "username", "password", "confirm_password"],
        "requires_otp": False,
        "complexity": "complex"
    },
    {
        "name": "React Form",
        "file": "tests/react_form.html",
        "expected_fields": ["email", "username", "password", "confirm_password"],
        "requires_otp": False,
        "complexity": "framework"
    }
]

# ============================================================================
# TEST RUNNER
# ============================================================================

class AutomationTestRunner:
    """Automated test runner with metrics collection."""
    
    def __init__(self, base_dir: Path, verbose: bool = True):
        self.base_dir = base_dir
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.screenshot_dir = base_dir / ".test_screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)
    
    def log(self, message: str):
        """Log message if verbose."""
        if self.verbose:
            console.print(message)
    
    async def run_single_test(
        self,
        test_config: dict,
        browser: Browser,
        test_number: int,
        total_tests: int
    ) -> TestResult:
        """Run a single test and collect metrics."""
        test_name = test_config["name"]
        test_file = self.base_dir / test_config["file"]
        
        if not test_file.exists():
            return TestResult(
                test_name=test_name,
                url=str(test_file),
                success=False,
                duration_seconds=0,
                error_message=f"Test file not found: {test_file}",
                fields_detected=[],
                fields_filled={},
                screenshot_path=None,
                timestamp=datetime.now().isoformat()
            )
        
        console.print(f"\n[bold cyan]═══ Test {test_number}/{total_tests}: {test_name} ═══[/bold cyan]")
        
        start_time = time.time()
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to test page
            url = f"file:///{test_file.absolute().as_posix()}"
            await page.goto(url, wait_until="domcontentloaded", timeout=10000)
            self.log(f"[green]✓[/green] Page loaded: {test_name}")
            
            # Generate test identity
            identity = generate_identity()
            test_email = f"test_{int(time.time())}@example.com"
            
            # Initialize form filler
            filler = UnifiedFormFiller(page, identity, verbose=False)
            
            # Discover and fill fields
            detection_start = time.time()
            filled_fields = await filler.discover_and_fill_all(test_email)
            detection_time = (time.time() - detection_start) * 1000
            
            # Handle multi-step forms (OTP)
            if test_config.get("requires_otp", False):
                # Try to find and click "Send Code" button
                try:
                    send_buttons = await page.locator('button, [role="button"], input[type="submit"]').all()
                    for btn in send_buttons:
                        try:
                            if not await btn.is_visible() or not await btn.is_enabled():
                                continue
                            text = await btn.inner_text()
                            if any(keyword in text.lower() for keyword in ['send', 'code', 'verify', 'otp']):
                                await btn.click()
                                await asyncio.sleep(1)  # Wait for step 2 to appear
                                break
                        except:
                            continue
                    
                    # Now wait for OTP field to appear
                    otp_field = await filler.wait_for_otp_field(timeout=15)
                    if otp_field:
                        # Fill with test OTP
                        await otp_field.fill("123456")
                        filled_fields["otp"] = True
                    else:
                        filled_fields["otp"] = False
                except Exception as e:
                    filled_fields["otp"] = False
            
            # Collect field detection results
            fields_detected = []
            for field_type in test_config["expected_fields"]:
                detected = filled_fields.get(field_type, False)
                fields_detected.append(FieldDetectionResult(
                    field_type=field_type,
                    detected=detected,
                    confidence=100 if detected else 0,
                    time_ms=detection_time / len(test_config["expected_fields"]),
                    context="main"
                ))
            
            # Check if all expected fields were filled
            all_filled = all(filled_fields.get(f, False) for f in test_config["expected_fields"])
            
            duration = time.time() - start_time
            
            # Capture screenshot
            screenshot_path = self.screenshot_dir / f"{test_name.replace(' ', '_')}_{int(time.time())}.png"
            await page.screenshot(path=str(screenshot_path))
            
            result = TestResult(
                test_name=test_name,
                url=url,
                success=all_filled,
                duration_seconds=duration,
                error_message=None if all_filled else "Not all expected fields were filled",
                fields_detected=fields_detected,
                fields_filled=filled_fields,
                screenshot_path=str(screenshot_path),
                timestamp=datetime.now().isoformat()
            )
            
            if all_filled:
                console.print(f"[green]✓ Test PASSED[/green] ({duration:.2f}s)")
            else:
                console.print(f"[yellow]⚠ Test PARTIAL[/yellow] ({duration:.2f}s)")
            
            return result
        
        except Exception as e:
            duration = time.time() - start_time
            console.print(f"[red]✗ Test FAILED[/red]: {e}")
            
            # Capture error screenshot
            try:
                screenshot_path = self.screenshot_dir / f"{test_name.replace(' ', '_')}_error_{int(time.time())}.png"
                await page.screenshot(path=str(screenshot_path))
            except:
                screenshot_path = None
            
            return TestResult(
                test_name=test_name,
                url=str(test_file),
                success=False,
                duration_seconds=duration,
                error_message=str(e),
                fields_detected=[],
                fields_filled={},
                screenshot_path=str(screenshot_path) if screenshot_path else None,
                timestamp=datetime.now().isoformat()
            )
        
        finally:
            await context.close()
    
    async def run_all_tests(self, iterations: int = 1) -> TestMetrics:
        """Run all tests and collect metrics."""
        console.print("\n[bold cyan]╔═══════════════════════════════════════╗[/bold cyan]")
        console.print("[bold cyan]║   Automated Test Runner v1.0         ║[/bold cyan]")
        console.print("[bold cyan]╚═══════════════════════════════════════╝[/bold cyan]\n")
        
        total_start = time.time()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            total_tests = len(TEST_PAGES) * iterations
            test_count = 0
            
            for iteration in range(iterations):
                if iterations > 1:
                    console.print(f"\n[bold yellow]═══ Iteration {iteration + 1}/{iterations} ═══[/bold yellow]")
                
                for test_config in TEST_PAGES:
                    test_count += 1
                    result = await self.run_single_test(
                        test_config,
                        browser,
                        test_count,
                        total_tests
                    )
                    self.results.append(result)
                    
                    # Small delay between tests
                    await asyncio.sleep(0.5)
            
            await browser.close()
        
        total_duration = time.time() - total_start
        
        # Calculate metrics
        metrics = self._calculate_metrics(total_duration)
        
        return metrics
    
    def _calculate_metrics(self, total_duration: float) -> TestMetrics:
        """Calculate aggregated metrics from test results."""
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        durations = [r.duration_seconds for r in self.results]
        avg_duration = statistics.mean(durations) if durations else 0
        
        # Field detection accuracy
        field_detection_accuracy = {}
        field_types = set()
        for result in self.results:
            for field in result.fields_detected:
                field_types.add(field.field_type)
        
        for field_type in field_types:
            detections = [
                field.detected
                for result in self.results
                for field in result.fields_detected
                if field.field_type == field_type
            ]
            if detections:
                field_detection_accuracy[field_type] = sum(detections) / len(detections) * 100
        
        # Field fill success rate
        field_fill_success_rate = {}
        for field_type in field_types:
            fills = [
                result.fields_filled.get(field_type, False)
                for result in self.results
            ]
            if fills:
                field_fill_success_rate[field_type] = sum(fills) / len(fills) * 100
        
        return TestMetrics(
            total_tests=total_tests,
            successful_tests=successful_tests,
            failed_tests=failed_tests,
            success_rate=success_rate,
            avg_duration=avg_duration,
            field_detection_accuracy=field_detection_accuracy,
            field_fill_success_rate=field_fill_success_rate,
            total_duration=total_duration
        )
    
    def display_results(self, metrics: TestMetrics):
        """Display test results in a formatted table."""
        console.print("\n[bold green]═══════════════════════════════════════[/bold green]")
        console.print("[bold green]         TEST RESULTS SUMMARY          [/bold green]")
        console.print("[bold green]═══════════════════════════════════════[/bold green]\n")
        
        # Overall metrics
        table = Table(title="Overall Metrics", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Tests", str(metrics.total_tests))
        table.add_row("Successful", f"{metrics.successful_tests} ({metrics.success_rate:.1f}%)")
        table.add_row("Failed", str(metrics.failed_tests))
        table.add_row("Avg Duration", f"{metrics.avg_duration:.2f}s")
        table.add_row("Total Duration", f"{metrics.total_duration:.2f}s")
        
        console.print(table)
        
        # Field detection accuracy
        console.print("\n")
        detection_table = Table(title="Field Detection Accuracy", show_header=True, header_style="bold cyan")
        detection_table.add_column("Field Type", style="cyan")
        detection_table.add_column("Accuracy", style="green")
        
        for field_type, accuracy in sorted(metrics.field_detection_accuracy.items()):
            color = "green" if accuracy >= 90 else "yellow" if accuracy >= 70 else "red"
            detection_table.add_row(field_type, f"[{color}]{accuracy:.1f}%[/{color}]")
        
        console.print(detection_table)
        
        # Field fill success rate
        console.print("\n")
        fill_table = Table(title="Field Fill Success Rate", show_header=True, header_style="bold cyan")
        fill_table.add_column("Field Type", style="cyan")
        fill_table.add_column("Success Rate", style="green")
        
        for field_type, rate in sorted(metrics.field_fill_success_rate.items()):
            color = "green" if rate >= 90 else "yellow" if rate >= 70 else "red"
            fill_table.add_row(field_type, f"[{color}]{rate:.1f}%[/{color}]")
        
        console.print(fill_table)
        
        # Individual test results
        console.print("\n")
        results_table = Table(title="Individual Test Results", show_header=True, header_style="bold cyan")
        results_table.add_column("Test Name", style="cyan")
        results_table.add_column("Status", style="green")
        results_table.add_column("Duration", style="yellow")
        
        for result in self.results:
            status = "[green]✓ PASS[/green]" if result.success else "[red]✗ FAIL[/red]"
            results_table.add_row(
                result.test_name,
                status,
                f"{result.duration_seconds:.2f}s"
            )
        
        console.print(results_table)
    
    def save_report(self, metrics: TestMetrics, output_file: Path):
        """Save detailed report to JSON file."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "metrics": asdict(metrics),
            "results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "duration_seconds": r.duration_seconds,
                    "error_message": r.error_message,
                    "fields_detected": [asdict(f) for f in r.fields_detected],
                    "fields_filled": r.fields_filled,
                    "screenshot_path": r.screenshot_path,
                    "timestamp": r.timestamp
                }
                for r in self.results
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        console.print(f"\n[green]✓[/green] Report saved to: {output_file}")

# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Main entry point."""
    base_dir = Path(__file__).parent
    
    # Run tests
    runner = AutomationTestRunner(base_dir, verbose=True)
    metrics = await runner.run_all_tests(iterations=1)
    
    # Display results
    runner.display_results(metrics)
    
    # Save report
    report_dir = base_dir / ".test_reports"
    report_dir.mkdir(exist_ok=True)
    report_file = report_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    runner.save_report(metrics, report_file)
    
    # Exit with appropriate code
    if metrics.success_rate < 100:
        console.print(f"\n[yellow]⚠ Some tests failed. Success rate: {metrics.success_rate:.1f}%[/yellow]")
        return 1
    else:
        console.print(f"\n[green]✓ All tests passed! Success rate: {metrics.success_rate:.1f}%[/green]")
        return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Tests interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]✗ Fatal error: {e}[/red]")
        sys.exit(1)
