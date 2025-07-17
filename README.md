# Claude Sync

A tool to sync your Claude.ai project knowledge files to your local machine. This tool uses browser automation to extract and download all your project files, maintaining an organized local backup.

## Features

- 🔄 **Project Knowledge Sync** - Download all projects and their knowledge files
- 📁 **Organized Storage** - Maintains a clean directory structure matching your Claude.ai organization
- 🎯 **Selective Sync** - Sync specific projects or all projects at once
- 📊 **Progress Tracking** - Real-time progress updates during sync
- 💾 **Metadata Preservation** - Saves project descriptions and sync timestamps
- 🖥️ **Headless Mode** - Can run in background without opening browser window

## Prerequisites

- Python 3.8+
- Chrome browser installed
- Chrome DevTools Protocol enabled (see setup below)

## Installation

**Currently only tested on MacOS Sonoma**

1. Clone the repository.

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Enable Chrome DevTools Protocol:
```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222

# Windows
chrome.exe --remote-debugging-port=9222
```

4. Log in to Claude.ai in the Chrome instance that opened

## Usage

### Sync All Projects
```bash
python sync_cli.py sync
```

### Sync Specific Project
```bash
python sync_cli.py sync-project "Project Name"
```

### List Synced Projects
```bash
python sync_cli.py list
```

### Command Line Options
```bash
python sync_cli.py --help

Options:
  --storage PATH     Storage directory (default: claude_sync_data)
  --headless         Run browser in headless mode
  --quiet            Suppress progress output
```

## Project Structure

### Synced Data Structure

By default, synced data is stored in `./claude_sync_data/` relative to your current working directory.

```
./claude_sync_data/              # Created in current directory
├── .metadata/
│   └── sync_state.json          # Sync history and state
└── projects/
    ├── Project-Name-1/
    │   ├── project.json         # Project metadata
    │   └── knowledge/
    │       ├── file1.txt        # Knowledge files
    │       ├── file2.pdf
    │       └── ...
    └── Project-Name-2/
        ├── project.json
        └── knowledge/
            └── ...
```

To use a custom storage location:
```bash
python sync_cli.py sync --storage ~/Documents/claude_backup
```

### Source Code Structure
```
claude_sync/
├── claude_sync/
│   ├── __init__.py
│   ├── models.py               # Pydantic models for data structures
│   ├── browser/
│   │   ├── __init__.py
│   │   ├── config.py          # Browser configuration
│   │   ├── manager.py         # Chrome browser management
│   │   └── connection.py      # Page interaction logic
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── project.py         # Project list extraction
│   │   └── knowledge.py       # Knowledge file extraction
│   └── sync/
│       ├── __init__.py
│       ├── orchestrator.py    # Main sync coordination
│       └── storage.py         # Local storage management
├── sync_cli.py                # Command-line interface
├── requirements.txt
└── README.md
```

## How It Works

1. **Browser Automation**: Uses Playwright to control Chrome via DevTools Protocol
2. **Project Discovery**: Navigates to Claude.ai projects page and clicks "View All" to load all projects
3. **Content Extraction**: For each project:
   - Navigates to the project page
   - Extracts list of knowledge files
   - Clicks on each file to open the modal
   - Extracts the file content from the modal
   - Saves to local storage
4. **Progress Tracking**: Provides real-time updates on sync progress

## Architecture

### Key Components

- **BrowserManager**: Manages Chrome browser lifecycle and connections
- **ChromeConnection**: Handles page navigation and interactions
- **ProjectExtractor**: Extracts project information from HTML
- **KnowledgeExtractor**: Extracts knowledge file metadata
- **SyncOrchestrator**: Coordinates the entire sync process
- **LocalStorage**: Manages the local file system storage

### Data Flow
```
Claude.ai → Browser Automation → HTML Extraction → Local Storage
                ↑                        ↓
                └── Progress Updates ────┘
```

## Development

### Running Tests
```bash
pytest tests/
```

### Test Scripts
- `test_real_world.py` - Test project and file extraction
- `test_file_download.py` - Test file content download
- `test_sync_simple.py` - Test basic sync functionality

## Limitations

- Requires Chrome to be running with DevTools Protocol enabled
- Cannot download files that require special handling (some PDFs may only save metadata)
- Sync speed depends on number of projects and files
- Must maintain login session in Chrome

## Troubleshooting

### Chrome Connection Issues
- Ensure Chrome is running with `--remote-debugging-port=9222`
- Check that no other application is using port 9222
- Try closing all Chrome instances and restarting

### Login Issues
- Make sure you're logged into Claude.ai in the Chrome instance
- If using 2FA, complete the login process before running sync

### File Download Issues
- Some files may take longer to load - the tool waits for modals to appear
- PDF files may only show preview text rather than full content

## Future Enhancements

- [ ] Incremental sync (only download new/changed files)
- [ ] File content comparison and versioning
- [ ] Export to different formats
- [ ] Scheduled automatic syncs
- [ ] Support for other Claude.ai data types (conversations, etc.)

## Contributing

Contributions are welcome! Please submit a Pull Request.
