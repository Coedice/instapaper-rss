from collections import OrderedDict

import yaml

FIELD_ORDER = [
    "url",
    "description",
    "summarise",
    "whitelist_regex",
    "blacklist_regex",
    "allowed_languages",
]

yaml.add_representer(
    OrderedDict,
    lambda dumper, data: dumper.represent_mapping(
        "tag:yaml.org,2002:map", data.items()
    ),
)


def feed_sort_key(feed) -> str:
    key = feed["url"]
    key = key.replace("https://", "")
    key = key.replace("http://", "")
    key = key.replace("www.", "")
    key = key.lower()
    return key


def source_sort_key(source) -> str:
    return feed_sort_key(source["feeds"][0])


# Get categories
with open("config/sources.yml", "r") as sources_file:
    categories = yaml.safe_load(sources_file)

# Sort sources in each category
for category in categories:
    for source in category["sources"]:
        source["feeds"].sort(key=feed_sort_key)

    category["sources"].sort(key=source_sort_key)

# Arrange fields within each source
for category in categories:
    if category["sources"] is None:
        continue

    for source in category["sources"]:
        for i, feed in enumerate(source["feeds"]):
            new_feed = OrderedDict()

            # Add fields in specified order
            for key in FIELD_ORDER:
                if key in feed:
                    new_feed[key] = feed[key]

            # Add remaining fields
            for key in feed:
                if key not in FIELD_ORDER:
                    new_feed[key] = feed[key]

            # Update feed
            source["feeds"][i] = new_feed

# Write categories
with open("config/sources.yml", "w") as sources_file:
    yaml.dump(categories, sources_file)
