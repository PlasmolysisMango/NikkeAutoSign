# app.py
import json
import logging
import os
import random
import traceback
from logging.handlers import RotatingFileHandler

from flask import Flask, request, jsonify

from blablalink_reader import BlablaLinkReader
from send import sc_send

app = Flask(__name__)

# 配置
UPLOAD_FOLDER = 'upload'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
COOKIES_PATH = "cookies.json"
app.config['COOKIES_PATH'] = COOKIES_PATH

_LOGGER = logging.getLogger(__name__)


# ✅ 统一响应格式函数
def make_response(success=True, message="操作成功", data=None):
    return jsonify({
        "success": success,
        "message": message,
        "data": data
    })


# ✅ 自定义业务异常
class ApiException(Exception):
    def __init__(self, message="请求失败", status_code=400):
        super().__init__()
        self.message = message
        self.status_code = status_code


# 🛡️ 全局异常处理器

@app.errorhandler(ApiException)
def handle_api_exception(e):
    _LOGGER.warning(f"ApiException: {e.message}")
    return make_response(success=False, message=e.message), e.status_code


@app.errorhandler(404)
def handle_not_found(e):
    return make_response(success=False, message="接口未找到"), 404


@app.errorhandler(405)
def handle_method_not_allowed(e):
    return make_response(success=False, message="请求方法不被允许"), 405


@app.errorhandler(500)
def handle_internal_error(e):
    # 记录完整堆栈
    _LOGGER.error(f"InternalServerError: {str(e)}\n{traceback.format_exc()}")
    return make_response(success=False, message="服务器内部错误"), 500


# 捕获所有未处理的异常（包括 ValueError, FileNotFoundError 等）
@app.errorhandler(Exception)
def handle_unexpected_error(e):
    _LOGGER.error(f"UnexpectedError: {str(e)}\n{traceback.format_exc()}")
    return make_response(success=False, message="操作失败"), 500


def get_upload_cookies_path():
    return os.path.join(app.config['UPLOAD_FOLDER'], app.config['COOKIES_PATH'])


# ✅ 接口1：上传 Cookies
@app.route('/upload_cookies', methods=['POST'])
def upload_cookies():
    if 'file' in request.files:
        file = request.files['file']
        if not file.filename:
            raise ApiException("未选择文件")

        if not file.filename.endswith('.json'):
            raise ApiException("仅支持 .json 文件")

        filepath = get_upload_cookies_path()
        file.save(str(filepath))
        return make_response(message="Cookies 文件上传成功", data={"path": filepath})

    if request.is_json:
        data = request.get_json()
        if not isinstance(data, dict):
            raise ApiException("JSON 数据必须是一个 Cookie 字典")

        filepath = get_upload_cookies_path()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return make_response(message="Cookies JSON 数据保存成功", data={"path": filepath})

    raise ApiException("请上传 JSON 文件或发送 JSON 字典")


# ✅ 接口2：执行签到
@app.route('/sign', methods=['POST'])
def sign():
    filepath = get_upload_cookies_path()
    if not os.path.exists(filepath):
        raise ApiException("未找到 cookies 文件，请先上传")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
    except json.JSONDecodeError as e:
        raise ApiException(f"cookies 文件格式错误，JSON 解析失败: {str(e)}")
    except Exception as e:
        raise ApiException(f"读取 cookies 文件时发生错误: {str(e)}")

    if not isinstance(cookies, (dict, list)):
        raise ApiException("cookies 文件内容必须是对象或数组")

    reader = BlablaLinkReader(cookies=cookies)
    reader.init_session()

    # 签到
    _LOGGER.info("开始签到")
    err_list = []
    try:
        ret = reader.check_in()
        _LOGGER.info(f"签到成功: {ret}")
    except Exception as e:
        err_list.append(f"每日签到任务失败: {str(e)}")

    # 随机选择帖子并点赞
    _LOGGER.info("开始阅读并点赞")
    try:
        want_like_num = random.randint(6, 8)
        unliked_list, next_cursor = reader.list_post(want=20, filter_is_liked=False)
        to_read_list = random.choices(unliked_list, k=want_like_num)
    except Exception as e:
        err_list.append(f"获取帖子失败: {str(e)}")
    else:
        for uuid, title, is_liked in to_read_list:
            try:
                ret = reader.read_post(uuid)
                _LOGGER.info(f"阅读帖子成功, title={title}, data={ret}")
                reader.like_post(uuid)
                _LOGGER.info(f"点赞帖子成功, title={title}, data={ret}")
            except Exception as e:
                err_list.append(f"阅读/点赞帖子失败: {str(e)}")

    _LOGGER.info(f"任务完成，开始检查积分任务状态")
    message_list = []
    try:
        reader.check_task_finished()
        _LOGGER.info(f"积分任务状态已完成")
        if err_list:
            _LOGGER.info(f"积分任务已完成，清空错误列表: {err_list}")
            message_list.append(f"积分任务已完成，错误列表: {err_list}")
            err_list = []
    except Exception as e:
        err_list.append(f"检查积分任务状态失败: {str(e)}")

    # 发送通知
    if err_list:
        try:
            err_msg = "\n\n".join(err_list)
            sc_send(title="[Nikke自动签到]签到失败！", message=f"签到失败:\n\n {err_msg}")
        except Exception as e:
            err_list.append(f"发送通知失败: {str(e)}")
        raise ApiException(f"签到失败: {err_list}")

    # 展示当前总积分
    _LOGGER.info(f"总积分获取")
    try:
        total_reward = reader.get_total_reward()
        message_list.append(f"总积分: {total_reward}")
    except Exception as e:
        _LOGGER.error(f"总积分获取失败: {str(e)}")
        message_list.append(f"总积分获取失败: {str(e)}")
    message = "签到成功！\n\n" + "\n\n".join(message_list)
    try:
        sc_send(title="[Nikke自动签到]成功！", message=message)
    except Exception as e:
        _LOGGER.error(f"发送通知失败: {str(e)}")
    return make_response(message="签到成功")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[
                            logging.StreamHandler(),
                            RotatingFileHandler(
                                'app.log',
                                maxBytes=10 * 1024 * 1024,  # 10MB
                                backupCount=5,  # 保留 5 个备份文件
                                encoding='utf-8'
                            )
                        ])
    app.run(host='0.0.0.0', port=5000, debug=False)  # 注意：生产环境务必 debug=False
