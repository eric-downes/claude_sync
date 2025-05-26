# Claude Sync

**DEPRECATED**: With the release of the [Cluade SDK](https://github.com/anthropics/anthropic-sdk-python) there is no need for this tool!

A tool for synchronizing between Claude Code and Claude AI projects.

## Overview

Claude Sync provides bidirectional synchronization between local files accessible to Claude Code and knowledge bases in Claude AI projects.

## Features

- Synchronize local files with Claude project knowledge bases
- Configure multiple projects with different synchronization settings
- Track changes to ensure efficient updates

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/claude-sync.git
cd claude-sync

# Install the OAuth MCP submodule for enhanced authentication support
git submodule add https://github.com/eric-downes/mcp-oauth.git mcp-oauth
git submodule update --init --recursive

# Install dependencies 
npm install --legacy-peer-deps

# Build the project
npm run build

# Or install globally
npm install -g . --legacy-peer-deps
```

## Usage

```bash
# Set the API mode (browser or mock)
claude-sync mode --mode browser  # Use browser automation with Claude.ai (recommended)
claude-sync mode --mode mock     # Use mock client for testing

# List all projects in your Claude.ai account
claude-sync list-projects
claude-sync list  # Shorthand

# Configure a new project
claude-sync config

# Sync files to a Claude project
claude-sync sync --project my-project

# Sync all projects to subdirectories in ~/claude
claude-sync sync-all

# Watch files for changes and auto-sync
claude-sync watch --project my-project

# Start the MCP server for Claude Code integration
claude-sync server --port 8022
```

## API Modes

Claude Sync provides access to your Claude projects through the following modes:

### Browser Mode (Recommended)
Uses browser automation to interact with Claude.ai. This is the primary supported method for accessing Claude projects. Set your credentials:

```bash
# Set environment variables for Claude.ai credentials
export CLAUDE_EMAIL=your-email@example.com
export CLAUDE_PASSWORD=your-password

# Or add them to a .env file in your project directory
echo "CLAUDE_EMAIL=your-email@example.com" >> .env
echo "CLAUDE_PASSWORD=your-password" >> .env
```

### Mock Mode
Uses a mock client that simulates Claude API responses. Useful for testing without a Claude account.

**Note:** Desktop mode and LevelDB integration have been deprecated as no project data was found in the Claude Desktop database. Use browser mode for all production synchronization.

## Implementation Approach

Claude Sync uses the Model Context Protocol (MCP) to create a bridge between Claude Code and Claude AI projects. Given the current limitations in direct API access to Claude Projects, we implement:

1. A custom MCP server that handles the synchronization logic
2. Authentication using standard Claude credentials
3. File tracking to minimize transfer needs

## Development

```bash
# Run tests
npm test

# Build the project
npm run build
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT