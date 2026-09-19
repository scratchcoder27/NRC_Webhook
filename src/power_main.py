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

import logging
logger = logging.getLogger(__name__)

# MARK: GLOBALS

WEBHOOK_URL_POWER = None
POWER_URL = "https://www.nrc.gov/reading-rm/doc-collections/event-status/reactor-status/PowerReactorStatusForLast365Days.txt"
BUFFER_SIZE = 1970 # discord has 2000 limit
WAIT_TIME = 2 #seconds
TEST_MODE = False

response = None
today_reports = {}
yesterday_reports = {}
current_day = ""
buffer = []
webhook_urls = []

# MARK: CONFIG
def initialize_config():
    global WEBHOOK_URL_POWER, webhook_urls, TEST_MODE
    load_dotenv()

    WEBHOOK_URL_POWER = getenv("WEBHOOK_URL_POWER")
    if not WEBHOOK_URL_POWER:
        raise Exception("WEBHOOK_URL_POWER not set in .env file.")
    
    argv_lower = [arg.lower() for arg in argv]
    TEST_MODE = ("-test" in argv_lower) or ("-t" in argv_lower)

    # MARK: GET WEBHOOK URLS
    webhook_urls.clear() # if we were running from server_run, this was never cleared, so urls would pile up
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
            
    hash_input = " ".join(
        f"{plant}:{report.date}:{report.time}:{report.plant_name}:{report.power}"
        for plant, report in sorted(today_reports.items())
    ) #could probably have made Report have a __str__ method, which might have been better
    hash_input += " " + str(current_day)

    curr_hash = sha256(hash_input.encode("UTF-8")).hexdigest()

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
                    logging.debug("Packet sent successfully.")
                else:
                    logging.error(f"Failed: {post_response.status_code}")
                    logging.error(post_response.text)

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
    
    prepare_data()
    send_data()

    if not TEST_MODE:
        datamgmt.set_power_data(curr_hash) # NOTE: if chnk 1 succeeds, while chnk2 fails, both will be resent next time

if __name__ == "__main__":
    try:
        main(False) # was invoked directly or with actions
    except Exception as e:
        print(f"{colors.TERMINAL_RED}ERROR: {e}{colors.TERMINAL_RESET}")
        logging.exception("Error in Power main script")
        exit(1)