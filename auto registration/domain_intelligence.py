#!/usr/bin/env python3
"""
Domain Intelligence Database
Persistent knowledge system for learning from registration attempts
Author: vinayakkumar9000
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from contextlib import contextmanager
import logging

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class DomainProfile:
    """Profile for a specific domain."""
    domain: str
    framework: Optional[str] = None
    verification_type: Optional[str] = None
    success_rate: float = 0.0
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    known_fields: Dict[str, List[str]] = None
    known_selectors: Dict[str, List[str]] = None
    failed_selectors: Dict[str, List[str]] = None
    otp_average_seconds: Optional[int] = None
    anti_bot_mechanisms: List[str] = None
    complexity_score: float = 0.5
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    last_updated: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.known_fields is None:
            self.known_fields = {}
        if self.known_selectors is None:
            self.known_selectors = {}
        if self.failed_selectors is None:
            self.failed_selectors = {}
        if self.anti_bot_mechanisms is None:
            self.anti_bot_mechanisms = []
        if self.metadata is None:
            self.metadata = {}
        if self.last_updated is None:
            self.last_updated = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "domain": self.domain,
            "framework": self.framework,
            "verification_type": self.verification_type,
            "success_rate": self.success_rate,
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "known_fields": json.dumps(self.known_fields),
            "known_selectors": json.dumps(self.known_selectors),
            "failed_selectors": json.dumps(self.failed_selectors),
            "otp_average_seconds": self.otp_average_seconds,
            "anti_bot_mechanisms": json.dumps(self.anti_bot_mechanisms),
            "complexity_score": self.complexity_score,
            "last_success": self.last_success,
            "last_failure": self.last_failure,
            "last_updated": self.last_updated,
            "metadata": json.dumps(self.metadata)
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DomainProfile':
        """Create from dictionary."""
        return cls(
            domain=data["domain"],
            framework=data.get("framework"),
            verification_type=data.get("verification_type"),
            success_rate=data.get("success_rate", 0.0),
            total_attempts=data.get("total_attempts", 0),
            successful_attempts=data.get("successful_attempts", 0),
            failed_attempts=data.get("failed_attempts", 0),
            known_fields=json.loads(data.get("known_fields", "{}")),
            known_selectors=json.loads(data.get("known_selectors", "{}")),
            failed_selectors=json.loads(data.get("failed_selectors", "{}")),
            otp_average_seconds=data.get("otp_average_seconds"),
            anti_bot_mechanisms=json.loads(data.get("anti_bot_mechanisms", "[]")),
            complexity_score=data.get("complexity_score", 0.5),
            last_success=data.get("last_success"),
            last_failure=data.get("last_failure"),
            last_updated=data.get("last_updated"),
            metadata=json.loads(data.get("metadata", "{}"))
        )

@dataclass
class RegistrationAttempt:
    """Record of a registration attempt."""
    id: Optional[int] = None
    domain: str = ""
    workflow_id: str = ""
    success: bool = False
    execution_time: float = 0.0
    total_cost: float = 0.0
    verification_method: Optional[str] = None
    fields_detected: Dict[str, str] = None
    selectors_used: Dict[str, str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    models_used: List[str] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.fields_detected is None:
            self.fields_detected = {}
        if self.selectors_used is None:
            self.selectors_used = {}
        if self.models_used is None:
            self.models_used = []
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

# ============================================================================
# DOMAIN INTELLIGENCE DATABASE
# ============================================================================

class DomainIntelligence:
    """
    Persistent knowledge system for domain-specific intelligence.
    Learns from every registration attempt to improve future success.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize domain intelligence database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or Path(__file__).parent / "domain_intelligence.db"
        self.logger = logging.getLogger("domain_intelligence")
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Domain profiles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS domain_profiles (
                    domain TEXT PRIMARY KEY,
                    framework TEXT,
                    verification_type TEXT,
                    success_rate REAL DEFAULT 0.0,
                    total_attempts INTEGER DEFAULT 0,
                    successful_attempts INTEGER DEFAULT 0,
                    failed_attempts INTEGER DEFAULT 0,
                    known_fields TEXT,
                    known_selectors TEXT,
                    failed_selectors TEXT,
                    otp_average_seconds INTEGER,
                    anti_bot_mechanisms TEXT,
                    complexity_score REAL DEFAULT 0.5,
                    last_success TEXT,
                    last_failure TEXT,
                    last_updated TEXT,
                    metadata TEXT
                )
            """)
            
            # Registration attempts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registration_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    execution_time REAL,
                    total_cost REAL,
                    verification_method TEXT,
                    fields_detected TEXT,
                    selectors_used TEXT,
                    error_type TEXT,
                    error_message TEXT,
                    models_used TEXT,
                    timestamp TEXT,
                    metadata TEXT,
                    FOREIGN KEY (domain) REFERENCES domain_profiles(domain)
                )
            """)
            
            # Selector performance table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS selector_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    field_type TEXT NOT NULL,
                    selector TEXT NOT NULL,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    last_used TEXT,
                    UNIQUE(domain, field_type, selector)
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_attempts_domain 
                ON registration_attempts(domain)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_attempts_success 
                ON registration_attempts(success)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_selector_perf_domain 
                ON selector_performance(domain, field_type)
            """)
    
    # ========================================================================
    # DOMAIN PROFILE OPERATIONS
    # ========================================================================
    
    def get_profile(self, domain: str) -> Optional[DomainProfile]:
        """
        Get profile for a domain.
        
        Args:
            domain: Domain name
        
        Returns:
            DomainProfile or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM domain_profiles WHERE domain = ?",
                (domain,)
            )
            row = cursor.fetchone()
            
            if row:
                return DomainProfile.from_dict(dict(row))
            return None
    
    def create_profile(self, profile: DomainProfile) -> bool:
        """
        Create new domain profile.
        
        Args:
            profile: DomainProfile to create
        
        Returns:
            True if created successfully
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                data = profile.to_dict()
                
                cursor.execute("""
                    INSERT INTO domain_profiles 
                    (domain, framework, verification_type, success_rate, 
                     total_attempts, successful_attempts, failed_attempts,
                     known_fields, known_selectors, failed_selectors,
                     otp_average_seconds, anti_bot_mechanisms, complexity_score,
                     last_success, last_failure, last_updated, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data["domain"], data["framework"], data["verification_type"],
                    data["success_rate"], data["total_attempts"],
                    data["successful_attempts"], data["failed_attempts"],
                    data["known_fields"], data["known_selectors"],
                    data["failed_selectors"], data["otp_average_seconds"],
                    data["anti_bot_mechanisms"], data["complexity_score"],
                    data["last_success"], data["last_failure"],
                    data["last_updated"], data["metadata"]
                ))
                
                self.logger.info(f"Created profile for domain: {profile.domain}")
                return True
        except Exception as e:
            self.logger.error(f"Error creating profile: {e}")
            return False
    
    def update_profile(self, profile: DomainProfile) -> bool:
        """
        Update existing domain profile.
        
        Args:
            profile: DomainProfile to update
        
        Returns:
            True if updated successfully
        """
        try:
            profile.last_updated = datetime.utcnow().isoformat()
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                data = profile.to_dict()
                
                cursor.execute("""
                    UPDATE domain_profiles SET
                        framework = ?, verification_type = ?, success_rate = ?,
                        total_attempts = ?, successful_attempts = ?, failed_attempts = ?,
                        known_fields = ?, known_selectors = ?, failed_selectors = ?,
                        otp_average_seconds = ?, anti_bot_mechanisms = ?,
                        complexity_score = ?, last_success = ?, last_failure = ?,
                        last_updated = ?, metadata = ?
                    WHERE domain = ?
                """, (
                    data["framework"], data["verification_type"], data["success_rate"],
                    data["total_attempts"], data["successful_attempts"],
                    data["failed_attempts"], data["known_fields"],
                    data["known_selectors"], data["failed_selectors"],
                    data["otp_average_seconds"], data["anti_bot_mechanisms"],
                    data["complexity_score"], data["last_success"],
                    data["last_failure"], data["last_updated"],
                    data["metadata"], data["domain"]
                ))
                
                self.logger.info(f"Updated profile for domain: {profile.domain}")
                return True
        except Exception as e:
            self.logger.error(f"Error updating profile: {e}")
            return False
    
    def get_or_create_profile(self, domain: str) -> DomainProfile:
        """
        Get existing profile or create new one.
        
        Args:
            domain: Domain name
        
        Returns:
            DomainProfile
        """
        profile = self.get_profile(domain)
        if profile is None:
            profile = DomainProfile(domain=domain)
            self.create_profile(profile)
        return profile
    
    # ========================================================================
    # REGISTRATION ATTEMPT OPERATIONS
    # ========================================================================
    
    def record_attempt(self, attempt: RegistrationAttempt) -> bool:
        """
        Record a registration attempt.
        
        Args:
            attempt: RegistrationAttempt to record
        
        Returns:
            True if recorded successfully
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO registration_attempts
                    (domain, workflow_id, success, execution_time, total_cost,
                     verification_method, fields_detected, selectors_used,
                     error_type, error_message, models_used, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    attempt.domain, attempt.workflow_id, attempt.success,
                    attempt.execution_time, attempt.total_cost,
                    attempt.verification_method,
                    json.dumps(attempt.fields_detected),
                    json.dumps(attempt.selectors_used),
                    attempt.error_type, attempt.error_message,
                    json.dumps(attempt.models_used),
                    attempt.timestamp, json.dumps(attempt.metadata)
                ))
                
                # Update domain profile
                self._update_profile_from_attempt(attempt)
                
                # Update selector performance
                if attempt.success and attempt.selectors_used:
                    self._update_selector_performance(
                        attempt.domain,
                        attempt.selectors_used,
                        success=True
                    )
                
                self.logger.info(
                    f"Recorded attempt for {attempt.domain}: "
                    f"success={attempt.success}"
                )
                return True
        except Exception as e:
            self.logger.error(f"Error recording attempt: {e}")
            return False
    
    def _update_profile_from_attempt(self, attempt: RegistrationAttempt):
        """Update domain profile based on attempt."""
        profile = self.get_or_create_profile(attempt.domain)
        
        # Update attempt counts
        profile.total_attempts += 1
        if attempt.success:
            profile.successful_attempts += 1
            profile.last_success = attempt.timestamp
        else:
            profile.failed_attempts += 1
            profile.last_failure = attempt.timestamp
        
        # Update success rate
        profile.success_rate = (
            profile.successful_attempts / profile.total_attempts
            if profile.total_attempts > 0
            else 0.0
        )
        
        # Update known selectors on success
        if attempt.success and attempt.selectors_used:
            for field_type, selector in attempt.selectors_used.items():
                if field_type not in profile.known_selectors:
                    profile.known_selectors[field_type] = []
                if selector not in profile.known_selectors[field_type]:
                    profile.known_selectors[field_type].append(selector)
        
        # Update verification method
        if attempt.verification_method:
            profile.verification_type = attempt.verification_method
        
        self.update_profile(profile)
    
    def _update_selector_performance(
        self,
        domain: str,
        selectors: Dict[str, str],
        success: bool
    ):
        """Update selector performance tracking."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            for field_type, selector in selectors.items():
                cursor.execute("""
                    INSERT INTO selector_performance
                    (domain, field_type, selector, success_count, failure_count, last_used)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(domain, field_type, selector) DO UPDATE SET
                        success_count = success_count + ?,
                        failure_count = failure_count + ?,
                        last_used = ?
                """, (
                    domain, field_type, selector,
                    1 if success else 0,
                    0 if success else 1,
                    datetime.utcnow().isoformat(),
                    1 if success else 0,
                    0 if success else 1,
                    datetime.utcnow().isoformat()
                ))
    
    def get_best_selectors(
        self,
        domain: str,
        field_type: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get best performing selectors for a field type.
        
        Args:
            domain: Domain name
            field_type: Field type (e.g., "email", "password")
            limit: Maximum number of selectors to return
        
        Returns:
            List of selector dictionaries with performance metrics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT selector, success_count, failure_count,
                       CAST(success_count AS REAL) / 
                       NULLIF(success_count + failure_count, 0) as success_rate
                FROM selector_performance
                WHERE domain = ? AND field_type = ?
                ORDER BY success_rate DESC, success_count DESC
                LIMIT ?
            """, (domain, field_type, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # QUERY OPERATIONS
    # ========================================================================
    
    def get_success_rate(self, domain: str) -> float:
        """Get success rate for a domain."""
        profile = self.get_profile(domain)
        return profile.success_rate if profile else 0.0
    
    def get_known_selectors(self, domain: str) -> Dict[str, List[str]]:
        """Get known working selectors for a domain."""
        profile = self.get_profile(domain)
        return profile.known_selectors if profile else {}
    
    def get_recent_attempts(
        self,
        domain: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get recent registration attempts.
        
        Args:
            domain: Optional domain filter
            limit: Maximum number of attempts to return
        
        Returns:
            List of attempt dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if domain:
                cursor.execute("""
                    SELECT * FROM registration_attempts
                    WHERE domain = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (domain, limit))
            else:
                cursor.execute("""
                    SELECT * FROM registration_attempts
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_domains,
                    AVG(success_rate) as avg_success_rate,
                    SUM(total_attempts) as total_attempts,
                    SUM(successful_attempts) as total_successes
                FROM domain_profiles
            """)
            stats = dict(cursor.fetchone())
            
            cursor.execute("""
                SELECT COUNT(*) as recent_attempts
                FROM registration_attempts
                WHERE timestamp > datetime('now', '-7 days')
            """)
            stats.update(dict(cursor.fetchone()))
            
            return stats


