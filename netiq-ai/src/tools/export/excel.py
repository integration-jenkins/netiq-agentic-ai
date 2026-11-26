"""Memory-efficient OpenPyXL streaming Excel export service with formula-injection protection.

Architecture Role:
------------------
Generates XLSX workbooks exclusively on the backend from verified `VerifiedResult` snapshots:
1. Streaming Write-Only Mode: Uses `openpyxl.Workbook(write_only=True)` to handle large
   telecom inventory datasets with minimal memory overhead.
2. Formula Injection Protection: Sanitizes any string cell starting with `=`, `+`, `-`, `@`,
   tab, or carriage return by prepending a single quote `'`.
3. Metadata Sheet: Always includes a dedicated `Metadata` worksheet recording report name,
   report ID, circle, data version, data date, mode, and applied filters.
4. Sheet Splitting: Automatically splits data rows across numbered worksheets when row
   counts exceed `max_rows_per_sheet`.
5. Safe Temp Storage & Cleanup: Stores exports in a controlled temporary directory, tracks
   ownership metadata, prevents path traversal, and purges expired files.
"""

from __future__ import annotations

import os
import re
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl import Workbook

from src.session.result_store import VerifiedResult
from src.settings.env import PROJECT_ROOT

# Characters that trigger formula evaluation in Excel / Calc
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{4,64}$")
EXCEL_MAX_ROWS_PER_SHEET = 1_000_000


def sanitize_excel_cell(value: Any) -> Any:
    """Neutralize potential spreadsheet formula injection in untrusted text values."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return f"'{value}"
    return value


def sanitize_filename(name: str) -> str:
    """Produce a safe download filename without path separators or special chars."""
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_")
    return clean or "NETIQ_Report"


@dataclass
class ExportedFileRecord:
    """Metadata for a generated Excel export stored on disk."""
    file_id: str
    file_name: str
    file_path: Path
    owner_username: str
    result_id: str
    row_count: int
    created_at: float
    expires_at: float


class ExportSecurityError(Exception):
    """Raised on unauthorized export file access or invalid file identifier."""


class ExportNotFoundError(Exception):
    """Raised when an export file_id does not exist or has expired."""


class ExcelExportService:
    """Generates and manages authorized XLSX exports from verified results."""

    def __init__(
        self,
        export_dir: Path | None = None,
        ttl_seconds: int = 1800,
        max_rows_per_sheet: int = EXCEL_MAX_ROWS_PER_SHEET,
    ) -> None:
        self.export_dir = export_dir or (PROJECT_ROOT / "data" / "exports")
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self.max_rows_per_sheet = max_rows_per_sheet
        self._lock = threading.Lock()
        self._files: dict[str, ExportedFileRecord] = {}

    def cleanup_expired(self) -> int:
        """Remove expired temporary export files from disk and registry."""
        now = time.time()
        removed = 0
        with self._lock:
            expired_ids = [fid for fid, rec in self._files.items() if now > rec.expires_at]
            for fid in expired_ids:
                rec = self._files.pop(fid)
                try:
                    if rec.file_path.is_file():
                        rec.file_path.unlink()
                    removed += 1
                except OSError:
                    pass
        return removed

    def generate_excel(self, result: VerifiedResult) -> ExportedFileRecord:
        """Create an XLSX file in write-only streaming mode from a verified result."""
        self.cleanup_expired()

        file_id = f"file-{uuid.uuid4().hex[:12]}"
        base_label = sanitize_filename(result.report_id or result.report_name or "NETIQ_Export")
        circle_suffix = f"_{sanitize_filename(result.circle)}" if result.circle else ""
        file_name = f"{base_label}{circle_suffix}.xlsx"
        file_path = (self.export_dir / f"{file_id}.xlsx").resolve()

        # Verify resolved path remains inside export_dir (defense in depth)
        if self.export_dir.resolve() not in file_path.parents:
            raise ExportSecurityError("Resolved export path escapes export directory.")

        wb = Workbook(write_only=True)

        # 1. Data sheet(s) with automatic splitting
        columns = result.columns
        headers = [sanitize_excel_cell(col.label or col.field) for col in columns]
        fields = [col.field for col in columns]

        if not fields and result.rows:
            fields = list(result.rows[0].keys())
            headers = [sanitize_excel_cell(k) for k in fields]

        total_rows = len(result.rows)
        chunk_size = max(1, self.max_rows_per_sheet)

        if total_rows == 0:
            ws = wb.create_sheet(title="Data")
            if headers:
                ws.append(headers)
            else:
                ws.append(["Notice"])
                ws.append(["No records matched the query."])
        else:
            num_sheets = (total_rows + chunk_size - 1) // chunk_size
            for sheet_idx in range(num_sheets):
                sheet_title = "Data" if sheet_idx == 0 else f"Data_{sheet_idx + 1}"
                ws = wb.create_sheet(title=sheet_title)
                ws.append(headers)
                start = sheet_idx * chunk_size
                end = min(start + chunk_size, total_rows)
                for row in result.rows[start:end]:
                    ws.append([sanitize_excel_cell(row.get(f)) for f in fields])

        # 2. Metadata provenance sheet
        meta_ws = wb.create_sheet(title="Metadata")
        meta_ws.append(["Property", "Value"])
        meta_rows = [
            ("Report Name", result.report_name or result.report_id or "N/A"),
            ("Report ID", result.report_id or "N/A"),
            ("Domain", result.domain or "N/A"),
            ("Circle", result.circle or "All / Unspecified"),
            ("Data Mode", result.mode),
            ("Data Version", result.data_version or "Unavailable"),
            ("Data Date (Snapshot)", result.data_as_of or "Data date unavailable"),
            ("Applied Filters", str(result.applied_filters)),
            ("Total Exported Records", total_rows),
            ("Result ID", result.result_id),
            ("Exported By", result.owner_username),
            ("Exported At (UTC)", datetime.now(timezone.utc).isoformat()),
        ]
        for k, v in meta_rows:
            meta_ws.append([sanitize_excel_cell(k), sanitize_excel_cell(v)])

        wb.save(str(file_path))

        now = time.time()
        record = ExportedFileRecord(
            file_id=file_id,
            file_name=file_name,
            file_path=file_path,
            owner_username=result.owner_username,
            result_id=result.result_id,
            row_count=total_rows,
            created_at=now,
            expires_at=now + self.ttl_seconds,
        )
        with self._lock:
            self._files[file_id] = record
        return record

    def get_file_record(
        self,
        file_id: str,
        username: str,
        is_admin: bool = False,
    ) -> ExportedFileRecord:
        """Retrieve an export record after validating file_id format and ownership."""
        if not _SAFE_ID_PATTERN.match(file_id):
            raise ExportSecurityError("Invalid export file identifier.")

        self.cleanup_expired()
        with self._lock:
            rec = self._files.get(file_id)

        if not rec or not rec.file_path.is_file():
            raise ExportNotFoundError(f"Export file '{file_id}' not found or has expired.")

        if not is_admin and rec.owner_username != username:
            raise ExportSecurityError(f"User '{username}' is not authorized to download '{file_id}'.")

        return rec


default_excel_export_service = ExcelExportService()
