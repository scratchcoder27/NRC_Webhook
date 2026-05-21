from datetime import datetime, timedelta, UTC
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent  # root folder of the project
STATE_FILE = BASE_DIR / "state.json"

EXPIRY_DAYS = 4

def _read_file():
    if STATE_FILE.exists():
        try:
            full_state = json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            full_state = {}
    else:
        full_state = {}

    if "powerData" not in full_state:
        full_state["powerData"] = None 
    if "reportsData" not in full_state:
        full_state["reportsData"] = {}
        
    return full_state


def load_state():
    """
    Load state.json, clean expired report entries, and save the changes.
    Returns ONLY the reportsData dict:
        {
            "12345": "2026-05-18T10:20:00+00:00"
        }
    """
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
        STATE_FILE.write_text(json.dumps(full_state, indent=2))

    return cleaned_reports


def save_state(reports_data):
    """
    Save the reportsData dict back into the main state file.
    """
    full_state = _read_file()
    full_state["reportsData"] = reports_data
    STATE_FILE.write_text(json.dumps(full_state, indent=2))


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
    full_state = _read_file()
    full_state["powerData"] = str(power_string) 
    STATE_FILE.write_text(json.dumps(full_state, indent=2))


def get_power_data():
    """
    Returns the powerData string value.
    """
    full_state = _read_file()
    return full_state["powerData"]