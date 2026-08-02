from typing import Any, Optional

import requests


class Notifier:
    """Sends error notifications to an ntfy topic.

    Configured via the ``ntfy`` section of ``config/settings.yml``::

        ntfy:
          host: ntfy.sh
          topic: instapaper-errors

    Both ``host`` and ``topic`` are optional. If either is missing, the
    notifier is disabled and ``notify_error`` becomes a no-op.
    """

    def __init__(self, host: Optional[str] = None, topic: Optional[str] = None) -> None:
        self._host = host
        self._topic = topic

    @classmethod
    def from_settings(cls, settings: dict[str, Any]) -> "Notifier":
        ntfy_settings = settings.get("ntfy") or {}
        if not isinstance(ntfy_settings, dict):
            ntfy_settings = {}

        return cls(
            host=ntfy_settings.get("host"),
            topic=ntfy_settings.get("topic"),
        )

    @property
    def enabled(self) -> bool:
        return bool(self._host and self._topic)

    def notify_error(self, message: str) -> None:
        if not self.enabled:
            return

        url = f"https://{self._host.rstrip('/')}/{self._topic.lstrip('/')}"
        try:
            requests.post(url, data=message.encode("utf-8"), timeout=10)
        except Exception:
            # Notification failures must never break the main run
            pass
