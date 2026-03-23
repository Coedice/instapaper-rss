import os
import sys
from datetime import datetime, time
from hashlib import sha256
from typing import Any, List

import yaml
from rich import print as rprint
from rich.progress import track

from Feed import Feed
from PickleDictionary import PickleDictionary
from SavingQueue import SavingQueue

# Load settings from YAML
try:
    with open("config/settings.yml", "r") as settings_file:
        _settings = yaml.safe_load(settings_file) or {}
except FileNotFoundError:
    _settings = {}

# Load wrappers from YAML
try:
    with open("config/wrappers.yml", "r") as wrappers_file:
        _wrappers = yaml.safe_load(wrappers_file) or {}
except FileNotFoundError:
    _wrappers = {}

if not isinstance(_wrappers, dict):
    raise ValueError(
        "config/wrappers.yml must contain a mapping of wrapper names to URL templates"
    )

TESTING_MODE = _settings.get("testing_mode")
DEFAULT_PRIORITY = _settings.get("default_priority", "normal")
LOCK_FILE = ".running.lock"

DAY_NAME_TO_INDEX = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


def load_priorities() -> dict[str, dict[str, Any]]:
    try:
        with open("config/priorities.yml", "r") as priorities_file:
            priorities = yaml.safe_load(priorities_file) or {}
    except FileNotFoundError as exc:
        raise ValueError(
            "config/priorities.yml must exist and contain priorities"
        ) from exc

    if not isinstance(priorities, dict):
        raise ValueError("config/priorities.yml must contain a mapping of priorities")

    validate_priorities(priorities)
    return priorities


