# Claude.ai Project Knowledge MCP Server - Development Plan v2

## Project Overview
An MCP (Model Context Protocol) server that enables Claude Code to access text files from Claude.ai's "project knowledge" feature, allowing seamless integration between web-based Claude projects and local Claude Code instances.

## Key Learnings from Existing Implementations

### From claude_sync:
- **Browser automation approach works** - Uses Playwright for Claude.ai interaction
- **Backup system already implemented** - BackupManager with retention policies, integrity checks
- **File tracking exists** - Sync state management with hashing for change detection
- **Mock client for testing** - Helpful for TDD approach
- **Deprecated note mentions Claude SDK** - But SDK doesn't provide project knowledge access

### From mcp-oauth:
- **OAuth framework exists** - Can be adapted for Claude.ai session management
- **Token storage patterns** - Secure storage with encryption options
- **MCP server structure** - Good reference for our MCP implementation
- **TypeScript-based** - We'll convert key patterns to Python

## Updated Architecture

### 1. Authentication Strategy (Chrome + Session Management)
```python
# Chrome cookie extraction on macOS
- Location: ~/Library/Application Support/Google/Chrome/Default/Cookies
- Decrypt using Keychain access
- Fallback: Playwright automation for login
- Session persistence with refresh logic
```

### 2. Enhanced Sync Control & Backup Strategy
Building on claude_sync's BackupManager:

```python
class SyncPolicy:
    """Fine-grained sync control"""
    direction: Literal['pull', 'push', 'bidirectional']
    conflict_resolution: Literal['local_wins', 'remote_wins', 'manual', 'newest']
    file_patterns: List[str]  # glob patterns to include/exclude
    backup_before_sync: bool = True
    verify_after_sync: bool = True
    
class SafeSyncManager:
    """Prevents data loss during sync"""
    - Always backup before any destructive operation
    - Never auto-delete without explicit user confirmation
    - Maintain sync journal with rollback capability
    - Diff preview before applying changes
    - Checksum verification after transfers
```

### 3. TDD Implementation Plan with pytest

```python
# Test structure
tests/
├── unit/
│   ├── test_auth/
│   │   ├── test_chrome_cookie_extractor.py
│   │   ├── test_session_manager.py
│   │   └── test_playwright_fallback.py
│   ├── test_sync/
│   │   ├── test_backup_manager.py
│   │   ├── test_sync_policy.py
│   │   └── test_conflict_resolver.py
│   └── test_mcp/
│       ├── test_tools.py
│       └── test_server.py
├── integration/
│   ├── test_claude_client.py
│   ├── test_end_to_end_sync.py
│   └── test_mcp_integration.py
└── fixtures/
    ├── mock_claude_responses.py
    └── test_files/
```

### 4. Cross-Platform Implementation Notes

#### Windows Support
```python
# Chrome cookie location
cookie_paths = {
    'windows': r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cookies',
    'windows_key': 'DPAPI'  # Windows Data Protection API
}

# Implementation notes:
- Use pywin32 for DPAPI decryption
- Handle Windows path separators
- Test with Windows GitHub Actions runner
```

#### Linux Support
```python
# Chrome cookie location
cookie_paths = {
    'linux': '~/.config/google-chrome/Default/Cookies',
    'linux_key': 'gnome-keyring or kwallet'
}

# Implementation notes:
- Handle multiple keyring backends
- Consider snap/flatpak Chrome installations
- Test on Ubuntu and Fedora in CI
```

#### Browser Fallbacks
```python
# Priority order by platform
browser_priority = {
    'darwin': ['chrome', 'edge', 'firefox'],  # Safari too complex
    'win32': ['chrome', 'edge', 'firefox'],
    'linux': ['chrome', 'chromium', 'firefox']
}
```

## Implementation Roadmap (TDD Approach)

### Phase 1: Test Infrastructure & Core Auth (Week 1-2)
```python
# Start with tests first
- [ ] Set up pytest, coverage, mock infrastructure
- [ ] Write auth module tests
- [ ] Implement Chrome cookie extraction (macOS first)
- [ ] Test and implement session management
- [ ] Add Playwright fallback with tests
```

### Phase 2: Safe Sync System (Week 3-4)
```python
# Leverage claude_sync patterns
- [ ] Port and enhance BackupManager to Python
- [ ] Write comprehensive sync policy tests
- [ ] Implement conflict detection and resolution
- [ ] Add rollback and recovery mechanisms
- [ ] Create sync preview/diff functionality
```

