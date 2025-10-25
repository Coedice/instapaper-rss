import math
from hashlib import sha256
from typing import List

import yaml
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

TESTING_MODE = _settings.get("testing_mode")
MAX_SKIPS = _settings.get("max_skips")
FREQUENT_FEED_THRESHOLD = _settings.get("frequent_feed_threshold")


def url_mod(url: str, mod: int) -> int:
    hash_bytes = sha256(url.encode()).digest()
    return int.from_bytes(hash_bytes, "big") % mod


def process_feed_list(
    feed_list: List[dict[str]],
    last_saved_times: PickleDictionary,
    rss_urls: PickleDictionary,
    monthly_entries: PickleDictionary,
    feed_scans: PickleDictionary,
) -> None:
    saving_queue = SavingQueue(TESTING_MODE)

    for feed_item in track(feed_list, description="[bold green]Processing feeds..."):
        # Decide if we should skip
        feed_url = feed_item["url"]
        current_monthly_entries = (
            monthly_entries[feed_url] if feed_url in monthly_entries else math.inf
        )
        current_feed_scans = feed_scans[feed_url] if feed_url in feed_scans else 0
        enough_skips = current_feed_scans % MAX_SKIPS == url_mod(feed_url, MAX_SKIPS)
        feed_scans[feed_url] = current_feed_scans + 1
        if current_monthly_entries <= FREQUENT_FEED_THRESHOLD and not enough_skips:
            print(f"Skipping feed {feed_item['url']}")
            continue

        # Process feed
        feed = Feed(feed_item, rss_urls, last_saved_times, monthly_entries)
        feed.process_feed(saving_queue)
        print(f"Processed feed {feed_item['url']}")

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
        feed_list, last_saved_times, rss_urls, monthly_entries, feed_scans
    )

    # Pickle data
    if not TESTING_MODE:
        last_saved_times.save()
        rss_urls.save()
        monthly_entries.save()
        feed_scans.save()


if __name__ == "__main__":
    main()
