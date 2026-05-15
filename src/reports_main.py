import requests
from bs4 import BeautifulSoup
import discord
import json
from time import sleep
from os import getenv
from dotenv import load_dotenv

# MARK: CONFIG
url_test = "https://web.archive.org/web/20251215120022/https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en"
url_test2 = "https://web.archive.org/web/20231118072408/https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en"
url = "https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en.html"

load_dotenv()

WEBHOOK_URL_REPORT=getenv("WEBHOOK_URL_REPORT")
BUFFER_SIZE = 1950 # discord has 2000 limit
ACTUAL_BUFFER_SIZE = 1950 - len(">>> \n")
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

        # Normalize whitespace
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        if len(current_chunk) + len(line) + 1 > max_size:

            if current_chunk:
                chunks.append(current_chunk)

            current_chunk = line

        else:
            if current_chunk:
                current_chunk += "\n" + line
            else:
                current_chunk = line

    # Append final chunk
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
        with open(JSON_FILE_PATH, "r") as f:
            facility = json.load(f)

        facility = replace_text( # formatter likes it this way
            facility,
            "numberssss",
            number
        )

        facility = replace_text(
            facility,
            "datessss",
            event_data["Event Date"]
        )

        facility = replace_text(
            facility,
            "timessss",
            event_data["Event Time"]
        )

        facility = replace_text(
            facility,
            "emssss",
            event_data["Emergency Class"]
        )

        facility = replace_text(
            facility,
            "statessss",
            event_data["State"]
        )

        facility = replace_text(
            facility,
            "cityssss",
            event_data["City"]
        )

        facility = replace_text(
            facility,
            "sectionssss",
            "<unimplemented>"
        )

    except KeyError as e:
        print(f"Malformed event data: missing {e}")
        continue

    parsed_events.append({
        "number": number,
        "embed": facility,
        "chunks": chunks,
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
            print(f"Embed failed: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"Error sending embed: {e}")

    sleep(SLEEP_TIME)

    for chunk in event["chunks"]:

        payload = {
            "content": f">>> {chunk}"
        }

        try:

            response = requests.post(
                WEBHOOK_URL_REPORT,
                json=payload
            )

            if response.status_code == 204:
                print("Chunk sent successfully.")
            else:
                print(f"Chunk failed: {response.status_code}")
                print(response.text)

        except Exception as e:
            print(f"Error sending chunk: {e}")

        sleep(SLEEP_TIME)

# MARK: DEBUG
if not DEBUG:    exit()

with open("nrc_events.txt", "w", encoding="utf-8") as f:
    for i, event in enumerate(odd_text, start=1):
        odd_text = event.get_text("\n", strip=True)

        f.write(f"===== EVENT {i} =====\n")
        f.write(odd_text + "\n\n")