import json
import os

COOKIES_FILE_PATH = "cookies.json"
UPLOAD_COOKIES_FILE_PATH = "upload/cookies.json"
ACCOUNT_FILE_PATH = "account.json"
SEND_KEY_FILE_PATH = "send_key.json"


def parse_headers(header_str):
    headers = {}
    for line in header_str.splitlines():
        if not line.strip():
            continue
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()  # ← 关键：value.strip()
    return headers


def load_cookies():
    if os.path.exists(COOKIES_FILE_PATH):
        with open(COOKIES_FILE_PATH, "r") as f:
            cookies = json.load(f)
    else:
        with open(UPLOAD_COOKIES_FILE_PATH, "r") as f:
            cookies = json.load(f)

    return cookies
