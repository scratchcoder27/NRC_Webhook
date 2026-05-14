from datetime import date, timedelta


class Report:
    def __init__(self, date: str, time: str, plant_name: str, power: str):
        self.date = date
        self.time = time
        self.plant_name = plant_name
        self.power = power

    def to_string(self, changed=False):
        power_color = "\x1b[2;31m" if self.power != "100" else "\x1b[2;32m"

        bold_begin = "\x1b[1m" if changed else ""
        bold_end = "\x1b[0m" if changed else ""

        return (
            f"\x1b[2;36m[{self.time}]\x1b[0m "
            f"\x1b[2;34m{self.plant_name}\x1b[0m : "
            f"{bold_begin}{power_color}{self.power}%{bold_end}\x1b[0m"
        )


# MARK: PARSING
def parse_data(lines: list, target_date: date):
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
                # once we're past yesterday we can stop
                if yesterday_reports:
                    break

    except Exception as e:
        print(f"Error parsing line: {line}")
        print(f"Data: {data}")
        print(e)

    return today_reports, yesterday_reports