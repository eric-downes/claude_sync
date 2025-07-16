# Claude.ai Project Knowledge MCP Server - Development Plan

## Project Overview
An MCP (Model Context Protocol) server that enables Claude Code to access text files from Claude.ai's "project knowledge" feature, allowing seamless integration between web-based Claude projects and local Claude Code instances.

## Key Challenges & Solutions

### 1. Authentication Strategy
**Challenge**: Claude.ai uses session-based authentication (not API keys) for web access
**Solution**: Multi-approach authentication system:
- **Primary**: Browser cookie extraction using browser_cookie3 library
- **Secondary**: Headless browser automation (Playwright) for login flow
- **Fallback**: Manual session token input with secure storage

### 2. File Access Architecture
**Challenge**: No official API for project knowledge files
**Solution**: Web scraping approach with robust error handling:
- Intercept network requests to identify file download endpoints
- Parse project structure from web interface
- Cache files locally with version tracking
- Implement rate limiting to avoid detection

### 3. MCP Server Implementation
**Challenge**: Exposing Claude.ai files through standardized MCP interface
**Solution**: Python-based MCP server using FastMCP framework:
- Tools for listing projects and files
- Resources for file content access
- Prompts for common operations
- Real-time synchronization options

## Technical Architecture

### Components
1. **Authentication Module**
   - Session manager with token refresh
   - Secure credential storage (keyring)
   - Multi-method authentication support

2. **Claude.ai Client**
   - Web scraping with BeautifulSoup/Playwright
   - Request interception for API discovery
   - Rate limiting and retry logic
   - File content extraction and caching

3. **MCP Server**
   - FastMCP-based implementation
   - Tool definitions for CRUD operations
   - Resource providers for file access
   - Error handling and logging

4. **Local Cache**
   - SQLite for metadata storage
   - File system for content caching
   - Version tracking and diff support
   - Automatic cleanup policies

## MCP Server Capabilities

### Tools
```python
@mcp.tool()
async def list_projects() -> list[dict]:
    """List all available Claude.ai projects"""

@mcp.tool()
async def list_project_files(project_id: str) -> list[dict]:
    """List files in a specific project"""

@mcp.tool()
async def read_file(project_id: str, file_path: str) -> str:
    """Read content of a specific file"""

@mcp.tool()
async def sync_project(project_id: str) -> dict:
    """Synchronize all files from a project"""

@mcp.tool()
async def search_files(query: str, project_id: Optional[str] = None) -> list[dict]:
    """Search for files by name or content"""
```

### Resources
```python
@mcp.resource("project://{project_id}/{file_path}")
async def get_project_file(project_id: str, file_path: str) -> Resource:
    """Access project files as MCP resources"""
```

### Prompts
```python
@mcp.prompt()
async def analyze_project() -> Prompt:
    """Analyze project structure and suggest improvements"""

@mcp.prompt()
async def sync_all() -> Prompt:
    """Synchronize all projects from Claude.ai"""
```

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Set up Python project with FastMCP
- [ ] Implement authentication module
- [ ] Create basic Claude.ai client
- [ ] Test connection and session management

### Phase 2: File Access (Week 3-4)
- [ ] Reverse engineer file download endpoints
- [ ] Implement file listing and retrieval
- [ ] Add local caching system
- [ ] Create error handling and retry logic

### Phase 3: MCP Server (Week 5-6)
- [ ] Define MCP tool schemas
- [ ] Implement core MCP operations
- [ ] Add resource providers
- [ ] Create comprehensive logging

### Phase 4: Enhanced Features (Week 7-8)
- [ ] Add file search capabilities
- [ ] Implement incremental sync
- [ ] Create configuration management
- [ ] Add performance optimizations

### Phase 5: Testing & Documentation (Week 9-10)
- [ ] Unit and integration tests
- [ ] User documentation
- [ ] Installation guide
- [ ] Example use cases

## Project Structure
```
claude-project-knowledge-mcp/
├── src/
│   ├── __init__.py
│   ├── server.py           # MCP server entry point
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── session_manager.py
│   │   ├── browser_auth.py
│   │   └── credential_store.py
│   ├── client/
│   │   ├── __init__.py
│   │   ├── claude_client.py
│   │   ├── scraper.py
│   │   └── rate_limiter.py
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── file_cache.py
│   │   └── metadata_store.py
│   └── mcp/
│       ├── __init__.py
│       ├── tools.py
│       ├── resources.py
│       └── prompts.py
├── tests/
├── docs/
├── examples/
├── requirements.txt
├── pyproject.toml
├── README.md
└── LICENSE
```

## Key Dependencies
- `fastmcp` - MCP server framework
- `playwright` - Browser automation
- `browser_cookie3` - Cookie extraction
- `beautifulsoup4` - HTML parsing
- `httpx` - Async HTTP client
- `keyring` - Secure credential storage
- `sqlalchemy` - Database ORM
- `pydantic` - Data validation
- `rich` - Terminal UI
- `pytest` - Testing framework

## Security Considerations
1. **Credential Storage**: Use OS keyring for secure storage
2. **Session Management**: Implement token refresh and rotation
3. **Rate Limiting**: Respect Claude.ai's rate limits
4. **Data Privacy**: Local cache encryption option
5. **Access Control**: MCP-level permissions

## Performance Optimizations
1. **Caching**: Aggressive local caching with TTL
2. **Concurrent Downloads**: Async file retrieval
3. **Incremental Sync**: Only fetch changed files
4. **Compression**: Store cached files compressed
5. **Connection Pooling**: Reuse HTTP connections

## Error Handling Strategy
1. **Authentication Failures**: Automatic re-authentication
2. **Network Errors**: Exponential backoff retry
3. **Rate Limits**: Queue and delay requests
4. **Parse Errors**: Fallback strategies
5. **Cache Corruption**: Automatic recovery

## Testing Strategy
1. **Unit Tests**: All core components
2. **Integration Tests**: End-to-end workflows
3. **Mock Claude.ai**: Test without real connections
4. **Performance Tests**: Load and stress testing
5. **Security Tests**: Credential handling

## Success Metrics
- Reliable authentication (>99% success rate)
- Fast file access (<500ms average)
- Minimal API calls (aggressive caching)
- Zero credential leaks
- Seamless Claude Code integration

## Future Enhancements
1. **Write Support**: Upload changes back to Claude.ai
2. **Real-time Sync**: WebSocket-based updates
3. **Multi-user Support**: Team collaboration
4. **File Versioning**: Track changes over time
5. **Advanced Search**: Full-text search capabilities