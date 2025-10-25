from urllib.parse import urlparse

import yaml

VALID_KEYS = [
    "url",
    "description",
    "summarise",
    "blacklist_regex",
    "whitelist_regex",
    "allowed_languages",
]


def is_url_valid_syntax(url: str) -> bool:
    parsed = urlparse(url)
    return all([parsed.scheme in ("http", "https"), parsed.netloc])


with open("config/sources.yml", "r") as sources_file:
    catagories = yaml.safe_load(sources_file)

all_urls = set()
for category in catagories:
    for source in category["sources"]:
        for feed in source["feeds"]:
            url = feed["url"]

            # Check for duplicates
            assert url not in all_urls, f"Duplicate URL: {url}"
            all_urls.add(url)

            # Check URL is valid
            assert is_url_valid_syntax(url), f"Invalid URL: {url}"

            # Check keys are valid
            for key in feed:
                if key not in VALID_KEYS:
                    raise KeyError(f'Invalid key "{key}" for feed {url}')
