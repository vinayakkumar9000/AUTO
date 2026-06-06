# AI-First Architecture Redesign Plan

## Executive Summary

Transform the Auto Registration system from a rule-based automation with AI fallbacks into an AI-first autonomous platform with multi-agent orchestration.

**Current State**: Rule Engine → AI Fallback  
**Target State**: AI Planning → Agent Execution → Verification → Learning

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Coordinator Agent                         │
│  (Workflow Orchestration, Model Selection, Budget Control)   │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼────────┐   ┌────────▼────────┐
│ Site Analyzer  │   │ Registration    │
│ Agent          │   │ Planner Agent   │
└───────┬────────┘   └────────┬────────┘
        │                     │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │                     │
┌───────▼────────┐   ┌────────▼────────┐   ┌────────────────┐
│ Form           │   │ Email           │   │ OTP Agent      │
│ Intelligence   │   │ Intelligence    │   │                │
└───────┬────────┘   └────────┬────────┘   └────────┬───────┘
        │                     │                     │
        └──────────┬──────────┴─────────────────────┘
                   │
        ┌──────────▼──────────┐
        │                     │
┌───────▼────────┐   ┌────────▼────────┐   ┌────────────────┐
│ Verification   │   │ Recovery        │   │ Learning       │
│ Agent          │   │ Agent           │   │ Agent          │
└────────────────┘   └─────────────────┘   └────────────────┘
```

---

## Phase 1: Foundation Layer (Week 1)

### 1.1 Model Routing Layer

**File**: `ai_model_router.py`

```python
class ModelTier(Enum):
    FAST = "fast"           # GPT-5.4 nano, DeepSeek-V4-Flash
    BALANCED = "balanced"   # GPT-5.4 mini (default)
    ADVANCED = "advanced"   # DeepSeek-V4-Pro, Kimi-K2.5
    PREMIUM = "premium"     # GPT-5.2, GLM-5

class ModelRouter:
    def select_model(self, task_type: str, confidence: float, budget: float) -> str
    def escalate_model(self, current_model: str, reason: str) -> str
    def get_cost_estimate(self, model: str, tokens: int) -> float
```

**Tasks**:
- [ ] Implement tier-based model selection
- [ ] Add cost tracking per request
- [ ] Implement automatic escalation logic
- [ ] Add budget enforcement

### 1.2 Agent Base Class

**File**: `agents/base_agent.py`

```python
class BaseAgent(ABC):
    def __init__(self, model_router: ModelRouter, db: Database)
    
    @abstractmethod
    async def execute(self, context: Dict) -> AgentResult
    
    def get_confidence(self) -> float
    def should_escalate(self) -> bool
    def log_execution(self, result: AgentResult)
```

**Tasks**:
- [ ] Create abstract base agent
- [ ] Implement confidence scoring
- [ ] Add execution logging
- [ ] Implement retry logic

### 1.3 Domain Intelligence Database

**File**: `domain_intelligence.py`

```python
class DomainProfile:
    domain: str
    framework: str
    verification_type: str
    success_rate: float
    known_fields: Dict[str, str]
    known_selectors: Dict[str, str]
    otp_average_seconds: int
    last_updated: datetime
    
class DomainIntelligence:
    def get_profile(self, domain: str) -> Optional[DomainProfile]
    def update_profile(self, domain: str, result: RegistrationResult)
    def get_success_rate(self, domain: str) -> float
    def get_known_selectors(self, domain: str) -> Dict[str, str]
