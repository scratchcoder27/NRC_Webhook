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


def has_doc(doc_id):
    """
    Check if document already exists in state.
    """

    state = load_state()
    return str(doc_id) in state


def add_doc(doc_id):
    """
    Add/update a document with current timestamp.
    """

    state = load_state()

    state[str(doc_id)] = datetime.now(UTC).isoformat()

    save_state(state)


def remove_doc(doc_id):
    """
    Remove a document from state.
    """

    state = load_state()

    state.pop(str(doc_id), None)

    save_state(state)


def add_docs(doc_ids):
    """
    Add multiple document IDs.
    """

    state = load_state()
    timestamp = datetime.now(UTC).isoformat()

    for doc_id in doc_ids:
        state[str(doc_id)] = timestamp

    save_state(state)


def get_new_docs(doc_ids):
    """
    Return only docs not already stored.
    """

    state = load_state()

    return [
        doc_id
        for doc_id in doc_ids
        if str(doc_id) not in state
    ]