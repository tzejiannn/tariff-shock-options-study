"""
Generates lists of US trading days (Mon–Fri, excluding major holidays)
for each collection phase defined in settings.yaml.
"""

from datetime import date, timedelta

# US market holidays 2025 (NYSE observed dates)
_HOLIDAYS_2025 = {
    date(2025, 1, 1),   # New Year's Day
    date(2025, 1, 20),  # MLK Day
    date(2025, 2, 17),  # Presidents' Day
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 26),  # Memorial Day
    date(2025, 6, 19),  # Juneteenth
    date(2025, 7, 4),   # Independence Day
    date(2025, 9, 1),   # Labor Day
    date(2025, 11, 27), # Thanksgiving
    date(2025, 12, 25), # Christmas
}

_HOLIDAYS_2026 = {
    date(2026, 1, 1),   # New Year's Day
    date(2026, 1, 19),  # MLK Day
}

_HOLIDAYS = _HOLIDAYS_2025 | _HOLIDAYS_2026


def is_trading_day(d: date) -> bool:
    return d.weekday() < 5 and d not in _HOLIDAYS


def trading_days_between(start: str, end: str) -> list[str]:
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    result = []
    current = s
    while current <= e:
        if is_trading_day(current):
            result.append(current.isoformat())
        current += timedelta(days=1)
    return result


def weekly_trading_days(start: str, end: str) -> list[str]:
    all_days = trading_days_between(start, end)
    if not all_days:
        return []
    result = []
    last_week = None
    for d in all_days:
        dt = date.fromisoformat(d)
        week = dt.isocalendar()[:2]  # (year, week_number)
        if week != last_week:
            result.append(d)
            last_week = week
    return result


def get_collection_dates(phase: dict) -> list[str]:
    freq = phase["frequency"]
    start = phase["start"]
    end = phase["end"]
    if freq == "daily":
        return trading_days_between(start, end)
    elif freq == "weekly":
        return weekly_trading_days(start, end)
    else:
        raise ValueError(f"Unknown frequency: {freq}")


if __name__ == "__main__":
    # Quick sanity check
    from config.loader import cfg
    for phase in cfg["collection"]["phases"]:
        dates = get_collection_dates(phase)
        print(f"Phase {phase['id']} ({phase['name']}): {len(dates)} collection days")
        print(f"  First: {dates[0]}  Last: {dates[-1]}\n")