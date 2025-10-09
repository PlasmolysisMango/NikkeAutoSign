import logging
import random
import time

import requests
from requests import JSONDecodeError

from common import load_cookies, parse_headers

_LOGGER = logging.getLogger(__name__)

main_h = '''
Host: api.blablalink.com
Connection: keep-alive
Content-Length: 100
sec-ch-ua-platform: "Windows"
x-channel-type: 2
sec-ch-ua: "Chromium";v="140", "Not=A?Brand";v="24", "Microsoft Edge";v="140"
sec-ch-ua-mobile: ?0
x-language: zh-TW
x-common-params: {"game_id":"16","area_id":"global","source":"pc_web","intl_game_id":"29080","language":"zh-TW","env":"prod","data_statistics_scene":"outer","data_statistics_page_id":"https://www.blablalink.com/","data_statistics_client_type":"pc_web","data_statistics_lang":"zh-TW"}
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0
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

mission_h = '''
Host: api.blablalink.com
Connection: keep-alive
Pragma: no-cache
Cache-Control: no-cache
sec-ch-ua-platform: "Windows"
x-channel-type: 2
sec-ch-ua: "Chromium";v="140", "Not=A?Brand";v="24", "Microsoft Edge";v="140"
sec-ch-ua-mobile: ?0
x-language: zh-TW
x-common-params: {"game_id":"16","area_id":"global","source":"pc_web","intl_game_id":"29080","language":"zh-TW","env":"prod","data_statistics_scene":"outer","data_statistics_page_id":"https://www.blablalink.com/mission","data_statistics_client_type":"pc_web","data_statistics_lang":"zh-TW"}
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0
Accept: application/json, text/plain, */*
DNT: 1
Origin: https://www.blablalink.com
Sec-Fetch-Site: same-site
Sec-Fetch-Mode: cors
Sec-Fetch-Dest: empty
Referer: https://www.blablalink.com/
Accept-Encoding: gzip, deflate, br, zstd
Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7
'''


class BlablaLinkReader:
    def __init__(self, cookies=None):
        self.cookies = cookies or load_cookies()
        self.host = "https://api.blablalink.com"
        self.headers = parse_headers(main_h)
        self.mission_headers = parse_headers(mission_h)
        self.session: requests.Session | None = None
        self.mission_session: requests.Session | None = None

    def init_session(self):
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.cookies.update(self.cookies)

        self.mission_session = requests.Session()
        self.mission_session.headers.update(self.mission_headers)
        self.mission_session.cookies.update(self.cookies)

        _LOGGER.info(f"初始化session成功")

    @staticmethod
    def _safe_json_response(resp: requests.Response):
        try:
            return resp.json()
        except JSONDecodeError:
            return resp.text

    def session_post(self, *args, session, random_sleep=True, **kwargs):
        _LOGGER.info(f"POST 请求: {args}, {kwargs}")
        ret: requests.Response = session.post(*args, **kwargs)
        ret.raise_for_status()
        if random_sleep:
            time.sleep(random.uniform(0.2, 0.8))
        _LOGGER.info(f"POST 结果: {self._safe_json_response(ret)}")
        return ret

    def api_post(self, url, json_data, message="请求", session=None):
        if not session:
            session = self.session
        ret: requests.Response = self.session_post(url, session=session, json=json_data)
        json_ret = ret.json()
        if json_ret.get("code") != 0:
            raise Exception(f"{message}失败: {json_ret}")
        return json_ret

    def session_get(self, *args, session, random_sleep=True, **kwargs):
        _LOGGER.info(f"GET 请求: {args}, {kwargs}")
        ret: requests.Response = session.get(*args, **kwargs)
        ret.raise_for_status()
        if random_sleep:
            time.sleep(random.uniform(0.2, 0.8))
        _LOGGER.info(f"GET 结果: {self._safe_json_response(ret)}")
        return ret

    def api_get(self, url, params=None, message="请求", session=None):
        if not session:
            session = self.session
        ret: requests.Response = self.session_get(url, session=session, params=params)
        json_ret = ret.json()
        if json_ret.get("code") != 0:
            raise Exception(f"{message}失败: {json_ret}")
        return json_ret

    def list_post(self, want=20, filter_is_liked=None, start_cursor=None, max_page=10):
        url = self.host + "/api/ugc/direct/standalonesite/Dynamics/GetPostList"
        next_cursor = None or start_cursor
        post_set = set()
        page = 0
        for i in range(max_page):
            # json_data = {"search_type": 0, "plate_id": 46, "plate_unique_id": "recommend", "order_by": 2, "limit": "10",
            #              "regions": []}
            limit_num = 10
            json_data = {
                "search_type": 0,
                "plate_id": 46,
                "plate_unique_id": "recommend",
                "order_by": 2,
                "limit": str(limit_num),
                "regions": ["en", "ja", "ko", "zh-TW"]
            }
            if next_cursor:
                # "nextPageCursor": "1494c8c443fcf906792fdf4c76854bf1fb9a1cc7764a7326d7de759e991a6e1e",
                json_data["nextPageCursor"] = next_cursor
            elif page > 0:
                raise Exception("nextPageCursor is None")
            json_ret = self.api_post(url, json_data, message=f"获取列表第{page + 1}页")
            next_cursor = json_ret["data"]["page_info"]["next_page_cursor"]
            for post_data in json_ret["data"].get("list", []):
                uuid, title, is_liked = self._parse_post(post_data)
                if filter_is_liked is not None and filter_is_liked != is_liked:
                    continue
                post_set.add((uuid, title, is_liked))
            if len(post_set) >= want:
                break
        if len(post_set) < want:
            raise Exception(f"获取列表失败, 结果数量不足, want={want}, get={len(post_set)}, max_page={max_page}")
        _LOGGER.info(f"获取列表成功，{post_set}")
        return list(post_set), next_cursor

    @staticmethod
    def _is_post_liked(post_data):
        my_upvote = post_data.get("my_upvote", {})
        if my_upvote:
            return bool(my_upvote["is_star"])
        return False

    def _parse_post(self, post_data):
        uuid = post_data["post_uuid"]
        title = post_data["title"]
        is_liked = self._is_post_liked(post_data)
        return uuid, title, is_liked

    def like_post(self, uuid):
        url = self.host + "/api/ugc/proxy/standalonesite/Dynamics/PostStar"
        json_data = {
            "post_uuid": str(uuid),
            "type": 1,
            "like_type": 1
        }
        json_ret = self.api_post(url, json_data, message="点赞帖子")
        _LOGGER.info(f"点赞成功: {json_ret}")
        return json_ret

    def read_post(self, uuid):
        url = self.host + "/api/ugc/direct/standalonesite/Dynamics/GetPost"
        # {"post_uuid":"6438288651724120935","browse_post":2,"original_content":0}
        json_data = {
            "post_uuid": str(uuid),
            "browse_post": 2,
            "original_content": 0
        }
        json_ret = self.api_post(url, json_data, message="阅读帖子")
        _LOGGER.info(f"获取帖子成功: {json_ret}")
        return json_ret

    def check_in(self):
        url = self.host + "/api/lip/proxy/lipass/Points/DailyCheckIn"
        # {"task_id": "15"}
        json_data = {"task_id": "15"}
        json_ret = self.api_post(url, json_data, message="签到")
        _LOGGER.info(f"签到成功: {json_ret}")
        return json_ret

    def check_task_finished(self):
        url = self.host + "/api/lip/proxy/lipass/Points/GetTaskListWithStatusV2"
        # ?get_top=false&intl_game_id=29080
        params = {
            "get_top": False,
            "intl_game_id": 29080
        }
        json_ret = self.api_get(url, params=params, message="获取任务状态", session=self.mission_session)
        _LOGGER.info(f"获取任务状态成功: {json_ret}")
        task_status_list = []
        for task_data in json_ret["data"].get("tasks", []):
            task_name = task_data["task_name"]
            task_status = task_data["reward_infos"][0]["is_completed"]
            task_status_list.append((task_name, task_status))
        _LOGGER.info(f"任务状态: {task_status_list}")
        unfinished_task_list = [task_name for task_name, task_status in task_status_list if not task_status]
        if unfinished_task_list:
            raise Exception(f"任务未完成: {unfinished_task_list}")
        return task_status_list

    def get_total_reward(self):
        url = self.host + "/api/lip/proxy/lipass/Points/GetUserTotalPoints"
        json_ret = self.api_get(url, message="获取总积分", session=self.mission_session)
        _LOGGER.info(f"获取总积分成功: {json_ret}")
        return json_ret["data"]["total_points"]


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[logging.StreamHandler()])
    reader = BlablaLinkReader()
    reader.init_session()

    reader.check_task_finished()
    reader.get_total_reward()
