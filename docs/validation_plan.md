# Validation Plan: Better Tools POC

## Core Problems to Validate

1. **Auth Complexity** ✓
   - Current: Complex auth detection and handling
   - Playwright: Reuses existing browser session
   - **Test**: Can Playwright connect to pre-authenticated Chrome?

2. **Connection Reliability** ✓
   - Current: WebSocket drops, manual reconnection
   - Playwright: Built-in retry and reconnection
   - **Test**: Does connection survive network blips?

3. **Unattended Operation** ✓
   - Current: Requires monitoring for auth/connection issues  
   - Playwright: Should run indefinitely without intervention
   - **Test**: Can it run for 24 hours unattended?

## Minimal Validation Tests

### Test 1: Basic Connection (5 minutes)
```bash
# 1. Ensure Chrome is running and logged into Claude
# 2. Run the POC
python minimal_playwright_poc.py

# Success criteria:
# - Connects to existing Chrome ✓
# - No auth prompt ✓  
# - Can access projects ✓
```

### Test 2: Session Persistence (10 minutes)
```python
# Test that auth survives script restarts
for i in range(5):
    print(f"Run {i+1}")
    # Run script
    subprocess.run(["python", "minimal_playwright_poc.py"])
    time.sleep(60)  # Wait between runs

# Success criteria:
# - All 5 runs succeed without re-auth
# - No manual intervention needed
```

### Test 3: Connection Recovery (10 minutes)
```python
# Test connection resilience
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    page = browser.contexts[0].pages[0]
    
    # Simulate connection issues
    print("Testing connection recovery...")
    
    # 1. Navigate away and back
    page.goto("https://google.com")
    page.goto("https://claude.ai/projects")
    
    # 2. Long operation
    page.wait_for_timeout(30000)  # 30 second wait
    
    # 3. Can still access protected content?
    projects = page.query_selector_all('a[href*="/project/"]')
    print(f"Still working: {len(projects)} projects found")
```

### Test 4: Unattended Operation (1 hour)
```python
# Leave running for 1 hour
import time
from datetime import datetime

def hourly_check():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        page = browser.contexts[0].pages[0]
        page.goto("https://claude.ai/projects")
        projects = len(page.query_selector_all('a[href*="/project/"]'))
        print(f"{datetime.now()}: Found {projects} projects")
        return projects > 0

# Run 6 times (every 10 minutes for 1 hour)
for i in range(6):
    success = hourly_check()
    if not success:
        print("FAILED - manual intervention needed")
        break
    time.sleep(600)  # 10 minutes
else:
    print("SUCCESS - ran for 1 hour unattended")
```

## Quick Decision Matrix

| Issue | Current Approach | Playwright + CDP | Validated? |
|-------|-----------------|------------------|------------|
| Auth handling | Complex, in code | Chrome handles it | ✓ Test 1 |
| Connection drops | Manual recovery | Auto-recovery | ✓ Test 3 |
| Wait strategies | time.sleep() | Smart waits | ✓ Built-in |
| Unattended ops | Fragile | Robust | ✓ Test 4 |
| Code complexity | High | Low | ✓ See POC |

## Minimal Implementation Path

If validation succeeds:

1. **Phase 1**: Add BeautifulSoup to current code (1 day)
   - Immediate improvement
   - Low risk

2. **Phase 2**: Playwright connection layer (2 days)
   - Replace ChromeClient connection logic
   - Keep existing extraction logic

3. **Phase 3**: Full refactor (3 days)
   - Playwright for navigation
   - BeautifulSoup for parsing
   - Proper error handling

Total: ~1 week for robust solution vs ongoing maintenance of fragile code

## Go/No-Go Criteria

**GO if:**
- [ ] Basic POC works without auth prompts
- [ ] Can run 5 times in a row without intervention
- [ ] Survives 1 hour unattended test

**NO-GO if:**
- [ ] Still requires auth handling in code
- [ ] Connection is not more reliable
- [ ] Can't run unattended

The POC should take < 30 minutes to validate these concerns.