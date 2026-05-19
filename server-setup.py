#!/usr/bin/env python3

import shutil
import subprocess
import sys
from pathlib import Path

# MARK: Helpers

def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def run(cmd, check=True):
    print(f"\n> {' '.join(cmd)}")
    subprocess.run(cmd, check=check)


# MARK: Header

print(" NRC-Webhook Setup")

# MARK: Check Python

python_cmd = shutil.which("python3") or shutil.which("python")

if not python_cmd:
    print("Python is not installed.")
    sys.exit(1)

print(f"Using Python: {python_cmd}")

# MARK: Check crontab

if not command_exists("crontab"):
    print("\nERROR: crontab is not installed.")
    print("Install cron support first.\n")

    print("Arch Linux:")
    print("  sudo pacman -S cronie")
    print("  sudo systemctl enable --now cronie\n")

    print("Ubuntu/Debian:")
    print("  sudo apt install cron\n")

    sys.exit(1)

# MARK: Optional venv

create_venv = input(
    "\nCreate virtual environment? (y/n): "
).strip().lower()

project_dir = Path.cwd()

if create_venv == "y":

    print("\nCreating virtual environment...")

    run([python_cmd, "-m", "venv", ".venv"])

    python_cmd = str(project_dir / ".venv" / "bin" / "python")

# MARK: Install requirements

print("\nInstalling dependencies...")

run([
    python_cmd,
    "-m",
    "pip",
    "install",
    "-r",
    "requirements.txt"
])

# MARK: Cron setup

power_cmd = (
    f"cd {project_dir} && "
    f"{python_cmd} {project_dir}/src/power_main.py "
    f">> {project_dir}/power.log 2>&1"
)

report_cmd = (
    f"cd {project_dir} && "
    f"{python_cmd} {project_dir}/src/reports_main.py "
    f">> {project_dir}/reports.log 2>&1"
)

print("\nSetting up cron jobs...")

try:
    existing_cron = subprocess.check_output(
        ["crontab", "-l"],
        text=True,
        stderr=subprocess.DEVNULL
    )
except subprocess.CalledProcessError:
    existing_cron = ""

# Remove old entries
filtered_lines = []

for line in existing_cron.splitlines():
    if (
        "power_main.py" not in line
        and "reports_main.py" not in line
    ):
        filtered_lines.append(line)

# MARK: Add new jobs

# Power:
# Daily at 01:00 UTC
filtered_lines.append(
    f"0 1 * * * {power_cmd}"
)

# Reports:
# Every 6 hours
filtered_lines.append(
    f"0 */6 * * * {report_cmd}"
)

new_cron = "\n".join(filtered_lines) + "\n"

proc = subprocess.run(
    ["crontab", "-"],
    input=new_cron,
    text=True,
    check=True
)

# MARK: Finish

print("Setup complete.")

print("\nInstalled cron jobs:\n")

run(["crontab", "-l"])

print(
    "\nRemember to create environment variables:\n"
)

print("WEBHOOK_URL_POWER")
print("WEBHOOK_URL_REPORT")

print(
    "\nThey may contain either:"
)

print("- a single URL")
print("- or a comma-separated list of URLs")

print("\nDone.")