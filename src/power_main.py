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
        raise Exception("WEBHOOK_URL_POWER not set in .env file.")
    
    arg_string = (" ".join(argv)).lower()
    TEST_MODE = (("-test" in arg_string) or ("-t" in arg_string))

    # MARK: GET WEBHOOK URLS
    if "," in WEBHOOK_URL_POWER:
        try:
            for item in WEBHOOK_URL_POWER.split(","):
                webhook_urls.append(item.strip())
        except Exception:
            raise Exception("Invalid formatting in WEBHOOK_URL_POWER value in environment file")
    else:
        webhook_urls.append(WEBHOOK_URL_POWER)


# MARK: DATA FETCHING & PROCESSING
def fetch_and_process_data():
    global response
    try:
        response = requests.get(POWER_URL)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch power data: {response.status_code}")
    except Exception as e:
        raise Exception(f"Error fetching data: {e}")

    print("Data fetched successfully.")
    
    response_lines = [line.strip() for line in response.text.splitlines() if line.strip()]    

    return response_lines


# MARK: PARSING
def parse_data(response_lines) -> str:
    global today_reports, yesterday_reports, current_day
    
    try:
        today_reports, yesterday_reports, current_day = power_parser.parse_data(response_lines)
    except Exception as e:
        raise Exception(f"Error parsing data: {e}")
            
    curr_hash = sha256((" ".join(sorted(today_reports)) + " " + str(current_day)).encode('UTF-8')).hexdigest()
    return curr_hash


# MARK: DATA PREPARATION
def prepare_data():
    global buffer
    HEADER = (
        f"**Reactor Status for {current_day}** *(updated: <t:{int(time())}:R>)*"
    )

    if TEST_MODE:
        HEADER += " **[TEST MODE]**"

    buffer = []

    string_payload = (
        HEADER +
        "\n```ansi\n"
    )

    len_string = len(string_payload)

    for plant_name, report in today_reports.items():

        changed = False
        yesterday_power = report.power  # default: no prior data means "no change"

        if plant_name in yesterday_reports:
            yesterday_power = yesterday_reports[plant_name].power
            if yesterday_power != report.power:
                changed = True

        report_str = report.to_string(changed, yesterday_power)

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
            raise Exception(f"Error sending message: {e}")


def main(in_memory=False):
    datamgmt.set_in_memory_mode(in_memory)
    initialize_config()
    
    response_lines = fetch_and_process_data()
    curr_hash = parse_data(response_lines)
    
    if not TEST_MODE:
        prev_hash = datamgmt.get_power_data()
        if prev_hash == curr_hash:
            print('No new data')
            return
        
        datamgmt.set_power_data(curr_hash)
    
    prepare_data()
    send_data()


if __name__ == "__main__":
    try:
        main(False) # was invoked directly or with actions
    except Exception as e:
        print(f"{colors.TERMINAL_RED}ERROR: {e}{colors.TERMINAL_RESET}")
        exit(1)