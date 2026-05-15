import requests
from bs4 import BeautifulSoup
import discord
import json
from time import sleep
from os import getenv
from dotenv import load_dotenv

url_test="https://web.archive.org/web/20251215120022/https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en"
url_test2="https://web.archive.org/web/20231118072408/https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en"
url = "https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en.html"
load_dotenv()
WEBHOOK_URL_REPORT=getenv("WEBHOOK_URL_REPORT")
BUFFER_SIZE = 1950 # discord has 2000 limit

response = requests.get(url_test)

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
    elif isinstance(obj, dict):
        return {key: replace_text(value, old, new) for key, value in obj.items()}
    return obj

soup = BeautifulSoup(response.text, "lxml")
all_event = soup.find("div", class_="event-summary number text-center") 
raw_doc_numbers = [anchor.text for anchor in all_event]
print(raw_doc_numbers)
doc_numbers=[numbers for numbers in raw_doc_numbers if numbers.isdigit()]
print(doc_numbers)

cycle=0
for number in doc_numbers:
    data={}
    print(number)
    findit = soup.find("div", id=f"en{doc_numbers[cycle]}", class_="grid border") 
    for b in findit.find_all("b"):
        key = b.get_text(strip=True).replace(":", "")
        value = b.next_sibling
        if isinstance(value, str):
            value = value.strip()
        else:
            value = ""
        data[key] = value
    
    text = soup.select("div.border")
    #NRC responds with Report text adn HEADER, this filters the text out
    odd_text = text[1::2]

    #print(data)
    print(odd_text)
    #print(text2)
    with open("facility.json", "r") as f:
        facility = json.load(f)
        # Replace text
    facility = replace_text(facility, "numberssss", doc_numbers[cycle])
    


    embed = facility
    # MARK: DISCORD WEBHOOK
    try:
        
        response = requests.post(WEBHOOK_URL_REPORT, json=embed)

        if response.status_code == 204:
            print("Message sent successfully.")
        else:
            print(f"Failed: {response.status_code}")
            print(response.text)

        
    except Exception as e:
        print(f"Error sending header message: {e}")

    buffer = odd_text[cycle]
    try:
        for chunk in buffer:
            payload = {
                "content": chunk.get_text("\n", strip=True)
            }

            response = requests.post(WEBHOOK_URL_REPORT, json=payload)

            if response.status_code == 204:
                print("Message sent successfully.")
            else:
                print(f"Failed: {response.status_code}")
                print(response.text)

            sleep(600)
    except Exception as e:
        print(f"Error sending text message: {e}")




with open("nrc_events.txt", "w", encoding="utf-8") as f:
    for i, event in enumerate(odd_text, start=1):
        odd_text = event.get_text("\n", strip=True)

        f.write(f"===== EVENT {i} =====\n")
        f.write(odd_text + "\n\n")