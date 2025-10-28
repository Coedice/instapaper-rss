# Instapaper RSS

Subscribe to RSS/Atom feeds and save items to [Instapaper](https://www.instapaper.com/).

## Quick start

1. Add your [Instapaper](https://www.instapaper.com/u) cookies to `config/cookies.yml`
2. Configure the RSS feeds you would like to subscribe to in `config/sources.yml`
3. Run command `make run`

## Sources YAML

In the `config/sources.yml` the following attributes may be used:

| Attribute | Description | Required |
| - | - | - |
| `url` | The URL to the RSS file, or a webpage which has an RSS file in it | Required |
| `description` | A description of what the source is | Optional |
| `summarise` | Summarise the content of RSS items with [Perplexity](https://www.perplexity.ai/) | Optional |
| `blacklist_regex` | A regex pattern to match against the title of the RSS item. If it matches, the item will not be saved | Optional |
| `whitelist_regex` | A regex pattern to match against the title of the RSS item. If it matches, the item will be saved | Optional |
| `allowed_languages` | A list of allowable languages for the RSS item's title to be writen in, in order to be saved | Optional |

## Settings

The application reads configuration values from `config/settings.yml`. The following keys are supported:

- `testing_mode`: When true the program will not actually save entries to Instapaper; it will only print what it would do. Useful for development and testing.
- `frequent_feed_threshold`: If a feed has more than this number of entries in the last month it will be treated as _frequent_ and the feed will be processed every time.
- `max_skips`: Controls many runs should occur before _infrequent_ feeds are processed (defined by `frequent_feed_threshold`). Infrequent feed processing is staggered by URL hash.

## Setting up Auto-run

A reccomended way to use this tool:

1. Set up an internet-connected always-on computer (such as a Raspberry Pi)
2. Install `uv` on that computer
3. Update `REMOTE_LOGIN_IDENTIFIER` and `REMOTE_PATH` in the `Makefile` to your choice
4. Run command `make deploy`
5. Add crontab `0 6-21 * * * cd /home/pi/Documents/instapaper-rss && PATH="/home/pi/.local/bin:$PATH" make run > /home/pi/log.txt 2>&1`
