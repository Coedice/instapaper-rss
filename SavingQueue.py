import os
import re
import urllib.parse
from typing import List

import yaml
from rich.progress import track

from Entry import Entry
from request import request

COOKIE_PROBLEM_PAGE_URL = "https://www.instapaper.com/hello2?u=https%3A%2F%2Fexample.com&s=&cookie_notice=1&a=%20read-later"


class SavingQueue:
    def __init__(self, testing_mode: bool) -> None:
        self._entries: List[Entry] = []
        self._testing_mode = testing_mode
        self._get_cookies()
        self._get_form_key()

    def enqueue(self, entry: Entry) -> None:
        self._entries.append(entry)

    def __len__(self) -> int:
        return len(self._entries)

    def _sort_entries(self) -> None:
        self._entries = sorted(self._entries, key=(lambda entry: entry.url))

    def _get_cookies(self) -> None:
        # Load cookies from YAML file
        cookie_path = "config/cookies.yml"
        if not os.path.exists(cookie_path):
            raise FileNotFoundError(
                "No cookies file found at config/cookies.yml. "
                "Create config/cookies.yml with your cookie mapping (pfh, pfp, pfu)."
            )

        with open(cookie_path, "r") as f:
            cookies = yaml.safe_load(f) or {}

        if not isinstance(cookies, dict):
            raise ValueError(
                "config/cookies.yml must contain a mapping of cookie names to values"
            )

        self._cookies = cookies

    def _get_form_key(self) -> None:
        cookie_problem_page = request(
            COOKIE_PROBLEM_PAGE_URL, cookies=self._cookies
        ).text
        start_index = re.search(
            '<input type="hidden" name="form_key" value="', cookie_problem_page
        ).end()
        end_index = (
            re.search('"/>', cookie_problem_page[start_index:]).start() + start_index
        )
        self._form_key = cookie_problem_page[start_index:end_index]

    def save_entries(self) -> None:
        self._sort_entries()

        for entry in track(self._entries, description="[bold green]Saving entries..."):
            if self._testing_mode:
                print(f"Would have saved {entry.url}")
                continue

            instapaper_url = f"https://www.instapaper.com/add?url={urllib.parse.quote(entry.url)}&form_key={self._form_key}"
            instapaper_request = request(instapaper_url, cookies=self._cookies)

            if instapaper_request.status_code // 100 != 2:
                print(f"Instapaper save link failed: {entry.url}")
