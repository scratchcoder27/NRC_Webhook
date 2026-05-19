#!/bin/bash

set -e

echo " NRC Automation Setup"

# Check for Python
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "Python is not installed."
    echo "Please install Python 3 first."
    exit 1
fi

echo "Using Python: $($PYTHON_CMD --version)"

# venv
read -p "Create virtual environment? (y/n): " CREATE_VENV

if [[ "$CREATE_VENV" =~ ^[Yy]$ ]]; then

    echo "Creating virtual environment..."

    $PYTHON_CMD -m venv .venv

    source .venv/bin/activate

    PYTHON_CMD="$(pwd)/.venv/bin/python"
    PIP_CMD="$(pwd)/.venv/bin/pip"

else

    PIP_CMD="pip3"
fi

# Install requirements
echo "Installing dependencies..."

$PIP_CMD install -r requirements.txt

# Get project directory
PROJECT_DIR="$(pwd)"

POWER_CMD="$PYTHON_CMD $PROJECT_DIR/src/power_main.py"
REPORT_CMD="$PYTHON_CMD $PROJECT_DIR/src/reports_main.py"

# Create cron (timer program) entries
echo "Setting up cron jobs..."

TMP_CRON=$(mktemp)

crontab -l 2>/dev/null > "$TMP_CRON" || true

# Remove old entries
grep -v "power_main.py" "$TMP_CRON" | grep -v "reports_main.py" > "${TMP_CRON}.clean"

mv "${TMP_CRON}.clean" "$TMP_CRON"

# Power report:
# Daily at 01:00 UTC
echo "0 1 * * * cd $PROJECT_DIR && $POWER_CMD >> $PROJECT_DIR/power.log 2>&1" >> "$TMP_CRON"

# Reports:
# Every 6 hours
echo "0 */6 * * * cd $PROJECT_DIR && $REPORT_CMD >> $PROJECT_DIR/reports.log 2>&1" >> "$TMP_CRON"

crontab "$TMP_CRON"

rm "$TMP_CRON"

echo "Setup complete."
echo
echo "Installed cron jobs:"
echo
crontab -l

echo "Remember to create a .env file or set the environment variables `WEBHOOK_URL_POWER` and `WEBHOOK_URL_POWER`"
echo "They can be set either to the url itself, or a comma separated list of urls"

echo "Exiting setup"