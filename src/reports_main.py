from re import findall as re_findall
import requests
from bs4 import BeautifulSoup
import discord
import json
from time import sleep
from os import getenv
from dotenv import load_dotenv
from copy import deepcopy
from sys import exit

import colors

# MARK: CONFIG
url_test = "https://web.archive.org/web/20251215120022/https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en"
url_test2 = "https://web.archive.org/web/20231118072408/https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en"
url_test_reactor = "https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2026/20260102en"
url = "https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en.html"

URL = url_test_reactor

load_dotenv()
is_reactor_report = False

WEBHOOK_URL_REPORT = getenv("WEBHOOK_URL_REPORT")
BUFFER_SIZE = 950 # discord has 1000 limit for embed fields
SLEEP_TIME = 3 # secs
# DEBUG = False
IS_GITHUB_ACTIONS = True

if IS_GITHUB_ACTIONS:
    import datamgmt

try:
    with open("facility_schema.json", "r") as f:
        facility_schema_str = f.read()
except FileNotFoundError:
    print("The facility report schema file does not exist")

try:
    with open("plant_schema.json", "r") as f:
        plant_schema_str = f.read()
except FileNotFoundError:
    print("The plant report schema file does not exist")


# MARK: GET WEBHOOK URLS
webhook_urls = []
if "," in WEBHOOK_URL_REPORT:
    try:
        for item in WEBHOOK_URL_REPORT.split(","):
            webhook_urls.append(item.strip())
    except Exception:
        print("ERROR: Invalid formatting in WEBHOOK_URL_REPORT value in environment file")
else:
    webhook_urls.append(WEBHOOK_URL_REPORT)

# MARK: HELPERS

def format_table(data: list) -> str:
    headers = ["Unit", "SCRAM", "RX Crit", "Init PWR", "Curr PWR"]
    widths = [4, 5, 7, 8, 8]
    
    top_border    = "┌" + "┬".join("─" * w for w in widths) + "┐"
    header_sep    = "├" + "┼".join("─" * w for w in widths) + "┤"
    bottom_border = "└" + "┴".join("─" * w for w in widths) + "┘"

    header_cells = [f"{headers[i]:^{widths[i]-2}}" for i in range(len(headers))] # header
    header_row   = "│" + "│".join(header_cells) + "│"
    table_lines = [top_border, header_row, header_sep]

    for row in data:
        filtered_row = [row[0], row[1], row[2], row[3], row[4]]
        
        if len(filtered_row) != len(headers):
            return f"Error: Expected {len(headers)} columns of data, got {len(filtered_row)}."
        
        data_cells = [f" {filtered_row[i]:<{widths[i]-2}} " for i in range(len(filtered_row))]
        data_row   = "│" + "│".join(data_cells) + "│"
        table_lines.append(data_row)

    table_lines.append(bottom_border)
    return "\\n".join(table_lines)


# MARK: GET DATA
try:
    print("Fetching data...")
    response = requests.get(URL)
    print("Successfully fetched data")
except Exception as e:
    print("Error while getting data: " + e)

if response.status_code != 200:
    print("Error while getting data, recieved status code " + response.status_code)
    exit()

# MARK: PREPROCESS
# quick and fast way to just get the doc numbers, without having to parse the entire code
doc_numbers = re_findall(
    r'<div[^>]*class="grid border"[^>]*id="en(\d+)"[^>]*>',
    response.text
)

if IS_GITHUB_ACTIONS:
    pass


# MARK: CHUNKER
def chunk_lines(lines, max_size):
    chunks = []
    current_chunk = []
    current_length = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Split oversized individual lines
        while len(line) > max_size:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            chunks.append(line[:max_size])
            line = line[max_size:]

        # Normal accumulation
        if current_length + len(line) + 1 > max_size:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_length = len(line)
        else:
            current_chunk.append(line)
            current_length += len(line) + 1 # +1 for the newline

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks

