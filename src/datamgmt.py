from datetime import datetime, timedelta, UTC
from pathlib import Path
import json
import os
from threading import Lock

# MARK: GLOBALS

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "state.json"

EXPIRY_DAYS = 4

_IN_MEMORY_MODE = False
_MEMORY_STATE = None
_IS_DIRTY = False
_STATE_LOCK = Lock()

DEFAULT_STATE = {
    "powerData": None,
    "reportsData": {},
}

# MARK: READ
def _read_file_from_disk() -> dict:
    if not STATE_FILE.exists():
        return DEFAULT_STATE.copy()

    try:
        with open(STATE_FILE, 'r') as f:
            full_state = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"{STATE_FILE} contains invalid JSON and was not loaded"
        ) from e # good for more helpful traces

    if not isinstance(full_state, dict):
        raise RuntimeError(f"{STATE_FILE} does not contain a JSON object")

    full_state.setdefault("powerData", None)
    full_state.setdefault("reportsData", {})

    if not isinstance(full_state["reportsData"], dict):
        raise RuntimeError("state.json: reportsData is not a dictionary")

    return full_state

# MARK: MEM AND ATOM
def set_in_memory_mode(enabled: bool) -> None:
    global _IN_MEMORY_MODE, _MEMORY_STATE

    with _STATE_LOCK:
        if enabled and not _IN_MEMORY_MODE:
            _MEMORY_STATE = _read_file_from_disk()

        elif not enabled and _IN_MEMORY_MODE:
            _save_memory_to_disk_locked()
            _MEMORY_STATE = None

        _IN_MEMORY_MODE = enabled


def _save_memory_to_disk_locked() -> None:
    global _IS_DIRTY

    if (_MEMORY_STATE is None) or not _IS_DIRTY:
        return

    _atomic_write(_MEMORY_STATE)
    _IS_DIRTY = False


def save_memory_to_disk() -> None:
    with _STATE_LOCK:
        _save_memory_to_disk_locked()

def _atomic_write(full_state: dict) -> None:
    temp_file = STATE_FILE.with_suffix(".json.tmp") # rare case where server could crash while writing

    data = json.dumps(full_state, indent=2)

    temp_file.write_text(data)
    os.replace(temp_file, STATE_FILE)


def _get_state_locked() -> dict:
    if _IN_MEMORY_MODE:
        if _MEMORY_STATE is None:
            raise RuntimeError("In-memory mode enabled but memory state is None")
        return _MEMORY_STATE

    return _read_file_from_disk()


def _mark_dirty_locked(): # just to make code nicer
    global _IS_DIRTY
    _IS_DIRTY = True


def _write_state_locked(full_state: dict) -> None:
    if _IN_MEMORY_MODE:
        _mark_dirty_locked()
    else:
        _atomic_write(full_state)

# MARK: LOAD STATE
def load_state() -> dict:
    """
    Return a copy of the current reportsData, with expired entries removed.
    """
    global _IS_DIRTY

    with _STATE_LOCK:
        full_state = _get_state_locked()
        reports = full_state["reportsData"]

        cutoff = datetime.now(UTC) - timedelta(days=EXPIRY_DAYS)

        cleaned_reports = {
            doc_id: timestamp
            for doc_id, timestamp in reports.items()
            if datetime.fromisoformat(timestamp) > cutoff # python generators are nice
        }

        if len(cleaned_reports) != len(reports):
            full_state["reportsData"] = cleaned_reports
            _write_state_locked(full_state)

        return cleaned_reports.copy()

# MARK: ADD DOCS
def add_docs(doc_ids) -> None:
    """
    Add document ids to reportsData.
    """
    if not doc_ids:
        return

    with _STATE_LOCK:
        full_state = _get_state_locked()
        reports = full_state["reportsData"]

        timestamp = datetime.now(UTC).isoformat()

        for doc_id in doc_ids:
            reports[str(doc_id)] = timestamp

        _write_state_locked(full_state)

# MARK: POWER DATA
def set_power_data(power_string) -> None:
    """
    Overwrites the powerData string with a new custom string. (Now with the power of the atom)
    """
    with _STATE_LOCK:
        full_state = _get_state_locked()
        full_state["powerData"] = str(power_string)
        _write_state_locked(full_state)


def get_power_data():
    """
    Returns the powerData string value.
    """
    with _STATE_LOCK:
        full_state = _get_state_locked()
        return full_state["powerData"]