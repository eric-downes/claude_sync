# Project Structure

## Directory Layout

```
claude_sync/
├── src/                      # Source code
│   ├── chrome/              # Chrome DevTools Protocol implementation
│   │   ├── __init__.py
│   │   ├── client.py        # Basic Chrome client
│   │   ├── robust_client.py # Robust client with reconnection
│   │   └── exceptions.py    # Custom exceptions
│   └── extractors/          # Data extraction modules
│       ├── __init__.py
│       ├── models.py        # Pydantic models
│       ├── projects.py      # Project list extractor
│       └── knowledge.py     # Project knowledge extractor
├── tests/                   # Test suite
│   ├── unit/               # Unit tests
│   │   ├── test_chrome_client.py
│   │   ├── test_project_extractor.py
│   │   └── test_project_knowledge_extractor.py
│   └── conftest.py         # Pytest configuration
├── scripts/                 # Utility scripts
│   ├── extract_dlpos_files.py           # DLPoS extraction demo
│   ├── test_robust_client.py            # Robust client testing
│   ├── test_dlpos_knowledge_extraction.py # Knowledge extraction test
│   ├── launch_chrome_with_claude.py     # Chrome launcher
│   └── ...                              # Other utility scripts
├── config/                  # Configuration files
│   ├── claude_sync_startup.sh          # Startup script
│   └── com.claude.sync.plist            # macOS plist
├── pyproject.toml          # Project configuration
├── README.md               # Project documentation
└── .gitignore              # Git ignore patterns
```

## Key Components

### Chrome Client (`src/chrome/`)
- **client.py**: Basic Chrome DevTools Protocol client
- **robust_client.py**: Enhanced client with automatic reconnection and better error handling

### Extractors (`src/extractors/`)
- **projects.py**: Extracts list of Claude.ai projects
- **knowledge.py**: Extracts knowledge files from specific projects
- **models.py**: Pydantic models for data validation

### Tests (`tests/`)
- Comprehensive unit tests for all components
- Test-driven development approach

### Scripts (`scripts/`)
- Utility scripts for testing and development
- Manual testing tools
- Chrome launch utilities

## Sensitive Files
- `api-key`: Contains API credentials (gitignored)
- `mcp-oauth/`: OAuth configuration (if needed)

## Next Components to Implement
1. LocalStorageManager - For saving extracted data locally
2. SyncOrchestrator - For coordinating the sync process
3. CLI Interface - For user interaction