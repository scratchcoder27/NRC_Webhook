from datetime import datetime, timedelta, UTC
from pathlib import Path
import json
from threading import Lock

BASE_DIR = Path(__file__).resolve().parent.parent  # root folder of the project
STATE_FILE = BASE_DIR / "state.json"

EXPIRY_DAYS = 4

_IN_MEMORY_MODE = False
_MEMORY_STATE = None
_IS_DIRTY = False
_STATE_LOCK = Lock()


def set_in_memory_mode(enabled: bool):
    global _IN_MEMORY_MODE, _MEMORY_STATE
    with _STATE_LOCK:
        _IN_MEMORY_MODE = enabled
        if _IN_MEMORY_MODE and _MEMORY_STATE is None:
            _MEMORY_STATE = _read_file_from_disk() # memory state is empty, so we use the saved file


def save_memory_to_disk():
    global _MEMORY_STATE, _IS_DIRTY
    with _STATE_LOCK:
        if _MEMORY_STATE is not None and _IS_DIRTY:
            STATE_FILE.write_text(json.dumps(_MEMORY_STATE, indent=2))
            _IS_DIRTY = False


def _read_file_from_disk():
    if STATE_FILE.exists():
        try:
            full_state = json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            full_state = {}
    else:
        full_state = {} # we "reset" the json file

    if "powerData" not in full_state:
        full_state["powerData"] = None 
    if "reportsData" not in full_state:
        full_state["reportsData"] = {}
        
    return full_state


def _read_file():
    if _IN_MEMORY_MODE:
        return _MEMORY_STATE
    return _read_file_from_disk()


def _write_file(full_state):
    if _IN_MEMORY_MODE:
        return
    STATE_FILE.write_text(json.dumps(full_state, indent=2)) # to improve debugging


def load_state():
    """
    Load state.json, clean expired report entries, and save the changes.
    Returns *ONLY* the reportsData dict:
        {
            "12345": "2026-05-18T10:20:00+00:00"
        }
    """
    global _IS_DIRTY
    with _STATE_LOCK:
        full_state = _read_file()
        reports = full_state["reportsData"]

        cutoff = datetime.now(UTC) - timedelta(days=EXPIRY_DAYS)
        
        cleaned_reports = {
            doc_id: timestamp
            for doc_id, timestamp in reports.items()
            if datetime.fromisoformat(timestamp) > cutoff
        }

        # If we filtered anything out, save the cleaned state back to disk
        if len(cleaned_reports) != len(reports):
            full_state["reportsData"] = cleaned_reports
            if _IN_MEMORY_MODE:
                _IS_DIRTY = True
            else:
                _write_file(full_state)

        return cleaned_reports


def save_state(reports_data):
    """
    Save the reportsData dict back into the main state file.
    """
    global _IS_DIRTY
    with _STATE_LOCK:
        full_state = _read_file()
        full_state["reportsData"] = reports_data
        if _IN_MEMORY_MODE:
            _IS_DIRTY = True
        else:
            _write_file(full_state)


def add_docs(doc_ids):
    """
    Add multiple document IDs to reportsData.
    """
    reports_data = load_state()
    timestamp = datetime.now(UTC).isoformat()

    for doc_id in doc_ids:
        reports_data[str(doc_id)] = timestamp

    save_state(reports_data)


def set_power_data(power_string):
    """
    Overwrites the powerData string with a new custom string.
    """
    global _IS_DIRTY
    with _STATE_LOCK:
        full_state = _read_file()
        full_state["powerData"] = str(power_string) 
        if _IN_MEMORY_MODE:
            _IS_DIRTY = True
        else:
            _write_file(full_state)


def get_power_data():
    """
    Returns the powerData string value.
    """
    with _STATE_LOCK:
        full_state = _read_file()
        return full_state["powerData"]