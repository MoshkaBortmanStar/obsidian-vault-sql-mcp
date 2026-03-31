import argparse
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .database import VaultDB

mcp = FastMCP("obsidian-mcp")

_vaults: dict[str, VaultDB] = {}


def _get(vault_name: str) -> VaultDB:
    if vault_name not in _vaults:
        available = list(_vaults.keys())
        raise ValueError(f"Vault '{vault_name}' not configured. Available: {available}")
    return _vaults[vault_name]


# ------------------------------------------------------------------
# Tools
# ------------------------------------------------------------------


@mcp.tool()
def list_vaults() -> dict:
    """List all configured vaults."""
    return {"vaults": list(_vaults.keys())}


@mcp.tool()
def index_vault(vault_name: str) -> dict:
    """
    Scan a vault directory and populate its SQLite database with all .md notes.
    Call this once after first setup, or whenever notes are added/moved outside this server.
    """
    db = _get(vault_name)
    count = db.index_all()
    return {"vault": vault_name, "indexed": count}


@mcp.tool()
def list_notes(vault_name: str) -> dict:
    """List all notes in a vault (reads from SQLite — fast)."""
    db = _get(vault_name)
    return {"vault": vault_name, "notes": db.list_all()}


@mcp.tool()
def search_notes(vault_name: str, query: str) -> dict:
    """
    Search notes by name in SQLite (case-insensitive substring match).
    Returns list of matching notes with their paths.
    """
    db = _get(vault_name)
    results = db.search(query)
    return {"vault": vault_name, "query": query, "results": results, "count": len(results)}


@mcp.tool()
def read_note(vault_name: str, note_name: str) -> dict:
    """
    Find note by name via SQLite and return its full markdown content.
    Supports exact and fuzzy name matching.
    """
    db = _get(vault_name)
    note = db.find_note(note_name)
    if note is None:
        raise ValueError(f"Note '{note_name}' not found in vault '{vault_name}'")
    content = Path(note["absolute_path"]).read_text(encoding="utf-8")
    return {
        "vault": vault_name,
        "name": note["name"],
        "path": note["relative_path"],
        "folder": note["folder"],
        "content": content,
    }


@mcp.tool()
def create_note(vault_name: str, name: str, content: str, folder: str = "") -> dict:
    """
    Create a new .md note and register it in SQLite.
    folder: relative path from vault root, e.g. "projects/2026". Leave empty for root.
    """
    db = _get(vault_name)
    rel = db.create_note(name, content, folder)
    return {"vault": vault_name, "created": name, "path": str(rel).replace("\\", "/")}


@mcp.tool()
def update_note(vault_name: str, note_name: str, content: str) -> dict:
    """
    Overwrite the content of an existing note.
    SQLite last_modified is updated automatically.
    """
    db = _get(vault_name)
    db.update_note(note_name, content)
    return {"vault": vault_name, "updated": note_name}


@mcp.tool()
def move_note(vault_name: str, note_name: str, new_folder: str) -> dict:
    """
    Move a note to a different folder inside the vault.
    SQLite path is updated automatically.
    new_folder: relative path from vault root, e.g. "archive/2025". Empty string = vault root.
    """
    db = _get(vault_name)
    new_path = db.move_note(note_name, new_folder)
    return {
        "vault": vault_name,
        "moved": note_name,
        "new_path": str(new_path).replace("\\", "/"),
    }


@mcp.tool()
def delete_note(vault_name: str, note_name: str) -> dict:
    """Delete a note from disk and remove its record from SQLite."""
    db = _get(vault_name)
    db.delete_note(note_name)
    return {"vault": vault_name, "deleted": note_name}


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="obsidian-mcp",
        description="MCP server for Obsidian vaults with SQLite indexing",
    )
    parser.add_argument(
        "--config",
        metavar="FILE",
        help='Path to JSON config file: {"vaults": {"name": "/path/to/vault"}}',
    )
    parser.add_argument(
        "--vault",
        action="append",
        metavar="NAME=PATH",
        help="Add a vault inline, e.g. --vault personal=/home/user/notes. Can be repeated.",
    )
    args = parser.parse_args()

    vaults: dict[str, str] = {}

    if args.config:
        with open(args.config, encoding="utf-8") as f:
            cfg = json.load(f)
        vaults.update(cfg.get("vaults", {}))

    if args.vault:
        for entry in args.vault:
            if "=" not in entry:
                parser.error(f"--vault must be in NAME=PATH format, got: {entry!r}")
            name, path = entry.split("=", 1)
            vaults[name.strip()] = path.strip()

    if not vaults:
        parser.error("No vaults configured. Use --config FILE or --vault NAME=PATH.")

    for name, path in vaults.items():
        vault_path = Path(path)
        if not vault_path.exists():
            raise SystemExit(f"Vault path does not exist: {path}")
        _vaults[name] = VaultDB(name, vault_path)

    mcp.run()


if __name__ == "__main__":
    main()
