from datetime import datetime, timedelta, UTC
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent # root folder of the project
STATE_FILE = BASE_DIR / "state.json"

EXPIRY_DAYS = 4

def load_state():
    """
    Load state.json and remove expired entries.
    Returns a dict:
        {
            "12345": "2026-05-18T10:20:00+00:00"
        }
    """

    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
    else:
        state = {}

    cutoff = datetime.now(UTC) - timedelta(days=EXPIRY_DAYS)

    cleaned_state = {
        doc_id: timestamp
        for doc_id, timestamp in state.items()
        if datetime.fromisoformat(timestamp) > cutoff
    }

    return cleaned_state


def save_state(state):
    """
    Save state dict to disk.
    """

    STATE_FILE.write_text(
        json.dumps(state, indent=2)
    )


def add_docs(doc_ids):
    """
    Add multiple document IDs.
    """

    state = load_state()
    timestamp = datetime.now(UTC).isoformat()

    for doc_id in doc_ids:
        state[str(doc_id)] = timestamp

    save_state(state)