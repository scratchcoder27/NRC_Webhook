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
from os import getenv
from dotenv import load_dotenv
from hashlib import sha256

import requests
import power_parser
from sys import argv

import colors
import datamgmt

# MARK: GLOBALS

WEBHOOK_URL_POWER = None
webhook_urls = []
POWER_URL = "https://www.nrc.gov/reading-rm/doc-collections/event-status/reactor-status/PowerReactorStatusForLast365Days.txt"
BUFFER_SIZE = 1970 # discord has 2000 limit
WAIT_TIME = 2 #seconds
TEST_MODE = False

response = None
today_reports = {}
yesterday_reports = {}
current_day = ""
buffer = []

# MARK: CONFIG
def initialize_config():
    global WEBHOOK_URL_POWER, webhook_urls, TEST_MODE
    load_dotenv()

    WEBHOOK_URL_POWER = getenv("WEBHOOK_URL_POWER")
    if not WEBHOOK_URL_POWER:
        print("WEBHOOK_URL_POWER not set in .env file.")
        exit(1)
    
    arg_string = (" ".join(argv)).lower()
    TEST_MODE = (("-test" in arg_string) or ("-t" in arg_string))

    # MARK: GET WEBHOOK URLS
    if "," in WEBHOOK_URL_POWER:
        try:
            for item in WEBHOOK_URL_POWER.split(","):
                webhook_urls.append(item.strip())
        except Exception:
            print("ERROR: Invalid formatting in WEBHOOK_URL_POWER value in environment file")
    else:
        webhook_urls.append(WEBHOOK_URL_POWER)


# MARK: DATA FETCHING & PROCESSING
def fetch_and_process_data():
    global response
    try:
        response = requests.get(POWER_URL)
        if response.status_code != 200:
            print(f"Failed to fetch power data: {response.status_code}")
            exit(1)
    except Exception as e:
        print(f"Error fetching data: {e}")
        exit(1)

    print("Data fetched successfully.")

    response_lines = [line.strip() for line in response.text.splitlines() if line.strip()]
    if not response_lines:
        return sha256(b"", usedforsecurity=False).hexdigest(), []

    header = response_lines[0]
    data_lines_sorted = sorted(response_lines[1:]) # sort it, just in case the data order is flipped
    normalized_content = header + "\n" + "\n".join(data_lines_sorted) # join them again for the hash
    
    curr_hash = sha256(normalized_content.encode('utf-8'), usedforsecurity=False).hexdigest()

    return curr_hash, response_lines


# MARK: PARSING
def parse_data(response_lines):
    global today_reports, yesterday_reports, current_day
    
    try:
        today_reports, yesterday_reports, current_day = power_parser.parse_data(response_lines)
    except Exception as e:
        print(f"Error parsing data: {e}")
        exit(1)


# MARK: DATA PREPARATION
def prepare_data():
    global buffer
    HEADER = (
        f"**Reactor Status for {current_day}** *(updated: <t:{int(time())}:R>)* {"**[TEST MODE]**" if TEST_MODE else ""}"
    )

    buffer = []

    string_payload = (
        HEADER +
        "\n```ansi\n"
    )

    len_string = len(string_payload)

    for plant_name, report in today_reports.items():

        changed = False

        if plant_name in yesterday_reports:
            yesterday_report = yesterday_reports[plant_name]

            if yesterday_report.power != report.power:
                changed = True

        report_str = report.to_string(changed, yesterday_report.power)

        if (len_string + len(report_str) + 1 + 4) > BUFFER_SIZE: # newline + three backticks
            buffer.append(string_payload + "\n```")

            string_payload = "```ansi\n"

            len_string = len(string_payload)

        string_payload += report_str + "\n"
        len_string += len(report_str) + 1

    if string_payload.strip() != "```ansi":
        buffer.append(string_payload + "\n```")


# MARK: DISCORD WEBHOOK
def send_data():
    for url in webhook_urls:
        try:
            for chunk in buffer:
                payload = {
                    "content": chunk
                }

                post_response = requests.post(url, json=payload)

                if post_response.status_code == 204:
                    print("Packet sent successfully.")
                else:
                    print(f"Failed: {post_response.status_code}")
                    print(post_response.text)

                sleep(WAIT_TIME)
        except Exception as e:
            print(f"Error sending message: {e}")


def main(in_memory=False):
    datamgmt.set_in_memory_mode(in_memory)
    initialize_config()
    
    curr_hash, response_lines = fetch_and_process_data()
    
    if not TEST_MODE:
        prev_hash = datamgmt.get_power_data()
        if prev_hash == curr_hash:
            print('No new data')
            return
        
        datamgmt.set_power_data(curr_hash)
        
    parse_data(response_lines)
    
    prepare_data()
    send_data()


if __name__ == "__main__":
    main(False) # was invoked directly or with actions