```

**Storage**: SQLite database (`domain_intelligence.db`)

**Tasks**:
- [ ] Design database schema
- [ ] Implement CRUD operations
- [ ] Add profile caching
- [ ] Implement auto-update on success/failure

---

## Phase 2: Core Agents (Week 2-3)

### 2.1 Coordinator Agent

**File**: `agents/coordinator_agent.py`

**Responsibilities**:
- Entry point for all registrations
- Orchestrate agent execution
- Select models dynamically
- Control budget
- Aggregate results

**Input**:
```python
{
    "url": "https://example.com/signup",
    "budget": 0.10,  # $0.10 max
    "timeout": 300   # 5 minutes
}
```

**Output**:
```python
{
    "workflow_id": "uuid",
    "strategy": "magic_link",
    "selected_models": {
        "site_analyzer": "gpt-5.4-mini",
        "planner": "gpt-5.4-mini",
        "form_intelligence": "deepseek-v4-flash"
    },
    "steps": [...],
    "total_cost": 0.0234,
    "success": true
}
```

**Tasks**:
- [ ] Implement workflow orchestration
- [ ] Add model selection logic
- [ ] Implement budget tracking
- [ ] Add step-by-step execution
- [ ] Implement result aggregation

### 2.2 Site Analyzer Agent

**File**: `agents/site_analyzer_agent.py`

**Responsibilities**:
- Analyze target website structure
- Detect framework (React/Vue/Angular/Next.js)
- Identify anti-bot mechanisms
- Detect verification requirements
- Assess signup complexity

**Output**:
```python
{
    "domain": "example.com",
    "framework": "react",
    "anti_bot": ["cloudflare", "turnstile"],
    "verification": "otp",
    "complexity": "medium",
    "estimated_steps": 5,
    "confidence": 0.92
}
```

**Tasks**:
- [ ] Implement framework detection
- [ ] Add anti-bot detection
- [ ] Implement verification type detection
- [ ] Add complexity scoring
- [ ] Cache results in domain intelligence

### 2.3 Registration Planner Agent

**File**: `agents/planner_agent.py`

**Responsibilities**:
- Generate dynamic execution plans
- No hardcoded flows
- Adapt to site analysis
- Consider domain intelligence

**Output**:
```python
{
    "strategy": "magic_link",
    "steps": [
        {"action": "navigate", "target": "signup_page"},
        {"action": "fill_field", "field": "email", "value": "generated"},
        {"action": "click_button", "selector": "submit"},
        {"action": "wait_email", "timeout": 60},
        {"action": "extract_link", "type": "magic"},
        {"action": "navigate", "target": "magic_link"},
        {"action": "verify_success"}
    ],
    "estimated_time": 90,
    "confidence": 0.88
}
```

**Tasks**:
- [ ] Implement dynamic plan generation
- [ ] Add strategy selection logic
- [ ] Implement step sequencing
- [ ] Add confidence scoring
- [ ] Integrate domain intelligence

### 2.4 Form Intelligence Agent

**File**: `agents/form_intelligence_agent.py`

**Responsibilities**:
- Understand form fields semantically
- Map fields to identity data
- Handle dynamic forms
- Reconstruct form structure

**Output**:
```python
{
    "fields": [
        {
            "selector": "input[name='email']",
            "type": "email",
            "required": true,
            "confidence": 0.98
        },
        {
            "selector": "input[id='pwd']",
            "type": "password",
            "required": true,
            "confidence": 0.95
        }
    ],
    "form_type": "registration",
    "multi_step": true,
    "confidence": 0.91
}
```

**Tasks**:
- [ ] Implement semantic field analysis
- [ ] Add field mapping logic
- [ ] Implement dynamic form handling
- [ ] Add confidence scoring
- [ ] Cache successful mappings

### 2.5 Email Intelligence Agent

**File**: `agents/email_intelligence_agent.py`

**Responsibilities**:
- Monitor inbox intelligently
- Classify emails
- Extract OTP/magic links
- Handle multiple verification types

**Output**:
```python
{
    "email_type": "verification",
    "verification_method": "otp",
    "otp": "123456",
    "magic_link": null,
    "confidence": 0.96,
    "received_at": "2026-06-06T10:30:00Z"
}
```

**Tasks**:
- [ ] Implement email classification
- [ ] Add OTP extraction
- [ ] Add magic link extraction
- [ ] Implement smart polling
- [ ] Add confidence scoring

### 2.6 OTP Agent

**File**: `agents/otp_agent.py`

**Responsibilities**:
- Extract OTP from various formats
- Validate OTP format
- Handle retries
- Track expiration

**Output**:
```python
{
    "otp": "123456",
    "format": "6-digit",
    "expires_in": 180,
    "confidence": 0.99
}
```

**Tasks**:
- [ ] Implement multi-format OTP extraction
- [ ] Add validation logic
- [ ] Implement retry handling
- [ ] Add expiration tracking

### 2.7 Verification Agent

**File**: `agents/verification_agent.py`

**Responsibilities**:
- Verify registration success
- Check authenticated state
- Validate account creation
- Return confidence score

**Checks**:
- Dashboard access
- Session cookies
- Account profile page
- Logout button presence
- Welcome message

**Output**:
```python
{
    "success": true,
    "verification_method": "dashboard_access",
    "confidence": 0.94,
    "evidence": [
        "dashboard_url_changed",
        "session_cookie_present",
        "logout_button_found"
    ]
}
```

**Tasks**:
- [ ] Implement multi-method verification
- [ ] Add confidence scoring
- [ ] Implement evidence collection
- [ ] Add false positive detection

### 2.8 Recovery Agent

**File**: `agents/recovery_agent.py`

**Responsibilities**:
- Classify failures
- Generate alternative plans
- Implement retry strategies
- Escalate when needed

**Failure Types**:
- CAPTCHA detected
- Rate limit hit
- Invalid selector
- Missing field
- Email rejected
- OTP expired
- Timeout
- Anti-bot trigger

**Output**:
```python
{
    "failure_type": "otp_timeout",
    "alternative_plan": {
        "action": "request_new_otp",
        "steps": [...]
    },
    "escalate_model": true,
    "confidence": 0.82
}
```

**Tasks**:
- [ ] Implement failure classification
- [ ] Add alternative plan generation
- [ ] Implement retry strategies
- [ ] Add escalation logic

### 2.9 Learning Agent

**File**: `agents/learning_agent.py`

**Responsibilities**:
- Store successful patterns
- Update domain intelligence
- Track success rates
- Improve over time

**Storage**:
```python
{
    "domain": "example.com",
    "successful_selectors": {
        "email": ["input[name='email']", "input[id='user_email']"],
        "password": ["input[type='password']"]
    },
    "failed_selectors": {
        "email": ["input[name='mail']"]
    },
    "success_rate": 0.93,
    "total_attempts": 150,
    "last_success": "2026-06-06T10:30:00Z"
}
```

**Tasks**:
- [ ] Implement pattern storage
- [ ] Add success rate tracking
- [ ] Implement selector ranking
- [ ] Add automatic profile updates

---

## Phase 3: Integration Layer (Week 4)

### 3.1 Backward Compatibility Wrapper

**File**: `legacy_adapter.py`

Maintain existing API while routing through new agent system.

```python
async def run_automation(url: str, api_key: str) -> None:
    # Route through Coordinator Agent
    coordinator = CoordinatorAgent(...)
    result = await coordinator.execute({
        "url": url,
        "budget": 0.10
    })
    # Return in legacy format
