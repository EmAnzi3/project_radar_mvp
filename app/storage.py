from pathlib import Path
import json
import sqlite3
from datetime import datetime
from typing import Iterable

from app.config import BASE_DIR, DATABASE_URL
from app.models import ProjectRecord


def _sqlite_path() -> Path:
    url = DATABASE_URL

    if url.startswith("sqlite:///"):
        raw = url.replace("sqlite:///", "", 1)
        path = Path(raw)

        if not path.is_absolute():
            path = BASE_DIR / path

        return path

    return BASE_DIR / "data" / "project_radar.sqlite"


DB_PATH = _sqlite_path()


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS records (
            external_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            cup TEXT,
            title TEXT,
            category TEXT,
            region TEXT,
            province TEXT,
            municipality TEXT,
            client TEXT,
            estimated_value_eur REAL,
            commercial_score INTEGER,
            is_active INTEGER NOT NULL DEFAULT 1,
            first_seen TEXT,
            last_seen TEXT,
            last_run_id TEXT,
            payload_json TEXT NOT NULL
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS source_files (
            source TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            signature TEXT NOT NULL,
            processed_at TEXT NOT NULL,
            PRIMARY KEY (source, file_name)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            total_records INTEGER DEFAULT 0,
            note TEXT
        )
        """)

        conn.commit()


def file_signature(path: Path) -> dict:
    stat = path.stat()
    signature = f"{path.name}|{stat.st_size}|{stat.st_mtime_ns}"

    return {
        "file_name": path.name,
        "file_path": str(path.resolve()),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "signature": signature,
    }


def collect_source_file_signatures(source: str, folder: Path) -> list[dict]:
    files = sorted(folder.glob("*.zip")) + sorted(folder.glob("*.csv"))
    return [file_signature(p) for p in files]


def source_is_unchanged(source: str, current_files: list[dict]) -> bool:
    init_db()

    if not current_files:
        return False

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT file_name, signature FROM source_files WHERE source = ?",
            (source,),
        ).fetchall()

    previous = {r["file_name"]: r["signature"] for r in rows}
    current = {f["file_name"]: f["signature"] for f in current_files}

    return previous == current


def save_source_file_signatures(source: str, files: list[dict]) -> None:
    init_db()
    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute("DELETE FROM source_files WHERE source = ?", (source,))

        for f in files:
            conn.execute(
                """
                INSERT INTO source_files (
                    source, file_name, file_path, size_bytes, mtime_ns, signature, processed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source,
                    f["file_name"],
                    f["file_path"],
                    f["size_bytes"],
                    f["mtime_ns"],
                    f["signature"],
                    now,
                ),
            )

        conn.commit()


def start_run(source: str, note: str | None = None) -> str:
    init_db()
    run_id = datetime.now().strftime("%Y%m%d%H%M%S")
    started_at = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO runs (run_id, source, started_at, note)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, source, started_at, note),
        )
        conn.commit()

    return run_id


def finish_run(run_id: str, total_records: int) -> None:
    completed_at = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE runs
            SET completed_at = ?, total_records = ?
            WHERE run_id = ?
            """,
            (completed_at, total_records, run_id),
        )
        conn.commit()


def save_records(records: Iterable[ProjectRecord], source: str, run_id: str) -> int:
    init_db()
    now = datetime.now().isoformat(timespec="seconds")

    records = list(records)

    with get_connection() as conn:
        # Se stiamo processando un dataset completo, prima marchiamo tutto come non attivo.
        # I record presenti nel nuovo dataset verranno rimessi attivi sotto.
        conn.execute(
            "UPDATE records SET is_active = 0 WHERE source = ?",
            (source,),
        )

        for r in records:
            external_id = r.external_id or r.cup or f"{r.source}:{r.title}"

            previous = conn.execute(
                "SELECT first_seen FROM records WHERE external_id = ?",
                (external_id,),
            ).fetchone()

            first_seen = previous["first_seen"] if previous else (r.first_seen or now)
            r.first_seen = first_seen
            r.last_seen = now

            payload = json.dumps(r.model_dump(), ensure_ascii=False)

            conn.execute(
                """
                INSERT INTO records (
                    external_id,
                    source,
                    cup,
                    title,
                    category,
                    region,
                    province,
                    municipality,
                    client,
                    estimated_value_eur,
                    commercial_score,
                    is_active,
                    first_seen,
                    last_seen,
                    last_run_id,
                    payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                ON CONFLICT(external_id) DO UPDATE SET
                    source = excluded.source,
                    cup = excluded.cup,
                    title = excluded.title,
                    category = excluded.category,
                    region = excluded.region,
                    province = excluded.province,
                    municipality = excluded.municipality,
                    client = excluded.client,
                    estimated_value_eur = excluded.estimated_value_eur,
                    commercial_score = excluded.commercial_score,
                    is_active = 1,
                    last_seen = excluded.last_seen,
                    last_run_id = excluded.last_run_id,
                    payload_json = excluded.payload_json
                """,
                (
                    external_id,
                    source,
                    r.cup,
                    r.title,
                    r.category,
                    r.region,
                    r.province,
                    r.municipality,
                    r.client,
                    r.estimated_value_eur,
                    r.commercial_score,
                    first_seen,
                    now,
                    run_id,
                    payload,
                ),
            )

        conn.commit()

    return len(records)


def load_records(
    source: str = "OpenCUP",
    limit: int = 120,
    only_active: bool = True,
) -> list[ProjectRecord]:
    init_db()

    where = "WHERE source = ?"
    params: list = [source]

    if only_active:
        where += " AND is_active = 1"

    sql = f"""
    SELECT payload_json
    FROM records
    {where}
    ORDER BY
        commercial_score DESC,
        estimated_value_eur DESC,
        last_seen DESC
    LIMIT ?
    """

    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    out: list[ProjectRecord] = []

    for row in rows:
        data = json.loads(row["payload_json"])
        out.append(ProjectRecord(**data))

    return out


def count_records(source: str = "OpenCUP", only_active: bool = True) -> int:
    init_db()

    where = "WHERE source = ?"
    params: list = [source]

    if only_active:
        where += " AND is_active = 1"

    with get_connection() as conn:
        row = conn.execute(
            f"SELECT COUNT(*) AS n FROM records {where}",
            params,
        ).fetchone()

    return int(row["n"] or 0)