# MARK: PARSING
soup = BeautifulSoup(response.text, "lxml")
all_event = soup.find("div", class_="event-summary number text-center") 
# raw_doc_numbers = [anchor.text for anchor in all_event]
# doc_numbers=[numbers for numbers in raw_doc_numbers if numbers.isdigit()]
# print(doc_numbers)

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
        
        if key == "Emergency Class": # because it isn't bold unlike the others
            cfr_text = field.parent.get_text("\n", strip=True)

            lines = [
                line.strip()
                for line in cfr_text.splitlines()
                if line.strip()
            ]

            try:
                cfr_index = lines.index("10 CFR Section:")
                event_data["CFR Section"] = " ".join(
                    lines[cfr_index + 1:]
                )
            except (ValueError, IndexError):
                event_data["CFR Section"] = ""

        event_data[key] = value

    if "RX Type" in event_data.keys():
        is_reactor_report = True
    
    # MARK: extract reactor table
    if is_reactor_report:
        table = None
        reactor_data = []
        
        for sibling in processing_event.find_next_siblings(): # made extra annoying by the fact that there can be mixed reports in one page
            
            # Stop searching if we hit the Event Text block or a new event block
            if sibling.name == "div" and ("border" in sibling.get("class", []) or "grid" in sibling.get("class", [])):
                break 
                
            if sibling.name == "table":
                table = sibling
                break
        
        if table:
            table_body = table.find("tbody")            
            reactor_data = []
            
            rows_source = table_body if table_body else table
            
            for row in rows_source.find_all('tr'):
                cols = [element.text.strip() for element in row.find_all('td')]
                for i, item in enumerate(cols):
                    if item == "N":
                        cols[i] = "No"
                    elif item == "Y":
                        cols[i] = "Yes"
                if cols:
                    reactor_data.append(cols)
            
        else:
            print(f"Error: Failed finding reactor info table for event {number}")

    # MARK: extract text block
    try:
        text_tag = odd_text[cycle]
    except IndexError:
        print(f"Missing text block for event {number}")
        continue

    text = text_tag.get_text("\n", strip=True)

    chunks = chunk_lines(text.splitlines(), BUFFER_SIZE)

    # MARK: INTERPRET DATA
    print("Plant Report" if is_reactor_report else "Facility Report")
    try:

        fields = []
        fields.append(("<number>", number))
        fields.append(("<concperson>", event_data["Person (Organization)"]))
        fields.append(("<hqofficer>", event_data["HQ OPS Officer"]))
        fields.append(("<eventDate>", event_data["Event Date"]))
        fields.append(("<eventTime>", event_data["Event Time"]))
        fields.append(("<personNotified>", event_data["NRC Notified By"]))
        fields.append(("<emergencyClass>", event_data["Emergency Class"]))
        fields.append(("<section>", event_data["CFR Section"]))
        fields.append(("<state>", event_data["State"]))
        fields.append(("<region>", event_data["Region"]))
        fields.append(("<notifyDate>", event_data["Notification Date"]))

        if is_reactor_report:
            fields.append(("<notifyTime>", event_data["Notification Time"]))
            fields.append(("<facility>", event_data["Facility"]))
            fields.append(("<unit>", event_data["Unit"]))
            fields.append(("<rxType>", event_data["RX Type"]))

            #if reactor_data:
            #    fields.append(("<reactorData>", format_table(reactor_data)))
            #else:
            #    fields.append(("<reactorData>", "No reactor data found."))
        else:
            fields.append(("<county>", event_data["County"]))
            fields.append(("<city>", event_data["City"]))
            fields.append(("<reporg>", event_data["Rep Org"]))

        
        embed_str = plant_schema_str if is_reactor_report else facility_schema_str

        for old, new in fields:
            embed_str = embed_str.replace(old, str(new))
        
        try:
            embed_data = json.loads(embed_str)
        except json.JSONDecodeError as e:
            print("Error while parsing json after replacements:", e)
            exit()
        
        del embed_str

    except KeyError as e:
        print(f"{colors.TERMINAL_RED}  Malformed event data: missing {e}{colors.TERMINAL_RESET}")
        continue

    # MARK: INSERT CHUNKS
    embed = embed_data["embeds"][0]

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
        "embed": embed_data,
        "metadata": event_data
    })


del soup # cleap up

# MARK: SENDING DATA
for webhook_url in webhook_urls:
    for inum, event in enumerate(parsed_events):
        print(f"Sending event {event['number']}")

        # Send embed
        try:
            response = requests.post(
                webhook_url,
                json=event["embed"]
            )

            if response.status_code == 204:
                print("Embed sent successfully.")
            else:
                print(f"{colors.TERMINAL_RED} Embed failed: {response.status_code} {colors.TERMINAL_RESET}")
                print(response.text)

        except Exception as e:
            print(f"{colors.TERMINAL_RED} Error sending embed: {e}{colors.TERMINAL_RESET}")

        if (inum + 1) != len(parsed_events):
            sleep(SLEEP_TIME)