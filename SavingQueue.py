import json
import os
from typing import List

import yaml
from rich.progress import track

from Entry import Entry
from Notifier import Notifier
from request import request

SESSION_URL = "https://www.instapaper.com/data/user_session"
CREATE_URL = "https://www.instapaper.com/data/bookmarks/create"


class SavingQueue:
    def __init__(self, testing_mode: bool, notifier: Notifier) -> None:
        self._entries: List[Entry] = []
        self._testing_mode = testing_mode
        self._notifier = notifier
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
        headers = {"X-Requested-With": "XMLHttpRequest"}
        response = request(SESSION_URL, headers=headers, cookies=self._cookies)
        data = json.loads(response.text)
        self._form_key = data["user"]["form_key"]

    def save_entries(self) -> None:
        self._sort_entries()

        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "X-Form-Key": self._form_key,
        }

        for entry in track(self._entries, description="[bold green]Saving entries..."):
            if self._testing_mode:
                print(f"Would have saved {entry.url}")
                continue

            response = request(
                CREATE_URL,
                method="POST",
                headers=headers,
                cookies=self._cookies,
                data={"url": entry.url},
            )

            if response.status_code // 100 != 2:
                print(f"Instapaper save link failed: {entry.url}")
                self._notifier.notify_error(f"Instapaper save link failed: {entry.url}")
