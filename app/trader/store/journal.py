import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from zoneinfo import ZoneInfo


class Journal:
    """JSONL-based audit trail for trades, skips, and verdicts."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _encode(self, obj):
        """Custom JSON encoder for Decimal, Enum, and datetime."""
        if isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, Enum):
            return obj.name
        elif isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    def log(self, kind: str, payload: dict, day: date | None = None) -> None:
        """Append a log entry to the daily JSONL file.

        Args:
            kind: Log entry kind (e.g., "trade_open", "skip", "verdict")
            payload: Dictionary of data to log
            day: Date for the file; defaults to today
        """
        if day is None:
            day = date.today()

        # Prepare entry with timestamp and kind
        entry = {"ts": datetime.now(ZoneInfo("UTC")).isoformat(), "kind": kind, **payload}

        # Determine file path
        file_path = self.root / f"{day.isoformat()}.jsonl"

        # Append to file in append mode
        with open(file_path, "a") as f:
            f.write(json.dumps(entry, default=self._encode) + "\n")

    def read(self, day: date) -> list[dict]:
        """Read all log entries for a given day.

        Args:
            day: Date to read entries for

        Returns:
            List of entry dictionaries; empty list if file doesn't exist
        """
        file_path = self.root / f"{day.isoformat()}.jsonl"

        if not file_path.exists():
            return []

        entries = []
        with open(file_path, "r") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))

        return entries
