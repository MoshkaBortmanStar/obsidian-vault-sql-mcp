# obsidian-mcp

MCP server for Obsidian vaults — file-based note management with SQLite indexing.

## Usage

```bash
uvx obsidian-mcp --vault personal=/path/to/vault
# or via config file
uvx obsidian-mcp --config config.json
```

Config file format (`config.json`):
```json
{
  "vaults": {
    "personal": "/path/to/my-vault",
    "work": "/path/to/work-vault"
  }
}
```

## Tools

- `list_vaults` — list configured vaults
- `index_vault(vault_name)` — scan vault and populate SQLite index
- `list_notes(vault_name)` — list all indexed notes
- `search_notes(vault_name, query)` — search notes by name
- `read_note(vault_name, note_name)` — read note content
- `create_note(vault_name, name, content, folder?)` — create note
- `update_note(vault_name, note_name, content)` — update note content
- `move_note(vault_name, note_name, new_folder)` — move note
- `delete_note(vault_name, note_name)` — delete note

## Claude Code config

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uvx",
      "args": ["obsidian-mcp", "--config", "/path/to/config.json"]
    }
  }
}
```