```

**Tasks**:
- [ ] Create adapter layer
- [ ] Maintain existing function signatures
- [ ] Route through agent system
- [ ] Preserve all existing features

### 3.2 Cost Optimizer

**File**: `cost_optimizer.py`

```python
class CostOptimizer:
    def optimize_model_selection(self, task: str, history: List) -> str
    def cache_result(self, key: str, result: Any)
    def get_cached_result(self, key: str) -> Optional[Any]
    def track_spending(self, model: str, tokens: int, cost: float)
    def get_budget_status(self) -> Dict
```

**Tasks**:
- [ ] Implement result caching
- [ ] Add spending tracking
- [ ] Implement budget alerts
- [ ] Add cost optimization logic

---

## Phase 4: Testing & Validation (Week 5)

### 4.1 Agent Unit Tests

**File**: `tests/test_agents.py`

Test each agent independently:
- [ ] Coordinator Agent tests
- [ ] Site Analyzer Agent tests
- [ ] Planner Agent tests
- [ ] Form Intelligence Agent tests
- [ ] Email Intelligence Agent tests
- [ ] OTP Agent tests
- [ ] Verification Agent tests
- [ ] Recovery Agent tests
- [ ] Learning Agent tests

### 4.2 Integration Tests

**File**: `tests/test_integration.py`

Test complete workflows:
- [ ] Simple email-only registration
- [ ] OTP verification flow
- [ ] Magic link flow
- [ ] Multi-step registration
- [ ] Recovery scenarios
- [ ] Learning system updates

### 4.3 Real-World Testing

Test on actual sites:
- [ ] IBM registration
- [ ] GitHub
- [ ] GitLab
- [ ] Discord
- [ ] Slack
- [ ] Notion

Track:
- Success rate
- Cost per registration
- Time per registration
- Model usage distribution
- Learning improvements

---

## Phase 5: Production Deployment (Week 6)

### 5.1 Migration Strategy

1. **Parallel Running** (Week 6.1-6.3)
   - Run both old and new systems
   - Compare results
   - Validate accuracy

2. **Gradual Rollout** (Week 6.4-6.5)
   - 10% traffic to new system
   - 50% traffic to new system
   - 100% traffic to new system

3. **Legacy Deprecation** (Week 6.6-6.7)
   - Mark old system as deprecated
   - Maintain for 1 month
   - Remove after validation

### 5.2 Monitoring & Observability

**File**: `monitoring.py`

Track:
- Agent execution times
- Model usage distribution
- Cost per registration
- Success rates
- Failure patterns
- Learning improvements

**Dashboard Metrics**:
- Total registrations
- Success rate (%)
- Average cost ($)
- Average time (s)
- Model distribution
- Top failures
- Learning curve

---

## Success Metrics

### Quantitative Targets

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Success Rate | 85% | 95%+ | +10% |
| Avg Cost | $0.013 | $0.008 | -38% |
| Avg Time | 45s | 30s | -33% |
| Recovery Rate | 20% | 60% | +40% |

### Qualitative Targets

- ✅ AI-first orchestration (not fallback)
- ✅ Learning from every run
- ✅ Autonomous recovery
- ✅ Independent verification
- ✅ Cost optimization
- ✅ Backward compatibility
- ✅ Production-ready (no TODOs)

### Architecture Quality

Target: **9.5/10**

Criteria:
- Clean separation of concerns
- Testable components
- Extensible design
- Maintainable codebase
- Well-documented
- Production-ready

---

## File Structure

```
auto registration/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py
│   ├── coordinator_agent.py
│   ├── site_analyzer_agent.py
│   ├── planner_agent.py
│   ├── form_intelligence_agent.py
│   ├── email_intelligence_agent.py
│   ├── otp_agent.py
│   ├── verification_agent.py
│   ├── recovery_agent.py
│   └── learning_agent.py
├── ai_model_router.py
├── domain_intelligence.py
├── cost_optimizer.py
├── legacy_adapter.py
├── monitoring.py
├── domain_intelligence.db
├── auto_registration_v5.py  # New entry point
├── auto_registration_v4.py  # Legacy (maintained)
└── tests/
    ├── test_agents.py
    ├── test_integration.py
    └── test_real_world.py
