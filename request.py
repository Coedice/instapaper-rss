import requests


def request(url: str, headers: dict = None, cookies: dict = None) -> str:
    try:
        return requests.get(url, headers=headers, cookies=cookies)
    except Exception as e:
        print(f"Got error {e} on attempt for url {url}")
        raise e
