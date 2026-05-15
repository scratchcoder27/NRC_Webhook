from time import sleep, time
from datetime import date

import requests
import power_parser

from os import getenv
from dotenv import load_dotenv
load_dotenv()

# MARK: GLOBALS

WEBHOOK_URL_POWER = getenv("WEBHOOK_URL_POWER")
WEBHOOK_URL_REPORT = getenv("WEBHOOK_URL_REPORT")

if not WEBHOOK_URL_POWER:
    print("WEBHOOK_URL_POWER not set in .env file.")
    exit()

if not WEBHOOK_URL_REPORT:
    print("WEBHOOK_URL_REPORT not set in .env file.")
    exit()

import colors
print(f'{colors.COLOR_RED}This text is in red{colors.COLOR_RESET}')

POWER_URL = "https://www.nrc.gov/reading-rm/doc-collections/event-status/reactor-status/PowerReactorStatusForLast365Days.txt"
REPORT_URL="https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en.html"

BUFFER_SIZE = 1950 # discord has 2000 limit
WAIT_TIME = 5 #seconds

# MARK: DATA FETCHING
try:
    response = requests.get(POWER_URL)
    # response_report = requests.get(REPORT_URL)

    if response.status_code != 200:
        print(f"Failed to fetch power data: {response.status_code}")
        exit()

    # if response_report.status_code != 200:
    #     print(f"Failed to fetch report data: {response.status_code}")
    #     exit()


except Exception as e:
    print(f"Error fetching data: {e}")
    exit()

print("Data fetched successfully.")

response_lines = [line.strip() for line in response.text.splitlines()]

try:
    today_reports, yesterday_reports = power_parser.parse_data(
        response_lines,
        date.today()
    )
except Exception as e:
    print(f"Error parsing data: {e}")
    exit()

# if response_lines:    del response_lines # free data

# MARK: DATA PREPARATION
HEADER = (
    f"**Reactor Status for {date.today().strftime("%B %d, %Y")}** *(updated: <t:{int(time())}:t>)*"
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

    report_str = report.to_string(changed)

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
try:
    for chunk in buffer:
        payload = {
            "content": chunk
        }

        response = requests.post(WEBHOOK_URL_POWER, json=payload)

        if response.status_code == 204:
            print("Message sent successfully.")
        else:
            print(f"Failed: {response.status_code}")
            print(response.text)

        sleep(WAIT_TIME)
except Exception as e:
    print(f"Error sending message: {e}")

# Parsing report data
