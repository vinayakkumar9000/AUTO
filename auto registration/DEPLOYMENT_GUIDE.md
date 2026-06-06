# Deployment Guide

**Multi-Agent Auto Registration System**  
**Version:** 1.0.0  
**Date:** 2026-06-06

---

## Quick Start

### 1. Install Dependencies

```bash
cd "D:\AUTO\auto registration"
pip install -r requirements.txt
pip install -r tests/requirements-test.txt
```

### 2. Deploy System

```bash
python deploy.py deploy
```

This will:
- Check dependencies
- Create required directories
- Configure the system (API key prompt)
- Initialize database
- Run tests (optional)

### 3. Verify Installation

```bash
python deploy.py status
```

---

## Manual Deployment

### Step 1: Install Dependencies

```bash
pip install playwright anthropic rich
playwright install chromium
```

### Step 2: Configure API Key

Create `config.json`:

```json
{
  "api_key": "your-bai-api-key-here",
  "default_model": "gpt-4o-mini",
  "budget_per_registration": 0.01,
  "timeout": 180,
  "max_retries": 3,
  "log_level": "INFO"
}
```

### Step 3: Initialize Database

```bash
python -c "from domain_intelligence import DomainIntelligence; DomainIntelligence()"
```

### Step 4: Run Tests

```bash
pytest tests/ -v
```

---

## Usage

### Basic Usage

```python
from integration_layer import create_integration_layer

# Create integration layer
integration = create_integration_layer()

# Execute registration
result = await integration.execute_registration(
    url="https://example.com/signup",
    budget=0.01,
    timeout=180
)

print(f"Success: {result['success']}")
print(f"Cost: ${result['cost']:.6f}")
```

### V4 Compatible Usage

```python
from integration_layer import create_v4_bridge

# Create V4 bridge
bridge = create_v4_bridge()

# Register account (V4 style)
result = await bridge.register_account(
    url="https://example.com/signup",
    email="test@example.com",
    password="SecurePass123!"
)
```

### With Callbacks

```python
def on_success(state):
    print(f"Registration successful: {state['id']}")

def on_failure(state):
    print(f"Registration failed: {state['id']}")

integration.register_callback("on_success", on_success)
integration.register_callback("on_failure", on_failure)

result = await integration.execute_registration(url="...")
```

---

## Configuration

### config.json Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| api_key | string | required | B.ai API key |
| default_model | string | "gpt-4o-mini" | Default AI model |
| budget_per_registration | float | 0.01 | Budget per registration ($) |
| timeout | int | 180 | Timeout in seconds |
| max_retries | int | 3 | Maximum retry attempts |
| log_level | string | "INFO" | Logging level |

### Environment Variables

```bash
export BAI_API_KEY="your-api-key"
export LOG_LEVEL="DEBUG"
```

---

## Monitoring

### Logs

Logs are stored in `.logs/` directory:
- `registration_YYYYMMDD.log` - Daily registration logs
- `errors_YYYYMMDD.log` - Error logs

### Screenshots

Screenshots are stored in `.screenshots/` directory:
- `YYYYMMDD_HHMMSS_01_initial.png` - Initial page
- `YYYYMMDD_HHMMSS_02_form_filled.png` - After form fill
- `YYYYMMDD_HHMMSS_03_success.png` - Success state

### Database

Domain intelligence is stored in `domain_intelligence.db`:
- Domain profiles
- Success rates
- Known selectors
- Performance metrics

---

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Cost per registration | $0.0008 | $0.0012 |
| Execution time | < 60s | 45-90s |
| Success rate | 95%+ | 85%+ |

---

## Troubleshooting

### Issue: API Key Error

**Solution:** Ensure API key is set in `config.json` or environment variable.

```bash
python deploy.py deploy  # Re-run deployment
```

### Issue: Database Locked

**Solution:** Close other processes using the database.

```bash
python deploy.py clean  # Clean and reinitialize
python deploy.py deploy
```

### Issue: Tests Failing

**Solution:** Install test dependencies.

```bash
pip install -r tests/requirements-test.txt
pytest tests/ -v
```

### Issue: Slow Performance

**Solution:** Check system resources and adjust timeout.

```json
{
  "timeout": 300,
  "budget_per_registration": 0.015
}
```

---

## Maintenance

### Update Dependencies

```bash
pip install --upgrade -r requirements.txt
```

### Clean Logs

```bash
python deploy.py clean
```

### Backup Database

```bash
cp domain_intelligence.db domain_intelligence.db.backup
```

### View Statistics

```python
from domain_intelligence import DomainIntelligence

db = DomainIntelligence()
stats = db.get_statistics()
print(stats)
```

---

## Production Checklist

- [ ] Install all dependencies
- [ ] Configure API key
- [ ] Initialize database
- [ ] Run test suite
- [ ] Set up monitoring
- [ ] Configure logging
- [ ] Set budget limits
- [ ] Test with real websites
- [ ] Monitor costs
- [ ] Review performance

---

## Support

For issues or questions:
1. Check logs in `.logs/` directory
2. Review error screenshots in `.screenshots/`
3. Run `python deploy.py status`
4. Check GitHub issues

---

## Architecture Overview

```
User Request
    ↓
Integration Layer (entry point)
    ↓
Cost Optimizer (budget check)
    ↓
Coordinator Agent (orchestration)
    ↓
9 Specialized Agents
    ↓
Performance Monitor (tracking)
    ↓
Learning Agent (improvement)
    ↓
Result
```

---

## Security

- API keys stored in `config.json` (gitignored)
- Database encrypted at rest (optional)
- Logs sanitized (no sensitive data)
- Screenshots stored locally only

---

## License

See LICENSE file for details.
