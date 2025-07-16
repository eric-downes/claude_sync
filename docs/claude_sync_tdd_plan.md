# Claude Sync Tool - TDD Implementation Plan

## Overview
Build a production-ready Python tool to sync Claude.ai project knowledge locally using Chrome DevTools Protocol (CDP) with Test-Driven Development.

## Architecture

### Core Components

```
claude-sync/
├── src/
│   ├── __init__.py
│   ├── chrome/
│   │   ├── __init__.py
│   │   ├── client.py          # ChromeClient
│   │   ├── connection.py      # WebSocket connection management
│   │   └── exceptions.py      # Chrome-specific exceptions
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── projects.py        # ProjectExtractor
│   │   ├── knowledge.py       # ProjectKnowledgeExtractor
│   │   └── models.py          # Data models (Project, KnowledgeFile)
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── manager.py         # LocalStorageManager
│   │   ├── hasher.py          # File hashing utilities
│   │   └── conflict.py        # Conflict resolution
│   ├── sync/
│   │   ├── __init__.py
│   │   ├── orchestrator.py    # SyncOrchestrator
│   │   └── strategies.py      # Sync strategies
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py        # Configuration management
│   └── cli/
│       ├── __init__.py
│       └── main.py            # CLI interface
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── chrome_responses.py
│   │   └── sample_data.py
│   ├── unit/
│   │   ├── test_chrome_client.py
│   │   ├── test_project_extractor.py
│   │   ├── test_knowledge_extractor.py
│   │   ├── test_storage_manager.py
│   │   └── test_sync_orchestrator.py
│   ├── integration/
│   │   └── test_full_sync.py
│   └── conftest.py
├── pyproject.toml
├── setup.py
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Implementation Order (TDD)

### Phase 1: Foundation
1. **Project Setup**
   - Initialize project with pytest, pytest-asyncio, pytest-mock
   - Set up pyproject.toml with proper dependencies
   - Configure testing framework

2. **ChromeClient** (Week 1)
   - Test: Connection to Chrome debug port
   - Test: Page enumeration and filtering
   - Test: WebSocket message handling
   - Test: Error handling (no Chrome, port blocked, etc.)
   - Implementation: Basic CDP client
   - **Manual Test**: Successfully login with/without existing credentials
   - **Manual Test**: Handle credential expiration gracefully

### Phase 2: Data Extraction
3. **Data Models** (Week 1)
   - Test: Project model validation
   - Test: KnowledgeFile model validation
   - Implementation: Pydantic models

4. **ProjectExtractor** (Week 2)
   - Test: Extract project list from DOM
   - Test: Handle empty project list
   - Test: Extract project metadata
   - Implementation: DOM navigation and extraction

5. **ProjectKnowledgeExtractor** (Week 2)
   - Test: Navigate to project page
   - Test: Extract knowledge files
   - Test: Handle various file types
   - Test: Extract file content
   - Implementation: Knowledge extraction logic

### Phase 3: Storage
6. **LocalStorageManager** (Week 3)
   - Test: Create project directory structure
   - Test: Save knowledge files
   - Test: Detect file changes (hashing)
   - Test: Backup before modifications
   - Implementation: File system operations

7. **Conflict Resolution** (Week 3)
   - Test: Detect conflicts
   - Test: Generate conflict reports
   - Test: Conservative backup strategy
   - Test: User prompts before permanent deletion
   - Implementation: Backup + ask-on-delete strategy
   - Note: Always keep copies, storage is not a concern for project knowledge

### Phase 4: Orchestration
8. **SyncOrchestrator** (Week 4)
   - Test: Full sync workflow
   - Test: Incremental sync
   - Test: Error recovery
   - Test: Progress reporting
   - Implementation: Orchestration logic

### Phase 5: CLI & Config
9. **Configuration** (Week 4)
   - Test: Load/save config
   - Test: Validate settings
   - Implementation: Config management

10. **CLI Interface** (Week 5)
    - Test: Command parsing
    - Test: Output formatting
    - Implementation: Click-based CLI

### Phase 6: Containerization
11. **Container Support** (Week 6)
    - Research lightweight alternatives to Docker (Podman, etc.)
    - Create container image
    - Test cross-platform compatibility
    - Documentation for team deployment

## Test Strategy

### Unit Tests
- Mock all external dependencies (Chrome, filesystem)
- Test each component in isolation
- Aim for 90%+ coverage

### Integration Tests
- Use real Chrome instance (optional flag)
- Test full sync workflow
- Test error scenarios

### Test Fixtures
```python
# fixtures/chrome_responses.py
MOCK_PAGES_RESPONSE = [
    {
        "id": "1",
        "url": "https://claude.ai/projects",
        "title": "Projects - Claude",
        "type": "page",
        "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/1"
    }
]

MOCK_PROJECTS_DOM = {
    "projects": [
        {
            "name": "Test Project",
            "url": "https://claude.ai/project/test-id",
            "id": "test-id"
        }
    ]
}
```

## Error Handling Strategy

### Exception Hierarchy
```python
class ClaudeSyncError(Exception):
    """Base exception for all claude-sync errors"""

class ChromeConnectionError(ClaudeSyncError):
    """Chrome connection issues"""

class ExtractionError(ClaudeSyncError):
    """Data extraction failures"""

class StorageError(ClaudeSyncError):
    """File system operations"""

class SyncError(ClaudeSyncError):
    """Sync workflow errors"""
```

### Retry Logic
- Exponential backoff for Chrome connections
- Configurable retry attempts
- Clear error messages with recovery suggestions

## Key Design Decisions

1. **Async/Await**: Use asyncio for Chrome WebSocket communication
2. **Dependency Injection**: Pass dependencies to constructors for testability
3. **Configuration**: Support both CLI args and config file
4. **Logging**: Structured logging with different verbosity levels
5. **Progress Reporting**: Real-time updates during sync

## Testing Tools

- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-mock**: Mocking framework
- **pytest-cov**: Coverage reporting
- **responses**: Mock HTTP requests
- **websocket-client**: Mock WebSocket connections

## Development Workflow

1. Write failing test
2. Implement minimal code to pass
3. Refactor
4. Repeat

## Success Criteria

- All tests passing
- 90%+ code coverage
- Handles all error cases gracefully
- Clear documentation
- Type hints throughout
- Follows PEP 8

## Next Steps

1. Set up project structure
2. Configure testing framework
3. Start with ChromeClient tests
4. Implement incrementally following TDD