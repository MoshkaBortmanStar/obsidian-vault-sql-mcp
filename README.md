# obsidian-vault-sql-mcp

MCP server for [Obsidian](https://obsidian.md) vaults. Works directly with `.md` files on disk — no Obsidian app needed. Each vault gets its own SQLite index for fast note lookup by name.

## How it works

```
your-vault/
├── notes/
│   └── my-note.md
├── projects/
│   └── project-alpha.md
└── data-base-sqlite/       ← created automatically
    └── notes.db            ← SQLite index (name → path)
```

When you call `index_vault`, the server scans all `.md` files and stores their names and paths in SQLite. After that, finding a note by name is instant — no directory traversal needed. When you create, move or delete notes through the server, the index updates automatically.

Multiple vaults are supported — each has its own database inside it.

---

## Installation

Requires [uv](https://docs.astral.sh/uv/) installed.

```bash
uvx obsidian-vault-sql-mcp --help
```

No manual install needed — `uvx` handles everything on first run.

---

## Configuration

### Option A — inline vaults

```bash
uvx obsidian-vault-sql-mcp --vault personal=/path/to/my-vault --vault work=/path/to/work-vault
```

### Option B — config file

Create `config.json`:

```json
{
  "vaults": {
    "personal": "/path/to/my-vault",
    "work": "/path/to/work-vault"
  }
}
```

```bash
uvx obsidian-vault-sql-mcp --config /path/to/config.json
```

---

## Claude Code setup

Add to your Claude Code MCP settings (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uvx",
      "args": [
        "obsidian-vault-sql-mcp",
        "--config", "/path/to/config.json"
      ]
    }
  }
}
```

Or with inline vaults:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uvx",
      "args": [
        "obsidian-vault-sql-mcp",
        "--vault", "personal=C:/Users/you/Documents/MyVault"
      ]
    }
  }
}
```

---

## Tools

| Tool | Description |
|------|-------------|
| `list_vaults()` | List all configured vault names |
| `index_vault(vault_name)` | Scan vault and build/update SQLite index |
| `list_notes(vault_name)` | List all indexed notes |
| `search_notes(vault_name, query)` | Search notes by name (case-insensitive substring) |
| `read_note(vault_name, note_name)` | Read note content (exact or fuzzy name match) |
| `create_note(vault_name, name, content, folder?)` | Create a new `.md` note |
| `update_note(vault_name, note_name, content)` | Overwrite note content |
| `move_note(vault_name, note_name, new_folder)` | Move note to a different folder |
| `delete_note(vault_name, note_name)` | Delete note from disk and index |

---

## First-time setup

1. Start the server with your vault path
2. Call `index_vault("personal")` once — this scans all existing notes
3. Done — all other tools work immediately

After that, `index_vault` only needs to be called again if you add/move notes **outside** this server (e.g. manually in Obsidian).

---

## Example usage

```
search_notes("personal", "yandex")
→ [{ "name": "conspect-yandex-tracker", "relative_path": "notes/conspect-yandex-tracker.md" }]

read_note("personal", "conspect-yandex-tracker")
→ { "content": "# Конспект Yandex Tracker\n..." }

create_note("personal", "new-idea", "# New Idea\nText here", "inbox")
→ { "path": "inbox/new-idea.md" }

move_note("personal", "new-idea", "projects/2026")
→ { "new_path": "projects/2026/new-idea.md" }
```

---

## License

MIT
