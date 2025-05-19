# LevelDB Integration for Claude Sync

This document describes how we've integrated LevelDB access into Claude Sync to better access Claude Desktop's data.

## Implementation Components

1. **LevelDB MCP Submodule**
   - Standalone MCP for accessing LevelDB databases
   - Located in `/mcp-leveldb` directory
   - Can be used independently or as part of Claude Sync
   - Provides API for reading LevelDB data through HTTP

2. **LevelDB Desktop Client**
   - Extended implementation of ClaudeDesktopClient
   - Uses LevelDB MCP to access Claude Desktop's database
   - Finds and extracts project data from LevelDB

3. **API Mode Integration**
   - Added 'leveldb' as a new API mode
   - Updated client factory to support LevelDB mode
   - Added port configuration for LevelDB MCP server

## How It Works

1. The LevelDB MCP runs as a separate server that provides access to LevelDB databases
2. Claude Sync connects to this MCP server to read Claude Desktop's data
3. The LevelDBDesktopClient sends requests to the MCP to access the database
4. Project data is extracted from the database and made available through the regular Claude API client interface

## Usage

### Using the LevelDB Mode

```bash
# Set the API mode to leveldb with MCP server running on port 3000
claude-sync mode -m leveldb -p 3000

# Now all commands will use the LevelDB client
claude-sync list-projects
claude-sync sync-all
```

### Setting Up the LevelDB MCP

1. Navigate to the MCP submodule
   ```bash
   cd mcp-leveldb
   ```

2. Install dependencies
   ```bash
   npm install
   ```

3. Build the MCP
   ```bash
   npm run build
   ```

4. Start the MCP server
   ```bash
   node dist/cli.js server
   ```

5. Register with Claude Code (optional)
   ```bash
   claude mcp add leveldb -- node /path/to/claude_sync/mcp-leveldb/dist/cli.js server
   ```

### Testing the Implementation

A test script is provided to verify the LevelDB integration:

```bash
node scripts/test-leveldb-mode.js [port]
```

This script:
1. Sets the API mode to leveldb
2. Lists all projects found in Claude Desktop's LevelDB database
3. Restores the original API mode

## Debugging Claude Desktop Data

Use the debugging script to explore Claude Desktop's LevelDB data:

```bash
node scripts/debug-leveldb.js --prefix project
```

See the [LEVELDB_MCP.md](LEVELDB_MCP.md) file for more details on using the LevelDB MCP.