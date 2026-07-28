import requests


def request(
    url: str,
    headers: dict = None,
    cookies: dict = None,
    method: str = "GET",
    data: dict = None,
) -> str:
    try:
        if method == "POST":
            return requests.post(url, headers=headers, cookies=cookies, json=data)
        return requests.get(url, headers=headers, cookies=cookies)
    except Exception as e:
        print(f"Got error {e} on attempt for url {url}")
        raise e
