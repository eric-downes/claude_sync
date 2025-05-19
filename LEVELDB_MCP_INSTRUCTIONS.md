# Using the LevelDB MCP with Claude Sync

This document explains how to use the LevelDB MCP with the Claude Sync tool to access LevelDB databases, including the Claude Desktop application's storage.

## Setup

### Building the LevelDB MCP

1. Build the LevelDB MCP tool:

```bash
cd /Users/eric/compute/claude_sync/mcp-leveldb
npm install
npm run build
```

2. Verify the tool works correctly with a simple test:

```bash
npm run test:simple
```

### Registering with Claude Code

To use the LevelDB MCP with Claude Code, register it as follows:

```bash
claude mcp add leveldb -- node /Users/eric/compute/claude_sync/mcp-leveldb/dist/cli.js server
```

Verify it's registered correctly:

```bash
claude mcp list
```

## Exploring Claude Desktop Data

The LevelDB MCP is particularly useful for exploring Claude Desktop's LevelDB storage.

### Finding Claude Desktop's LevelDB

Claude Desktop typically stores its data in these locations:

- **macOS**: `~/Library/Application Support/Claude/Local Storage/leveldb`
- **Windows**: `%APPDATA%\Claude\Local Storage\leveldb`
- **Linux**: `~/.config/Claude/Local Storage/leveldb`

### Debugging with CLI Tools

The `debug-leveldb.js` script provides a simple way to inspect the Claude Desktop database:

```bash
# Make sure Claude Desktop is closed first!
node scripts/debug-leveldb.js

# Search for specific key prefixes
node scripts/debug-leveldb.js --prefix "_https://claude.ai"

# Look for specific keys
node scripts/debug-leveldb.js --key "_https://claude.ai lastLoginMethod"
```

### Using the MCP Through Claude Code

Once the MCP is registered, you can use it within Claude Code:

```typescript
const claudeAppDataPath = os.platform() === 'darwin' 
  ? path.join(os.homedir(), 'Library', 'Application Support', 'Claude')
  : os.platform() === 'win32'
    ? path.join(os.homedir(), 'AppData', 'Roaming', 'Claude')
    : path.join(os.homedir(), '.config', 'Claude');

const leveldbPath = path.join(claudeAppDataPath, 'Local Storage', 'leveldb');

// List all keys
const response = await fetch('http://localhost:3000/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    action: 'leveldb-keys',
    parameters: {
      dbPath: leveldbPath
    }
  })
});

const result = await response.json();
if (result.status === 'success') {
  console.log(`Found ${result.data.keys.length} keys`);
}
```

## Known Limitations

1. **Database Locking**: You must close Claude Desktop before accessing its LevelDB files to avoid locking issues.

2. **Data Structure**: Claude Desktop uses a complex data structure that may not directly expose project data in the LevelDB storage.

3. **Compatibility**: The format of the LevelDB data may change with updates to Claude Desktop.

## Troubleshooting

### Common Issues

1. **"Database is locked" errors**: Make sure Claude Desktop is closed before attempting to access its LevelDB files.

2. **"Not a LevelDB database" errors**: Verify the path is correct and contains valid LevelDB files.

3. **"Database is not open" errors**: Ensure you're opening the database before attempting operations.

### Debugging the MCP

To debug the MCP server directly:

```bash
cd mcp-leveldb
node --inspect dist/cli.js server
```

Then connect a debugger to port 9229.

## Next Steps

As we discovered in our LevelDB analysis, Claude Desktop may not store project data locally in an easily accessible format. Therefore, our recommended approaches for accessing Claude.ai projects are:

1. **Browser Automation**: Implementing the browser client to interact with Claude.ai directly.

2. **API Integration**: When direct API access becomes available, transitioning to using that API.

The LevelDB MCP remains a valuable tool for exploring and accessing any LevelDB database, including those used by Electron applications like Claude Desktop.