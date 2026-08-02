import pytest

from Notifier import Notifier


def test_disabled_when_no_ntfy_config():
    notifier = Notifier.from_settings({})
    assert not notifier.enabled


def test_disabled_when_only_host_set():
    notifier = Notifier.from_settings({"ntfy": {"host": "ntfy.sh"}})
    assert not notifier.enabled


def test_disabled_when_only_topic_set():
    notifier = Notifier.from_settings({"ntfy": {"topic": "my-topic"}})
    assert not notifier.enabled


def test_enabled_when_host_and_topic_set():
    notifier = Notifier.from_settings(
        {"ntfy": {"host": "ntfy.sh", "topic": "my-topic"}}
    )
    assert notifier.enabled


def test_notify_error_posts_to_ntfy(monkeypatch):
    posts = []

    class FakeResponse:
        def __init__(self, status_code=200):
            self.status_code = status_code

    def fake_post(url, data=None, timeout=None):
        posts.append((url, data, timeout))
        return FakeResponse()

    monkeypatch.setattr("requests.post", fake_post)

    notifier = Notifier(host="ntfy.sh", topic="my-topic")
    notifier.notify_error("Something went wrong")

    assert len(posts) == 1
    url, data, timeout = posts[0]
    assert url == "https://ntfy.sh/my-topic"
    assert data == b"Something went wrong"
    assert timeout == 10


def test_notify_error_swallows_request_exceptions(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        raise ConnectionError("network down")

    monkeypatch.setattr("requests.post", fake_post)

    notifier = Notifier(host="ntfy.sh", topic="my-topic")
    # Must not raise
    notifier.notify_error("Something went wrong")


def test_notify_error_noop_when_disabled(monkeypatch):
    called = []

    def fake_post(url, data=None, timeout=None):
        called.append(url)
        raise AssertionError("should not be called")

    monkeypatch.setattr("requests.post", fake_post)

    notifier = Notifier()
    notifier.notify_error("Something went wrong")
    assert called == []
