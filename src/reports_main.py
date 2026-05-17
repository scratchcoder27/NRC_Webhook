import requests
from bs4 import BeautifulSoup
import discord
import json
from time import sleep
from os import getenv
from dotenv import load_dotenv
from copy import deepcopy
import colors

# MARK: CONFIG
url_test = "https://web.archive.org/web/20251215120022/https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en"
url_test2 = "https://web.archive.org/web/20231118072408/https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en"
url_test_reactor = "https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2026/20260102en"
url = "https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en.html"

URL = url

load_dotenv()

WEBHOOK_URL_REPORT = getenv("WEBHOOK_URL_REPORT")
BUFFER_SIZE = 900 # discord has 1000 limit for embed fields
SLEEP_TIME = 5 # secs
DEBUG = True

try:
    with open("src/facility_schema.json", "r") as f:
        facility_schema = json.load(f)
except FileNotFoundError:
    print("The facility report schema file does not exist")

try:
    with open("src/plant_schema.json", "r") as f:
        plant_schema = json.load(f)
except FileNotFoundError:
    print("The plant report schema file does not exist")

is_reactor_report = False

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

def format_table(data: list) -> str:
    headers = ["Unit", "SCRAM", "RX Crit", "Init PWR", "Curr PWR"]
    widths = [6, 9, 9, 12, 12]
    
    top_border    = "┌" + "┬".join("─" * w for w in widths) + "┐"
    header_sep    = "├" + "┼".join("─" * w for w in widths) + "┤"
    bottom_border = "└" + "┴".join("─" * w for w in widths) + "┘"

    header_cells = [f" {headers[i]:^{widths[i]-2}} " for i in range(len(headers))] # header
    header_row   = "│" + "│".join(header_cells) + "│"
    table_lines = [top_border, header_row, header_sep]

    for row in data:
        filtered_row = [row[0], row[1], row[2], row[3], row[5]]
        
        if len(filtered_row) != len(headers):
            return f"Error: Expected {len(headers)} columns of data, got {len(filtered_row)}."
        
        data_cells = [f" {filtered_row[i]:<{widths[i]-2}} " for i in range(len(filtered_row))]
        data_row   = "│" + "│".join(data_cells) + "│"
        table_lines.append(data_row)

    table_lines.append(bottom_border)

    return "\n".join(table_lines)


# MARK: GET DATA
try:
    print("Fetching data...")
    response = requests.get(URL)
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
                if cols:
                    reactor_data.append(cols)
            
            # print(reactor_data)
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
        embed_data = deepcopy(plant_schema if is_reactor_report else facility_schema)

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

            if reactor_data:
                fields.append(("<reactorData>", format_table(reactor_data)))
            else:
                fields.append(("<reactorData>", "No reactor data found."))
        else:
            fields.append(("<county>", event_data["County"]))
            fields.append(("<city>", event_data["City"]))
            fields.append(("<reporg>", event_data["Rep Org"]))

        for placeholder, value in fields:
            embed_data = replace_text(embed_data, placeholder, value)

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
        print(f"{colors.TERMINAL_RED} Error sending embed: {e}{colors.TERMINAL_RESET}")

    sleep(SLEEP_TIME)

# MARK: DEBUG
# if not DEBUG:    exit()