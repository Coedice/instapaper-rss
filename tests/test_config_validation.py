from urllib.parse import urlparse

import yaml

VALID_KEYS = {
    "url",
    "description",
    "priority",
    "wrappers",
    "blacklist_regex",
    "whitelist_regex",
    "allowed_languages",
}


def is_url_valid_syntax(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def test_wrappers_yaml_is_mapping():
    with open("config/wrappers.yml", "r") as f:
        wrappers = yaml.safe_load(f)
    assert isinstance(wrappers, dict), "config/wrappers.yml must be a mapping"


def test_sources_yaml_structure_and_constraints():
    with open("config/sources.yml", "r") as f:
        categories = yaml.safe_load(f)
    with open("config/wrappers.yml", "r") as f:
        wrappers = yaml.safe_load(f)
    with open("config/settings.yml", "r") as f:
        settings = yaml.safe_load(f)
    with open("config/priorities.yml", "r") as f:
        priorities = yaml.safe_load(f)

    assert isinstance(categories, list), "config/sources.yml must be a list"
    assert isinstance(wrappers, dict), "config/wrappers.yml must be a mapping"
    assert isinstance(settings, dict), "config/settings.yml must be a mapping"
    assert isinstance(priorities, dict), "config/priorities.yml must be a mapping"
    assert settings.get("default_priority") in priorities, (
        "default_priority in config/settings.yml must exist in config/priorities.yml"
    )

    for priority_name, rules in priorities.items():
        assert isinstance(rules, dict), (
            f"Priority '{priority_name}' in config/priorities.yml must be a mapping"
        )
        assert isinstance(rules.get("check_every"), int), (
            f"Priority '{priority_name}' must define an integer check_every"
        )
        assert rules["check_every"] > 0, (
            f"Priority '{priority_name}' check_every must be positive"
        )

        if "time_ranges" in rules:
            assert isinstance(rules["time_ranges"], list), (
                f"Priority '{priority_name}' time_ranges must be a list"
            )
            for time_range in rules["time_ranges"]:
                assert isinstance(time_range, dict), (
                    f"Priority '{priority_name}' time_ranges must contain mappings"
                )
                assert "start" in time_range and "end" in time_range, (
                    f"Priority '{priority_name}' time ranges must define start and end"
                )
                assert isinstance(time_range["start"], str), (
                    f"Priority '{priority_name}' time range start must be a string"
                )
                assert isinstance(time_range["end"], str), (
                    f"Priority '{priority_name}' time range end must be a string"
                )

                assert "days" in time_range, (
                    f"Priority '{priority_name}' time ranges must define days"
                )
                assert isinstance(time_range["days"], list), (
                    f"Priority '{priority_name}' time range days must be a list"
                )
                assert len(time_range["days"]) > 0, (
                    f"Priority '{priority_name}' time range days must not be empty"
                )
                for day_name in time_range["days"]:
                    assert isinstance(day_name, str), (
                        f"Priority '{priority_name}' time range days must contain strings"
                    )

    seen_urls = set()
    for category in categories:
        assert "sources" in category and isinstance(category["sources"], list)
        for source in category["sources"]:
            assert "feeds" in source and isinstance(source["feeds"], list)
            for feed in source["feeds"]:
                url = feed["url"]

                # Unique URLs
                assert url not in seen_urls, f"Duplicate URL: {url}"
                seen_urls.add(url)

                # Valid URL syntax
                assert is_url_valid_syntax(url), f"Invalid URL: {url}"

                # Valid keys only
                for key in feed:
                    assert key in VALID_KEYS, f"Invalid key '{key}' for feed {url}"

                # Wrappers exist and are a list
                if "wrappers" in feed:
                    names = feed["wrappers"]
                    assert isinstance(names, list), (
                        f"wrappers must be a list for feed {url}"
                    )
                    for name in names:
                        assert name in wrappers, (
                            f"Wrapper '{name}' is not defined in config/wrappers.yml"
                        )

                if "priority" in feed:
                    assert isinstance(feed["priority"], str), (
                        f"priority must be a string for feed {url}"
                    )
                    assert feed["priority"] in priorities, (
                        f"Priority '{feed['priority']}' is not defined in config/priorities.yml"
                    )
