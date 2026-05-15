from datetime import date, timedelta
import requests
from colors import *

class Report:
    def __init__(self, date: str, time: str, plant_name: str, power: str):
        self.date = date
        self.time = time
        self.plant_name = plant_name
        self.power = power

    def to_string(self, changed=False, yesterday_power=0):
        power_color = COLOR_RED if self.power != "100" else COLOR_GREEN

        bold_begin = COLOR_BOLD if changed else ""
        bold_end = f"{COLOR_RESET} {COLOR_CYAN}[original: {yesterday_power}]{COLOR_RESET}" if changed else ""

        return (
            f"{COLOR_CYAN}[{self.time}]{COLOR_RESET} "
            f"{COLOR_BLUE}{self.plant_name}{COLOR_RESET} : "
            f"{bold_begin}{power_color}{self.power}%{bold_end}{COLOR_RESET}"
        )


# MARK: PARSING
def parse_data(lines: list, target_date: date) -> tuple:
    today_str = target_date.strftime("%-m/%-d/%Y")
    yesterday_str = (target_date - timedelta(days=1)).strftime("%-m/%-d/%Y")

    today_reports = {}
    yesterday_reports = {}

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

            if report.date == today_str:
                today_reports[report.plant_name] = report

            elif report.date == yesterday_str:
                yesterday_reports[report.plant_name] = report

            elif report.date != today_str:
                # once we're past yesterday we can stops
                if yesterday_reports:
                    break
    

    except Exception as e:
        print(f"Error parsing line: {line}")
        print(f"Data: {data}")
        print(e)

    
    return today_reports, yesterday_reports
