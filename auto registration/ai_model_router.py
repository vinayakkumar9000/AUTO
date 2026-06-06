#!/usr/bin/env python3
"""
AI Model Router
Intelligent model selection with tier-based routing and cost optimization
Author: vinayakkumar9000
"""

from enum import Enum
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

# ============================================================================
# MODEL TIERS AND CONFIGURATION
# ============================================================================

class ModelTier(Enum):
    """Model performance tiers for intelligent routing."""
    FAST = "fast"           # Quick, cheap tasks
    BALANCED = "balanced"   # Default tier
    ADVANCED = "advanced"   # Complex reasoning
    PREMIUM = "premium"     # Highest capability

@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    name: str
    tier: ModelTier
    input_price: float      # Price per 1M tokens
    output_price: float     # Price per 1M tokens
    max_tokens: int
    recommended_for: list
    description: str

# Model catalog with pricing and capabilities
MODEL_CATALOG = {
    # FAST TIER - Quick operations
    "gpt-5.4-nano": ModelConfig(
        name="GPT-5.4 Nano",
        tier=ModelTier.FAST,
        input_price=0.05,
        output_price=0.20,
        max_tokens=4096,
        recommended_for=["field_classification", "selector_validation", "simple_reasoning"],
        description="Ultra-fast for simple tasks"
    ),
    "gpt-5-nano": ModelConfig(
        name="GPT-5 Nano",
        tier=ModelTier.FAST,
        input_price=0.08,
        output_price=0.25,
        max_tokens=4096,
        recommended_for=["field_classification", "button_detection"],
        description="Fast and efficient"
    ),
    "deepseek-v4-flash": ModelConfig(
        name="DeepSeek-V4-Flash",
        tier=ModelTier.FAST,
        input_price=0.28,
        output_price=0.56,
        max_tokens=8192,
        recommended_for=["field_classification", "form_analysis"],
        description="Fast with good accuracy"
    ),
    
    # BALANCED TIER - Default choice
    "gpt-5.4-mini": ModelConfig(
        name="GPT-5.4 Mini",
        tier=ModelTier.BALANCED,
        input_price=0.15,
        output_price=0.60,
        max_tokens=16384,
        recommended_for=["form_analysis", "registration_planning", "error_diagnosis", "verification"],
        description="Best balance of speed, cost, and accuracy (DEFAULT)"
    ),
    "deepseek-v3.2": ModelConfig(
        name="DeepSeek-V3.2",
        tier=ModelTier.BALANCED,
        input_price=0.29,
        output_price=0.44,
        max_tokens=32768,
        recommended_for=["form_analysis", "planning"],
        description="Balanced performance"
    ),
    "minimax-m2.7": ModelConfig(
        name="MiniMax-M2.7",
        tier=ModelTier.BALANCED,
        input_price=0.30,
        output_price=1.20,
        max_tokens=16384,
        recommended_for=["form_analysis", "otp_extraction"],
        description="Good for structured tasks"
    ),
    "minimax-m3": ModelConfig(
        name="MiniMax-M3",
        tier=ModelTier.BALANCED,
        input_price=0.30,
        output_price=1.20,
        max_tokens=16384,
        recommended_for=["form_analysis", "planning"],
        description="Alternative balanced option"
    ),
    
    # ADVANCED TIER - Complex tasks
    "deepseek-v4-pro": ModelConfig(
        name="DeepSeek-V4-Pro",
        tier=ModelTier.ADVANCED,
        input_price=0.87,
        output_price=1.74,
        max_tokens=32768,
        recommended_for=["complex_workflows", "recovery_generation", "unknown_sites"],
        description="Advanced reasoning capabilities"
    ),
    "kimi-k2.5": ModelConfig(
        name="Kimi-K2.5",
        tier=ModelTier.ADVANCED,
        input_price=0.59,
        output_price=3.00,
        max_tokens=32768,
        recommended_for=["complex_reasoning", "multi_step_recovery"],
        description="High quality for difficult tasks"
    ),
    "glm-5.1": ModelConfig(
        name="GLM-5.1",
        tier=ModelTier.ADVANCED,
        input_price=1.40,
        output_price=4.40,
        max_tokens=32768,
        recommended_for=["complex_workflows", "advanced_planning"],
        description="Advanced Chinese model"
    ),
    
    # PREMIUM TIER - Highest capability
    "gpt-5.2": ModelConfig(
        name="GPT-5.2",
        tier=ModelTier.PREMIUM,
        input_price=2.50,
        output_price=10.00,
        max_tokens=128000,
        recommended_for=["extremely_complex_sites", "multi_step_recovery", "planner_escalation"],
        description="Highest capability (use sparingly)"
    ),
    "glm-5": ModelConfig(
        name="GLM-5",
        tier=ModelTier.PREMIUM,
        input_price=2.00,
        output_price=8.00,
        max_tokens=128000,
        recommended_for=["complex_chinese_sites", "advanced_recovery"],
        description="Premium Chinese model"
    ),
    "gemini-3.1-pro": ModelConfig(
        name="Gemini-3.1-Pro",
        tier=ModelTier.PREMIUM,
        input_price=3.50,
        output_price=10.50,
        max_tokens=1000000,
        recommended_for=["extremely_complex_sites", "long_context"],
        description="Highest capability with massive context"
    ),
}