# ============================================================================
# CLI FOR TESTING
# ============================================================================

if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    
    console.print("\n[bold cyan]Domain Intelligence Database - Test[/bold cyan]\n")
    
    # Initialize database
    db = DomainIntelligence()
    
    # Create test profile
    profile = DomainProfile(
        domain="example.com",
        framework="react",
        verification_type="otp",
        known_selectors={
            "email": ["input[name='email']", "input[type='email']"],
            "password": ["input[type='password']"]
        }
    )
    
    db.create_profile(profile)
    console.print("[green]✓[/green] Created test profile")
    
    # Record test attempt
    attempt = RegistrationAttempt(
        domain="example.com",
        workflow_id="test-123",
        success=True,
        execution_time=45.2,
        total_cost=0.0023,
        verification_method="otp",
        selectors_used={
            "email": "input[name='email']",
            "password": "input[type='password']"
        }
    )
    
    db.record_attempt(attempt)
    console.print("[green]✓[/green] Recorded test attempt")
    
    # Display statistics
    stats = db.get_statistics()
    console.print(f"\n[cyan]Statistics:[/cyan]")
    for key, value in stats.items():
        console.print(f"  {key}: {value}")
    
    # Display profile
    updated_profile = db.get_profile("example.com")
    if updated_profile:
        console.print(f"\n[cyan]Profile for example.com:[/cyan]")
        console.print(f"  Success Rate: {updated_profile.success_rate:.2%}")
        console.print(f"  Total Attempts: {updated_profile.total_attempts}")
        console.print(f"  Framework: {updated_profile.framework}")
        console.print(f"  Verification: {updated_profile.verification_type}")
