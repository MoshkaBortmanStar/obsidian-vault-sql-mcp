import shutil
import sqlite3
from pathlib import Path
from typing import Optional

DB_FOLDER = "data-base-sqlite"
DB_FILE = "notes.db"


class VaultDB:
    def __init__(self, name: str, vault_root: Path):
        self.name = name
        self.vault_root = vault_root.resolve()
        self.db_dir = self.vault_root / DB_FOLDER
        self.db_path = self.db_dir / DB_FILE
        self.db_dir.mkdir(exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    name          TEXT    NOT NULL,
                    filename      TEXT    NOT NULL,
                    relative_path TEXT    NOT NULL UNIQUE,
                    absolute_path TEXT    NOT NULL,
                    folder        TEXT    DEFAULT '',
                    last_modified REAL,
                    created_at    REAL    DEFAULT (unixepoch())
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON notes(name)")
            conn.commit()

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index_all(self) -> int:
        """Scan vault root for all .md files and upsert into DB."""
        count = 0
        with self._connect() as conn:
            for md_file in self.vault_root.rglob("*.md"):
                if DB_FOLDER in md_file.parts:
                    continue
                rel = md_file.relative_to(self.vault_root)
                folder = str(rel.parent) if str(rel.parent) != "." else ""
                conn.execute(
                    """
                    INSERT INTO notes (name, filename, relative_path, absolute_path, folder, last_modified)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(relative_path) DO UPDATE SET
                        name          = excluded.name,
                        absolute_path = excluded.absolute_path,
                        folder        = excluded.folder,
                        last_modified = excluded.last_modified
                    """,
                    (
                        md_file.stem,
                        md_file.name,
                        str(rel).replace("\\", "/"),
                        str(md_file),
                        folder,
                        md_file.stat().st_mtime,
                    ),
                )
                count += 1
            conn.commit()
        return count

    # ------------------------------------------------------------------
    # Search / find
    # ------------------------------------------------------------------

    def search(self, query: str) -> list[dict]:
        """Case-insensitive substring search by note name."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, filename, relative_path, folder FROM notes WHERE name LIKE ? ORDER BY name",
                (f"%{query}%",),
            ).fetchall()
        return [dict(r) for r in rows]

    def find_note(self, note_name: str) -> Optional[dict]:
        """Exact match first, then fuzzy. Returns full row or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM notes WHERE name = ? LIMIT 1", (note_name,)
            ).fetchone()
            if row is None:
                row = conn.execute(
                    "SELECT * FROM notes WHERE name LIKE ? LIMIT 1",
                    (f"%{note_name}%",),
                ).fetchone()
        return dict(row) if row else None

    def list_all(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, relative_path, folder FROM notes ORDER BY folder, name"
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def create_note(self, name: str, content: str, folder: str = "") -> Path:
        filename = f"{name}.md"
        if folder:
            note_path = self.vault_root / folder / filename
            note_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            note_path = self.vault_root / filename
        note_path.write_text(content, encoding="utf-8")
        rel = note_path.relative_to(self.vault_root)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO notes (name, filename, relative_path, absolute_path, folder, last_modified)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(relative_path) DO UPDATE SET last_modified = excluded.last_modified
                """,
                (
                    name,
                    filename,
                    str(rel).replace("\\", "/"),
                    str(note_path),
                    folder,
                    note_path.stat().st_mtime,
                ),
            )
            conn.commit()
        return rel

    def update_note(self, note_name: str, content: str) -> None:
        note = self._require(note_name)
        path = Path(note["absolute_path"])
        path.write_text(content, encoding="utf-8")
        with self._connect() as conn:
            conn.execute(
                "UPDATE notes SET last_modified = ? WHERE relative_path = ?",
                (path.stat().st_mtime, note["relative_path"]),
            )
            conn.commit()

    def move_note(self, note_name: str, new_folder: str) -> Path:
        note = self._require(note_name)
        old_path = Path(note["absolute_path"])
        if new_folder:
            new_dir = self.vault_root / new_folder
            new_dir.mkdir(parents=True, exist_ok=True)
            new_path = new_dir / old_path.name
        else:
            new_path = self.vault_root / old_path.name
        shutil.move(str(old_path), str(new_path))
        new_rel = new_path.relative_to(self.vault_root)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE notes
                SET relative_path = ?, absolute_path = ?, folder = ?, last_modified = ?
                WHERE relative_path = ?
                """,
                (
                    str(new_rel).replace("\\", "/"),
                    str(new_path),
                    new_folder,
                    new_path.stat().st_mtime,
                    note["relative_path"],
                ),
            )
            conn.commit()
        return new_rel

    def delete_note(self, note_name: str) -> None:
        note = self._require(note_name)
        Path(note["absolute_path"]).unlink()
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM notes WHERE relative_path = ?", (note["relative_path"],)
            )
            conn.commit()

    # ------------------------------------------------------------------

    def _require(self, note_name: str) -> dict:
        note = self.find_note(note_name)
        if note is None:
            raise ValueError(f"Note '{note_name}' not found in vault '{self.name}'")
        return note