# Default model for each tier
DEFAULT_MODELS = {
    ModelTier.FAST: "deepseek-v4-flash",
    ModelTier.BALANCED: "gpt-5.4-mini",
    ModelTier.ADVANCED: "deepseek-v4-pro",
    ModelTier.PREMIUM: "gpt-5.2"
}

# Task to tier mapping
TASK_TIER_MAP = {
    "field_classification": ModelTier.FAST,
    "selector_validation": ModelTier.FAST,
    "button_detection": ModelTier.FAST,
    "form_analysis": ModelTier.BALANCED,
    "registration_planning": ModelTier.BALANCED,
    "error_diagnosis": ModelTier.BALANCED,
    "verification": ModelTier.BALANCED,
    "otp_extraction": ModelTier.BALANCED,
    "magic_link_detection": ModelTier.BALANCED,
    "complex_workflows": ModelTier.ADVANCED,
    "recovery_generation": ModelTier.ADVANCED,
    "unknown_sites": ModelTier.ADVANCED,
    "multi_step_recovery": ModelTier.ADVANCED,
    "extremely_complex_sites": ModelTier.PREMIUM,
    "planner_escalation": ModelTier.PREMIUM,
}

# ============================================================================
# MODEL ROUTER
# ============================================================================

class ModelRouter:
    """
    Intelligent model router with tier-based selection and cost optimization.
    """
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path(__file__).parent / "config.json"
        self.total_cost = 0.0
        self.request_count = 0
        self.model_usage = {}
        self.load_preferences()
    
    def load_preferences(self):
        """Load user model preferences from config."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.preferred_models = config.get("preferred_models", {})
            else:
                self.preferred_models = {}
        except Exception:
            self.preferred_models = {}
    

    @property
    def models(self):
        """Get list of all available models."""
        all_models = []
        all_models.extend(self.tier_1_models)
        all_models.extend(self.tier_2_models)
        all_models.extend(self.tier_3_models)
        all_models.extend(self.tier_4_models)
        return all_models
    
    @property
    def tier_1_models(self):
        """Get tier 1 (FAST) models."""
        return [m for m, c in MODEL_CATALOG.items() if c.tier == ModelTier.FAST]
    
    @property
    def tier_2_models(self):
        """Get tier 2 (BALANCED) models."""
        return [m for m, c in MODEL_CATALOG.items() if c.tier == ModelTier.BALANCED]
    
    @property
    def tier_3_models(self):
        """Get tier 3 (ADVANCED) models."""
        return [m for m, c in MODEL_CATALOG.items() if c.tier == ModelTier.ADVANCED]
    
    @property
    def tier_4_models(self):
        """Get tier 4 (PREMIUM) models."""
        return [m for m, c in MODEL_CATALOG.items() if c.tier == ModelTier.PREMIUM]

    def select_model(
        self,
        task_type: str,
        confidence: float = 1.0,
        budget_remaining: float = float('inf'),
        context_size: int = 1000
    ) -> str:
        """
        Select the most appropriate model for a task.
        
        Args:
            task_type: Type of task (e.g., "field_classification", "form_analysis")
            confidence: Current confidence level (0.0-1.0)
            budget_remaining: Remaining budget in dollars
            context_size: Estimated context size in tokens
        
        Returns:
            Model identifier string
        """
        # Get base tier for task
        base_tier = TASK_TIER_MAP.get(task_type, ModelTier.BALANCED)
        
        # Escalate tier if confidence is low
        if confidence < 0.5:
            base_tier = self._escalate_tier(base_tier, 2)
        elif confidence < 0.7:
            base_tier = self._escalate_tier(base_tier, 1)
        
        # Check if user has preferred model for this tier
        tier_name = base_tier.value
        if tier_name in self.preferred_models:
            preferred = self.preferred_models[tier_name]
            if preferred in MODEL_CATALOG:
                model_config = MODEL_CATALOG[preferred]
                # Verify budget and context size
                if self._check_budget(model_config, context_size, budget_remaining):
                    return preferred
        
        # Get default model for tier
        default_model = DEFAULT_MODELS[base_tier]
        model_config = MODEL_CATALOG[default_model]
        
        # Check budget constraint
        if not self._check_budget(model_config, context_size, budget_remaining):
            # Try to downgrade to cheaper tier
            cheaper_tier = self._downgrade_tier(base_tier)
            if cheaper_tier != base_tier:
                default_model = DEFAULT_MODELS[cheaper_tier]
        
        return default_model
    
    def escalate_model(self, current_model: str, reason: str) -> str:
        """
        Escalate to a more capable model.
        
        Args:
            current_model: Current model identifier
            reason: Reason for escalation
        
        Returns:
            New model identifier
        """
        if current_model not in MODEL_CATALOG:
            return DEFAULT_MODELS[ModelTier.BALANCED]
        
        current_config = MODEL_CATALOG[current_model]
        current_tier = current_config.tier
        
        # Escalate one tier
        new_tier = self._escalate_tier(current_tier, 1)
        
        if new_tier == current_tier:
            # Already at highest tier, try different model in same tier
            return self._get_alternative_model(current_model)
        
        return DEFAULT_MODELS[new_tier]
    
    def get_cost_estimate(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for a model call.
        
        Args:
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        
        Returns:
            Estimated cost in dollars
        """
        if model not in MODEL_CATALOG:
            return 0.0
        
        config = MODEL_CATALOG[model]
        input_cost = (input_tokens / 1_000_000) * config.input_price
        output_cost = (output_tokens / 1_000_000) * config.output_price
        
        return input_cost + output_cost
    
    def track_usage(self, model: str, input_tokens: int, output_tokens: int):
        """Track model usage and costs."""
        cost = self.get_cost_estimate(model, input_tokens, output_tokens)
        self.total_cost += cost
        self.request_count += 1
        
        if model not in self.model_usage:
            self.model_usage[model] = {
                "count": 0,
                "total_cost": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0
            }
        
        self.model_usage[model]["count"] += 1
        self.model_usage[model]["total_cost"] += cost
        self.model_usage[model]["total_input_tokens"] += input_tokens
        self.model_usage[model]["total_output_tokens"] += output_tokens
    
    def get_usage_stats(self) -> Dict:
        """Get usage statistics."""
        return {
            "total_cost": self.total_cost,
            "request_count": self.request_count,
            "model_usage": self.model_usage,
            "average_cost_per_request": self.total_cost / max(1, self.request_count)
        }
    
    def reset_stats(self):
        """Reset usage statistics."""
        self.total_cost = 0.0
        self.request_count = 0
        self.model_usage = {}
    
    # Private helper methods
    
    def _escalate_tier(self, tier: ModelTier, levels: int = 1) -> ModelTier:
        """Escalate tier by specified levels."""
        tier_order = [ModelTier.FAST, ModelTier.BALANCED, ModelTier.ADVANCED, ModelTier.PREMIUM]
        current_index = tier_order.index(tier)
        new_index = min(current_index + levels, len(tier_order) - 1)
        return tier_order[new_index]
    
    def _downgrade_tier(self, tier: ModelTier) -> ModelTier:
        """Downgrade tier by one level."""
        tier_order = [ModelTier.FAST, ModelTier.BALANCED, ModelTier.ADVANCED, ModelTier.PREMIUM]
        current_index = tier_order.index(tier)
        new_index = max(current_index - 1, 0)
        return tier_order[new_index]
    
    def _check_budget(self, model_config: ModelConfig, context_size: int, budget: float) -> bool:
        """Check if model fits within budget."""
        estimated_cost = self.get_cost_estimate(
            model_config.name.lower().replace(" ", "-").replace(".", ""),
            context_size,
            context_size // 2  # Assume output is half of input
        )
        return estimated_cost <= budget
    
    def _get_alternative_model(self, current_model: str) -> str:
        """Get alternative model in same tier."""
        if current_model not in MODEL_CATALOG:
            return DEFAULT_MODELS[ModelTier.BALANCED]
        
        current_tier = MODEL_CATALOG[current_model].tier
        
        # Find other models in same tier
        alternatives = [
            model_id for model_id, config in MODEL_CATALOG.items()
            if config.tier == current_tier and model_id != current_model
        ]
        
        if alternatives:
            return alternatives[0]
        
        return current_model


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_model_info(model: str) -> Optional[ModelConfig]:
    """Get configuration for a specific model."""
    return MODEL_CATALOG.get(model)

