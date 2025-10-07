import json
import logging
import os.path

import requests

from common import COOKIES_FILE_PATH, UPLOAD_COOKIES_FILE_PATH

_LOGGER = logging.getLogger(__name__)

h = '''
Host: api.blablalink.com
Connection: keep-alive
Content-Length: 16
sec-ch-ua-platform: "Windows"
x-channel-type: 2
sec-ch-ua: "Not;A=Brand";v="99", "Microsoft Edge";v="139", "Chromium";v="139"
sec-ch-ua-mobile: ?0
x-language: zh-TW
x-common-params: {"game_id":"16","area_id":"global","source":"pc_web","intl_game_id":"29080","language":"zh-TW","env":"prod","data_statistics_scene":"outer","data_statistics_page_id":"https://www.blablalink.com/","data_statistics_client_type":"pc_web","data_statistics_lang":"zh-TW"}
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0
Accept: application/json, text/plain, */*
DNT: 1
Content-Type: application/json
Origin: https://www.blablalink.com
Sec-Fetch-Site: same-site
Sec-Fetch-Mode: cors
Sec-Fetch-Dest: empty
Referer: https://www.blablalink.com/
Accept-Encoding: gzip, deflate, br, zstd
Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7
'''


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


def check_in(cookies=None):
    url = "https://api.blablalink.com/api/lip/proxy/lipass/Points/DailyCheckIn"
    headers = parse_headers(h)
    _LOGGER.info(f"获取到headers: {headers}")
    cookies = cookies or load_cookies()
    _LOGGER.info(f"获取到cookies: {cookies}")
    data = {"task_id": "15"}
    ret = requests.post(url, headers=headers, cookies=cookies, json=data)
    ret.raise_for_status()
    _LOGGER.info("结果: " + ret.text)
    '''
    2025-10-06 00:25:56,600 - INFO - 结果: {"code":0,"code_type":0,"msg":"ok","data":{"status":1},"seq":"6e080ee0-7341-4a15-ae24-f3c93af7a648"}
    2025-10-06 00:26:48,883 - INFO - 结果: {"code":1001009,"code_type":1,"msg":"system error","data":null,"seq":"229ce4aa-d29e-4045-801f-13cfb1958f16"}
    '''
    json_ret = ret.json()
    if json_ret.get("code") != 0:
        _LOGGER.error(f"签到失败: {json_ret}")
        raise Exception(f"签到失败: {json_ret}")
    return json_ret


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[logging.StreamHandler()])
    check_in()
