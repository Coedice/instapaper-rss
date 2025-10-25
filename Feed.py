import re
from datetime import datetime, timezone
from time import mktime

from bs4 import BeautifulSoup
from langdetect import detect

from Entry import Entry
from PickleDictionary import PickleDictionary
from request import request
from SavingQueue import SavingQueue


def current_unix_time() -> int:
    date_time = datetime.now(timezone.utc)
    return int(mktime(date_time.timetuple()))


class Feed:
    _SUMMARISE_PROMPT = "Summarise the following website in dot points, with a link afterwards to the website."

    _HEADERS = {
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    }

    _MONTH = 60 * 60 * 24 * 30

    def __init__(
        self,
        feed_item: dict[str],
        rss_urls: PickleDictionary,
        last_saved_times: PickleDictionary,
        monthly_entries: PickleDictionary,
    ) -> None:
        self._feed_url = feed_item["url"]
        self._rss_url = self._get_rss_url(rss_urls)
        self._last_saved_time = self._get_last_saved_time(last_saved_times)
        self._last_saved_times = last_saved_times
        self._monthly_entries = monthly_entries
        self._blacklist_regex = None
        self._whitelist_regex = None
        self._allowed_languages = None
        self._summarise = False

        if "blacklist_regex" in feed_item:
            self._blacklist_regex = feed_item["blacklist_regex"]

        if "whitelist_regex" in feed_item:
            self._whitelist_regex = feed_item["whitelist_regex"]

        if "allowed_languages" in feed_item:
            self._allowed_languages = feed_item["allowed_languages"]

        if "summarise" in feed_item:
            self._summarise = feed_item["summarise"]

    def _get_rss_url(self, rss_urls: PickleDictionary) -> str:
        # Find RSS file from cache
        if self._feed_url in rss_urls:
            return rss_urls[self._feed_url]

        # Find RSS URL from feed URL
        found_rss_url = self._feed_url
        feed_link = request(self._feed_url, headers=self._HEADERS)
        feed_xml = BeautifulSoup(feed_link.text, features="html.parser")

        if feed_xml.findChild("html"):
            rss_tag = feed_xml.find_all("link", attrs={"type": "application/rss+xml"})[
                0
            ]
            rss_url = rss_tag.get("href")

            # Convert relative RSS url to non-relative
            if rss_url[0] == "/":
                path_length = len(feed_link.request.path_url)
                root_url = self._feed_url[: len(self._feed_url) - path_length]
                rss_url = root_url + rss_url

            found_rss_url = rss_url

        # Save found RSS URL
        rss_urls[self._feed_url] = found_rss_url

        # Return result
        return found_rss_url

    def _get_last_saved_time(self, last_saved_times: PickleDictionary) -> int:
        if self._feed_url in last_saved_times:  # If cached
            # Find RSS file from cache
            return last_saved_times[self._feed_url]
        else:
            current_time = current_unix_time()

            # Set as now
            last_saved_times[self._feed_url] = current_time

            # Return result
            return current_time

    def process_feed(self, saving_queue: SavingQueue) -> None:
        try:
            rss_link = request(self._rss_url, headers=self._HEADERS)
        except Exception as e:
            print(f"Error {e} while processing feed {self._feed_url}. Skipped feed.")
            return

        # Parse RSS
        rss_xml = BeautifulSoup(rss_link.text, features="xml")
        entry_tags = rss_xml.find_all("entry") + rss_xml.find_all("item")
        new_time_of_latest_entry = self._last_saved_time

        # Reset monthly entries
        self._monthly_entries[self._feed_url] = 0

        # Process entries
        for entry_tag in entry_tags:
            # Create entry
            if self._summarise is False:
                entry = Entry(entry_tag)
            else:
                entry = Entry(entry_tag, self._SUMMARISE_PROMPT)

            # Don't count or save entry if title matches blacklist_regex
            if self._blacklist_regex and re.search(self._blacklist_regex, entry.title):
                continue

            # Don't count or save entry if title doesn't match whitelist_regex
            if self._whitelist_regex and not re.search(
                self._whitelist_regex, entry.title
            ):
                continue

            # Don't count or save entry if title's language is not allowed
            if (
                self._allowed_languages
                and detect(entry.title) not in self._allowed_languages
            ):
                continue

            # Count monthly entries
            if entry.publish_time > current_unix_time() - self._MONTH:
                self._monthly_entries[self._feed_url] += 1

            # Don't save entry if ID is before the last run datetime
            if entry.publish_time <= self._last_saved_time:
                continue

            # Add to saving queue
            saving_queue.enqueue(entry)

            # Update new_time_of_latest_entry
            new_time_of_latest_entry = max(new_time_of_latest_entry, entry.publish_time)

        # Save time of last entry
        self._last_saved_times[self._feed_url] = new_time_of_latest_entry