```

---

## Risk Mitigation

### Technical Risks

1. **Complexity Explosion**
   - Mitigation: Incremental development, thorough testing
   
2. **Performance Degradation**
   - Mitigation: Caching, model optimization, parallel execution
   
3. **Cost Overruns**
   - Mitigation: Budget enforcement, cost optimizer, tier system

4. **Backward Compatibility**
   - Mitigation: Adapter layer, parallel running, gradual rollout

### Business Risks

1. **Development Time**
   - Mitigation: 6-week phased approach, clear milestones
   
2. **User Disruption**
   - Mitigation: Maintain v4, gradual migration, rollback plan

---

## Next Steps

1. **Review & Approve** this architecture plan
2. **Start Phase 1**: Foundation layer implementation
3. **Weekly Reviews**: Track progress against milestones
4. **Continuous Testing**: Validate each component
5. **Production Deployment**: Gradual rollout with monitoring

---

## Conclusion

This architecture transforms the Auto Registration system from a rule-based automation tool into an AI-first autonomous platform that:

- **Learns** from every registration
- **Adapts** to new sites automatically
- **Recovers** from failures autonomously
- **Optimizes** costs intelligently
- **Verifies** success independently
- **Improves** over time

**Estimated Timeline**: 6 weeks  
**Estimated Effort**: 240 hours  
**Expected ROI**: 3-6 months

**Status**: Ready for implementation approval
