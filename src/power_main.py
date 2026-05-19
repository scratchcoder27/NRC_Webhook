"""
    NRC Webhook - Sends nuclear status updates to a discord server
    Copyright (C) 2026, rasa_vlk and scratchcoder27

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

    For any questions, contact the developers on discord or on github
"""

from time import sleep, time
from datetime import date

import requests
import power_parser
import colors

from os import getenv
from dotenv import load_dotenv
load_dotenv()

# MARK: GLOBALS

WEBHOOK_URL_POWER = getenv("WEBHOOK_URL_POWER")
if not WEBHOOK_URL_POWER:
    print("WEBHOOK_URL_POWER not set in .env file.")
    exit()

# MARK: GET WEBHOOK URLS
webhook_urls = []
if "," in WEBHOOK_URL_POWER:
    try:
        for item in WEBHOOK_URL_POWER.split(","):
            webhook_urls.append(item.strip())
    except Exception:
        print("ERROR: Invalid formatting in WEBHOOK_URL_POWER value in environment file")
else:
    webhook_urls.append(WEBHOOK_URL_POWER)

POWER_URL = "https://www.nrc.gov/reading-rm/doc-collections/event-status/reactor-status/PowerReactorStatusForLast365Days.txt"

BUFFER_SIZE = 1950 # discord has 2000 limit
WAIT_TIME = 2 #seconds

# MARK: DATA FETCHING
try:
    response = requests.get(POWER_URL)

    if response.status_code != 200:
        print(f"Failed to fetch power data: {response.status_code}")
        exit()


except Exception as e:
    print(f"Error fetching data: {e}")
    exit()

print("Data fetched successfully.")

response_lines = [line.strip() for line in response.text.splitlines()]

try:
    today_reports, yesterday_reports, current_day = power_parser.parse_data(response_lines)
except Exception as e:
    print(f"Error parsing data: {e}")
    exit()

if response_lines:    del response_lines # free data

# MARK: DATA PREPARATION
HEADER = (
    f"**Reactor Status for {current_day}** *(updated: <t:{int(time())}:R>)*"
)

buffer = []

string_payload = (
    HEADER +
    "\n```ansi\n"
)

len_string = len(string_payload)

first_chunk = True

for plant_name, report in today_reports.items():

    changed = False

    if plant_name in yesterday_reports:
        yesterday_report = yesterday_reports[plant_name]

        if yesterday_report.power != report.power:
            changed = True

    report_str = report.to_string(changed, yesterday_report.power)

    if len_string + len(report_str) + 1 + 4 > BUFFER_SIZE:
        buffer.append(string_payload + "\n```")

        first_chunk = False

        string_payload = "```ansi\n"

        len_string = len(string_payload)

    string_payload += report_str + "\n"
    len_string += len(report_str) + 1

if string_payload.strip() != "```ansi":
    buffer.append(string_payload + "\n```")


# MARK: DISCORD WEBHOOK
for url in webhook_urls:
    try:
        for chunk in buffer:
            payload = {
                "content": chunk
            }

            response = requests.post(url, json=payload)

            if response.status_code == 204:
                print("Packet sent successfully.")
            else:
                print(f"Failed: {response.status_code}")
                print(response.text)

            sleep(WAIT_TIME)
    except Exception as e:
        print(f"Error sending message: {e}")