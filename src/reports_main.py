import requests
from bs4 import BeautifulSoup
import discord
import json
from time import sleep
from os import getenv
from dotenv import load_dotenv
import copy
import colors

# MARK: CONFIG
url_test = "https://web.archive.org/web/20251215120022/https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en"
url_test2 = "https://web.archive.org/web/20231118072408/https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en"
url = "https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en.html"

load_dotenv()

WEBHOOK_URL_REPORT = getenv("WEBHOOK_URL_REPORT")
BUFFER_SIZE = 600 # discord has 1000 limit for embed fields
ACTUAL_BUFFER_SIZE = BUFFER_SIZE # not needed anymore
JSON_FILE_PATH = "src/facility.json"
SLEEP_TIME = 3 # secs prev: 600
DEBUG = True

# MARK: HELPERS
def replace_text(obj, old, new):
    if isinstance(obj, str):
        # Convert special Discord objects to strings automatically
        if isinstance(new, discord.Role):
            new = new.mention
        elif isinstance(new, discord.Member):
            new = new.mention
        else:
            new = str(new)
        return obj.replace(old, new)
    elif isinstance(obj, list):
        return [replace_text(item, old, new) for item in obj]
    elif isinstance(obj, tuple):
        return [replace_text(item, old, new) for item in obj]
    elif isinstance(obj, dict):
        return {key: replace_text(value, old, new) for key, value in obj.items()}
    return obj

# MARK: GET DATA
try:
    response = requests.get(url_test)
    print("Successfully fetched data")
except Exception as e:
    print("Error while getting data: " + e)

if response.status_code != 200:
    print("Error while getting data, recieved status code " + response.status_code)

# MARK: CHUNKER
def chunk_lines(lines, max_size):

    chunks = []
    current_chunk = ""

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # Split oversized individual lines
        while len(line) > max_size:

            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            chunks.append(line[:max_size])
            line = line[max_size:]

        # Normal accumulation
        if len(current_chunk) + len(line) + 1 > max_size:

            if current_chunk:
                chunks.append(current_chunk)

            current_chunk = line

        else:

            if current_chunk:
                current_chunk += "\n" + line
            else:
                current_chunk = line

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


# MARK: PARSING
soup = BeautifulSoup(response.text, "lxml")
all_event = soup.find("div", class_="event-summary number text-center") 
raw_doc_numbers = [anchor.text for anchor in all_event]
doc_numbers=[numbers for numbers in raw_doc_numbers if numbers.isdigit()]
print(doc_numbers)

parsed_events = []

text_blocks = soup.select("div.border")
odd_text = text_blocks[1::2]

try:
    with open(JSON_FILE_PATH, "r") as f:
        schema = json.load(f)
except FileNotFoundError:
    print("The facility.json file does not exist")

for cycle, number in enumerate(doc_numbers):

    print("Processing event no:", number)

    event_data = {}

    processing_event = soup.find(
        "div",
        id=f"en{number}",
        class_="grid border"
    )

    if processing_event is None:
        print(f"Could not find event {number}")
        continue

    # MARK: extract fields
    for field in processing_event.find_all("b"):

        key = field.get_text(strip=True).replace(":", "")

        value = field.next_sibling

        if isinstance(value, str):
            value = value.strip()
        else:
            value = ""

        event_data[key] = value

    # MARK: extract text block
    try:
        text_tag = odd_text[cycle]
    except IndexError:
        print(f"Missing text block for event {number}")
        continue

    text = text_tag.get_text("\n", strip=True)


    chunks = chunk_lines(
        text.splitlines(),
        ACTUAL_BUFFER_SIZE
    )

    # MARK: INTERPRET DATA
    try:
        facility = copy.deepcopy(schema)

        facility = replace_text( # formatter likes it this way
            facility,
            "<number>",
            number
        )

        facility = replace_text(
            facility,
            "<date>",
            event_data["Event Date"]
        )

        facility = replace_text(
            facility,
            "<time>",
            event_data["Event Time"]
        )

        facility = replace_text(
            facility,
            "<personNotified>",
            event_data["NRC Notified By"]
        )

        facility = replace_text(
            facility,
            "<emergencyClass>",
            event_data["Emergency Class"]
        )

        facility = replace_text(
            facility,
            "<state>",
            event_data["State"]
        )

        facility = replace_text(
            facility,
            "<city>",
            event_data["City"]
        )

        facility = replace_text(
            facility,
            "<region>",
            event_data["Region"]
        )

        facility = replace_text(
            facility,
            "<emergencyClass>",
            event_data["Emergency Class"]
        )


        facility = replace_text(
            facility,
            "<section>",
            "<unimplemented>"
        )

    except KeyError as e:
        print(f"Malformed event data: missing {e}")
        continue

    # MARK: INSERT CHUNKS
    embed = facility["embeds"][0]

    if "fields" not in embed:
        embed["fields"] = []

    for index, chunk in enumerate(chunks):

        embed["fields"].append({
            "name": (
                "Event Text"
                if index == 0
                else ""
            ),
            "value": f"```txt\n{chunk}\n```",
            "inline": False
        })

    parsed_events.append({
        "number": number,
        "embed": facility,
        "metadata": event_data
    })


# MARK: SENDING DATA
for event in parsed_events:

    print(f"Sending event {event['number']}")

    # Send embed
    try:
        response = requests.post(
            WEBHOOK_URL_REPORT,
            json=event["embed"]
        )

        if response.status_code == 204:
            print("Embed sent successfully.")
        else:
            print(f"{colors.TERMINAL_RED} Embed failed: {response.status_code} {colors.TERMINAL_RESET}")
            print(response.text)

    except Exception as e:
        print(f"Error sending embed: {e}")

    sleep(SLEEP_TIME)

# MARK: DEBUG
if not DEBUG:    exit()

# with open("nrc_events.txt", "w", encoding="utf-8") as f:
#     for i, event in enumerate(odd_text, start=1):
#         odd_text = event.get_text("\n", strip=True)

#         f.write(f"===== EVENT {i} =====\n")
#         f.write(odd_text + "\n\n")