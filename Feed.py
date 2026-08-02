import html
import json
import re
import warnings
from datetime import datetime, timezone
from time import mktime
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from langdetect import detect

from Entry import Entry
from Notifier import Notifier
from PickleDictionary import PickleDictionary
from request import request
from SavingQueue import SavingQueue

# Silence BeautifulSoup warning when parsing XML with html parser fallback
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def current_unix_time() -> int:
    date_time = datetime.now(timezone.utc)
    return int(mktime(date_time.timetuple()))


class Feed:
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
        wrappers: dict[str, str],
        notifier: Notifier,
    ) -> None:
        self._feed_url = feed_item["url"]
        self._rss_url = self._get_rss_url(rss_urls)
        self._last_saved_time = self._get_last_saved_time(last_saved_times)
        self._last_saved_times = last_saved_times
        self._monthly_entries = monthly_entries
        self._notifier = notifier
        self._blacklist_regex = None
        self._whitelist_regex = None
        self._allowed_languages = None
        self._wrappers = []

        if "blacklist_regex" in feed_item:
            self._blacklist_regex = feed_item["blacklist_regex"]

        if "whitelist_regex" in feed_item:
            self._whitelist_regex = feed_item["whitelist_regex"]

        if "allowed_languages" in feed_item:
            self._allowed_languages = feed_item["allowed_languages"]

        if "wrappers" in feed_item:
            self._wrappers = [wrappers[name] for name in feed_item["wrappers"]]

    def _get_rss_url(self, rss_urls: PickleDictionary) -> str:
        if self._is_instagram_profile():
            rss_urls[self._feed_url] = self._feed_url
            return self._feed_url

        # Find RSS file from cache
        if self._feed_url in rss_urls:
            return rss_urls[self._feed_url]

        # Find RSS URL from feed URL
        found_rss_url = self._feed_url
        feed_link = request(self._feed_url, headers=self._HEADERS)
        feed_xml = BeautifulSoup(feed_link.text, features="html.parser")

        if feed_xml.findChild("html"):
            rss_tags = feed_xml.find_all("link", attrs={"type": "application/rss+xml"})
            if rss_tags:
                rss_url = rss_tags[0].get("href")

                # Convert relative RSS url to non-relative
                if rss_url and rss_url[0] == "/":
                    path_length = len(feed_link.request.path_url)
                    root_url = self._feed_url[: len(self._feed_url) - path_length]
                    rss_url = root_url + rss_url

                if rss_url:
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
        if self._is_instagram_profile():
            entries = self._fetch_instagram_entries()
            self._process_entries(entries, saving_queue)
            return

        try:
            rss_link = request(self._rss_url, headers=self._HEADERS)
        except Exception as e:
            print(f"Error {e} while processing feed {self._feed_url}. Skipped feed.")
            self._notifier.notify_error(
                f"Error {e} while processing feed {self._feed_url}"
            )
            return

        # Parse RSS
        rss_xml = BeautifulSoup(rss_link.text, features="xml")
        entry_tags = rss_xml.find_all("entry") + rss_xml.find_all("item")
        entries = [Entry(entry_tag, self._wrappers) for entry_tag in entry_tags]
        self._process_entries(entries, saving_queue)

    def _process_entries(self, entries: list[Entry], saving_queue: SavingQueue) -> None:
        new_time_of_latest_entry = self._last_saved_time

        # Reset monthly entries
        self._monthly_entries[self._feed_url] = 0

        # Process entries
        for entry in entries:
            # Don't count or save entry if title matches blacklist_regex
            if self._blacklist_regex and re.search(self._blacklist_regex, entry.title):
                continue

            # Don't count or save entry if title doesn't match whitelist_regex
            if self._whitelist_regex and not re.search(
                self._whitelist_regex, entry.title
            ):
                continue

            # Don't count or save entry if title's language is not allowed
            if self._allowed_languages:
                try:
                    language = detect(entry.title)
                except Exception:
                    continue

                if language not in self._allowed_languages:
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

    def _is_instagram_profile(self) -> bool:
        parsed_url = urlparse(self._feed_url)
        return "instagram.com" in parsed_url.netloc and "/p/" not in parsed_url.path

    def _fetch_instagram_entries(self) -> list[Entry]:
        payload = self._fetch_instagram_payload()

        if payload is None:
            print(
                f"Instagram feed for {self._feed_url} returned invalid JSON. Skipped feed."
            )
            self._notifier.notify_error(
                f"Instagram feed for {self._feed_url} returned invalid JSON"
            )
            return []

        edges = self._get_instagram_edges(payload)

        entries: list[Entry] = []
        for edge in edges:
            node = edge.get("node", {}) if isinstance(edge, dict) else {}
            shortcode = node.get("shortcode")
            if not shortcode:
                continue

            post_url = f"https://www.instagram.com/p/{shortcode}/"
            caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
            caption = ""
            if caption_edges and isinstance(caption_edges[0], dict):
                caption = caption_edges[0].get("node", {}).get("text", "").strip()

            title = caption or post_url
            timestamp = node.get("taken_at_timestamp") or current_unix_time()
            pub_date = datetime.fromtimestamp(timestamp, timezone.utc).strftime(
                "%a, %d %b %Y %H:%M:%S %z"
            )

            xml = f"""
            <item>
              <title>{html.escape(title)}</title>
              <link>{post_url}</link>
              <pubDate>{pub_date}</pubDate>
            </item>
            """

            entry_tag = BeautifulSoup(xml, features="xml").find("item")
            if entry_tag is None:
                continue

            entries.append(Entry(entry_tag, self._wrappers))

        return entries

    def _fetch_instagram_payload(self) -> dict[str, Any] | None:
        fetchers = [
            self._fetch_instagram_json_api,
            self._fetch_instagram_web_profile_info,
            self._fetch_instagram_html_payload,
        ]

        for fetcher in fetchers:
            payload = fetcher()
            if payload is not None:
                return payload

        return None

    def _fetch_instagram_json_api(self) -> dict[str, Any] | None:
        profile_api_url = self._feed_url.rstrip("/") + "/?__a=1&__d=dis"
        try:
            response = request(profile_api_url, headers=self._HEADERS)
            return self._parse_instagram_payload(response.text)
        except Exception:
            return None

    def _fetch_instagram_web_profile_info(self) -> dict[str, Any] | None:
        username = self._extract_instagram_username()
        if not username:
            return None

        api_url = (
            "https://i.instagram.com/api/v1/users/web_profile_info/?username="
            + username
        )

        headers = dict(self._HEADERS)
        headers["x-ig-app-id"] = "936619743392459"

        try:
            response = request(api_url, headers=headers)
            return self._parse_instagram_payload(response.text)
        except Exception:
            return None

    def _fetch_instagram_html_payload(self) -> dict[str, Any] | None:
        try:
            html_response = request(self._feed_url, headers=self._HEADERS)
            return self._parse_instagram_payload(html_response.text)
        except Exception:
            return None

    def _extract_instagram_username(self) -> str | None:
        parsed_url = urlparse(self._feed_url)
        segments = [segment for segment in parsed_url.path.split("/") if segment]
        if not segments:
            return None
        return segments[0]

    def _parse_instagram_payload(self, response_text: str) -> dict[str, Any] | None:
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        soup = BeautifulSoup(response_text, "html.parser")
        script_candidates = []

        next_data = soup.find("script", id="__NEXT_DATA__")
        if next_data and next_data.string:
            script_candidates.append(next_data.string)

        for script in soup.find_all("script"):
            if not script.string:
                continue
            if "edge_owner_to_timeline_media" not in script.string:
                continue
            script_candidates.append(script.string)

        for raw_script in script_candidates:
            cleaned_json = self._extract_json_object(raw_script)
            if not cleaned_json:
                continue
            try:
                return json.loads(cleaned_json)
            except json.JSONDecodeError:
                continue

        return None

    def _extract_json_object(self, raw_script: str) -> str | None:
        start_index = raw_script.find("{")
        end_index = raw_script.rfind("}")
        if start_index == -1 or end_index == -1 or end_index <= start_index:
            return None
        return raw_script[start_index : end_index + 1]

    def _get_instagram_edges(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        media = self._find_media_dict(payload)
        if not media:
            return []

        edges = media.get("edges")
        if isinstance(edges, list):
            return edges

        return []

    def _find_media_dict(self, obj: Any) -> dict[str, Any] | None:
        if isinstance(obj, dict):
            if "edge_owner_to_timeline_media" in obj and isinstance(
                obj["edge_owner_to_timeline_media"], dict
            ):
                return obj["edge_owner_to_timeline_media"]

            for value in obj.values():
                found = self._find_media_dict(value)
                if found:
                    return found

        elif isinstance(obj, list):
            for item in obj:
                found = self._find_media_dict(item)
                if found:
                    return found

        return None