def list_models_by_tier(tier: ModelTier) -> list:
    """List all models in a specific tier."""
    return [
        model_id for model_id, config in MODEL_CATALOG.items()
        if config.tier == tier
    ]

def get_cheapest_model(tier: ModelTier) -> str:
    """Get the cheapest model in a tier."""
    models = list_models_by_tier(tier)
    if not models:
        return DEFAULT_MODELS[ModelTier.BALANCED]
    
    cheapest = min(
        models,
        key=lambda m: MODEL_CATALOG[m].input_price + MODEL_CATALOG[m].output_price
    )
    return cheapest


# ============================================================================
# CLI FOR TESTING
# ============================================================================

if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    
    console.print("\n[bold cyan]AI Model Router - Configuration[/bold cyan]\n")
    
    # Display all models
    table = Table(title="Available Models")
    table.add_column("Model", style="cyan")
    table.add_column("Tier", style="yellow")
    table.add_column("Input Price", style="green")
    table.add_column("Output Price", style="green")
    table.add_column("Max Tokens", style="blue")
    table.add_column("Description", style="white")
    
    for model_id, config in MODEL_CATALOG.items():
        table.add_row(
            config.name,
            config.tier.value.upper(),
            f"${config.input_price}/M",
            f"${config.output_price}/M",
            str(config.max_tokens),
            config.description
        )
    
    console.print(table)
    
    # Test router
    console.print("\n[bold cyan]Testing Model Router[/bold cyan]\n")
    router = ModelRouter()
    
    test_cases = [
        ("field_classification", 0.95, "High confidence field classification"),
        ("field_classification", 0.60, "Low confidence field classification"),
        ("form_analysis", 0.85, "Standard form analysis"),
        ("recovery_generation", 0.70, "Recovery after failure"),
        ("extremely_complex_sites", 0.50, "Complex unknown site"),
    ]
    
    for task, confidence, description in test_cases:
        model = router.select_model(task, confidence)
        config = MODEL_CATALOG[model]
        console.print(f"[cyan]{description}[/cyan]")
        console.print(f"  Task: {task}, Confidence: {confidence}")
        console.print(f"  Selected: [green]{config.name}[/green] ({config.tier.value})")
        console.print()
