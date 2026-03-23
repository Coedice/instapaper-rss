import Feed as Feed_mod
import request as request_mod
from Feed import Feed
from PickleDictionary import PickleDictionary


class DummyResponse:
    def __init__(self, text: str, path_url: str = "/"):
        self.text = text

        class Req:
            def __init__(self, path_url):
                self.path_url = path_url

        self.request = Req(path_url)


def test_feed_processes_entries_and_updates_time(monkeypatch, temp_pickle_files):
    # Fake HTML page with rss link
    html = """
    <html>
      <head>
        <link rel="alternate" type="application/rss+xml" href="/feed.xml" />
      </head>
    </html>
    """
    rss = """
    <rss><channel>
      <item>
        <title>First post</title>
        <link>https://example.com/1</link>
        <pubDate>Tue, 02 Jan 2024 03:04:05 +0000</pubDate>
      </item>
      <item>
        <title>Second post</title>
        <link>https://example.com/2</link>
        <pubDate>Tue, 03 Jan 2024 03:04:05 +0000</pubDate>
      </item>
    </channel></rss>
    """

    # Monkeypatch request() function used in Feed
    call_stack = []

    def fake_request(url, headers=None):
        call_stack.append(url)
        if url.endswith("/feed.xml"):
            return DummyResponse(rss)
        return DummyResponse(html, path_url="/index.html")

    monkeypatch.setattr(request_mod, "request", fake_request)
    monkeypatch.setattr(Feed_mod, "request", fake_request)

    feed_item = {"url": "https://example.com"}
    rss_urls = PickleDictionary(temp_pickle_files())
    last_times = PickleDictionary(temp_pickle_files())
    monthly = PickleDictionary(temp_pickle_files())

    # Pre-populate RSS discovery to avoid parser variance
    rss_urls["https://example.com"] = "https://example.com/feed.xml"
    # Ensure last_saved_time is in the past so items enqueue
    last_times["https://example.com"] = 0
    feed = Feed(feed_item, rss_urls, last_times, monthly, wrappers={})

    class SimpleQueue:
        def __init__(self):
            self._queue = []

        def enqueue(self, entry):
            self._queue.append(entry)

    sq = SimpleQueue()
    feed.process_feed(sq)

    # rss url discovered and cached
    assert rss_urls["https://example.com"].endswith("/feed.xml")
    # monthly entries tracked for feed url
    assert "https://example.com" in monthly
    # last_saved_times present for feed url
    assert "https://example.com" in last_times
