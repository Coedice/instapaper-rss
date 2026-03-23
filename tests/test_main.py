from datetime import time

import pytest

import main
from PickleDictionary import PickleDictionary

ALL_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def test_is_time_in_ranges_accepts_overnight_window():
    assert main.is_time_in_ranges(
        [{"days": ALL_DAYS, "start": "22:00", "end": "02:00"}],
        current_time=time(23, 30),
    )
    assert main.is_time_in_ranges(
        [{"days": ALL_DAYS, "start": "22:00", "end": "02:00"}],
        current_time=time(1, 15),
    )
    assert not main.is_time_in_ranges(
        [{"days": ALL_DAYS, "start": "22:00", "end": "02:00"}],
        current_time=time(12, 0),
    )


def test_should_process_feed_skips_outside_time_range(temp_pickle_files):
    feed_scans = PickleDictionary(temp_pickle_files())
    priorities = {
        "normal": {
            "check_every": 1,
            "time_ranges": [{"days": ALL_DAYS, "start": "09:00", "end": "10:00"}],
        }
    }

    should_process, reason = main.should_process_feed(
        {"url": "https://example.com/feed.xml"},
        feed_scans,
        priorities,
        "normal",
        current_time=time(8, 0),
    )

    assert not should_process
    assert reason == "outside normal priority time ranges"
    assert "https://example.com/feed.xml" not in feed_scans


def test_should_process_feed_uses_priority_schedule(temp_pickle_files):
    feed_scans = PickleDictionary(temp_pickle_files())
    priorities = {
        "normal": {
            "check_every": 3,
            "time_ranges": [{"days": ALL_DAYS, "start": "00:00", "end": "23:59"}],
        }
    }
    feed_item = {"url": "https://example.com/feed.xml"}
    offset = main.url_mod(feed_item["url"], 3)

    for scan_count in range(offset):
        feed_scans[feed_item["url"]] = scan_count
        should_process, reason = main.should_process_feed(
            feed_item,
            feed_scans,
            priorities,
            "normal",
            current_time=time(12, 0),
        )
        assert not should_process
        assert reason == "normal priority: skipping this cycle"

    feed_scans[feed_item["url"]] = offset
    should_process, reason = main.should_process_feed(
        feed_item,
        feed_scans,
        priorities,
        "normal",
        current_time=time(12, 0),
    )

    assert should_process
    assert reason == "normal"


def test_should_process_feed_rejects_unknown_priority(temp_pickle_files):
    feed_scans = PickleDictionary(temp_pickle_files())

    with pytest.raises(ValueError, match="Priority 'urgent'.*not defined"):
        main.should_process_feed(
            {"url": "https://example.com/feed.xml", "priority": "urgent"},
            feed_scans,
            {"normal": {"check_every": 1}},
            "normal",
            current_time=time(12, 0),
        )


def test_is_time_in_ranges_honors_days_filter():
    time_ranges = [
        {
            "days": ["mon", "tue", "wed", "thu", "fri"],
            "start": "16:30",
            "end": "22:59",
        },
        {"days": ["sat", "sun"], "start": "00:00", "end": "23:59"},
    ]

    assert not main.is_time_in_ranges(
        time_ranges, current_time=time(12, 0), current_weekday=2
    )
    assert main.is_time_in_ranges(
        time_ranges, current_time=time(18, 0), current_weekday=2
    )
    assert main.is_time_in_ranges(
        time_ranges, current_time=time(12, 0), current_weekday=5
    )