### Phase 3: MCP Server Core (Week 5-6)
```python
# Python FastMCP implementation
- [ ] Define and test MCP tool schemas
- [ ] Implement list_projects, list_files, read_file
- [ ] Add sync operations with safety checks
- [ ] Create backup and restore tools
- [ ] Test error handling and edge cases
```

### Phase 4: Enhanced Features (Week 7-8)
```python
# Advanced functionality
- [ ] Selective sync with patterns
- [ ] Incremental sync optimization
- [ ] Search across projects
- [ ] Version history browsing
- [ ] Cross-platform compatibility
```

### Phase 5: Production Readiness (Week 9-10)
```python
# Polish and documentation
- [ ] Performance optimization
- [ ] Comprehensive integration tests
- [ ] Documentation and examples
- [ ] CI/CD with multi-platform tests
- [ ] Security audit
```

## Key Dependencies (Python)
```toml
[project]
dependencies = [
    "fastmcp>=0.2.0",          # MCP server framework
    "playwright>=1.40.0",       # Browser automation
    "pycookiecheat>=0.5.1",     # Chrome cookie extraction
    "httpx>=0.25.0",           # Async HTTP client
    "cryptography>=41.0.0",     # Cookie decryption
    "keyring>=24.0.0",         # Cross-platform credential storage
    "pytest>=7.4.0",           # Testing framework
    "pytest-asyncio>=0.21.0",   # Async test support
    "pytest-cov>=4.1.0",       # Coverage reporting
    "rich>=13.0.0",            # Terminal UI
]
```

## Safety Features (Addressing Your Concerns)

### 1. **No Automatic Deletions**
- Deletions require explicit confirmation
- Soft-delete with recovery period
- Backup before any destructive operation

### 2. **Sync Conflict Prevention**
```python
class ConflictResolver:
    def detect_conflicts(self, local_file, remote_file):
        # Compare timestamps and hashes
        # Show diff to user
        # Let user choose resolution
        
    def preview_changes(self):
        # Show what will be synced
        # Highlight potential issues
        # Require confirmation for risky operations
```

### 3. **Backup Redundancy**
- Local backups (default)
- Optional cloud backup integration
- Versioned backups with retention
- Integrity verification

### 4. **Sync Journal**
```python
class SyncJournal:
    # Track every sync operation
    # Enable rollback to any point
    # Audit trail for debugging
    # Crash recovery support
```

## Testing Strategy (TDD Focus)

### Unit Tests First
```python
# Example: Test cookie extraction before implementing
def test_chrome_cookie_extraction_macos(mock_keychain):
    extractor = ChromeCookieExtractor()
    mock_keychain.get_password.return_value = b'encryption_key'
    
    cookies = extractor.extract_cookies('claude.ai')
    
    assert 'sessionKey' in cookies
    assert cookies['sessionKey'].startswith('sk-ant-')
```

### Integration Tests with Mocks
```python
# Test full sync flow without hitting real Claude.ai
def test_safe_sync_with_conflicts(mock_claude_client, temp_files):
    sync_manager = SafeSyncManager(mock_claude_client)
    
    # Create conflict scenario
    local_file = temp_files / "test.md"
    local_file.write_text("Local content")
    mock_claude_client.get_file_content.return_value = "Remote content"
    
    # Sync should detect conflict
    result = sync_manager.sync_file(local_file)
    
    assert result.has_conflict
    assert result.backup_created
    assert local_file.read_text() == "Local content"  # No auto-overwrite
```

### End-to-End Tests (Optional Real Claude.ai)
```python
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("CLAUDE_TEST_ACCOUNT"), 
                    reason="Requires test account")
def test_real_claude_sync():
    # Full integration test with real account
    pass
```

## Migration Path from Existing Code

1. **Reuse claude_sync components**:
   - Port BackupManager to Python
   - Adapt sync state tracking
   - Learn from browser automation approach

2. **Leverage mcp-oauth patterns**:
   - Token/session storage
   - MCP server structure
   - Error handling patterns

3. **Improve on limitations**:
   - Better conflict handling
   - Safer sync operations
   - Cross-platform support

## Success Metrics
- Zero data loss incidents
- 100% backup success rate before modifications
- Clear sync previews and confirmations
- Comprehensive test coverage (>90%)
- Multi-platform compatibility
- Fast sync performance (<1s per file)
- Secure credential handling

This plan incorporates your feedback for TDD, safety controls, cross-platform support, and leverages the existing code you've shared. The focus is on preventing data loss while providing flexible sync options.