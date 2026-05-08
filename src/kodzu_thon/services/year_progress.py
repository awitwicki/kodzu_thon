from datetime import datetime


def progress_bar(value: float, total: float = 100, length: int = 100, fill: str = "█") -> str:
    percent = f"{100 * (value / float(total)):.2f}"
    filled = int(length * value // total)
    bar = fill * filled + "-" * (length - filled)
    return f" |{bar}| {percent}% "


def get_year_progress(length: int = 20) -> str:
    day_of_year = datetime.now().timetuple().tm_yday
    bar = progress_bar(day_of_year, 365, length=length)
    return f"{bar} {day_of_year}/365"