def parse_clock(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise ValueError(
            f"Invalid clock value '{value}'. Expected HH:MM in 24-hour time."
        ) from exc


def parse_day(day_name: str) -> int:
    normalized = day_name.strip().lower()
    if normalized not in DAY_NAME_TO_INDEX:
        valid_days = ", ".join(DAY_NAME_TO_INDEX)
        raise ValueError(f"Invalid day '{day_name}'. Expected one of: {valid_days}")

    return DAY_NAME_TO_INDEX[normalized]


def validate_priorities(priorities: dict[str, dict[str, Any]]) -> None:
    for priority_name, rules in priorities.items():
        if not isinstance(rules, dict):
            raise ValueError(
                f"Priority '{priority_name}' in config/priorities.yml must be a mapping"
            )

        check_every = rules.get("check_every")
        if not isinstance(check_every, int) or check_every <= 0:
            raise ValueError(
                f"Priority '{priority_name}' must define a positive integer check_every"
            )

        time_ranges = rules.get("time_ranges")
        if time_ranges is None:
            continue

        if not isinstance(time_ranges, list):
            raise ValueError(
                f"Priority '{priority_name}' time_ranges must be a list of ranges"
            )

        for time_range in time_ranges:
            if not isinstance(time_range, dict):
                raise ValueError(
                    f"Priority '{priority_name}' time_ranges must contain mappings"
                )

            if "start" not in time_range or "end" not in time_range:
                raise ValueError(
                    f"Priority '{priority_name}' time ranges must define start and end"
                )

            parse_clock(time_range["start"])
            parse_clock(time_range["end"])

            days = time_range.get("days")
            if days is None:
                raise ValueError(
                    f"Priority '{priority_name}' time ranges must define days"
                )

            if not isinstance(days, list) or not days:
                raise ValueError(
                    f"Priority '{priority_name}' time range days must be a non-empty list"
                )

            for day_name in days:
                if not isinstance(day_name, str):
                    raise ValueError(
                        f"Priority '{priority_name}' time range days must contain strings"
                    )
                parse_day(day_name)


def is_time_in_range(current_time: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= current_time <= end

    return current_time >= start or current_time <= end


def is_day_in_range(days: list[str], current_weekday: int) -> bool:
    day_indexes = {parse_day(day_name) for day_name in days}
    return current_weekday in day_indexes


def is_time_in_ranges(
    time_ranges: list[dict[str, Any]] | None,
    current_time: time | None = None,
    current_weekday: int | None = None,
) -> bool:
    if not time_ranges:
        return True

    now = datetime.now()
    current = current_time or now.time().replace(second=0, microsecond=0)
    weekday = current_weekday if current_weekday is not None else now.weekday()

    for time_range in time_ranges:
        if not is_day_in_range(time_range["days"], weekday):
            continue

        start = parse_clock(time_range["start"])
        end = parse_clock(time_range["end"])
        if is_time_in_range(current, start, end):
            return True

    return False


def get_priority_name(
    feed_item: dict[str, Any],
    priorities: dict[str, dict[str, Any]],
    default_priority: str,
) -> str:
    priority_name = feed_item.get("priority", default_priority)
    if priority_name not in priorities:
        raise ValueError(
            f"Priority '{priority_name}' for feed {feed_item['url']} is not defined"
        )

    return priority_name


def should_process_feed(
    feed_item: dict[str, Any],
    feed_scans: PickleDictionary,
    priorities: dict[str, dict[str, Any]],
    default_priority: str,
    current_time: time | None = None,
    current_weekday: int | None = None,
) -> tuple[bool, str]:
    priority_name = get_priority_name(feed_item, priorities, default_priority)
    rules = priorities[priority_name]
    time_ranges = rules.get("time_ranges")

    if not is_time_in_ranges(time_ranges, current_time, current_weekday):
        return False, f"outside {priority_name} priority time ranges"

    feed_url = feed_item["url"]
    current_feed_scans = feed_scans[feed_url] if feed_url in feed_scans else 0
    check_every = rules["check_every"]
    is_scheduled_run = current_feed_scans % check_every == url_mod(
        feed_url, check_every
    )
    feed_scans[feed_url] = current_feed_scans + 1

    if not is_scheduled_run:
        return False, f"{priority_name} priority: skipping this cycle"

    return True, priority_name


_priorities = load_priorities()
if DEFAULT_PRIORITY not in _priorities:
    raise ValueError(
        f"default_priority '{DEFAULT_PRIORITY}' is not defined in config/priorities.yml"
    )


def url_mod(url: str, mod: int) -> int:
    hash_bytes = sha256(url.encode()).digest()
    return int.from_bytes(hash_bytes, "big") % mod


def process_feed_list(
    feed_list: List[dict[str]],
    last_saved_times: PickleDictionary,
    rss_urls: PickleDictionary,
    monthly_entries: PickleDictionary,
    feed_scans: PickleDictionary,
    wrappers: dict[str, str],
    priorities: dict[str, dict[str, Any]],
    default_priority: str,
) -> None:
    saving_queue = SavingQueue(TESTING_MODE)

    for feed_item in track(feed_list, description="[bold green]Processing feeds..."):
        feed_url = feed_item["url"]
        rprint(f"Processing feed [blue underline]{feed_url}[/blue underline]")
        should_process, status = should_process_feed(
            feed_item, feed_scans, priorities, default_priority
        )
        if not should_process:
            rprint(f"  [dark_orange3]Skipped:[/dark_orange3] {status}")
            continue

        # Process feed
        feed = Feed(feed_item, rss_urls, last_saved_times, monthly_entries, wrappers)
        feed.process_feed(saving_queue)
        rprint("  [green]Processed[/green]")

    saving_queue.save_entries()


def main() -> None:
    # Unpickle data
    last_saved_times = PickleDictionary("last_save_times.dat")
    rss_urls = PickleDictionary("rss_urls.dat")
    monthly_entries = PickleDictionary("monthly_entries.dat")
    feed_scans = PickleDictionary("feed_scans.dat")

    # Get source list
    with open("config/sources.yml") as source_list_file:
        section_list = yaml.safe_load(source_list_file)

    # Combine section lists into feed list
    feed_list = []
    for section in section_list:
        for source in section["sources"]:
            feed_list += source["feeds"]

    # Process feed list
    process_feed_list(
        feed_list,
        last_saved_times,
        rss_urls,
        monthly_entries,
        feed_scans,
        _wrappers,
        _priorities,
        DEFAULT_PRIORITY,
    )

    # Pickle data
    if not TESTING_MODE:
        last_saved_times.save()
        rss_urls.save()
        monthly_entries.save()
        feed_scans.save()


if __name__ == "__main__":
    # Create lock file
    if os.path.exists(LOCK_FILE):
        print(f"Lock file {LOCK_FILE} exists. Another instance may be running.")
        sys.exit(1)

    try:
        # Create lock file with PID
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))

        main()
    finally:
        # Clean up lock file
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
