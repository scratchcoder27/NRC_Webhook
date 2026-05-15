import requests
from bs4 import BeautifulSoup
url_test="https://web.archive.org/web/20251215120022/https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en"
url = "https://www.nrc.gov/reading-rm/doc-collections/event-status/event/en.html"
response = requests.get(url_test)

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
    

    print(data)
    print(text)
    #print(text2)
with open("nrc_events.txt", "w", encoding="utf-8") as f:
    for i, event in enumerate(text, start=1):
        text = event.get_text("\n", strip=True)

        f.write(f"===== EVENT {i} =====\n")
        f.write(text + "\n\n")