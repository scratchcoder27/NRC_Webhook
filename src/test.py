import requests
from bs4 import BeautifulSoup

response = requests.get("https://www.nrc.gov/reading-rm/doc-collections/event-status/event/event-notification-rpt-lastmonth.txt")

text = response.text

records = []
current_record = ""

for line in text.splitlines():

    if line.startswith((
        "Power Reactor|",
        "Agreement State|",
        "Non-Agreement State|",
        "Part 21|",
        "Fuel Cycle|",
        "Materials|"
    )):

        if current_record:
            records.append(current_record)

        current_record = line

    else:
        current_record += "\n" + line

if current_record:
    records.append(current_record)

# Header
header = records.pop(0)

columns = header.split("|")

expected_splits = len(columns) - 1

for record in records:

    try:
        parts = record.split("|", expected_splits)

        data = dict(zip(columns, parts))

        print(data["En No"])
        print(data["Site Name"])
        print(data["State Cd"])

        # FULL EVENT TEXT
        print(data["Event Text"][:500])

        print("=" * 60)

    except Exception as e:
        print("Parse failed:", e)