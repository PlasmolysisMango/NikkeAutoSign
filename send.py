import json
import logging
import re

import requests

from common import SEND_KEY_FILE_PATH

_LOGGER = logging.getLogger(__name__)

def sc_send(title, message='', options=None):
    with open(SEND_KEY_FILE_PATH, "r") as f:
        json_dic = json.load(f)
    send_key = json_dic["SEND_KEY"]

    if options is None:
        options = {}
    # 判断 sendkey 是否以 'sctp' 开头，并提取数字构造 URL
    if send_key.startswith('sctp'):
        match = re.match(r'sctp(\d+)t', send_key)
        if match:
            num = match.group(1)
            url = f'https://{num}.push.ft07.com/send/{send_key}.send'
        else:
            raise ValueError('Invalid sendkey format for sctp')
    else:
        url = f'https://sctapi.ftqq.com/{send_key}.send'
    params = {
        'title': title,
        'desp': message,
        **options
    }
    headers = {
        'Content-Type': 'application/json;charset=utf-8'
    }
    response = requests.post(url, json=params, headers=headers)
    result = response.json()
    return result


if __name__ == '__main__':
    sc_send('测试标题', '测试内容')
