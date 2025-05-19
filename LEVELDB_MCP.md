# LevelDB MCP for Claude Sync

This submodule provides a Model Context Protocol (MCP) tool for accessing LevelDB databases, particularly useful for accessing Claude Desktop's stored data.

## Setup

1. Build the LevelDB MCP:

```bash
cd mcp-leveldb
npm install
npm run build
```

2. Register the MCP with Claude Code:

```bash
claude mcp add leveldb -- node /Users/eric/compute/claude_sync/mcp-leveldb/dist/cli.js server
```

3. Start the MCP server:

```bash
cd mcp-leveldb
node dist/cli.js server
```

## Using with Claude Code

Once the MCP is registered and running, you can access it from Claude Code to explore LevelDB databases:

```
// Example: Get all projects from Claude Desktop
const claudeAppDataPath = os.platform() === 'darwin' 
  ? path.join(os.homedir(), 'Library', 'Application Support', 'Claude')
  : os.platform() === 'win32'
    ? path.join(os.homedir(), 'AppData', 'Roaming', 'Claude')
    : path.join(os.homedir(), '.config', 'Claude');

const leveldbPath = path.join(claudeAppDataPath, 'Local Storage', 'leveldb');

const response = await fetch('http://localhost:3000/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    action: 'leveldb-get-all',
    parameters: {
      dbPath: leveldbPath,
      prefix: 'project'
    }
  })
});

const result = await response.json();
if (result.status === 'success') {
  const projects = result.data.entries;
  console.log(`Found ${projects.length} projects`);
  // Process projects...
}
```

## Debugging Claude Desktop Data

The repository includes a debug script to help explore Claude Desktop's data:

```bash
node scripts/debug-leveldb.js
```

Options:
- `--path <path>`: Custom path to a LevelDB database (default: Claude Desktop's LevelDB)
- `--key <key>`: Look up a specific key
- `--prefix <prefix>`: Filter keys by prefix
- `--limit <number>`: Limit the number of results

Example to find Claude projects:

```bash
node scripts/debug-leveldb.js --prefix project
```

## API Reference

The LevelDB MCP provides the following endpoints:

### 1. `leveldb-get`

Get a specific key from a LevelDB database.

Parameters:
- `dbPath` (string): Path to the LevelDB database directory
- `key` (string): The key to retrieve

### 2. `leveldb-get-all`

Get all entries from a LevelDB database, optionally filtered by prefix.

Parameters:
- `dbPath` (string): Path to the LevelDB database directory
- `prefix` (string, optional): Filter keys starting with this prefix
- `limit` (number, optional): Maximum number of entries to return
- `skip` (number, optional): Number of entries to skip

### 3. `leveldb-keys`

Get all keys from a LevelDB database, optionally filtered by prefix.

Parameters:
- `dbPath` (string): Path to the LevelDB database directory
- `prefix` (string, optional): Filter keys starting with this prefix
- `limit` (number, optional): Maximum number of keys to return
- `skip` (number, optional): Number of keys to skip

### 4. `leveldb-info`

Get information about a LevelDB database.

Parameters:
- `dbPath` (string): Path to the LevelDB database directory