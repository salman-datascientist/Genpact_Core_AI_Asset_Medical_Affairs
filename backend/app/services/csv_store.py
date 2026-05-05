"""CSV persistence with file locking (POSIX). Dynamic CSVs are auto-created on first access."""

from __future__ import annotations

import csv
import fcntl
import io
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# backend/app/services/csv_store.py -> backend/
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = _BACKEND_ROOT / "data"

DYNAMIC_FILES: Dict[str, List[str]] = {
    "iep_requests.csv": [
        "request_id",
        "created_at",
        "updated_at",
        "title",
        "tpp_summary",
        "drug_id",
        "therapy_area_id",
        "geography_id",
        "lifecycle_stage",
        "status",
    ],
    "iep_sections.csv": [
        "section_id",
        "request_id",
        "stage",
        "section_key",
        "content_json",
        "confidence_avg",
    ],
    "reviews.csv": [
        "review_id",
        "request_id",
        "approver",
        "decision",
        "comments",
        "timestamp",
    ],
    "chat_messages.csv": [
        "message_id",
        "request_id",
        "role",
        "content",
        "timestamp",
    ],
}


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for fname, headers in DYNAMIC_FILES.items():
        path = DATA_DIR / fname
        if not path.exists():
            with path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=headers)
                w.writeheader()


@contextmanager
def _locked(path: Path, mode: str):
    ensure_data_dir()
    f = path.open(mode, encoding="utf-8")
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield f
    finally:
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        f.close()


def read_table(name: str) -> List[Dict[str, Any]]:
    """Read a CSV from backend/data (seed or dynamic)."""
    ensure_data_dir()
    path = DATA_DIR / name
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_all_rows(name: str, fieldnames: Iterable[str], rows: List[Dict[str, Any]]) -> None:
    ensure_data_dir()
    path = DATA_DIR / name
    fn = list(fieldnames)
    with _locked(path, "w") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fn})


def append_row(name: str, row: Dict[str, Any]) -> None:
    """Append one row to a dynamic CSV under an exclusive lock."""
    if name not in DYNAMIC_FILES:
        raise KeyError(f"Unknown dynamic table: {name}")
    ensure_data_dir()
    path = DATA_DIR / name
    headers = DYNAMIC_FILES[name]
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        write_all_rows(name, headers, [{k: row.get(k, "") for k in headers}])
        return
    with _locked(path, "r+") as f:
        raw = f.read()
        existing = list(csv.DictReader(io.StringIO(raw))) if raw.strip() else []
        normalized = {k: str(row.get(k, "")) for k in headers}
        existing.append(normalized)
        f.seek(0)
        f.truncate()
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in existing:
            w.writerow({k: r.get(k, "") for k in headers})


def upsert_section(
    request_id: str,
    stage: str,
    section_key: str,
    content_json: str,
    confidence_avg: str = "",
) -> None:
    rows = read_table("iep_sections.csv")
    sid = None
    new_rows: List[Dict[str, Any]] = []
    for r in rows:
        if (
            r.get("request_id") == request_id
            and r.get("stage") == stage
            and r.get("section_key") == section_key
        ):
            sid = r.get("section_id")
            r["content_json"] = content_json
            if confidence_avg:
                r["confidence_avg"] = confidence_avg
        new_rows.append(r)
    if sid is None:
        import uuid

        sid = str(uuid.uuid4())
        new_rows.append(
            {
                "section_id": sid,
                "request_id": request_id,
                "stage": stage,
                "section_key": section_key,
                "content_json": content_json,
                "confidence_avg": confidence_avg or "",
            }
        )
    write_all_rows("iep_sections.csv", DYNAMIC_FILES["iep_sections.csv"], new_rows)


def delete_sections_for_request(request_id: str, stage: Optional[str] = None) -> None:
    rows = read_table("iep_sections.csv")
    kept = [
        r
        for r in rows
        if not (r.get("request_id") == request_id and (stage is None or r.get("stage") == stage))
    ]
    write_all_rows("iep_sections.csv", DYNAMIC_FILES["iep_sections.csv"], kept)


def update_request_row(request_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rows = read_table("iep_requests.csv")
    found = None
    out: List[Dict[str, Any]] = []
    for r in rows:
        if r.get("request_id") == request_id:
            new_r = {**r, **{k: str(v) if v is not None else "" for k, v in updates.items()}}
            found = new_r
            out.append(new_r)
        else:
            out.append(r)
    if found:
        write_all_rows("iep_requests.csv", DYNAMIC_FILES["iep_requests.csv"], out)
    return found


def get_request(request_id: str) -> Optional[Dict[str, Any]]:
    for r in read_table("iep_requests.csv"):
        if r.get("request_id") == request_id:
            return r
    return None
