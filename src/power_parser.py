from datetime import date, timedelta, datetime
import requests
from colors import *

class Report:
    def __init__(self, date: str, time: str, plant_name: str, power: str):
        self.date = date
        self.time = time
        self.plant_name = plant_name
        self.power = power

    def to_string(self, changed=False, previous_day_power=0):
        power_color = COLOR_RED if self.power != "100" else COLOR_GREEN

        bold_begin = COLOR_BOLD if changed else ""
        bold_end = f"{COLOR_RESET} {COLOR_CYAN}[original: {previous_day_power}]{COLOR_RESET}" if changed else ""

        return (
            f"{COLOR_CYAN}[{self.time}]{COLOR_RESET} "
            f"{COLOR_BLUE}{self.plant_name}{COLOR_RESET} : "
            f"{bold_begin}{power_color}{self.power}%{bold_end}{COLOR_RESET}"
        )


# MARK: PARSING
def parse_data(lines: list) -> tuple:
    current_day_str : str = None
    previous_day_str : str = None

    current_day_reports = {}
    previous_day_reports = {}

    try:
        for line in lines[1:]:  # skip header
            data = line.split("|")

            date_time = data[0].split(" ")

            report = Report(
                date_time[0],
                date_time[1] + " " + date_time[2],
                data[1],
                data[2]
            )

            if current_day_str == None: # only the first one
                current_day_str = report.date
                try:
                    current_day = datetime.strptime(current_day_str, "%m/%d/%Y").date()
                    previous_day_str = (current_day - timedelta(days=1)).strftime("%-m/%-d/%Y")
                except Exception:
                    print("Invalid date parsed: " + current_day_str)
                

            if report.date == current_day_str:
                current_day_reports[report.plant_name] = report

            elif report.date == previous_day_str:
                previous_day_reports[report.plant_name] = report

            elif report.date != current_day_str:
                # once we're past previous_day we can stops
                if previous_day_reports:
                    break
    

    except Exception as e:
        print(f"Error parsing line: {line}")
        print(f"Data: {data}")
        print(e)

    
    return current_day_reports, previous_day_reports, current_day_str
