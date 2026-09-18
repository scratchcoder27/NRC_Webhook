import logging
from logging.handlers import TimedRotatingFileHandler 
# NOTE: might have used RotatingFileHandler instead? This seems better for a time based application like this
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "logs" / "server.log"


def setup_logging():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    handler = TimedRotatingFileHandler(
        LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Avoid adding duplicate handlers if setup_logging() is called twice.
    if not root.handlers:
        root.addHandler(handler)