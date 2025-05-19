#!/usr/bin/env node

/**
 * Debug script to explore Claude Desktop LevelDB directly
 * 
 * Usage:
 * node scripts/debug-leveldb.js [options]
 * 
 * Options:
 *  --path <path>    Path to the LevelDB database directory
 *  --key <key>      Specific key to look up
 *  --prefix <pfx>   Prefix to filter keys by
 *  --limit <num>    Limit number of results
 */

import { Level } from 'level';
import os from 'os';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Handle command line arguments
const args = process.argv.slice(2);
const options = {};

for (let i = 0; i < args.length; i++) {
  if (args[i].startsWith('--')) {
    const key = args[i].slice(2);
    options[key] = args[i + 1] || true;
    if (args[i + 1] && !args[i + 1].startsWith('--')) {
      i++;
    }
  }
}

// Default Claude Desktop path based on OS
let claudeDesktopPath = '';
if (os.platform() === 'darwin') {
  claudeDesktopPath = path.join(os.homedir(), 'Library', 'Application Support', 'Claude');
} else if (os.platform() === 'win32') {
  claudeDesktopPath = path.join(os.homedir(), 'AppData', 'Roaming', 'Claude');
} else {
  claudeDesktopPath = path.join(os.homedir(), '.config', 'Claude');
}

// Default LevelDB path is in Claude Desktop's Local Storage
const defaultLevelDBPath = path.join(claudeDesktopPath, 'Local Storage', 'leveldb');
const dbPath = options.path || defaultLevelDBPath;

console.log('Claude Desktop path:', claudeDesktopPath);
console.log('LevelDB path:', dbPath);

// Helper function to parse a value if it's a JSON string
function tryParseJSON(value) {
  if (typeof value === 'string' && (value.startsWith('{') || value.startsWith('['))) {
    try {
      return JSON.parse(value);
    } catch (e) {
      // Return as is if not valid JSON
      return value;
    }
  }
  return value;
}

// Main function
async function main() {
  console.log(`Looking at LevelDB at: ${dbPath}`);
  
  if (!fs.existsSync(dbPath)) {
    console.error(`Database path does not exist: ${dbPath}`);
    return;
  }
  
  try {
    // Open the database with utf8 encoding to avoid parsing errors
    const db = new Level(dbPath, { valueEncoding: 'utf8' });
    
    try {
      await db.open();
      console.log('Successfully opened database');
      
      if (options.key) {
        // Get a specific key
        try {
          const value = await db.get(options.key);
          const parsedValue = tryParseJSON(value);
          console.log('Key:', options.key);
          console.log('Value:', JSON.stringify(parsedValue, null, 2));
        } catch (error) {
          if (error.code === 'LEVEL_NOT_FOUND') {
            console.error(`Key not found: ${options.key}`);
          } else {
            console.error(`Error getting key: ${error.message}`);
          }
        }
      } else if (options.prefix) {
        // Get entries with a prefix
        const entries = [];
        const limit = options.limit ? parseInt(options.limit, 10) : Infinity;
        
        try {
          for await (const [key, value] of db.iterator()) {
            try {
              const keyStr = key.toString();
              
              if (keyStr.startsWith(options.prefix)) {
                const parsedValue = tryParseJSON(value);
                entries.push({ key: keyStr, value: parsedValue });
                
                if (entries.length >= limit) {
                  break;
                }
              }
            } catch (entryError) {
              console.warn(`Skipping entry due to error: ${entryError.message}`);
            }
          }
          
          console.log(`Found ${entries.length} entries with prefix "${options.prefix}":`);
          entries.forEach(entry => {
            console.log(`- ${entry.key}: ${JSON.stringify(entry.value, null, 2)}`);
          });
        } catch (iterError) {
          console.error(`Error iterating over database: ${iterError.message}`);
        }
      } else {
        // List all keys (sample)
        const keys = [];
        const sampleData = {};
        let size = 0;
        
        // Get directory size
        const files = fs.readdirSync(dbPath);
        for (const file of files) {
          const filePath = path.join(dbPath, file);
          if (fs.statSync(filePath).isFile()) {
            size += fs.statSync(filePath).size;
          }
        }
        
        // Sample keys and data
        try {
          const limitKeys = 20; // Only show a sample of keys
          const limitSample = 5; // Only sample a few entries
          let sampleCount = 0;
          
          for await (const [key, value] of db.iterator()) {
            try {
              const keyStr = key.toString();
              keys.push(keyStr);
              
              // Only sample a few entries for display
              if (sampleCount < limitSample) {
                try {
                  sampleData[keyStr] = tryParseJSON(value);
                  sampleCount++;
                } catch (parseError) {
                  sampleData[keyStr] = 'Error: Could not parse value';
                }
              }
              
              if (keys.length >= limitKeys) {
                break;
              }
            } catch (entryError) {
              console.warn(`Skipping entry due to error: ${entryError.message}`);
            }
          }
          
          console.log('Database Information:');
          console.log(`- Size: ${size} bytes`);
          console.log(`- Sample Keys (first ${limitKeys}):`);
          keys.forEach(key => console.log(`  - ${key}`));
          console.log('- Sample Data:');
          console.log(JSON.stringify(sampleData, null, 2));
          
          // Look specifically for any project keys
          let projectKeys = keys.filter(key => key.includes('project'));
          if (projectKeys.length > 0) {
            console.log(`\nFound ${projectKeys.length} project-related keys:`);
            projectKeys.forEach(key => console.log(`  - ${key}`));
          } else {
            console.log('\nNo project-related keys found.');
          }
        } catch (iterError) {
          console.error(`Error iterating over database: ${iterError.message}`);
        }
      }
    } finally {
      await db.close();
      console.log('Database closed');
    }
  } catch (dbError) {
    console.error(`Error opening database: ${dbError.message}`);
  }
}

main().catch(console.error);